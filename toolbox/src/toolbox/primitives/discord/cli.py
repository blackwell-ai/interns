"""discord primitive — read recent messages from channels via the Discord API.

Uses the account token (`TOOLBOX_TOKEN_DISCORD`). NOTE: driving a personal
Discord account this way is a self-bot and violates Discord's Terms of Service
(account-ban risk). It exists only because the operator explicitly opted in
(see brain/decisions/2026-06-15-researcher-daily-digest.md). Read-only: the only
call is GET /channels/<id>/messages.

Output rows match the `extract` item shape so Discord folds into the same
items.jsonl the digest filters: {source, label, title, url, text, author, ts}.
"""

from __future__ import annotations

import re
import sys
import time

import httpx
import typer

from toolbox.core import events, io

app = typer.Typer(no_args_is_help=True)

_API = "https://discord.com/api/v9"
_UA = "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0"
_MENTION = re.compile(r"<(?:@[!&]?|#)\d+>")   # <@id> <@!id> <@&role> <#chan>
_EMOJI = re.compile(r"<a?:(\w+):\d+>")        # <:name:id> / <a:name:id>


@app.callback()
def _group():
    """discord primitive."""


def _clean(text: str) -> str:
    text = _EMOJI.sub(r":\1:", text or "")
    text = _MENTION.sub("", text)
    return " ".join(text.split())


def message_to_item(m: dict, label: str, guild_id: str, min_chars: int = 15) -> dict | None:
    """Pure: one API message -> an item, or None to drop it.

    Drops bot messages and one-line chatter; pulls embed title/description when
    the message body is just a link. Exported for tests.
    """
    if (m.get("author") or {}).get("bot"):
        return None
    content = _clean(m.get("content") or "")
    if len(content) < min_chars:
        for e in m.get("embeds") or []:
            extra = _clean((e.get("title") or "") + " " + (e.get("description") or ""))
            if extra:
                content = (content + " " + extra).strip()
                break
    if len(content) < min_chars:
        return None
    author = (m.get("author") or {})
    cid = m.get("channel_id") or ""
    return {
        "source": label,
        "label": label,
        "title": content[:80],
        "url": f"https://discord.com/channels/{guild_id}/{cid}/{m.get('id', '')}",
        "link": "",
        "text": content[:4000],
        "author": author.get("global_name") or author.get("username") or "",
        "score": None,
        "comments": None,
        "ts": m.get("timestamp"),
    }


@app.command()
def fetch(
    in_: str = typer.Option(..., "--in", help="CSV with guild_id, channel_id, label columns"),
    out: str = typer.Option(..., "--out", help="items.jsonl (one record per kept message)"),
    limit: int = typer.Option(50, "--limit", help="messages per channel"),
    min_chars: int = typer.Option(15, "--min-chars", help="drop messages shorter than this"),
    append: bool = typer.Option(False, "--append", help="append to out instead of overwriting"),
):
    import csv as _csv
    from pathlib import Path

    from toolbox.core import auth

    p = Path(out)
    # A self-bot token can be revoked at any time; a missing/dead token must not
    # kill the whole digest. Warn and contribute nothing instead.
    try:
        token = auth.get_token("discord")
    except Exception as e:
        if not append and p.exists():
            p.unlink()
        events.emit("discord.skipped", reason=str(e)[:120])
        typer.echo(f"discord.fetch: skipped (no usable token: {str(e)[:80]})")
        return

    with Path(in_).open(encoding="utf-8", newline="") as f:
        rows = [r for r in _csv.DictReader(f) if (r.get("channel_id") or "").strip()]

    if not append and p.exists():
        p.unlink()

    headers = {"Authorization": token, "User-Agent": _UA}
    kept = total = 0
    errors: list[str] = []
    with httpx.Client(headers=headers, timeout=30) as client:
        for r in rows:
            cid = r["channel_id"].strip()
            gid = (r.get("guild_id") or "").strip()
            label = (r.get("label") or f"Discord {cid}").strip()
            url = f"{_API}/channels/{cid}/messages?limit={limit}"
            try:
                for _ in range(4):  # ride out rate limits
                    resp = client.get(url)
                    if resp.status_code == 429:
                        time.sleep(float(resp.headers.get("retry-after", 2)) + 0.5)
                        continue
                    resp.raise_for_status()
                    break
                msgs = resp.json()
            except Exception as e:  # never let one channel crash the sweep
                errors.append(f"{label}: {str(e)[:120]}")
                continue
            if not isinstance(msgs, list):
                errors.append(f"{label}: unexpected response")
                continue
            for m in msgs:
                total += 1
                item = message_to_item(m, label, gid, min_chars=min_chars)
                if item:
                    io.append_jsonl(out, item)
                    kept += 1
            time.sleep(0.4)  # be gentle on the API

    events.emit("discord.fetched", channels=len(rows), messages=total, kept=kept, errors=len(errors))
    msg = f"discord.fetch: {kept}/{total} messages kept from {len(rows)} channels"
    if errors:
        msg += f" ({len(errors)} channel errors: {'; '.join(errors[:3])})"
    typer.echo(msg)


if __name__ == "__main__":
    sys.exit(app())
