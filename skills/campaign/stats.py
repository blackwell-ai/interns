#!/usr/bin/env python3
"""Print campaign stats from Supabase — no log file or Notion needed.

Usage:
  python3 skills/campaign/stats.py
  python3 skills/campaign/stats.py --last 5
"""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "toolbox" / "src"))

from toolbox.core import auth, config


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--last", type=int, default=20,
                        help="Show only the N most recent campaigns (default 20)")
    args = parser.parse_args()

    token = auth.session_token()
    headers = {
        "apikey": config.supabase_anon_key(),
        "Authorization": f"Bearer {token}",
    }
    base = config.supabase_url()

    campaigns_r = httpx.get(
        f"{base}/rest/v1/campaigns",
        params={"select": "run_id,sender,sender_email,template_name,icp_description,sent_count,created_at",
                "order": "created_at.desc", "limit": str(args.last + 20)},
        headers=headers, timeout=30,
    )
    campaigns_r.raise_for_status()
    campaigns = [c for c in campaigns_r.json() if c.get("sender_email") != "shamit.dsouza@gmail.com"][:args.last]

    if not campaigns:
        print("No campaigns found.")
        return

    run_ids = [c["run_id"] for c in campaigns]
    ids_param = "(" + ",".join(run_ids) + ")"

    replies_r = httpx.get(
        f"{base}/rest/v1/replies",
        params={"run_id": f"in.{ids_param}", "select": "run_id,sentiment"},
        headers=headers, timeout=30,
    )
    replies_r.raise_for_status()

    reply_counts: dict[str, int] = defaultdict(int)
    sentiment_counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for row in replies_r.json():
        rid = row.get("run_id", "")
        reply_counts[rid] += 1
        sentiment_counts[rid][row.get("sentiment") or "unknown"] += 1

    print(f"\n{'date':<12} {'sender':<10} {'icp/template':<50} {'sent':>5} {'replied':>8} {'rate':>6}  sentiment")
    print("-" * 110)
    for c in campaigns:
        rid = c["run_id"]
        date = (c.get("created_at") or "")[:10]
        sender = (c.get("sender") or "")[:10]
        label = (c.get("icp_description") or c.get("template_name") or "")[:50]
        sent = c.get("sent_count") or 0
        replied = reply_counts.get(rid, 0)
        rate = f"{replied/sent*100:.0f}%" if sent else "n/a"
        sents = sentiment_counts.get(rid, {})
        sent_str = "  ".join(f"{k}:{v}" for k, v in sorted(sents.items())) if sents else ""
        print(f"{date:<12} {sender:<10} {label:<50} {sent:>5} {replied:>8} {rate:>6}  {sent_str}")

    total_sent = sum(c.get("sent_count") or 0 for c in campaigns)
    total_replied = sum(reply_counts.get(c["run_id"], 0) for c in campaigns)
    overall = f"{total_replied/total_sent*100:.1f}%" if total_sent else "n/a"
    print("-" * 110)
    print(f"Total: {total_replied} replies / {total_sent} sent ({overall})\n")


if __name__ == "__main__":
    main()
