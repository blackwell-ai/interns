#!/usr/bin/env python3
"""Read-only probe: which replies to our outbound still need a response?

This is a TEST harness, not a production scanner. It writes nothing. It exists
to answer one question: can an LLM reliably read a full email thread and decide
(a) whether the latest inbound message is a genuine human reply (vs a bounce,
out-of-office, or "no longer employed" auto-response), and (b) whether the ball
is in our court (they replied and we have not answered since).

It leans on the LLM for the genuine-vs-noise call rather than rules. As a control
it ALSO computes a cheap deterministic signal (who sent the last message) and
prints both side by side, so we can see where the model and the structure differ.

Speed: when ANTHROPIC_API_KEY is set, triage runs against the API concurrently
(--concurrency), which is far faster than the per-call `claude -p` subprocess.
Each run prints phase timings (fetch vs triage) so the cost is visible.

Usage:
  python3 skills/campaign/reply_triage_probe.py --account you@blackwell.com --ledger
  python3 skills/campaign/reply_triage_probe.py --log <log> --max 30 --concurrency 10

Nothing is persisted. Run it as often as you like.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
import time
from pathlib import Path

import httpx

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))
sys.path.insert(0, str(_REPO_ROOT / "toolbox" / "src"))

from toolbox.core import auth, config, llm as llm_mod
from toolbox.primitives.gmail import lib as gmail_lib
from skills.campaign import gog_auth
from skills.campaign.reply_scan import load_campaign_log
from pydantic import BaseModel


# Team sender + CC addresses. All of these count as "US" so a teammate CC'd on a
# send is never mistaken for the prospect who replied. Mirrors SENDERS in
# server/agent.py.
TEAM = {
    "armaan.priyadarshan.29@dartmouth.edu",
    "samarjit.deshmukh.29@dartmouth.edu",
    "ethanpzhou@berkeley.edu",
    "shamitd@stanford.edu",
}

ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
TRIAGE_MODEL = os.environ.get("TRIAGE_MODEL", "claude-sonnet-4-6")


# ---- LLM classification of a whole thread --------------------------------

class _Triage(BaseModel):
    action: str        # reply | reroute | none
    confidence: str    # clear | borderline (borderline = true gray zone, human glance)
    reroute_to: str    # named new contact to pursue when action=reroute, else ""
    category: str      # genuine | ooo | left_company | bounce | other_auto (reference)
    their_ask: str     # one line: what they actually want, or "" if none
    reason: str        # one line: why this action
    priority: str = ""  # hot | warm | cold (only when action=reply), else ""
    ooo_until: str = ""  # when category=ooo: return date (YYYY-MM-DD) or short phrase, else ""


_SYSTEM = (
    "You triage replies to a B2B cold-outreach email. You are given the full thread "
    "in order, each message labelled US (us, the sender) or THEM (the recipient or "
    "their systems). Decide the single best ACTION given the latest state.\n\n"
    "Read the WHOLE thread, then answer one question: does this need a response "
    "from us, or is it wrapped up / chill for now? Pick the action from that.\n\n"
    "action is one of:\n"
    "- reply: it needs us. The latest message is from THEM and leaves a real open "
    "loop we have not already answered: a question, genuine interest, a proposed "
    "meeting or time we have not confirmed, or an objection that invites a response.\n"
    "- reroute: the thread hands us a DIFFERENT named contact to pursue instead "
    "(a referral, a handoff, 'X has left, reach Y' with a usable name/email). "
    "Pursue that contact, do not reply to the sender. Put it in reroute_to.\n"
    "- none: nothing is needed from us. Either we sent the last message (ball is in "
    "their court), or the thread is wrapped up: a confirmation or acceptance of a "
    "time ('Tuesday works', 'confirmed'), a closing line that asks nothing ('sounds "
    "good', 'thanks'), a flat decline, an OOO, a bounce, an auto-reply, or 'no "
    "longer here' with no one to pursue. If logistics are settled and there is no "
    "open question or ask, it is none even when THEM sent last.\n\n"
    "reroute_to: when action=reroute, the name and/or email to pursue; otherwise an "
    "empty string.\n\n"
    "their_ask: a SHORT phrase, at most about 6 words, for what they want, e.g. "
    "'wants pricing', 'proposing Tue 3pm', 'how did you get my email'. Not a "
    "sentence. \"\" if there is no ask.\n\n"
    "confidence: 'clear' when the right action is obvious. A clean referral, a flat no, "
    "a bounce, an OOO, and an explicit question are all clear. Use 'borderline' ONLY "
    "when you genuinely cannot tell which action is right (e.g. a vague reply that may "
    "or may not want a response). Do NOT mark reroutes or dead ends as borderline just "
    "because they are not replies, those are clear. Reserve borderline for true "
    "judgement calls. Trust your judgement.\n\n"
    "category (reference only): genuine | ooo | left_company | bounce | other_auto.\n\n"
    "ooo_until (ONLY when category=ooo, else \"\"): when the out-of-office message "
    "states when they return, give that date as YYYY-MM-DD if you can resolve it to "
    "a calendar date, otherwise a short phrase exactly as written ('next Monday', "
    "'after the 15th'). If no return time is given, use \"\".\n\n"
    "priority (ONLY when action=reply, else \"\"): rate how urgently we should "
    "respond, by buying intent. 'hot' = they propose or accept a meeting/call time, "
    "ask about pricing or next steps, or show strong explicit interest. 'warm' = "
    "positive and engaged, a genuine question that invites dialogue, soft interest. "
    "'cold' = lukewarm, a minor or skeptical question with little intent."
)

_JSON_TAIL = (
    "\n\nReturn ONLY a JSON object, no prose, with exactly these keys: "
    '{"action": "reply"|"reroute"|"none", "confidence": "clear"|"borderline", '
    '"reroute_to": string, "category": string, "their_ask": string, "reason": string, '
    '"priority": "hot"|"warm"|"cold"|"", "ooo_until": string}'
)


def _triage_from_dict(d: dict) -> _Triage:
    conf = str(d.get("confidence", "clear")).strip().lower()
    action = str(d.get("action", "none")).strip().lower()
    if action not in ("reply", "reroute", "none"):
        action = "none"
    pri = str(d.get("priority", "")).strip().lower()
    return _Triage(
        action=action,
        confidence="borderline" if conf.startswith("border") else "clear",
        reroute_to=str(d.get("reroute_to") or ""),
        category=str(d.get("category", "?")),
        their_ask=str(d.get("their_ask") or ""),
        reason=str(d.get("reason") or ""),
        priority=pri if pri in ("hot", "warm", "cold") else "",
        ooo_until=str(d.get("ooo_until") or ""),
    )


async def triage_api(client: httpx.AsyncClient, sem: asyncio.Semaphore, rendered: str) -> _Triage:
    """One Anthropic API call, async, gated by a shared concurrency semaphore."""
    async with sem:
        try:
            r = await client.post(
                ANTHROPIC_URL,
                headers={
                    "x-api-key": os.environ["ANTHROPIC_API_KEY"],
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": TRIAGE_MODEL,
                    "max_tokens": 1024,
                    "system": _SYSTEM,
                    "messages": [{"role": "user",
                                  "content": "=== THREAD ===\n" + rendered[:8000] + _JSON_TAIL}],
                },
                timeout=60,
            )
            r.raise_for_status()
            text = r.json()["content"][0]["text"].strip()
            if text.startswith("```"):
                text = re.sub(r"^```\w*\n|\n```$", "", text).strip()
            return _triage_from_dict(json.loads(text))
        except Exception as e:  # noqa: BLE001 - probe surfaces failures inline
            return _Triage(action="none", confidence="clear", reroute_to="",
                           category="error", their_ask="", reason=f"api failed: {str(e)[:80]}")


async def triage_cli(sem: asyncio.Semaphore, rendered: str) -> _Triage:
    """Fallback when no API key: the slower `claude -p` subprocess via llm_mod."""
    async with sem:
        def _go() -> _Triage:
            try:
                return llm_mod.parse(_SYSTEM + "\n\n=== THREAD ===\n" + rendered[:8000], _Triage)
            except Exception as e:  # noqa: BLE001
                return _Triage(action="none", confidence="clear", reroute_to="",
                               category="error", their_ask="", reason=f"classify failed: {str(e)[:80]}")
        return await asyncio.to_thread(_go)


# ---- Gmail thread fetch (no helper exists in gmail_lib) ------------------

async def get_thread(client: httpx.AsyncClient, thread_id: str) -> dict:
    r = await client.get(f"{gmail_lib.api_base()}/threads/{thread_id}", params={"format": "full"})
    r.raise_for_status()
    return r.json()


async def list_all(client: httpx.AsyncClient, query: str, cap: int = 0) -> list[str]:
    """All message ids matching `query`, paginating past Gmail's 500-per-page limit.
    cap=0 means no cap (pull the entire window). This is what makes coverage complete
    instead of 'most recent N'."""
    ids: list[str] = []
    token = None
    while True:
        params = {"q": query, "maxResults": 500}
        if token:
            params["pageToken"] = token
        r = await client.get(f"{gmail_lib.api_base()}/messages", params=params)
        if r.status_code == 404:
            break
        r.raise_for_status()
        d = r.json()
        ids += [m["id"] for m in (d.get("messages") or [])]
        token = d.get("nextPageToken")
        if not token or (cap and len(ids) >= cap):
            break
    return ids[:cap] if cap else ids


async def fetch_contacted() -> set[str]:
    """Every recipient we have emailed, from the Supabase `contacted` ledger
    (paginated). This is the set we ask Gmail about directly, so we fetch only
    prospect replies instead of scanning the whole inbox.

    The whole ledger is team-wide and written by different users, so a per-user
    session only sees its own rows under RLS. When TRIAGE_LEDGER_SERVICE_KEY is
    set (the wizard passes the service-role key), read with service role so the
    full ledger is visible; otherwise fall back to the caller's session."""
    svc = os.environ.get("TRIAGE_LEDGER_SERVICE_KEY", "")
    if svc:
        headers = {"apikey": svc, "Authorization": f"Bearer {svc}"}
    else:
        token = auth.session_token()
        headers = {"apikey": config.supabase_anon_key(),
                   "Authorization": f"Bearer {token}"}
    out: set[str] = set()
    offset, page = 0, 1000
    async with httpx.AsyncClient(timeout=30) as supa:
        while True:
            r = await supa.get(
                f"{config.supabase_url()}/rest/v1/contacted",
                params={"select": "recipient", "channel": "eq.email",
                        "limit": page, "offset": offset},
                headers=headers,
            )
            r.raise_for_status()
            rows = r.json()
            out |= {row["recipient"].strip().lower() for row in rows if row.get("recipient")}
            if len(rows) < page:
                break
            offset += page
    return out


def _addr(m: dict) -> str:
    return gmail_lib.address_of(gmail_lib.header(m, "From")).lower()


def render_thread(msgs: list[dict], our_addrs: set[str]) -> tuple[str, str]:
    """Render the thread as US/THEM labelled blocks. Returns (rendered, last_sender)."""
    lines: list[str] = []
    last = "?"
    for m in msgs:
        who = "US" if _addr(m) in our_addrs else "THEM"
        last = who
        date = gmail_lib.header(m, "Date")
        body = gmail_lib.extract_text_parts(m.get("payload") or {}).strip()
        lines.append(f"--- {who} | {_addr(m)} | {date} ---\n{body[:1500]}")
    return "\n\n".join(lines), last


# ---- Probe --------------------------------------------------------------

async def _candidate_threads(gmail, our_addrs, contacts, use_ledger, since_days, recent,
                             max_threads, gsem) -> tuple[list[str], int, str]:
    """Return (thread_ids, n_found, scope_note)."""
    if use_ledger:
        # Ask Gmail only for inbound from people we emailed. Batch the ledger into
        # from:(a OR b OR ...) chunks so we never scan unrelated mail. Complete
        # within the window, no recency cap.
        contacted = await fetch_contacted()
        emails = list(contacted)
        batches = [emails[i:i + 50] for i in range(0, len(emails), 50)]

        async def batch_query(chunk):
            q = f"in:inbox newer_than:{since_days}d from:({' OR '.join(chunk)})"
            async with gsem:
                return await list_all(gmail, q, cap=recent)
        results = await asyncio.gather(*(batch_query(c) for c in batches))
        mids = list(dict.fromkeys(m for r in results for m in r))  # flatten + de-dupe

        async def meta(mid):
            async with gsem:
                try:
                    return await gmail_lib.get_message(gmail, mid, fmt="metadata")
                except Exception:  # noqa: BLE001 - skip a flaky message, do not abort
                    return None
        metas = await asyncio.gather(*(meta(mid) for mid in mids))

        order: list[str] = []
        seen: set[str] = set()
        for m in metas:
            if not m:
                continue
            tid = m.get("threadId")
            if tid and _addr(m) not in our_addrs and tid not in seen:
                seen.add(tid)
                order.append(tid)
        tids = order[:max_threads] if max_threads else order
        return (tids, len(order),
                f"  ledger {len(emails)} contacted, {len(mids)} prospect replies, "
                f"{len(tids)} threads")

    if contacts:
        emails = list(contacts.keys())
        mids = []
        for i in range(0, len(emails), 50):
            q = f"in:inbox newer_than:{since_days}d from:({' OR '.join(emails[i:i+50])})"
            mids += await gmail_lib.list_messages(gmail, q, max_results=500)
    else:
        mids = await gmail_lib.list_messages(gmail, f"in:inbox newer_than:{since_days}d", max_results=500)

    async def meta(mid):
        async with gsem:
            return mid, await gmail_lib.get_message(gmail, mid, fmt="metadata")
    pairs = await asyncio.gather(*(meta(mid) for mid in mids))
    tids, seen = [], set()
    for _mid, m in pairs:
        tid = m.get("threadId")
        if tid and tid not in seen:
            seen.add(tid)
            tids.append(tid)
    return tids[:max_threads], len(seen), ""


async def probe(log_path: str, account_override: str, since_days: int, max_threads: int,
                use_ledger: bool, recent: int, concurrency: int,
                as_json: bool = False) -> None:
    t_start = time.perf_counter()
    our_addrs: set[str] = set(TEAM)
    contacts: dict = {}

    if log_path:
        contacts, meta = load_campaign_log(log_path)
        account = account_override or meta.get("sender_email", "")
    else:
        account = account_override
    if not account:
        print("Need an account: pass --account, or a --log whose meta has sender_email.")
        return
    our_addrs.add(account.lower())

    token = gog_auth.get_access_token(account)
    async with httpx.AsyncClient(
        headers={"Authorization": f"Bearer {token}"}, timeout=60
    ) as gmail:
        gsem = asyncio.Semaphore(concurrency)

        t0 = time.perf_counter()
        thread_ids, n_found, scope = await _candidate_threads(
            gmail, our_addrs, contacts, use_ledger, since_days, recent, max_threads, gsem)

        # Fetch full threads in parallel.
        async def fetch(tid):
            async with gsem:
                return tid, await get_thread(gmail, tid)
        fetched = await asyncio.gather(*(fetch(t) for t in thread_ids))
        t_fetch = time.perf_counter() - t0

        # Prepare per-thread metadata (owner = first US sender = original outbound).
        prepared = []
        for tid, th in fetched:
            msgs = th.get("messages") or []
            rendered, last_sender = render_thread(msgs, our_addrs)
            owner = next((_addr(m) for m in msgs if _addr(m) in our_addrs), account)
            other = next((_addr(m) for m in msgs if _addr(m) not in our_addrs), "unknown")
            subject = gmail_lib.header(msgs[0], "Subject") if msgs else ""
            prepared.append({"tid": tid, "rendered": rendered, "last_sender": last_sender,
                             "owner": owner, "who": other, "subject": subject, "n": len(msgs)})

        # Triage all threads concurrently.
        use_api = bool(os.environ.get("ANTHROPIC_API_KEY"))
        asem = asyncio.Semaphore(concurrency)
        t1 = time.perf_counter()
        if use_api:
            async with httpx.AsyncClient(timeout=60) as api:
                verdicts = await asyncio.gather(
                    *(triage_api(api, asem, p["rendered"]) for p in prepared))
        else:
            verdicts = await asyncio.gather(
                *(triage_cli(asem, p["rendered"]) for p in prepared))
        t_triage = time.perf_counter() - t1

    rows, needs, reroute, gray, skip = [], [], [], [], []
    for p, v in zip(prepared, verdicts):
        row = {**p, "action": v.action, "confidence": v.confidence,
               "reroute_to": v.reroute_to, "category": v.category,
               "ask": v.their_ask, "reason": v.reason, "priority": v.priority}
        rows.append(row)
        if v.confidence == "borderline":
            gray.append(row)            # true judgement call: human glance
        elif v.action == "reply" and p["last_sender"] == "THEM":
            needs.append(row)           # they sent last and are waiting on us
        elif v.action == "reply":
            skip.append(row)            # we already sent the latest message; their court
        elif v.action == "reroute":
            reroute.append(row)         # pursue the named new contact
        else:
            skip.append(row)            # dead end: decline, OOO, bounce, left-no-contact

    if as_json:
        def slim(r: dict) -> dict:
            return {"thread_id": r["tid"], "who": r["who"], "owner": r["owner"],
                    "subject": r["subject"], "action": r["action"],
                    "confidence": r["confidence"], "reroute_to": r["reroute_to"],
                    "ask": r["ask"], "priority": r.get("priority", "")}
        print(json.dumps({
            "account": account,
            "found": n_found,
            "scope": scope.strip(),
            "counts": {"reply": len(needs), "reroute": len(reroute),
                       "gray": len(gray), "skip": len(skip)},
            "needs": [slim(r) for r in needs],
            "reroute": [slim(r) for r in reroute],
            "gray": [slim(r) for r in gray],
        }))
        return

    engine = f"API x{concurrency}" if use_api else f"CLI x{concurrency}"
    print(f"\nAccount: {account}   threads to triage: {len(thread_ids)} "
          f"(of {n_found} found, capped at {max_threads}){scope}")
    print(f"Timing: fetch {t_fetch:.1f}s + triage {t_triage:.1f}s [{engine}] "
          f"= {time.perf_counter() - t_start:.1f}s total\n")
    _print_report(rows, needs, reroute, gray, skip)


def _print_report(rows, needs, reroute, gray, skip) -> None:
    print("=" * 80)
    print("ALL THREADS")
    print("=" * 80)
    for r in rows:
        print(f"\n• {r['who']}  ({r['n']} msgs)  \"{r['subject'][:55]}\"  [sent by {r['owner']}]")
        rr = f" -> {r['reroute_to'][:40]}" if r["reroute_to"] else ""
        print(f"    action={r['action']:<8} conf={r['confidence']:<10} category={r['category']}{rr}")
        if r["ask"]:
            print(f"    their ask: {r['ask'][:90]}")
        print(f"    why: {r['reason'][:90]}")

    print("\n" + "=" * 80)
    print(f"NEEDS REPLY: {len(needs)} thread(s) a real person is waiting on")
    print("=" * 80)
    for r in needs:
        print(f"  - {r['who']:<32} owner: {r['owner']:<34} | {r['ask'][:55]}")
    if not needs:
        print("  (none)")

    print("\n" + "=" * 80)
    print(f"RE-ROUTE: {len(reroute)} thread(s) — pursue a different named contact")
    print("=" * 80)
    for r in reroute:
        print(f"  - {r['who']:<32} owner: {r['owner']:<28} -> {r['reroute_to'][:40]}")
    if not reroute:
        print("  (none)")

    print("\n" + "=" * 80)
    print(f"GRAY ZONE: {len(gray)} thread(s) — model unsure, human glance")
    print("=" * 80)
    for r in gray:
        print(f"  - {r['who']:<32} owner: {r['owner']:<28} | {r['ask'][:45]}")
    if not gray:
        print("  (none)")

    print(f"\nSKIP (dead ends: declines, OOO, bounces, left-no-contact): {len(skip)}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--log", default="", help="Campaign log JSONL (scopes to known contacts)")
    ap.add_argument("--account", default="", help="Gmail account to scan (overrides log meta)")
    ap.add_argument("--since-days", type=int, default=60, help="Inbox lookback window")
    ap.add_argument("--max", type=int, default=0, dest="max_threads",
                    help="Cap threads triaged (0 = no cap, triage every prospect reply)")
    ap.add_argument("--ledger", action="store_true",
                    help="Scope by intersecting inbound senders with the Supabase "
                         "contacted ledger (recommended)")
    ap.add_argument("--recent", type=int, default=0,
                    help="With --ledger: cap inbox messages scanned (0 = entire window)")
    ap.add_argument("--concurrency", type=int, default=8,
                    help="Parallel API/Gmail requests in flight")
    ap.add_argument("--json", action="store_true", dest="as_json",
                    help="Emit a JSON summary instead of the text report")
    args = ap.parse_args()
    if not args.log and not args.account:
        ap.error("pass --log or --account")
    asyncio.run(probe(args.log, args.account, args.since_days, args.max_threads,
                      args.ledger, args.recent, args.concurrency, args.as_json))


if __name__ == "__main__":
    main()
