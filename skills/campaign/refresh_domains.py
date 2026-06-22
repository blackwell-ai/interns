#!/usr/bin/env python3
"""Manage pre-fetched domain pools for each ICP mix segment.

Hunter Find-Companies is free but only available as an MCP tool (no public REST
API), so domain pools are populated by running this script via Claude Code, which
calls Find-Companies and writes the results here.

Workflow:
  1. Run `python3 skills/campaign/refresh_domains.py --status` to see which
     segments are missing or stale (> 7 days old).
  2. For each stale segment, ask Claude to call Hunter Find-Companies with the
     query shown, then run:
       python3 skills/campaign/refresh_domains.py --write \\
         --segment "DTC brands and retailers" \\
         --input /tmp/domains.csv
  3. campaigns via `run.py` (no --leads / --domains / --icp) will automatically
     use these pools instead of generating domains via LLM.

Domain CSV format (--input): one column named `domain`, one row per domain.
"""

from __future__ import annotations

import argparse
import csv
import sys
import tomllib
from datetime import UTC, datetime, timedelta
from pathlib import Path

_HERE = Path(__file__).parent
_ICP_MIX = _HERE / "icp_mix.toml"
_DOMAINS_DIR = _HERE / "domains"
_STALE_DAYS = 7


def _slug(label: str) -> str:
    import re
    return re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_")


def _load_segments() -> list[dict]:
    with open(_ICP_MIX, "rb") as f:
        return tomllib.load(f)["segments"]


def _domain_file(label: str) -> Path:
    return _DOMAINS_DIR / f"{_slug(label)}.csv"


def cmd_status() -> None:
    segments = _load_segments()
    now = datetime.now(UTC)
    print(f"{'Segment':<35} {'File':<10} {'Age':<12} {'Domains':<8} {'Hunter query'}")
    print("-" * 100)
    for seg in segments:
        label = seg["label"]
        icp = seg["icp"]
        f = _domain_file(label)
        if not f.exists():
            status, age, count = "MISSING", "-", "-"
        else:
            mtime = datetime.fromtimestamp(f.stat().st_mtime, tz=UTC)
            age_days = (now - mtime).days
            age = f"{age_days}d ago"
            rows = list(csv.DictReader(f.open()))
            count = str(len(rows))
            status = "STALE" if age_days >= _STALE_DAYS else "ok"
        print(f"{label:<35} {status:<10} {age:<12} {count:<8} {icp[:50]}")


def cmd_write(segment: str, input_path: str) -> None:
    segments = _load_segments()
    labels = [s["label"] for s in segments]
    if segment not in labels:
        print(f"Unknown segment {segment!r}. Valid: {labels}", file=sys.stderr)
        sys.exit(1)

    _DOMAINS_DIR.mkdir(exist_ok=True)
    out = _domain_file(segment)

    with open(input_path) as f:
        reader = csv.DictReader(f)
        if reader.fieldnames and "domain" in reader.fieldnames:
            domains = [r["domain"].strip() for r in reader if r.get("domain", "").strip()]
        else:
            f.seek(0)
            domains = [line.strip() for line in f if line.strip() and "." in line.strip()]

    with out.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["domain"])
        for d in domains:
            w.writerow([d])

    print(f"Wrote {len(domains)} domains to {out}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd")

    sub.add_parser("status", help="Show which segments have domain pools and their age")

    w = sub.add_parser("write", help="Write a domain pool for a segment from a CSV or line file")
    w.add_argument("--segment", required=True, help="Segment label (must match icp_mix.toml)")
    w.add_argument("--input", required=True, help="CSV with 'domain' column, or one domain per line")

    args = parser.parse_args()
    if args.cmd == "status" or args.cmd is None:
        cmd_status()
    elif args.cmd == "write":
        cmd_write(args.segment, args.input)


if __name__ == "__main__":
    main()
