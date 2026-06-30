"""Reply triage for the wizard: scan the team's sender inboxes and report which
prospect replies still need a response.

Reuses the validated probe (skills/campaign/reply_triage_probe.py) by running it
once per sender account with --json. On Railway there is no gog, so we mint a
Gmail access token from each sender's refresh token (server/gmail_auth) and pass
it through the env fast path gog_auth already supports (GMAIL_TOKEN_<SENDER>),
plus a Supabase session token for the contacted ledger. Read only: sends nothing.
"""
import asyncio
import json
import logging
import os
from typing import Awaitable, Callable

from skills.campaign import gog_auth

from . import agent, executor, gmail_auth, triage_dismiss

log = logging.getLogger(__name__)

_PROBE = executor.REPO_ROOT / "skills" / "campaign" / "reply_triage_probe.py"
SINCE_DAYS = 60


def _short(email: str) -> str:
    """A sender's first name if known, else the local part of the address."""
    for s in agent.SENDERS:
        if s["email"].lower() == (email or "").lower():
            return s["from_name"]
    return (email or "?").split("@")[0]


async def _run_account(email: str, env: dict, concurrency: int = 20) -> dict:
    cmd = ["python3", "-u", str(_PROBE), "--account", email, "--ledger",
           "--concurrency", str(concurrency), "--json"]
    proc = await asyncio.create_subprocess_exec(
        *cmd, env=env, cwd=str(executor.REPO_ROOT),
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    out, err = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError((err.decode(errors="replace") or "probe failed")[:300])
    text = out.decode(errors="replace").strip()
    if not text:
        raise RuntimeError("probe produced no output")
    return json.loads(text.splitlines()[-1])  # last line is the JSON summary


_PRIORITY_ORDER = {"hot": 0, "warm": 1, "cold": 2, "": 3}
_BUCKET_RANK = {"needs": 0, "reroute": 1, "gray": 2}


def _rank(r: dict) -> tuple[int, int]:
    """Sort key for choosing which copy of a person to keep: strongest bucket
    first (needs > reroute > gray), then hottest priority."""
    return (_BUCKET_RANK.get(r.get("_bucket", ""), 9),
            _PRIORITY_ORDER.get(r.get("priority", ""), 3))


def apply_dismissals(needs: list, reroute: list, gray: list,
                     dismissed: set[str]) -> tuple[list, list, list]:
    """Drop every row whose person (the prospect email in `who`) has been
    dismissed, across all three buckets. Pure so it is testable; case-insensitive
    to match how emails are stored."""
    if not dismissed:
        return needs, reroute, gray
    d = {e.strip().lower() for e in dismissed}

    def keep(items: list) -> list:
        return [r for r in items if (r.get("who") or "").strip().lower() not in d]

    return keep(needs), keep(reroute), keep(gray)


def merge_results(results: list[dict]) -> tuple[list, list, list]:
    """Collapse the team's triage to one row per person. Two passes:
    first dedupe by thread id (every teammate is CC'd, so the same reply lands in
    several inboxes), then dedupe by the person's email so someone with several
    threads (e.g. two campaigns) is not listed twice. We keep their strongest
    signal: needs over reroute over gray, hottest priority within that.
    Returns (needs, reroute, gray)."""
    by_thread: dict[str, dict] = {}
    for res in results:
        for bucket in ("needs", "reroute", "gray"):
            for r in res.get(bucket, []):
                tid = r.get("thread_id")
                if tid and tid not in by_thread:
                    by_thread[tid] = {**r, "_bucket": bucket}

    by_email: dict[str, dict] = {}
    for r in by_thread.values():
        key = (r.get("who") or r.get("thread_id") or "").strip().lower()
        if not key:
            continue
        cur = by_email.get(key)
        if cur is None or _rank(r) < _rank(cur):
            by_email[key] = r

    needs = [r for r in by_email.values() if r["_bucket"] == "needs"]
    reroute = [r for r in by_email.values() if r["_bucket"] == "reroute"]
    gray = [r for r in by_email.values() if r["_bucket"] == "gray"]
    return needs, reroute, gray


_PRIORITY_EMOJI = {"hot": ":fire:", "warm": ":large_yellow_circle:",
                   "cold": ":white_circle:", "": ":white_circle:"}
_MAX_SECTION = 2800  # Slack's mrkdwn section cap is 3000 chars; leave headroom
_MAX_BLOCKS = 45     # Slack allows 50 blocks/message; leave room for the heading


def _owner_sections(items: list, line: Callable[[dict], str]) -> list[dict]:
    """One section block per owner, owners A->Z, each a short bulleted list.
    A single owner with a very long list is split across sections so no section
    exceeds Slack's character cap."""
    groups: dict[str, list] = {}
    for r in items:
        groups.setdefault(_short(r.get("owner", "")), []).append(r)

    blocks: list[dict] = []
    for owner in sorted(groups, key=str.lower):
        rows = groups[owner]
        lines = [line(r) for r in rows]
        chunks: list[list[str]] = []
        buf, size = [], 0
        for ln in lines:
            if buf and size + len(ln) + 1 > _MAX_SECTION:
                chunks.append(buf)
                buf, size = [], 0
            buf.append(ln)
            size += len(ln) + 1
        if buf:
            chunks.append(buf)
        for i, chunk in enumerate(chunks):
            body = "\n".join(chunk)
            # Header (name + count) only on the first chunk; any overflow chunk is a
            # seamless continuation of the same owner, so a name appears exactly once.
            if i == 0:
                text = f":bust_in_silhouette: *{owner}*  ·  {len(rows)}\n{body}"
            else:
                text = body
            blocks.append({"type": "section",
                           "text": {"type": "mrkdwn", "text": text[:2999]}})
    return blocks


def _grouped_messages(title: str, items: list,
                      line: Callable[[dict], str]) -> list[dict]:
    """Owner-grouped sections for one bucket, split into Slack messages that stay
    under the per-message block limit."""
    secs = _owner_sections(items, line)
    msgs: list[dict] = []
    for i in range(0, len(secs), _MAX_BLOCKS):
        chunk = secs[i:i + _MAX_BLOCKS]
        heading = f"*{title}* ({len(items)})"
        if len(secs) > _MAX_BLOCKS:
            heading += f"  ·  part {i // _MAX_BLOCKS + 1}"
        blocks = [{"type": "section", "text": {"type": "mrkdwn", "text": heading}}]
        blocks += chunk
        msgs.append({"text": title, "blocks": blocks})
    return msgs


def format_messages(needs: list, reroute: list, gray: list,
                    errors: list[str], since_days: int) -> list[dict]:
    """Build Slack messages: a summary, then each bucket grouped by owner (A->Z)
    as short bulleted lists instead of wide tables. Within an owner, awaiting-reply
    people are hottest first. Each message is {text, blocks}."""
    needs = sorted(needs, key=lambda r: _PRIORITY_ORDER.get(r.get("priority", ""), 3))
    summary = (f":scroll: *Inbox triage* (last {since_days} days). "
               f"*{len(needs)}* awaiting reply, *{len(reroute)}* reroute, "
               f"*{len(gray)}* worth a glance.\n"
               ":fire: hot  ·  :large_yellow_circle: warm  ·  :white_circle: cold")
    msgs: list[dict] = [{"text": summary,
                         "blocks": [{"type": "section",
                                     "text": {"type": "mrkdwn", "text": summary}}]}]
    if needs:
        def line(r: dict) -> str:
            emoji = _PRIORITY_EMOJI.get(r.get("priority", ""), ":white_circle:")
            ask = " ".join((r.get("ask") or "").split())  # one line, no stray breaks
            tail = f"  —  {ask[:45]}" if ask else ""
            return f"{emoji} {r['who']}{tail}"
        msgs += _grouped_messages("Awaiting reply", needs, line)
    if reroute:
        # Reroutes are pursued autonomously, so just show how many per owner.
        counts: dict[str, int] = {}
        for r in reroute:
            owner = _short(r.get("owner", ""))
            counts[owner] = counts.get(owner, 0) + 1
        lines = [f":bust_in_silhouette: *{owner}*  ·  {n}"
                 for owner, n in sorted(counts.items(), key=lambda kv: kv[0].lower())]
        heading = (f"*Reroute to a new contact* ({len(reroute)})  ·  "
                   "handled autonomously")
        text = heading + "\n" + "\n".join(lines)
        msgs.append({"text": "Reroute to a new contact",
                     "blocks": [{"type": "section",
                                 "text": {"type": "mrkdwn", "text": text[:2999]}}]})
    if gray:
        def line(r: dict) -> str:
            return f"• {r['who']}"
        msgs += _grouped_messages("Worth a glance", gray, line)
    if not (needs or reroute or gray):
        msgs.append({"text": "Nothing needs action right now.", "blocks": None})
    if errors:
        msgs.append({"text": ":warning: Some inboxes faltered: "
                     + "; ".join(errors)[:400], "blocks": None})
    return msgs


async def run_triage(send_update: Callable[[str], Awaitable[None]],
                     since_days: int = SINCE_DAYS) -> list[dict]:
    """Triage every sender inbox and return Slack messages ({text, blocks})."""
    env = {**os.environ}
    try:
        env["TOOLBOX_SESSION_TOKEN"] = await asyncio.to_thread(
            executor._get_supabase_session_token)
    except Exception:
        env["TOOLBOX_SESSION_TOKEN"] = os.environ.get("SUPABASE_SECRET_KEY", "")
    # The contacted ledger is team-wide; read it with the service-role key so RLS
    # does not hide rows written by other users (a per-user session sees only its
    # own sends). Read only, ledger table only.
    env["TRIAGE_LEDGER_SERVICE_KEY"] = os.environ.get("SUPABASE_SECRET_KEY", "")

    accounts: list[str] = []
    for s in agent.SENDERS:
        suffix = gog_auth._SENDER_ENV_KEYS.get(s["email"])
        if not suffix:
            continue
        try:
            env[f"GMAIL_TOKEN_{suffix}"] = await asyncio.to_thread(
                gmail_auth.get_access_token, s["email"])
            accounts.append(s["email"])
        except Exception as e:
            await send_update(f":warning: could not authenticate "
                              f"{s['from_name']}: {str(e)[:120]}")

    if not accounts:
        return [{"text": "No sender inboxes could be opened for divination.",
                 "blocks": None}]

    await send_update(f":crystal_ball: Reading the replies across "
                      f"{len(accounts)} inboxes...")
    raw = await asyncio.gather(*[_run_account(e, env) for e in accounts],
                               return_exceptions=True)
    results, errors = [], []
    for email, res in zip(accounts, raw):
        if isinstance(res, Exception):
            log.warning("triage[%s] failed: %s", email, res)
            errors.append(f"{_short(email)}: {str(res)[:120]}")
        else:
            log.info("triage[%s] found=%s counts=%s scope=%s",
                     email, res.get("found"), res.get("counts"), res.get("scope"))
            results.append(res)

    needs, reroute, gray = merge_results(results)
    # Hide anyone a human has marked 'not relevant'. load_dismissed is best-effort
    # (returns an empty set on any failure), so triage never breaks on this.
    dismissed = await triage_dismiss.load_dismissed()
    needs, reroute, gray = apply_dismissals(needs, reroute, gray, dismissed)
    return format_messages(needs, reroute, gray, errors, since_days)
