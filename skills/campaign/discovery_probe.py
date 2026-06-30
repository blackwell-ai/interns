#!/usr/bin/env python3
"""Discovery probe — measure how many fresh domains an ICP can generate, $0 credits.

Exercises ONLY the free `claude -p` discovery half of the pipeline:
sub-category (niche) decomposition + per-niche domain generation, with the same
dedup and niche-regeneration logic a real run uses. It never calls Hunter, never
sends an email, and never writes to the ledger — so it costs nothing but LLM
subscription time. Use it to confirm the niche-generation loop keeps producing
genuinely new ICPs and fresh domains instead of collapsing into duplicates.

It also isolates the sub-category cache into a temp directory, so probing does
NOT mark real niches as "searched" (which would make a later real run skip them).

Examples
--------
  # Can we generate 2000 unique domains for DTC brands? Stop early once we either
  # hit the target or stall. ~13s per niche (serialized claude -p), so a deep
  # probe takes a while — start with a smaller --max-niches to gauge yield.
  python3 skills/campaign/discovery_probe.py \
      --icp "DTC e-commerce brands selling consumer products" \
      --target 2000 --max-niches 40

  # Also report how many generated domains are genuinely NEW (never contacted),
  # by reading the Supabase ledger (a free read, not a Hunter credit):
  python3 skills/campaign/discovery_probe.py --icp "DTC brands" \
      --target 2000 --max-niches 40 --check-fresh

  # Write the unique domains to a CSV you can eyeball:
  python3 skills/campaign/discovery_probe.py --icp "DTC brands" \
      --max-niches 25 --out /tmp/dtc_domains.csv
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import sys
import tempfile
import time
from pathlib import Path

# Repo root + toolbox on sys.path (mirrors tests/conftest.py).
_ROOT = Path(__file__).resolve().parents[2]
for _p in (str(_ROOT), str(_ROOT / "toolbox" / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from skills.campaign import run as camp  # noqa: E402


def _load_contacted(check_fresh: bool) -> set[str]:
    """Return the set of already-contacted domains, or empty if not checking.

    Reads the Supabase ledger — a free GET, never a Hunter credit. Degrades to an
    empty set (with a warning) if auth is missing, so the probe still runs.
    """
    if not check_fresh:
        return set()
    try:
        from toolbox.core import auth
        token = auth.session_token()
        counts = camp.load_domain_counts(token)
        print(f"  ledger: {len(counts)} domains already contacted (excluded from 'fresh')")
        return set(counts.keys())
    except Exception as e:  # noqa: BLE001 - any auth/network failure should degrade, not crash
        print(f"  ⚠ --check-fresh skipped: could not read ledger ({str(e)[:80]})")
        return set()


def _hunter_key() -> str | None:
    """Resolve the Hunter key the way run.py does, for the FREE email-count check.

    Only used to call /v2/email-count, which Hunter documents as zero-credit. The
    paid domain-search is never called by this probe.
    """
    try:
        from toolbox.core import auth
        return auth.get_token("hunter")
    except Exception:  # noqa: BLE001
        import os
        return os.environ.get("TOOLBOX_TOKEN_HUNTER")


def _precheck_pass_count(domains: list[str], key: str) -> int:
    """Return how many of `domains` have >=1 indexed executive email (FREE call).

    Runs Hunter's /v2/email-count for each domain concurrently. This is the exact
    gate the real pipeline uses to skip domains before spending a find credit, so
    its pass-rate is the realistic upper bound on enrichment yield — measured here
    at zero credit cost.
    """
    import httpx
    from toolbox.primitives.findemail import cli as findemail_cli

    async def run() -> int:
        sem = asyncio.Semaphore(8)
        passed = 0

        async with httpx.AsyncClient(timeout=30) as client:
            async def one(d: str) -> None:
                nonlocal passed
                async with sem:
                    if await findemail_cli._hunter_email_count(client, key, d) > 0:
                        passed += 1

            await asyncio.gather(*(one(d) for d in domains))
        return passed

    return asyncio.run(run())


def probe(icp: str, target: int, max_niches: int, check_fresh: bool,
          precheck: bool, stall_after: int, out: str | None) -> int:
    """Run the discovery-only loop and print a yield report. Returns exit code."""
    contacted = _load_contacted(check_fresh)

    key = None
    if precheck:
        key = _hunter_key()
        if not key:
            print("  ⚠ --precheck skipped: no Hunter key "
                  "(set TOOLBOX_TOKEN_HUNTER or `toolbox auth login`)")
            precheck = False
        else:
            print("  precheck ON: running FREE /v2/email-count per domain "
                  "(no find credits spent)")

    # Isolate the sub-category cache so we never mark real niches as searched.
    tmp_cache = Path(tempfile.mkdtemp(prefix="discovery_probe_"))
    camp._SUBCAT_DIR = tmp_cache
    cache = camp.SubcategoryCache(icp)

    print(f"\nProbing discovery for ICP: {icp!r}")
    print(f"  target {target} unique domains · cap {max_niches} niches · "
          f"isolated cache {tmp_cache.name}\n")

    # Seed the first batch of niches (same sizing as a real run).
    import math
    n_seed = min(camp._SUBCAT_COUNT, max(5, math.ceil(target / 5)))
    t0 = time.time()
    niches = camp.generate_subcategories(icp, n_seed)
    cache.add(niches)
    print(f"seeded {len(cache.all_labels())} niches ({time.time()-t0:.0f}s)\n")

    unique: dict[str, None] = {}      # insertion-ordered set of unique domains
    fresh_unique: set[str] = set()    # unique AND never contacted
    per_niche: list[tuple[str, int, int]] = []  # (label, generated, fresh_new)
    niche_count = 0
    stall = 0
    precheck_tested = 0   # domains run through the free email-count gate
    precheck_passed = 0   # of those, how many have an indexed exec email

    while len(unique) < target and niche_count < max_niches:
        pending = cache.unsearched()
        if not pending:
            # Test the regeneration path: ask for more niches, excluding known ones.
            known = cache.all_labels()
            more = camp.generate_subcategories(icp, camp._SUBCAT_COUNT, known)
            newly = [s for s in more if s not in set(known)]
            cache.add(newly)
            print(f"  regenerated niches: {len(newly)} new of {len(more)} returned"
                  + ("  ⚠ none new — niche space exhausting" if not newly else ""))
            if not newly:
                print("  stopping: niche regeneration returned nothing new.")
                break
            pending = cache.unsearched()

        label = pending[0]
        cache.mark_searched(label)
        niche_count += 1

        domains = camp.generate_domains_for_subcat(
            label, camp._SUBCAT_DOMAIN_COUNT, exclude_domains=set(unique) | contacted
        )
        before = len(unique)
        for d in domains:
            unique.setdefault(d, None)
        new_unique = len(unique) - before
        new_fresh = 0
        for d in domains:
            if d not in contacted and d not in fresh_unique:
                fresh_unique.add(d)
                new_fresh += 1
        per_niche.append((label, len(domains), new_fresh))

        # FREE gate check: of the genuinely-new domains this niche added, how many
        # have an indexed executive email (i.e. would survive to a paid find)?
        pc_note = ""
        if precheck and key:
            # Test this niche's domains that we haven't already contacted.
            to_test = [d for d in domains if d not in contacted]
            passed = _precheck_pass_count(to_test, key)
            precheck_tested += len(to_test)
            precheck_passed += passed
            pc_note = f", {passed}/{len(to_test)} have exec email"

        fresh_note = f", {new_fresh} fresh" if check_fresh else ""
        print(f"  niche {niche_count:>3} · {label[:44]:<44} "
              f"{len(domains):>2} gen, {new_unique:>2} new uniq{fresh_note}{pc_note}"
              f"  → {len(unique)} total")

        # Stall detection: consecutive niches adding almost nothing new = real
        # exhaustion (or dedup collapse), not worth more LLM calls.
        if new_unique <= 1:
            stall += 1
            if stall >= stall_after:
                print(f"\n  stopping: {stall} niches in a row added <=1 new domain "
                      f"(market or generator exhausting for this ICP).")
                break
        else:
            stall = 0

    elapsed = time.time() - t0
    total_gen = sum(g for _, g, _ in per_niche)
    dup_rate = 1 - (len(unique) / total_gen) if total_gen else 0.0

    print("\n" + "=" * 60)
    print(f"ICP                : {icp}")
    print(f"niches searched    : {niche_count}")
    print(f"domains generated  : {total_gen}  (raw, incl. duplicates)")
    print(f"unique domains     : {len(unique)}")
    print(f"dedup collapse     : {dup_rate*100:.0f}%  (lower = niches are distinct)")
    print(f"avg new uniq/niche : {len(unique)/niche_count:.1f}" if niche_count else "n/a")
    if check_fresh:
        print(f"fresh (uncontacted): {len(fresh_unique)}  "
              f"({len(fresh_unique)/max(1,len(unique))*100:.0f}% of unique)")
    if precheck and precheck_tested:
        pass_rate = precheck_passed / precheck_tested
        print(f"exec-email gate    : {precheck_passed}/{precheck_tested} pass "
              f"({pass_rate*100:.0f}%)  ← realistic enrichment yield, $0 to measure")
    print(f"time               : {elapsed:.0f}s")

    # Projections. Without precheck we can only project unique-domain supply; with
    # it we project actual qualifying contacts and the paid-credit cost to hit target.
    if precheck and precheck_tested:
        pass_rate = precheck_passed / precheck_tested
        contacts_per_niche = (len(unique) / niche_count) * pass_rate if niche_count else 0
        if contacts_per_niche >= 0.5:
            need_niches = math.ceil(target / contacts_per_niche)
            # Each domain that passes the gate costs ~1 find credit.
            credits = math.ceil(need_niches * (len(unique) / niche_count) * pass_rate)
            print(f"projection         : ~{need_niches} niches and ~{credits} Hunter "
                  f"credits to reach {target} qualifying contacts")
            print(f"                     (you topped out short because the gate, not "
                  f"generation, is the ceiling)")
        else:
            print("projection         : exec-email pass-rate too low for this ICP — "
                  "Hunter simply has few findable execs here; widen the ICP or change source")
    elif niche_count and len(unique) < target:
        rate = len(unique) / niche_count
        if rate > 0.5:
            need = math.ceil(target / rate)
            print(f"projection         : ~{need} niches to reach {target} unique domains "
                  f"at {rate:.1f}/niche  (run with --precheck to project actual contacts)")
        else:
            print("projection         : yield per niche too low — ICP space looks thin "
                  "or the exclusion list is forcing repeats")
    print("=" * 60)

    if out:
        with open(out, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["domain", "fresh"])
            for d in unique:
                w.writerow([d, "" if not check_fresh else ("yes" if d not in contacted else "no")])
        print(f"\nwrote {len(unique)} domains → {out}")

    # Exit non-zero if we clearly stalled well short of target, so this can gate CI.
    return 0 if (len(unique) >= target or niche_count >= max_niches) else 1


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--icp", required=True, help="ICP description to probe")
    ap.add_argument("--target", type=int, default=2000,
                    help="target unique domains (default 2000)")
    ap.add_argument("--max-niches", type=int, default=40,
                    help="cap on niches/LLM calls — bounds runtime (default 40, ~9min)")
    ap.add_argument("--check-fresh", action="store_true",
                    help="also count genuinely-new domains via the Supabase ledger (free read)")
    ap.add_argument("--precheck", action="store_true",
                    help="measure the real exec-email pass-rate via Hunter's FREE "
                         "/v2/email-count (no find credits) — the actual 300/700 gate")
    ap.add_argument("--stall-after", type=int, default=5,
                    help="stop after N consecutive niches adding <=1 new domain (default 5)")
    ap.add_argument("--out", help="write the unique domains to this CSV")
    args = ap.parse_args()
    sys.exit(probe(args.icp, args.target, args.max_niches, args.check_fresh,
                   args.precheck, args.stall_after, args.out))


if __name__ == "__main__":
    main()
