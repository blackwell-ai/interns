#!/usr/bin/env python3
"""Backfill the reply-examples corpus and voice cards from a founder's Sent mail.

This is a one-time / occasional OFFLINE backfill for the Slack /respond feature.
The /respond drafter retrieves (incoming email, reply we sent) pairs as few-shot
exemplars and injects a per-founder voice card so a drafted reply sounds like the
founder. Those come from two sources: the live feedback loop (every reply sent
from the queue) and this harvest of historical Sent mail. No code harvests the
Sent folder today, so this script seeds the corpus from what a founder has
already written.

What it does, for one --account:
  1. Walk the account's Sent folder over a lookback window (Gmail `in:sent`).
  2. For every reply the founder sent that had a prior inbound message in the
     same thread, form an (incoming, reply) pair. First-touch cold emails have
     no prior inbound and are naturally excluded.
  3. Curate: drop auto-replies and negative threads (bias toward threads that
     went well), tag each kept pair with a category and sentiment.
  4. Upsert the kept pairs into `reply_examples` (dedupe on our reply's Gmail id)
     and distill a voice card into `voice_cards`.

It calls the existing data-layer modules; it does not reimplement storage or
classification. Nothing about the mail body ever reaches stdout or logs: the
summary is counts only (repo rule: no PII in logs).

Environment (the same wizard env the /respond feature uses):
  - SUPABASE_URL, SUPABASE_SECRET_KEY : service-role writes to the two tables.
  - ANTHROPIC_API_KEY or the `claude` CLI : category tag + voice-card distill.
  - A gog token for --account (local `gog auth add`), or GMAIL_TOKEN_<SENDER>.

Usage:
  python3 skills/campaign/harvest_reply_examples.py --account you@blackwell.com
  python3 skills/campaign/harvest_reply_examples.py --account you@blackwell.com \
      --since-days 365 --max-threads 200 --dry-run
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import time
from pathlib import Path

import httpx

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))
sys.path.insert(0, str(_REPO_ROOT / "toolbox" / "src"))

from toolbox.primitives.gmail import lib as gmail_lib
from skills.campaign import gog_auth, reply_scan
from skills.campaign import reply_triage_probe as probe
from skills.campaign.wizard import reply_examples, voice_cards
from skills.campaign.wizard.agent import SENDERS

# Cap on how many of a founder's replies feed the voice card. distill_card also
# clamps internally; keeping it here bounds the token cost of the one call.
_VOICE_SAMPLE_CAP = 25


# ---- Sent-folder discovery --------------------------------------------------

async def list_sent_threads(gmail: httpx.AsyncClient, since_days: int,
                            max_threads: int) -> list[str]:
    """Distinct thread ids for messages in the Sent folder within the window.

    Paginates past Gmail's 500-per-page limit. This is the Sent folder
    specifically (`in:sent`), not the inbox: we want threads where the founder
    replied. `max_threads` of 0 means no cap. Order of first appearance is kept
    so a cap takes the most recent threads first (Gmail returns newest first)."""
    seen: set[str] = set()
    order: list[str] = []
    token: str | None = None
    while True:
        params: dict = {"q": f"in:sent newer_than:{since_days}d", "maxResults": 500}
        if token:
            params["pageToken"] = token
        r = await gmail.get(f"{gmail_lib.api_base()}/messages", params=params)
        if r.status_code == 404:
            break
        r.raise_for_status()
        data = r.json()
        for m in data.get("messages") or []:
            tid = m.get("threadId")
            if tid and tid not in seen:
                seen.add(tid)
                order.append(tid)
                if max_threads and len(order) >= max_threads:
                    return order
        token = data.get("nextPageToken")
        if not token:
            break
    return order


# ---- pair extraction --------------------------------------------------------

def _text(m: dict) -> str:
    """Plain-text body of a Gmail message, stripped."""
    return gmail_lib.extract_text_parts(m.get("payload") or {}).strip()


def extract_pairs(thread: dict, team: set[str]) -> list[dict]:
    """Every (incoming, reply) pair in a thread.

    Walk messages in order. For each OURS message that has at least one THEM
    message before it, pair it with the nearest preceding THEM message. That
    yields the inbound the founder was answering and the reply they sent. A
    first-touch cold email (no prior inbound) produces no pair. Returns raw
    dicts with the fields the corpus needs; curation happens in the caller.
    """
    msgs = thread.get("messages") or []
    pairs: list[dict] = []
    last_incoming: dict | None = None
    for m in msgs:
        is_ours = probe._addr(m) in team
        if is_ours:
            if last_incoming is None:
                continue  # first-touch send, nothing to learn a reply from
            incoming, reply = last_incoming, m
            incoming_subject = gmail_lib.header(incoming, "Subject")
            incoming_body = _text(incoming)
            reply_body = _text(reply)
            if not incoming_body or not reply_body:
                continue  # need both sides to be a usable exemplar
            pairs.append({
                "incoming_subject": incoming_subject,
                "incoming_body": incoming_body,
                "reply_body": reply_body,
                "message_id": reply.get("id", ""),
            })
        else:
            last_incoming = m
    return pairs


def founder_key(account: str) -> str:
    """The SENDERS key whose email matches the account (case-insensitive), or the
    local-part of the account as a fallback so the founder tag is still stable."""
    acct = (account or "").strip().lower()
    for s in SENDERS:
        if (s.get("email") or "").strip().lower() == acct:
            return s["key"]
    return acct.split("@")[0]


# ---- curation (classification off the hot path) -----------------------------

async def _curate(pair: dict, sem: asyncio.Semaphore) -> dict | None:
    """Attach sentiment + category to a pair, or return None to drop it.

    Sentiment gates first: skip auto-replies and negative threads so the corpus
    biases toward exchanges that went well. classify_sentiment and
    classify_category are blocking (LLM / rule) calls, run off-thread under a
    shared concurrency gate."""
    async with sem:
        sentiment = await asyncio.to_thread(
            reply_scan.classify_sentiment, pair["incoming_body"])
        if sentiment in ("auto_reply", "negative"):
            return None
        category = await asyncio.to_thread(
            reply_examples.classify_category,
            pair["incoming_subject"], pair["incoming_body"])
    return {**pair, "sentiment": sentiment, "category": category}


# ---- orchestration ----------------------------------------------------------

async def harvest(account: str, since_days: int, max_threads: int,
                  concurrency: int, dry_run: bool) -> None:
    t0 = time.perf_counter()
    founder = founder_key(account)
    team = set(probe.TEAM) | {account.lower()}

    token = gog_auth.get_access_token(account)
    async with httpx.AsyncClient(
        headers={"Authorization": f"Bearer {token}"}, timeout=60
    ) as gmail:
        gsem = asyncio.Semaphore(concurrency)

        thread_ids = await list_sent_threads(gmail, since_days, max_threads)

        async def fetch(tid: str) -> dict | None:
            async with gsem:
                try:
                    return await probe.get_thread(gmail, tid)
                except Exception:  # noqa: BLE001 - skip a flaky thread, keep going
                    return None
        threads = await asyncio.gather(*(fetch(t) for t in thread_ids))

    # Extract every pair, then dedupe within the run by our reply's Gmail id.
    pairs: list[dict] = []
    seen_mids: set[str] = set()
    for th in threads:
        if not th:
            continue
        for p in extract_pairs(th, team):
            mid = p.get("message_id", "")
            if not mid or mid in seen_mids:
                continue
            seen_mids.add(mid)
            pairs.append(p)

    # Curate concurrently. None means dropped by the sentiment gate.
    csem = asyncio.Semaphore(concurrency)
    curated = await asyncio.gather(*(_curate(p, csem) for p in pairs))
    kept = [c for c in curated if c is not None]
    skipped_sentiment = len(pairs) - len(kept)

    rows = [{
        "founder": founder,
        "category": c["category"],
        "incoming_subject": c["incoming_subject"],
        "incoming_body": c["incoming_body"],
        "reply_body": c["reply_body"],
        "sentiment": c["sentiment"],
        "source": "harvest",
        "is_gold": False,
        "message_id": c["message_id"],
    } for c in kept]

    inserted: int | str = "dry-run"
    if not dry_run:
        inserted = await reply_examples.upsert_examples(rows)

    # Voice card from up to N of the founder's kept replies.
    samples = [c["reply_body"] for c in kept][:_VOICE_SAMPLE_CAP]
    card = voice_cards.distill_card(samples)
    if not dry_run and card:
        await voice_cards.upsert_card(founder, card)

    # Counts only. Never print a subject, body, or address.
    print(f"\nHarvest for founder '{founder}' ({'dry-run' if dry_run else 'live'})")
    print(f"  threads scanned:       {len(thread_ids)}")
    print(f"  pairs found:           {len(pairs)}")
    print(f"  kept:                  {len(kept)}")
    print(f"  skipped by sentiment:  {skipped_sentiment}")
    print(f"  inserted:              {inserted}")
    print(f"  voice-card length:     {len(card)} chars")
    print(f"  time:                  {time.perf_counter() - t0:.1f}s\n")


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--account", required=True,
                    help="Founder Gmail account whose Sent folder to harvest")
    ap.add_argument("--since-days", type=int, default=180,
                    help="Sent-folder lookback window in days")
    ap.add_argument("--max-threads", type=int, default=0,
                    help="Cap threads scanned (0 = no cap)")
    ap.add_argument("--concurrency", type=int, default=8,
                    help="Parallel Gmail fetches and classification calls")
    ap.add_argument("--dry-run", action="store_true",
                    help="Plan and print the summary; write nothing")
    args = ap.parse_args()
    asyncio.run(harvest(args.account, args.since_days, args.max_threads,
                        args.concurrency, args.dry_run))


if __name__ == "__main__":
    main()
