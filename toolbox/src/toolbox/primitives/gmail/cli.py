"""gmail primitive — send mail, read replies/bounces.

The ledger check on send is THE one non-removable behavior (spec §5 rule 3):
claim → send → mark, with a local mirror appended the instant the provider
returns a message id so a crash between send and mark can never double-send
on resume (plan §7 item 1). See TOOL.md for the file contracts.
"""

from __future__ import annotations

import asyncio
import hashlib
import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import httpx
import typer
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from toolbox.core import auth, events, io, ledger, models
from toolbox.primitives.gmail import lib

app = typer.Typer(no_args_is_help=True)


@app.callback()
def _group():
    """gmail primitive."""


def _run_ctx() -> tuple[str, str, str]:
    return (
        os.environ.get("TOOLBOX_RUN_DIR", "."),
        os.environ.get("TOOLBOX_RUN_ID", ""),
        os.environ.get("TOOLBOX_SKILL", ""),
    )


_transient = retry(
    retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.TransportError)),
    wait=wait_exponential(multiplier=1, max=60),
    stop=stop_after_attempt(6),
    reraise=True,
)


@app.command()
def send(
    in_: str = typer.Option(..., "--in", help="outbox CSV: email,subject,body[,body_html,...]"),
    from_: str = typer.Option(..., "--from", help="From address (the connected Gmail account)"),
    from_name: str = typer.Option("", "--from-name"),
    reply_to: str = typer.Option("", "--reply-to"),
    cc: str = typer.Option("", "--cc", help="CC list (comma-separated) added to every send"),
    concurrency: int = typer.Option(8, "--concurrency"),
    allow_recontact: bool = typer.Option(False, "--allow-recontact",
                                         help="Deliberate follow-up sequences only. Logged loudly."),
    limit: int = typer.Option(0, "--limit", help="Send at most N rows (canary uses this)."),
    dry_run: bool = typer.Option(False, "--dry-run"),
):
    """Send every row of the outbox, exactly once per recipient, ever."""
    run_dir, run_id, skill = _run_ctx()
    rows = io.read_csv(in_, models.OutboxRow)
    if limit:
        rows = rows[:limit]

    if dry_run:
        asyncio.run(_dry_run(rows, run_dir))
        return

    sent_already = ledger.mirror_sent(run_dir)
    counts = asyncio.run(_send_all(rows, run_dir, run_id, skill, from_, from_name, reply_to,
                                   cc, concurrency, allow_recontact, sent_already))
    events.emit("gmail.send.summary", **counts)
    typer.echo(f"gmail.send: {counts}")
    if counts["quota_aborted"]:
        typer.echo("Hit the provider's hard quota wall — run failed cleanly; resume later.", err=True)
        raise typer.Exit(1)


async def _dry_run(rows: list[models.OutboxRow], run_dir: str) -> None:
    led = ledger.Ledger(auth.session_token())
    out = []
    try:
        for r in rows:
            try:
                status = await led.check("email", r.email)
            except Exception:
                status = "unknown (ledger unreachable)"
            out.append({"email": r.email, "subject": r.subject, "body": r.body,
                        "ledger": status})
    finally:
        await led.aclose()
    io.write_json(Path(run_dir) / "dryrun" / "gmail.send.json", out)
    events.emit("gmail.send.dryrun", count=len(out))


async def _send_all(rows, run_dir, run_id, skill, from_, from_name, reply_to,
                    cc, concurrency, allow_recontact, sent_already) -> dict:
    token = auth.get_token("gmail")
    led = ledger.Ledger(auth.session_token())
    sem = asyncio.Semaphore(max(1, concurrency))
    counts = {"sent": 0, "skipped_ledger": 0, "suppressed": 0, "failed": 0,
              "resumed_skip": 0, "quota_aborted": 0}
    quota_hit = asyncio.Event()

    # Gmail's per-user send rate is ~2.5 messages/sec (250 quota units/sec at 100
    # units per send). Pace sends below that so a burst does not trip the 403
    # rate-limit wall; retry-with-backoff in classify_send_error is the safety net.
    rate = float(os.environ.get("GMAIL_SEND_RATE", "2"))
    min_interval = 1.0 / rate if rate > 0 else 0.0
    gate = {"next": 0.0}
    gate_lock = asyncio.Lock()

    async def pace() -> None:
        if min_interval <= 0:
            return
        async with gate_lock:
            now = time.monotonic()
            wait = gate["next"] - now
            if wait > 0:
                await asyncio.sleep(wait)
                now = time.monotonic()
            gate["next"] = max(now, gate["next"]) + min_interval

    @_transient
    async def do_send(client: httpx.AsyncClient, raw: str) -> dict:
        await pace()
        return await lib.send_raw(client, raw)

    async with httpx.AsyncClient(headers={"Authorization": f"Bearer {token}"}, timeout=60) as client:
        async def one(row: models.OutboxRow) -> None:
            if quota_hit.is_set():
                return
            recipient = ledger.canonical(row.email)
            if recipient in sent_already:
                counts["resumed_skip"] += 1
                return
            async with sem:
                if quota_hit.is_set():  # re-check: the wall may have hit while queued
                    return
                claim = led.force_claim if allow_recontact else led.claim
                result = await claim("email", recipient, skill=skill, run_id=run_id)
                if result == "suppressed":
                    counts["suppressed"] += 1
                    events.emit("claim.suppressed", recipient=recipient)
                    return
                if result != "claimed":
                    counts["skipped_ledger"] += 1
                    events.emit("claim.skipped", recipient=recipient)
                    return
                raw = lib.build_raw_message(
                    to=recipient, subject=row.subject, body=row.body,
                    from_address=from_, from_name=from_name, reply_to=reply_to,
                    cc=cc, body_html=getattr(row, "body_html", "") or "",
                )
                try:
                    resp = await do_send(client, raw)
                except lib.QuotaExceeded as e:
                    quota_hit.set()
                    counts["quota_aborted"] += 1
                    events.emit("send.quota_wall", level="error", detail=str(e)[:200])
                    return
                except (lib.PermanentSendError, httpx.HTTPError) as e:
                    counts["failed"] += 1
                    ledger.mirror_append(run_dir, "email", recipient, "failed", reason=str(e)[:200])
                    await led.mark_failed("email", recipient, reason=str(e)[:200])
                    events.emit("send.failed", level="warn", recipient=recipient, reason=str(e)[:200])
                    return
                # Mirror FIRST (local truth for resume), then the DB round-trip.
                message_id = resp.get("id", "")
                ledger.mirror_append(run_dir, "email", recipient, "sent",
                                     message_id=message_id, ts=datetime.now(UTC).isoformat())
                body_hash = hashlib.sha256(row.body.encode()).hexdigest()[:16]
                await led.mark_sent("email", recipient, message_hash=body_hash)
                counts["sent"] += 1
                events.emit("send.ok", recipient=recipient, message_id=message_id)

        await asyncio.gather(*(one(r) for r in rows))
    await led.aclose()
    return counts


@app.command()
def bounces(
    since_days: int = typer.Option(7, "--since-days"),
    out: str = typer.Option("bounces.csv", "--out"),
):
    """Find delivery failures; mark recipients failed + suppress them (permanent)."""
    asyncio.run(_bounces(since_days, out))


async def _bounces(since_days: int, out: str) -> None:
    token = auth.get_token("gmail")
    led = ledger.Ledger(auth.session_token())
    found: list[dict] = []
    async with httpx.AsyncClient(headers={"Authorization": f"Bearer {token}"}, timeout=60) as client:
        query = f'from:mailer-daemon subject:"Delivery Status Notification" newer_than:{since_days}d'
        for mid in await lib.list_messages(client, query):
            msg = await lib.get_message(client, mid)
            parsed = lib.parse_bounce(msg)
            if not parsed:
                events.emit("bounce.unparseable", level="warn", message_id=mid)
                continue
            recipient, when = parsed
            await led.mark_failed("email", recipient, reason="bounced")
            await led.suppress("email", recipient, reason="bounce")
            found.append({"recipient": recipient, "bounced_at": when.isoformat(), "message_id": mid})
            events.emit("bounce.recorded", recipient=recipient)
    await led.aclose()
    io.write_csv(out, [models.Row(**b) for b in found])
    typer.echo(f"gmail.bounces: {len(found)} recorded")


@app.command()
def replies(
    in_: str = typer.Option(..., "--in", help="CSV of contacts we wrote to (email column)"),
    since_days: int = typer.Option(7, "--since-days"),
    out: str = typer.Option("replies.csv", "--out"),
    file_inbox_tasks: bool = typer.Option(False, "--file-inbox-tasks",
                                          help="File each reply as an inbox/queue/ task for a human."),
    classify: bool = typer.Option(True, "--classify/--no-classify",
                                  help="LLM-classify replies (positive/negative/auto)."),
):
    """Detect replies from previously contacted people (outreach charter step 6)."""
    asyncio.run(_replies(in_, since_days, out, file_inbox_tasks, classify))


async def _replies(in_: str, since_days: int, out: str, file_tasks: bool, classify: bool) -> None:
    from toolbox.core import config

    token = auth.get_token("gmail")
    contacts = {ledger.canonical(r.email) for r in io.read_csv(in_, models.Contact)}
    rows: list[dict] = []
    async with httpx.AsyncClient(headers={"Authorization": f"Bearer {token}"}, timeout=60) as client:
        for mid in await lib.list_messages(client, f"in:inbox newer_than:{since_days}d", max_results=200):
            msg = await lib.get_message(client, mid)
            sender = lib.address_of(lib.header(msg, "From"))
            if sender not in contacts:
                continue
            body = lib.extract_text_parts(msg.get("payload") or {})[:2000]
            sentiment = ""
            if classify:
                sentiment = _classify_reply(body)
            rows.append({"email": sender, "subject": lib.header(msg, "Subject"),
                         "snippet": msg.get("snippet", ""), "sentiment": sentiment,
                         "message_id": mid})
            events.emit("reply.found", recipient=sender, sentiment=sentiment)

    io.write_csv(out, [models.Row(**r) for r in rows])
    if file_tasks and rows:
        queue = config.repo_root() / "inbox" / "queue"
        queue.mkdir(parents=True, exist_ok=True)
        today = datetime.now(UTC).strftime("%Y-%m-%d")
        for r in rows:
            slug = r["email"].replace("@", "-at-").replace(".", "-")
            task = queue / f"{today}-reply-{slug}.md"
            task.write_text(
                f"""---
title: "Reply from {r["email"]} ({r["sentiment"] or "unclassified"})"
created: {today}
created_by: outreach-agent (gmail.replies)
assigned_to: human
claimed_by:
claimed_at:
---

## Task

{r["email"]} replied to our outreach — subject: "{r["subject"]}".

Snippet: {r["snippet"]}

Sentiment: {r["sentiment"] or "unclassified"}. Read the full thread in Gmail and respond;
anything ambiguous (pricing, partnership, anger) stays with a human per the charter.
""",
                encoding="utf-8",
            )
            events.emit("inbox.task_filed", path=str(task))
    typer.echo(f"gmail.replies: {len(rows)} found")


def _classify_reply(body: str) -> str:
    try:
        from pydantic import BaseModel

        from toolbox.core import llm

        class Sentiment(BaseModel):
            sentiment: str  # positive | negative | neutral | auto_reply

        return llm.parse(
            "Classify this email reply to a cold outreach. "
            "sentiment must be one of: positive (interested / wants a call), "
            "negative (not interested / unsubscribe), neutral, auto_reply (OOO etc).\n\n" + body,
            Sentiment,
        ).sentiment
    except Exception:
        return ""


if __name__ == "__main__":
    sys.exit(app())
