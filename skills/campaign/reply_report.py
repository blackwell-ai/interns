#!/usr/bin/env python3
"""Query Supabase for reply rates per run and variant.

Reads the campaign log for sent counts, then queries the `replies` table
for reply counts. Output is a simple table showing response rate per variant.

Usage:
  python3 skills/campaign/reply_report.py --log /tmp/campaign_abc12345.jsonl
  python3 skills/campaign/reply_report.py --log /tmp/campaign_abc12345.jsonl --run-id <uuid>
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "toolbox" / "src"))

from toolbox.core import auth, config


def load_campaign_log(log_path: str) -> list[dict]:
    """Returns contact entries only (skips _meta lines)."""
    entries: list[dict] = []
    p = Path(log_path)
    if not p.exists():
        return entries
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
            if not entry.get("_meta"):
                entries.append(entry)
        except json.JSONDecodeError:
            continue
    return entries


def sent_counts(entries: list[dict], run_id_filter: str = "") -> dict[tuple[str, str], int]:
    """Returns {(run_id, variant): count}."""
    counts: dict[tuple[str, str], int] = defaultdict(int)
    for e in entries:
        run_id = e.get("run_id", "")
        variant = e.get("variant", "a")
        if run_id_filter and run_id != run_id_filter:
            continue
        counts[(run_id, variant)] += 1
    return dict(counts)


def fetch_reply_counts(
    session_token: str,
    run_ids: list[str],
) -> dict[tuple[str, str], int]:
    """Query Supabase replies table; returns {(run_id, variant): count}."""
    if not run_ids:
        return {}
    # PostgREST: GET /replies?run_id=in.(id1,id2)&select=run_id,variant
    ids_param = "(" + ",".join(run_ids) + ")"
    r = httpx.get(
        f"{config.supabase_url()}/rest/v1/replies",
        params={"run_id": f"in.{ids_param}", "select": "run_id,variant"},
        headers={
            "apikey": config.supabase_anon_key(),
            "Authorization": f"Bearer {session_token}",
        },
        timeout=30,
    )
    r.raise_for_status()
    counts: dict[tuple[str, str], int] = defaultdict(int)
    for row in r.json():
        key = (row.get("run_id", ""), row.get("variant", "a"))
        counts[key] += 1
    return dict(counts)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--log", required=True,
                        help="Campaign log JSONL written by run.py")
    parser.add_argument("--run-id", default="",
                        help="Filter to a specific run (default: show all in log)")
    args = parser.parse_args()

    entries = load_campaign_log(args.log)
    if not entries:
        print(f"No entries found in {args.log}")
        sys.exit(0)

    sent = sent_counts(entries, run_id_filter=args.run_id)
    run_ids = list({k[0] for k in sent})

    session_token = auth.session_token()
    replies = fetch_reply_counts(session_token, run_ids)

    # Merge and print
    all_keys = sorted(set(sent) | set(replies))
    if not all_keys:
        print("Nothing to report.")
        return

    print(f"\n{'run_id':<38} {'variant':<8} {'sent':>6} {'replied':>8} {'rate':>7}")
    print("-" * 72)
    for key in all_keys:
        run_id, variant = key
        s = sent.get(key, 0)
        r = replies.get(key, 0)
        rate = f"{r/s*100:.1f}%" if s else "n/a"
        print(f"{run_id:<38} {variant:<8} {s:>6} {r:>8} {rate:>7}")
    print()

    total_sent = sum(sent.values())
    total_replied = sum(replies.get(k, 0) for k in sent)
    overall_rate = f"{total_replied/total_sent*100:.1f}%" if total_sent else "n/a"
    print(f"Overall: {total_replied}/{total_sent} replied ({overall_rate})")


if __name__ == "__main__":
    main()
