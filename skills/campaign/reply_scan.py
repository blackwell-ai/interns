#!/usr/bin/env python3
"""Scan Gmail inbox for replies to a campaign; write to Supabase `replies` table.

Reads the campaign log written by run.py to know which emails belong to which
run_id and variant. Classifies each reply's sentiment via LLM. Skips duplicates
(UNIQUE constraint on recipient + message_id in the replies table).

Usage:
  python3 skills/campaign/reply_scan.py --log /tmp/campaign_abc12345.jsonl
  python3 skills/campaign/reply_scan.py --log /tmp/campaign_abc12345.jsonl --since-days 14
"""

from __future__ import annotations

import argparse
import asyncio
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import httpx

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))
sys.path.insert(0, str(_REPO_ROOT / "toolbox" / "src"))

from toolbox.core import auth, config, events
from toolbox.core import llm as llm_mod
from toolbox.primitives.gmail import lib as gmail_lib
from skills.campaign import gog_auth, notion_sync
from pydantic import BaseModel


# ---- Campaign log helpers -----------------------------------------------

def load_campaign_log(log_path: str) -> tuple[dict[str, dict], dict]:
    """Returns ({email: {run_id, variant, sent_at}}, meta_entry)."""
    mapping: dict[str, dict] = {}
    meta: dict = {}
    p = Path(log_path)
    if not p.exists():
        return mapping, meta
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
            if entry.get("_meta"):
                meta = entry
                continue
            email = entry.get("email", "").strip().lower()
            if email:
                mapping[email] = entry
        except json.JSONDecodeError:
            continue
    return mapping, meta


# ---- Sentiment classification -------------------------------------------

class _Sentiment(BaseModel):
    sentiment: str  # positive | negative | neutral | auto_reply


def classify_sentiment(body: str) -> str:
    try:
        result = llm_mod.parse(
            "Classify this email reply to a cold outreach. "
            "Return one of: positive (interested or wants a call), "
            "negative (not interested or unsubscribe), neutral, auto_reply (OOO etc).\n\n"
            + body[:2000],
            _Sentiment,
        )
        return result.sentiment
    except Exception:
        return "unknown"


# ---- Supabase write -----------------------------------------------------

async def upsert_reply(
    client: httpx.AsyncClient,
    session_token: str,
    recipient: str,
    received_at: str,
    subject: str,
    snippet: str,
    sentiment: str,
    run_id: str,
    variant: str,
    message_id: str,
) -> bool:
    """Insert reply; returns True if inserted, False if duplicate."""
    r = await client.post(
        f"{config.supabase_url()}/rest/v1/replies",
        headers={
            "apikey": config.supabase_anon_key(),
            "Authorization": f"Bearer {session_token}",
            "Content-Type": "application/json",
            "Prefer": "resolution=ignore-duplicates,return=minimal",
        },
        json={
            "recipient": recipient,
            "received_at": received_at,
            "subject": subject,
            "snippet": snippet,
            "sentiment": sentiment,
            "run_id": run_id,
            "variant": variant,
            "message_id": message_id,
        },
    )
    if r.status_code in (200, 201):
        return True
    if r.status_code == 409:
        return False
    events.emit("reply.insert_error", level="warn", status=r.status_code, body=r.text[:200])
    return False


# ---- Main scan ----------------------------------------------------------

def _gog(*args: str, account: str = "") -> dict | list | None:
    """Run a gog command and return parsed JSON, or None on error."""
    cmd = ["gog"] + list(args) + ["--json", "--results-only", "--no-input"]
    if account:
        cmd += ["--account", account]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if result.returncode != 0:
        events.emit("gog.error", level="warn", cmd=args[0], reason=result.stderr[:200])
        return None
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return None


async def scan(log_path: str, since_days: int, classify: bool) -> list[dict]:
    contacts, meta = load_campaign_log(log_path)
    if not contacts:
        print(f"No entries in log: {log_path}")
        return []

    account = meta.get("sender_email", "")
    session_token = auth.session_token()
    found: list[dict] = []

    # Get token from gog once; use Gmail REST API for concurrent reads.
    gmail_token = gog_auth.get_access_token(account)

    async with httpx.AsyncClient(
        headers={"Authorization": f"Bearer {gmail_token}"}, timeout=60
    ) as gmail_client, httpx.AsyncClient(timeout=30) as supa_client:

        # Batch from: queries so Gmail filters — avoids scanning the whole inbox.
        emails = list(contacts.keys())
        message_ids: list[str] = []
        for i in range(0, max(1, len(emails)), 50):
            batch = emails[i: i + 50]
            from_filter = " OR ".join(batch)
            query = f"in:inbox newer_than:{since_days}d from:({from_filter})"
            batch_ids = await gmail_lib.list_messages(gmail_client, query, max_results=500)
            message_ids.extend(batch_ids)

        for mid in message_ids:
            msg = await gmail_lib.get_message(gmail_client, mid)
            sender = gmail_lib.address_of(gmail_lib.header(msg, "From"))
            if sender not in contacts:
                continue

            contact_info = contacts[sender]
            body = gmail_lib.extract_text_parts(msg.get("payload") or {})
            sentiment = classify_sentiment(body) if classify else ""

            date_header = gmail_lib.header(msg, "Date")
            try:
                from email.utils import parsedate_to_datetime
                received_at = parsedate_to_datetime(date_header).astimezone(UTC).isoformat()
            except Exception:
                received_at = datetime.now(UTC).isoformat()

            inserted = await upsert_reply(
                supa_client,
                session_token,
                recipient=sender,
                received_at=received_at,
                subject=gmail_lib.header(msg, "Subject"),
                snippet=(msg.get("snippet") or "")[:500],
                sentiment=sentiment,
                run_id=contact_info.get("run_id", ""),
                variant=contact_info.get("variant", ""),
                message_id=mid,
            )
            if inserted:
                found.append({"email": sender, "sentiment": sentiment, "run_id": contact_info.get("run_id")})
                events.emit("reply.recorded", recipient=sender, sentiment=sentiment,
                            run_id=contact_info.get("run_id"), variant=contact_info.get("variant"))
            else:
                events.emit("reply.duplicate", recipient=sender, message_id=mid)

        # Sync Notion reply count from Supabase (runs even if all were duplicates).
        if meta.get("notion_page_id") and meta.get("run_id"):
            total_replies = 0
            try:
                count_r = await supa_client.get(
                    f"{config.supabase_url()}/rest/v1/replies",
                    params={"run_id": f"eq.{meta['run_id']}", "select": "id"},
                    headers={
                        "apikey": config.supabase_anon_key(),
                        "Authorization": f"Bearer {session_token}",
                        "Prefer": "count=exact",
                        "Range": "0-0",
                    },
                )
                content_range = count_r.headers.get("Content-Range", "")
                if "/" in content_range:
                    total_replies = int(content_range.split("/")[-1])
            except Exception:
                total_replies = len(found)
            notion_sync.update_reply_count(meta["notion_page_id"], total_replies)

    return found


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--log", required=True,
                        help="Campaign log JSONL written by run.py")
    parser.add_argument("--since-days", type=int, default=30,
                        help="Look back this many days in Gmail inbox")
    parser.add_argument("--no-classify", action="store_true",
                        help="Skip LLM sentiment classification")
    args = parser.parse_args()

    found = asyncio.run(scan(args.log, args.since_days, classify=not args.no_classify))
    print(f"reply_scan: {len(found)} new replies recorded")
    for r in found:
        print(f"  {r['email']} [{r['sentiment']}] run={r['run_id'][:8] if r.get('run_id') else '?'}")


if __name__ == "__main__":
    main()
