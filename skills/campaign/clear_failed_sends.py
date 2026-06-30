#!/usr/bin/env python3
"""Clear contacted-ledger rows for sends that failed on a Gmail rate limit.

Background: before the rate-limit fix (see ERRORS_AND_LESSONS.md), a burst of
sends tripped Gmail's per-user limit, which returns HTTP 403. Those were
misclassified as permanent failures and written to the Supabase `contacted`
ledger as status=failed. Nothing actually delivered, but the rows make those
prospects look contacted, so they get skipped on retry and dropped from sourcing
dedup. This removes exactly those rows so they can be reached again.

Read-only by default. Pass --apply to delete.

  python3 skills/campaign/clear_failed_sends.py            # dry run, lists matches
  python3 skills/campaign/clear_failed_sends.py --apply    # delete them

Reads SUPABASE_URL and SUPABASE_SECRET_KEY from the environment, or from
credentials/.env. The secret (service-role) key is used so the whole team ledger
is visible, not just one user's rows.
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

# Substrings of the stored failure reason that identify a Gmail rate-limit 403
# (as opposed to a real bad address or a daily-cap wall).
RATE_PATTERNS = ["rateLimitExceeded", "userRateLimitExceeded",
                 "User-rate limit exceeded", "Queries per minute"]


def _load_env() -> dict[str, str]:
    import os
    env = dict(os.environ)
    dotenv = REPO_ROOT / "credentials" / ".env"
    if dotenv.exists():
        for line in dotenv.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env.setdefault(k.strip(), v.split("#")[0].strip().strip('"').strip("'"))
    return env


def _request(method: str, url: str, key: str, prefer: str = "") -> tuple[int, str]:
    req = urllib.request.Request(url, method=method)
    req.add_header("apikey", key)
    req.add_header("Authorization", f"Bearer {key}")
    if prefer:
        req.add_header("Prefer", prefer)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


def _or_filter() -> str:
    # PostgREST: or=(message_hash.ilike.*pat1*,message_hash.ilike.*pat2*)
    clauses = ",".join(f"message_hash.ilike.*{p}*" for p in RATE_PATTERNS)
    return f"({clauses})"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true", help="Delete the rows (default: dry run)")
    args = ap.parse_args()

    env = _load_env()
    base = env.get("SUPABASE_URL", "").rstrip("/")
    key = env.get("SUPABASE_SECRET_KEY", "")
    if not base or not key:
        print("ERROR: SUPABASE_URL and SUPABASE_SECRET_KEY must be set "
              "(env or credentials/.env).")
        sys.exit(1)

    params = {"channel": "eq.email", "status": "eq.failed",
              "or": _or_filter(), "select": "recipient,message_hash"}
    qs = urllib.parse.urlencode(params, safe="(),.*")
    url = f"{base}/rest/v1/contacted?{qs}"

    status, body = _request("GET", url, key)
    if status != 200:
        print(f"ERROR reading ledger ({status}): {body[:300]}")
        sys.exit(1)
    rows = json.loads(body)
    print(f"Matched {len(rows)} rate-limited failed row(s):")
    for r in rows[:60]:
        print(f"  {r['recipient']}")
    if len(rows) > 60:
        print(f"  ...and {len(rows) - 60} more")

    if not rows:
        print("Nothing to clear.")
        return
    if not args.apply:
        print("\nDry run. Re-run with --apply to delete these rows.")
        return

    status, body = _request("DELETE", url, key, prefer="return=representation")
    if status not in (200, 204):
        print(f"ERROR deleting ({status}): {body[:300]}")
        sys.exit(1)
    deleted = json.loads(body) if body.strip() else []
    print(f"\nDeleted {len(deleted)} row(s). Those prospects can be contacted again.")


if __name__ == "__main__":
    main()
