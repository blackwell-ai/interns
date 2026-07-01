"""Agentic project Q&A for the wizard.

Answers open-ended questions in Slack by running a Claude tool-use loop with a
READ-ONLY toolset. Claude decides which tools to call, we run them and feed the
results back, until it produces an answer. This handles unpredictable questions
("did Nathan reply?", "what's our reply rate this week?", "what can you do?")
that the fixed campaign/triage flows do not cover.

Security: every tool here only reads. There is no send, draft, or delete. Sending
stays exclusively behind the gated preview flow in slack_bot. An instruction that
arrives inside an email the agent reads therefore has nothing to act on.

The loop reports progress through an optional async `on_step` callback so the
caller can show a live "working on it" message while a slow answer is computed.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import anthropic
import httpx

from toolbox.primitives.gmail import lib as gmail_lib

from . import agent, config, gmail_auth

log = logging.getLogger(__name__)

QA_MODEL = "claude-sonnet-4-6"
CLASSIFY_MODEL = "claude-sonnet-4-6"
MAX_ITERS = 8  # cap the tool-use loop so a question can never run away on cost

_CAMPAIGN_DIR = Path(__file__).resolve().parents[1]
_DOCS = {
    "SKILL": _CAMPAIGN_DIR / "SKILL.md",
    "README": _CAMPAIGN_DIR / "server" / "README.md",
    "ARCHITECTURE": _CAMPAIGN_DIR / "server" / "ARCHITECTURE.md",
    "REPLY_TRIAGE": _CAMPAIGN_DIR / "REPLY_TRIAGE.md",
    "HOW_IT_WORKS": _CAMPAIGN_DIR / "HOW_IT_WORKS.md",
}


# ---- system prompt ------------------------------------------------------------

_SYSTEM = """You are the email_wizard, the agent who runs Blackwell's cold-outreach
campaigns, answering a teammate's question in a Slack thread.

You can do several things, and should describe them plainly if asked "what can you
do": plan and send outreach campaigns (you propose a plan and a sample email, and
a human confirms before anything sends), take a pasted or uploaded CSV of leads
and prepare a send, triage replies across the team inboxes (who is waiting on us,
who to reroute), draft morning follow-ups, and answer questions like this one.

For THIS question, use the tools to find real answers rather than guessing:
- read_doc to explain how the system works or what you can do (the docs are the
  source of truth for your own mechanics).
- search_inbox / read_email_thread to answer anything about specific replies or
  threads ("did X write back", "what did they say").
- list_replies for questions about a GROUP of people ("what are the aerospace
  companies saying", "which DTC brands replied", "negative replies this month").
  It scopes replies by the campaign ICP, sentiment, and window. To quote what a
  group actually said, list them first, then read a few of their threads with
  read_email_thread (or search_inbox on a recipient) and summarize the themes.
- lookup_contact to check whether and when we emailed someone and if they replied.
- sent_today for "how many have we sent today", "are we on track", or "how far
  from the daily target" — it is the exact calendar-day count from the ledger.
- campaign_stats for volume and reply-rate questions over a multi-day window.

Rules: you are READ ONLY here, you never send or change anything. If a tool returns
nothing useful, say so plainly instead of inventing an answer. Never reveal API
keys, tokens, or raw credentials. Keep the answer concise and specific for Slack:
plain text, no markdown headers, no em or en dashes. A light wizard voice is fine
(an "aye", a "scroll" for email) as long as the facts stay clear."""

_CLASSIFY_SYSTEM = """Classify the Slack message as exactly one word:
- "send" if it asks to launch, run, or send an outreach campaign, or hands over
  leads/contacts to email (e.g. "40 to DTC brands via Ethan", "blast these").
- "triage" ONLY if it is a command to scan the inboxes and process the whole
  pile of replies/reroutes right now (e.g. "triage the inboxes", "scan replies",
  "who is waiting on us", "run triage"). It is a bulk action over all inboxes.
- "question" for anything else, including any question ABOUT replies or a group
  of people ("what did the aerospace folks say", "how many DTC brands replied",
  "did Nathan write back", "summarize the responses from X"). When a message asks
  about replies rather than commanding a full inbox scan, it is a question.
Reply with only that one word, nothing else."""


# ---- tool schemas -------------------------------------------------------------

_TOOLS = [
    {
        "name": "read_doc",
        "description": "Read one of the project's own docs to explain how the "
                       "system works or what the wizard can do.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "enum": list(_DOCS.keys()),
                         "description": "Which doc to read."}
            },
            "required": ["name"],
        },
    },
    {
        "name": "search_inbox",
        "description": "Search a sender's Gmail inbox with a Gmail query string. "
                       "Returns matching messages (from, subject, date, snippet, "
                       "thread_id). Read only.",
        "input_schema": {
            "type": "object",
            "properties": {
                "account": {"type": "string",
                            "description": "Sender to search: a first name "
                                           "(Armaan/Samarjit/Ethan), an email, or "
                                           "'all' for every team inbox."},
                "query": {"type": "string",
                          "description": "Gmail search, e.g. 'from:nathan@x.com', "
                                         "'newer_than:7d', 'subject:pricing'."},
                "max_results": {"type": "integer",
                                "description": "Cap results per inbox (default 8)."},
            },
            "required": ["query"],
        },
    },
    {
        "name": "read_email_thread",
        "description": "Read a full email thread (both directions, US/THEM "
                       "labelled) by its thread_id. Read only.",
        "input_schema": {
            "type": "object",
            "properties": {
                "account": {"type": "string",
                            "description": "Which inbox the thread is in (name, "
                                           "email, or 'all')."},
                "thread_id": {"type": "string"},
            },
            "required": ["thread_id"],
        },
    },
    {
        "name": "lookup_contact",
        "description": "Check whether and when we emailed someone and whether they "
                       "replied. Matches an email or domain against the contacted "
                       "ledger and the replies table.",
        "input_schema": {
            "type": "object",
            "properties": {
                "needle": {"type": "string",
                           "description": "An email address or a domain fragment."},
            },
            "required": ["needle"],
        },
    },
    {
        "name": "campaign_stats",
        "description": "Aggregate sends and replies over a recent window: total "
                       "sent, replies, reply rate, and sentiment breakdown.",
        "input_schema": {
            "type": "object",
            "properties": {
                "since_days": {"type": "integer",
                               "description": "Lookback window in days (default 7)."},
            },
        },
    },
    {
        "name": "sent_today",
        "description": "Exact count of emails sent so far TODAY (since local "
                       "midnight), straight from the contacted ledger, plus the "
                       "daily target and how many remain. The ledger is TEAM-WIDE, "
                       "so this sums every sender's runs; the result includes a "
                       "by_sender / runs breakdown — always show it so the total is "
                       "not mistaken for one person's sends. Use for 'how many "
                       "today', 'are we on track', 'how far to the target' — it is "
                       "the calendar-day truth, where campaign_stats is a multi-day "
                       "rolling window.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "list_replies",
        "description": "List the people who replied, optionally scoped to a GROUP "
                       "of targets, a sentiment, and a time window. Use this to "
                       "answer questions about a slice of people, e.g. 'what are "
                       "the aerospace companies saying', 'which DTC brands "
                       "replied', 'show negative replies this month'. The group is "
                       "matched against the campaign ICP description each person "
                       "was emailed under. Returns recipients with sentiment, "
                       "subject, date, and the ICP they came from. Read only; for "
                       "the actual words of a reply, follow up with "
                       "read_email_thread or search_inbox on a recipient.",
        "input_schema": {
            "type": "object",
            "properties": {
                "group": {"type": "string",
                          "description": "Target group to scope to, matched against "
                                         "the campaign ICP (e.g. 'aerospace', 'DTC', "
                                         "'pet'). Omit for all replies."},
                "sentiment": {"type": "string",
                              "description": "Filter to one sentiment (e.g. "
                                             "'positive', 'negative', 'neutral'). "
                                             "Omit for any."},
                "since_days": {"type": "integer",
                               "description": "Lookback window in days (default 30)."},
            },
        },
    },
]


# ---- helpers ------------------------------------------------------------------

def _text_of(resp) -> str:
    return "".join(b.text for b in resp.content if b.type == "text").strip()


def _resolve_accounts(account: str | None) -> list[str]:
    """Map a name/email/'all' to one or more sender emails."""
    a = (account or "all").strip().lower()
    emails = [s["email"] for s in agent.SENDERS]
    if a in ("all", "everyone", "team", ""):
        return emails
    for s in agent.SENDERS:
        if a in (s["key"], s["from_name"].lower(), s["email"].lower()):
            return [s["email"]]
    if "@" in a:
        return [a]
    return emails


def _supa_headers() -> dict:
    key = config.SUPABASE_SECRET_KEY
    return {"apikey": key, "Authorization": f"Bearer {key}"}


def _step_label(name: str, inp: dict) -> str:
    if name == "read_doc":
        return f":books: reading {inp.get('name', 'the docs')}..."
    if name == "search_inbox":
        return f":mag: searching {inp.get('account', 'the')} inbox..."
    if name == "read_email_thread":
        return ":envelope_with_arrow: reading the thread..."
    if name == "lookup_contact":
        return f":scroll: checking the ledger for {inp.get('needle', '')}..."
    if name == "campaign_stats":
        return ":bar_chart: tallying sends and replies..."
    if name == "sent_today":
        return ":bar_chart: counting today's sends..."
    if name == "list_replies":
        grp = inp.get("group")
        return f":scroll: gathering replies{f' from {grp}' if grp else ''}..."
    return ":mage: working..."


# ---- tool implementations (all read-only) -------------------------------------

async def _read_doc(name: str) -> str:
    path = _DOCS.get(name)
    if not path or not path.exists():
        return f"(no doc named {name})"
    return path.read_text(encoding="utf-8")[:12000]


async def _search_inbox(account: str, query: str, max_results: int = 8) -> str:
    out: list[dict] = []
    for email in _resolve_accounts(account):
        try:
            token = await asyncio.to_thread(gmail_auth.get_access_token, email)
        except Exception as e:  # noqa: BLE001 - one inbox failing is not fatal
            out.append({"account": email, "error": str(e)[:100]})
            continue
        async with httpx.AsyncClient(
            headers={"Authorization": f"Bearer {token}"}, timeout=30
        ) as g:
            ids = await gmail_lib.list_messages(g, query, max_results=max_results)
            for mid in ids[:max_results]:
                m = await gmail_lib.get_message(g, mid, fmt="metadata")
                out.append({
                    "account": email,
                    "thread_id": m.get("threadId"),
                    "from": gmail_lib.header(m, "From"),
                    "subject": gmail_lib.header(m, "Subject"),
                    "date": gmail_lib.header(m, "Date"),
                    "snippet": (m.get("snippet") or "")[:200],
                })
    return json.dumps(out[:30]) if out else "no matching messages"


async def _read_email_thread(account: str, thread_id: str) -> str:
    # Lazy import: this pulls in a heavier chain (toolbox auth, gog_auth) and is
    # only needed when a thread is actually read, so keep it out of bot startup.
    from skills.campaign import reply_triage_probe as probe
    email = _resolve_accounts(account)[0]
    token = await asyncio.to_thread(gmail_auth.get_access_token, email)
    our = set(probe.TEAM) | {email.lower()}
    async with httpx.AsyncClient(
        headers={"Authorization": f"Bearer {token}"}, timeout=40
    ) as g:
        th = await probe.get_thread(g, thread_id)
    rendered, _ = probe.render_thread(th.get("messages") or [], our)
    return rendered[:6000] or "empty thread"


async def _lookup_contact(needle: str) -> str:
    needle = (needle or "").strip()
    if not needle:
        return "no email or domain given"
    h = _supa_headers()
    base = config.SUPABASE_URL
    async with httpx.AsyncClient(timeout=30) as s:
        c = await s.get(f"{base}/rest/v1/contacted",
                        params={"select": "recipient,run_id,created_at",
                                "recipient": f"ilike.*{needle}*", "limit": 25},
                        headers=h)
        r = await s.get(f"{base}/rest/v1/replies",
                        params={"select": "recipient,received_at,sentiment,subject",
                                "recipient": f"ilike.*{needle}*", "limit": 25},
                        headers=h)
    return json.dumps({
        "contacted": c.json() if c.status_code == 200 else c.text[:200],
        "replies": r.json() if r.status_code == 200 else r.text[:200],
    })


async def _campaign_stats(since_days: int = 7) -> str:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=since_days)).isoformat()
    h = _supa_headers()
    base = config.SUPABASE_URL
    async with httpx.AsyncClient(timeout=30) as s:
        camps = await s.get(f"{base}/rest/v1/campaigns",
                            params={"select": "sent_count,template_name,icp_description,created_at",
                                    "created_at": f"gte.{cutoff}", "limit": 1000},
                            headers=h)
        reps = await s.get(f"{base}/rest/v1/replies",
                           params={"select": "sentiment,received_at",
                                   "received_at": f"gte.{cutoff}", "limit": 5000},
                           headers=h)
    crows = camps.json() if camps.status_code == 200 else []
    rrows = reps.json() if reps.status_code == 200 else []
    sent = sum(int(c.get("sent_count") or 0) for c in crows)
    replies = len(rrows)
    sentiment: dict[str, int] = {}
    for r in rrows:
        key = (r.get("sentiment") or "unknown").lower()
        sentiment[key] = sentiment.get(key, 0) + 1
    rate = round(100 * replies / sent, 1) if sent else 0.0
    return json.dumps({
        "since_days": since_days, "campaigns": len(crows), "sent": sent,
        "replies": replies, "reply_rate_pct": rate, "sentiment": sentiment,
    })


# Defaults mirror slack_config (SLACK_SCHEDULE_TZ / SLACK_DAILY_TARGET). Read
# from the env directly so qa.py stays importable without the Slack config.
_DEFAULT_TZ = "America/Los_Angeles"
_DEFAULT_DAILY_TARGET = 2000


def _local_midnight_utc(now: datetime | None = None) -> datetime:
    """Midnight of the current local day (SLACK_SCHEDULE_TZ), as a UTC instant.
    Pure so the date-boundary math is testable: an 11pm-yesterday send must land
    before this cutoff, a 12:01am-today send after it. `now` is for tests."""
    tz = ZoneInfo(os.environ.get("SLACK_SCHEDULE_TZ", _DEFAULT_TZ))
    here = (now or datetime.now(tz)).astimezone(tz)
    midnight = here.replace(hour=0, minute=0, second=0, microsecond=0)
    return midnight.astimezone(timezone.utc)


def _parse_count(content_range: str | None) -> int | None:
    """PostgREST returns the exact total after the slash in Content-Range
    ('0-0/1234' -> 1234, '*/0' -> 0). None when it cannot be read."""
    if not content_range or "/" not in content_range:
        return None
    total = content_range.rsplit("/", 1)[-1].strip()
    return int(total) if total.isdigit() else None


async def _count_contacted_since(cutoff_iso: str, sent_only: bool = True) -> int | None:
    """Exact count of contacted rows created at/after the cutoff, via PostgREST's
    count=exact header (cheap: it returns the total, not the rows). Filters to
    status='sent' when present; if that column does not exist (4xx), retries
    counting every row, since a contacted row is written at send time anyway."""
    base, h = config.SUPABASE_URL, _supa_headers()
    params = {"select": "recipient", "created_at": f"gte.{cutoff_iso}", "limit": "1"}
    if sent_only:
        params["status"] = "eq.sent"
    async with httpx.AsyncClient(timeout=30) as s:
        r = await s.get(f"{base}/rest/v1/contacted", params=params,
                        headers={**h, "Prefer": "count=exact"})
    if r.status_code not in (200, 206):
        if sent_only:  # likely no 'status' column — count all rows instead
            return await _count_contacted_since(cutoff_iso, sent_only=False)
        return None
    return _parse_count(r.headers.get("content-range"))


async def _sent_breakdown(cutoff_iso: str) -> dict:
    """Per-sender / per-run split of today's sends, so the total is never a
    mystery number: the contacted ledger is team-wide, so 'sent today' sums every
    sender's runs. Maps each sent row's run_id to its campaign sender. Best-effort
    — returns {} if the rows or campaigns cannot be read."""
    base, h = config.SUPABASE_URL, _supa_headers()
    rows: list[dict] = []
    async with httpx.AsyncClient(timeout=30) as s:
        off = 0
        while True:
            r = await s.get(f"{base}/rest/v1/contacted",
                            params={"select": "run_id", "created_at": f"gte.{cutoff_iso}",
                                    "status": "eq.sent", "order": "run_id.asc",
                                    "offset": off, "limit": 1000}, headers=h)
            if r.status_code not in (200, 206):
                return {}
            batch = r.json()
            rows += batch
            if len(batch) < 1000:
                break
            off += 1000
        by_run: dict[str, int] = {}
        for x in rows:
            rid = x.get("run_id")
            if rid:
                by_run[rid] = by_run.get(rid, 0) + 1
        sender_by_run: dict[str, str] = {}
        if by_run:
            ids = ",".join(f'"{k}"' for k in by_run)
            c = await s.get(f"{base}/rest/v1/campaigns",
                            params={"select": "run_id,sender", "run_id": f"in.({ids})"},
                            headers=h)
            for row in (c.json() if c.status_code == 200 else []):
                sender_by_run[row.get("run_id")] = row.get("sender") or "unknown"
    by_sender: dict[str, int] = {}
    for rid, cnt in by_run.items():
        key = sender_by_run.get(rid, "unknown")
        by_sender[key] = by_sender.get(key, 0) + cnt
    return {"runs": len(by_run), "by_sender": by_sender}


async def _sent_today() -> str:
    cutoff = _local_midnight_utc().isoformat()
    n = await _count_contacted_since(cutoff)
    if n is None:
        return json.dumps({"error": "could not read the contacted ledger"})
    target = int(os.environ.get("SLACK_DAILY_TARGET", str(_DEFAULT_DAILY_TARGET)))
    # The ledger is team-wide, so this counts every sender. Include the split so
    # the number is transparent (e.g. "1445 across 12 runs: Samarjit 566, ...").
    breakdown = await _sent_breakdown(cutoff)
    return json.dumps({"window": "today (since local midnight, team-wide)",
                       "sent": n, "target": target, "remaining": max(0, target - n),
                       **breakdown})


async def _list_replies(group: str | None = None, sentiment: str | None = None,
                        since_days: int = 30) -> str:
    """Replies scoped to a target group (by campaign ICP), sentiment, and window.

    The join is campaigns(icp) -> run_id -> contacted(recipient) -> replies.
    Done as a few cheap PostgREST calls inside this one tool so the model gets
    clean rows to reason over instead of having to stitch the tables itself.
    """
    base, h = config.SUPABASE_URL, _supa_headers()
    cutoff = (datetime.now(timezone.utc) - timedelta(days=since_days)).isoformat()
    recipients: list[str] | None = None
    matched_icps: list[str] = []
    async with httpx.AsyncClient(timeout=30) as s:
        if group:
            c = await s.get(f"{base}/rest/v1/campaigns",
                            params={"select": "run_id,icp_description",
                                    "icp_description": f"ilike.*{group}*",
                                    "limit": 500}, headers=h)
            crows = c.json() if c.status_code == 200 else []
            run_ids = [r["run_id"] for r in crows if r.get("run_id")]
            matched_icps = sorted({r.get("icp_description", "") for r in crows})
            if not run_ids:
                return json.dumps({"group": group, "matched_campaigns": 0,
                                   "note": "no campaigns match that group"})
            ids = ",".join(f'"{r}"' for r in run_ids[:200])
            ct = await s.get(f"{base}/rest/v1/contacted",
                             params={"select": "recipient",
                                     "run_id": f"in.({ids})", "limit": 2000},
                             headers=h)
            rows = ct.json() if ct.status_code == 200 else []
            recipients = sorted({r["recipient"] for r in rows if r.get("recipient")})
            if not recipients:
                return json.dumps({"group": group, "matched_campaigns": len(run_ids),
                                   "contacted": 0, "note": "no one contacted yet"})
        params = {"select": "recipient,subject,sentiment,received_at",
                  "received_at": f"gte.{cutoff}", "order": "received_at.desc",
                  "limit": "200"}
        if sentiment:
            params["sentiment"] = f"ilike.{sentiment}"
        if recipients is not None:
            rids = ",".join(f'"{r}"' for r in recipients[:300])
            params["recipient"] = f"in.({rids})"
        r = await s.get(f"{base}/rest/v1/replies", params=params, headers=h)
    reps = r.json() if r.status_code == 200 else []
    counts: dict[str, int] = {}
    for row in reps:
        k = (row.get("sentiment") or "unknown").lower()
        counts[k] = counts.get(k, 0) + 1
    return json.dumps({
        "group": group, "sentiment_filter": sentiment, "since_days": since_days,
        "matched_icps": [i for i in matched_icps if i][:10],
        "total_replies": len(reps), "sentiment_counts": counts,
        "replies": reps[:60],
    })


_DISPATCH = {
    "read_doc": lambda i: _read_doc(i["name"]),
    "search_inbox": lambda i: _search_inbox(i.get("account", "all"), i["query"],
                                            int(i.get("max_results") or 8)),
    "read_email_thread": lambda i: _read_email_thread(i.get("account", "all"),
                                                      i["thread_id"]),
    "lookup_contact": lambda i: _lookup_contact(i["needle"]),
    "campaign_stats": lambda i: _campaign_stats(int(i.get("since_days") or 7)),
    "sent_today": lambda i: _sent_today(),
    "list_replies": lambda i: _list_replies(
        i.get("group") or None, i.get("sentiment") or None,
        int(i.get("since_days") or 30)),
}


async def _run_tool(name: str, inp: dict) -> str:
    fn = _DISPATCH.get(name)
    if not fn:
        return f"unknown tool: {name}"
    return await fn(inp)


# ---- public entry points ------------------------------------------------------

async def classify_intent(text: str) -> str:
    """One of 'send', 'triage', or 'question'. 'send' runs the gated campaign
    flow, 'triage' scans every inbox, 'question' answers via the read-only Q&A
    loop. On any failure, default to 'question' (the safe, non-sending path)."""
    try:
        client = anthropic.AsyncAnthropic(api_key=config.ANTHROPIC_API_KEY)
        resp = await client.messages.create(
            model=CLASSIFY_MODEL, max_tokens=5, system=_CLASSIFY_SYSTEM,
            messages=[{"role": "user", "content": text[:2000]}])
        out = _text_of(resp).lower()
        if "send" in out:
            return "send"
        if "triage" in out:
            return "triage"
        return "question"
    except Exception:  # noqa: BLE001
        log.exception("intent classify failed")
        return "question"


async def answer(question: str, on_step=None) -> str:
    """Run the read-only tool-use loop and return the final answer text.
    `on_step(label)` (async) is called before each tool runs, for a live status."""
    client = anthropic.AsyncAnthropic(api_key=config.ANTHROPIC_API_KEY)
    messages: list[dict] = [{"role": "user", "content": question}]
    resp = None
    for _ in range(MAX_ITERS):
        resp = await client.messages.create(
            model=QA_MODEL, max_tokens=1024, system=_SYSTEM,
            tools=_TOOLS, messages=messages)
        if resp.stop_reason != "tool_use":
            return _text_of(resp) or "I have no answer for that."
        messages.append({"role": "assistant", "content": resp.content})
        results = []
        for block in resp.content:
            if block.type != "tool_use":
                continue
            if on_step:
                try:
                    await on_step(_step_label(block.name, block.input))
                except Exception:  # noqa: BLE001 - a status update is best-effort
                    pass
            try:
                out = await _run_tool(block.name, block.input)
            except Exception as e:  # noqa: BLE001 - surface tool errors to the model
                out = f"tool error: {str(e)[:200]}"
            results.append({"type": "tool_result", "tool_use_id": block.id,
                            "content": out[:8000]})
        messages.append({"role": "user", "content": results})
    return (_text_of(resp) if resp else "") or \
        "I searched what I could but could not pin that down."
