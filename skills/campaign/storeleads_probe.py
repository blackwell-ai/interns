#!/usr/bin/env python3
"""Probe StoreLeads domain sourcing without burning Hunter credits.

Domain sourcing is fully decoupled from contact enrichment: this script touches
StoreLeads (and, unless --no-llm, one cheap structured Claude call to translate
the niche) and never calls Hunter/Apollo, so it spends zero email-finder credits.

Cost summary:
  StoreLeads : one search request per niche (cheap, request-based plan).
  Claude     : one small structured call per niche for filter translation,
               skipped entirely with --no-llm (hardcoded filters instead).
  Hunter     : none. This script never enriches.

Usage:
  # zero Claude tokens, zero Hunter — pure StoreLeads check with explicit filters
  python3 skills/campaign/storeleads_probe.py --no-llm \
      --q "maternity clothing" --category "/Apparel"

  # full sourcing seam (1 small Claude call to translate the niche), no Hunter
  python3 skills/campaign/storeleads_probe.py --subcat "DTC maternity clothing"

Reads TOOLBOX_TOKEN_STORELEADS from the environment or credentials/.env.
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))
sys.path.insert(0, str(_REPO_ROOT / "toolbox" / "src"))


def _load_env_file() -> None:
    """Load credentials/.env into os.environ (only keys not already set)."""
    import os
    env = _REPO_ROOT / "credentials" / ".env"
    if not env.exists():
        return
    for line in env.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        # strip inline comments and surrounding quotes
        val = val.split("#", 1)[0].strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = val


async def _main() -> int:
    ap = argparse.ArgumentParser(description="Probe StoreLeads sourcing (no Hunter).")
    ap.add_argument("--subcat", default="DTC maternity clothing",
                    help="niche to translate via Claude (ignored with --no-llm)")
    ap.add_argument("--no-llm", action="store_true",
                    help="skip Claude; use --q/--category filters directly")
    ap.add_argument("--q", default="maternity clothing",
                    help="keyword query for --no-llm mode")
    ap.add_argument("--category", default="",
                    help="StoreLeads category path for --no-llm mode (e.g. /Apparel)")
    ap.add_argument("--page-size", type=int, default=10, help="domains to fetch")
    args = ap.parse_args()

    _load_env_file()
    from skills.campaign import run, storeleads

    if not storeleads.available():
        print("FAIL: TOOLBOX_TOKEN_STORELEADS not set "
              "(env or credentials/.env). Sourcing would fall back to LLM.")
        return 1
    print("token configured: yes")

    if args.no_llm:
        # Pure StoreLeads check: explicit filters, zero Claude tokens.
        filters = dict(run._STORELEADS_BASE_FILTERS)
        if args.category:
            filters["f:cat"] = args.category
        print(f"[no-llm] q={args.q!r} filters={filters}")
        domains, cursor = await storeleads.search_domains(
            filters, q=args.q, page_size=args.page_size)
        print(f"\nStoreLeads returned {len(domains)} real domains "
              f"(more pages: {bool(cursor)}):")
    else:
        # Exercise the real production seam: translate -> StoreLeads (with the
        # category-miss retry) -> LLM fallback only if StoreLeads has nothing.
        print(f"sourcing niche via production path: {args.subcat!r} ...")
        domains = await run.source_domains_for_subcat(
            args.subcat, count=args.page_size)
        print(f"\nsource_domains_for_subcat returned {len(domains)} domains:")

    for d in domains[:args.page_size]:
        print(f"  {d}")
    print("\nHunter credits spent: 0  (enrichment not invoked)")
    return 0 if domains else 2


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main()))
