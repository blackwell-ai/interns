#!/usr/bin/env python3
"""Campaign orchestrator: ICP description -> source leads -> enrich -> compose -> send.

Providers:
  hunter / apollo   API-based. Claude generates target domains from your ICP,
                    then the provider finds the decision-maker email per domain.
  clay / origami    CSV export. Export leads from the tool's UI, pass with --leads.
                    We compose and send from that list directly.

Experiment mode (--experiment):
  Leads are split 50/50. Claude generates a meaningfully different variant B.
  Reply rates are tracked per variant in Supabase. Use reply_report.py to see results.

Usage:
  python3 skills/campaign/run.py \\
    --icp "DTC health and wellness brands" \\
    --provider hunter \\
    --from shamit.dsouza@gmail.com \\
    --from-name "Shamit" \\
    --experiment \\
    --limit 20 \\
    --dry-run

  # Clay/Origami: export CSV first, then:
  python3 skills/campaign/run.py \\
    --leads my_export.csv \\
    --provider clay \\
    --from shamit.dsouza@gmail.com \\
    --from-name "Shamit"
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import html as _html_module
import json
import math
import os
import re
import subprocess
import sys
import tempfile
import time
import tomllib
import uuid
from datetime import UTC, datetime
from pathlib import Path

import httpx
from pydantic import BaseModel

# Allow running as a standalone script from the repo root.
_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))
sys.path.insert(0, str(_REPO_ROOT / "toolbox" / "src"))

from toolbox.core import auth, config, events, io, ledger, models
from toolbox.core import llm as llm_mod
from toolbox.primitives.compose import lib as compose_lib
from toolbox.primitives.findemail import cli as findemail_cli
from toolbox.primitives.gmail import cli as gmail_cli
from skills.campaign import gog_auth, storeleads, visibility


# ---- LLM helpers -------------------------------------------------------

class _DomainList(BaseModel):
    domains: list[str]


class _SubcategoryList(BaseModel):
    subcategories: list[str]


class _VariantTemplate(BaseModel):
    subject: str
    body: str


class _SubcatFilters(BaseModel):
    """How a niche maps onto the StoreLeads e-commerce database.

    `applicable` is False when the niche is not consumer e-commerce (B2B
    services, logistics, software, manufacturing) — StoreLeads only indexes
    online stores, so those niches fall back to LLM domain generation.
    """
    applicable: bool
    q: str = ""        # keyword query matched against store descriptions
    category: str = "" # optional StoreLeads category path (e.g. "/Apparel")


# Each claude -p call reliably returns ~50 good domains; past that it repeats
# household names. A large pool is built from several calls, each nudged toward a
# different slice of the market to cut overlap.
#
# Measured: concurrent claude -p calls THROTTLE each other (the Claude
# subscription serializes inference) — 2 at once took 35s vs 13s for one. So
# domain generation is capped at 1 in flight. The speedup instead comes from
# running every segment as one job (not six separate invocations) and letting
# Hunter enrichment, which is real parallel HTTP, overlap the serial LLM calls.
def _banner(label: str) -> None:
    """Print a phase header so stage transitions are visible in streamed output."""
    bar = "─" * max(0, 60 - len(label) - 4)
    print(f"\n── {label} {bar}", flush=True)


_DOMAIN_CHUNK = 50
_LLM_CONCURRENCY = 1  # concurrent claude -p HURTS; serialize, overlap enrichment

# StoreLeads sourcing. When TOOLBOX_TOKEN_STORELEADS is set, each niche's domains
# come from real, live stores in the StoreLeads database instead of Claude
# guessing names. _STORELEADS_PER_NICHE real domains beat the ~20 Claude can
# recall before inventing. f:ds=Active keeps dead/parked stores out.
_STORELEADS_PER_NICHE = 50
_STORELEADS_BASE_FILTERS = {"f:ds": "Active"}
_FILL_TOLERANCE = 3   # don't fire another LLM/Hunter round when this few contacts short

# Credit circuit breakers for source_contacts_pipeline. A bug in enrichment
# (e.g. every domain raising) must never run away generating fresh niches and
# burning paid Hunter calls forever. These two caps bound the worst case.
_MAX_ENRICH_ERRORS_NO_PROGRESS = 20  # abort if this many enrichment calls fail without yielding a single contact
_MAX_SOURCING_NICHES = 60            # absolute cap on niches generated in one sourcing run (anti-infinite-loop backstop)
_DOMAIN_VARIATIONS = [
    "",
    "Focus on smaller and mid-market companies, not just the biggest brands.",
    "Focus on newer or niche companies founded in the last few years.",
    "Avoid the most obvious household names; include lesser-known players.",
    "Include relevant companies based outside the United States.",
    "Focus on specialized or sub-category players within this space.",
]


def _niche_cap(limit: int) -> int:
    """Per-run ceiling on niches searched, scaled to the requested contact count.

    The flat 60-niche backstop (~1200 domains, ~1000 new contacts after dedup and
    enrichment misses) means a single run can never fill a 2000 ask — it hits the
    cap and quits short. Scale the cap with the ask, roughly one niche per eight
    wanted contacts, while keeping 60 as the floor so small runs still get a
    generous explore budget. Credit burn stays bounded by the independent
    enrichment-error circuit breaker, so a higher niche cap is safe.
    """
    return max(_MAX_SOURCING_NICHES, math.ceil(max(0, limit) / 8))


def _normalize_icp(icp: str) -> str:
    """Canonical form of an ICP string, used as the sub-category cache key.

    Casing, surrounding whitespace, and trailing punctuation differences
    ('DTC brands', 'dtc  brands', 'DTC brands.') must resolve to one niche and
    exclusion memory rather than fragmenting into separate caches that each
    re-explore the market from scratch. Typos are intentionally left alone — we
    cannot safely guess intent — so they still fork their own cache.
    """
    import re
    return re.sub(r"\s+", " ", icp.strip().lower()).rstrip(".,;:!?")

_SUBCAT_DIR          = Path.home() / ".blackwell" / "subcats"
_SUBCAT_COUNT        = 25   # sub-categories to generate per ICP
_SUBCAT_DOMAIN_COUNT = 20   # domains to request per sub-category


class SubcategoryCache:
    """Persist which sub-categories have been generated and searched for an ICP.

    Stored at ~/.blackwell/subcats/<icp_hash>.json so runs across sessions pick
    up where the previous run left off — unexplored niches first, never repeating
    a sub-category whose domains have already gone to Hunter.
    """

    def __init__(self, icp: str) -> None:
        import hashlib
        slug = hashlib.md5(_normalize_icp(icp).encode()).hexdigest()[:12]
        self._path = _SUBCAT_DIR / f"{slug}.json"
        self._data: dict = self._load(icp)

    def _load(self, icp: str) -> dict:
        if self._path.exists():
            try:
                return json.loads(self._path.read_text())
            except Exception:
                pass
        return {"icp": icp, "subcategories": []}

    def _save(self) -> None:
        _SUBCAT_DIR.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(self._data, indent=2))

    def all_labels(self) -> list[str]:
        return [s["label"] for s in self._data["subcategories"]]

    def unsearched(self) -> list[str]:
        return [s["label"] for s in self._data["subcategories"] if not s.get("searched")]

    def add(self, labels: list[str]) -> None:
        existing = {s["label"] for s in self._data["subcategories"]}
        for label in labels:
            if label.strip() and label not in existing:
                self._data["subcategories"].append({"label": label, "searched": False})
        self._save()

    def mark_searched(self, label: str) -> None:
        for s in self._data["subcategories"]:
            if s["label"] == label:
                s["searched"] = True
        self._save()


def generate_subcategories(icp: str, count: int = _SUBCAT_COUNT,
                           exclude_labels: list[str] | None = None,
                           critique: bool = True) -> list[str]:
    """Ask Claude to map the ICP into specific, narrow sub-categories.

    `exclude_labels` are already-known niches passed verbatim into the prompt so
    a second call (when all sub-categories are exhausted) returns fresh niches.

    The biggest failure here is intent drift: an ICP like "affiliate marketing
    companies" gets read as "companies that RUN affiliate programs", which returns
    big consumer brands (Robinhood, Coinbase) instead of affiliate businesses. The
    prompt is written to read the market literally, and `critique` runs a second
    pass that drops any niche that wandered into a different industry.
    """
    exclude_note = ""
    if exclude_labels:
        exclude_note = (
            "\n\nDo NOT suggest any of these already-explored sub-categories:\n"
            + ", ".join(exclude_labels[:60])
        )
    result = llm_mod.parse(
        f"Map this target market into specific, narrow sub-categories: {icp}\n\n"
        "Read the market literally. Every sub-category must name a group of "
        "companies that ARE this kind of business. Never list companies that "
        "merely use, buy, have, or run this thing. For example, for 'affiliate "
        "marketing companies' the answer is affiliate networks, partner/affiliate "
        "SaaS, and performance-marketing agencies, NOT well-known brands that "
        "happen to run an affiliate program.\n\n"
        f"Generate {count} sub-categories. Each must be narrow enough that there are "
        "10-30 real companies in it, not hundreds. Make them distinct with no overlap. "
        "Do not name any specific companies. Phrase each one as '<qualifier> "
        "<target market>' so it stays anchored to the market above.\n"
        "Example for 'DTC brands': 'DTC maternity clothing', 'DTC men's grooming', "
        "'DTC pet supplements', 'DTC functional beverages'."
        + exclude_note,
        _SubcategoryList,
    )
    subcats = [s.strip() for s in result.subcategories if s.strip()]
    if critique:
        subcats = _critique_subcategories(icp, subcats)
    return subcats


def _critique_subcategories(icp: str, subcats: list[str]) -> list[str]:
    """Drop sub-categories that drifted off the target market.

    A second, cheap structured call that audits the generated list against the
    ICP and returns only the niches that genuinely describe companies in that
    market. This is the catch for intent drift the generation prompt still lets
    through. It never zeroes out sourcing: if the audit keeps nothing (an overcautious
    pass) or errors, the original list is returned unchanged.
    """
    if not subcats:
        return subcats
    listing = "\n".join(f"- {s}" for s in subcats)
    try:
        result = llm_mod.parse(
            "You are auditing sub-categories generated for an outreach target "
            f"market.\nTarget market: {icp}\n\nSub-categories:\n{listing}\n\n"
            "Return only the sub-categories that genuinely describe companies that "
            "ARE in this target market. Drop any that drifted to a different "
            "industry, or that describe companies which merely use, buy, or run the "
            "thing rather than being it. Keep the wording of the kept ones exactly "
            "as given. If every sub-category is a good fit, return all of them.",
            _SubcategoryList,
        )
    except Exception as e:  # noqa: BLE001 - the audit is best-effort, never fatal
        events.emit("campaign.subcat_critique_error", level="warn",
                    reason=str(e)[:120], icp=icp)
        return subcats
    kept = [s.strip() for s in result.subcategories if s.strip()]
    dropped = [s for s in subcats if s not in set(kept)]
    if dropped:
        events.emit("campaign.subcat_critique_dropped", level="info",
                    icp=icp, dropped=dropped[:20], kept=len(kept))
    return kept or subcats


def generate_domains_for_subcat(
    subcat: str,
    count: int = _SUBCAT_DOMAIN_COUNT,
    exclude_domains: set[str] | None = None,
) -> list[str]:
    """Generate domains for one specific niche sub-category.

    Narrow sub-categories let Claude enumerate real companies without padding;
    20 domains per niche is the reliable ceiling before Claude invents names.
    """
    exclude_note = ""
    if exclude_domains:
        sample = sorted(exclude_domains)[:300]
        exclude_note = (
            "\n\nDo NOT return any of these — already contacted:\n"
            + ", ".join(sample)
        )
    result = llm_mod.parse(
        f"List {count} real company website domains in this specific niche: {subcat}\n"
        "Real companies only. No www prefix, no paths. Return only the domains "
        "(e.g. 'glossier.com')."
        + exclude_note,
        _DomainList,
    )
    return [d.strip().lower() for d in result.domains if "." in d.strip()]


def subcat_to_filters(subcat: str) -> _SubcatFilters:
    """Translate a free-text niche into StoreLeads search filters.

    One cheap structured LLM call. StoreLeads only indexes consumer e-commerce
    stores, so `applicable` gates non-store niches (B2B/logistics/software/
    manufacturing) back to LLM domain generation. The keyword `q` does the
    targeting; `category` narrows it when an obvious top-level category fits.
    """
    return llm_mod.parse(
        "Map this outreach niche onto the StoreLeads e-commerce store database.\n"
        f"Niche: {subcat}\n\n"
        "StoreLeads only indexes online stores that sell products directly to "
        "consumers (Shopify, WooCommerce, etc.).\n"
        "- applicable: true ONLY if this niche describes consumer e-commerce "
        "stores. false for B2B services, software, logistics/3PL, agencies, or "
        "manufacturers.\n"
        "- q: a short 2-4 word keyword query matching such stores' product "
        "descriptions (e.g. 'maternity clothing', 'pet supplements').\n"
        "- category: one StoreLeads top-level category path if an obvious one "
        "fits, else empty string. Examples: /Apparel, /Beauty & Fitness, "
        "/Home & Garden, /Health, /Food & Drink, /Sporting Goods, /Pet Supplies, "
        "/Electronics.",
        _SubcatFilters,
    )


async def source_domains_for_subcat(
    subcat: str,
    count: int = _SUBCAT_DOMAIN_COUNT,
    exclude: set[str] | None = None,
    llm_sem: asyncio.Semaphore | None = None,
) -> list[str]:
    """Real domains for one niche: StoreLeads first, LLM generation as fallback.

    StoreLeads returns confirmed-live e-commerce stores, so no Hunter credit is
    spent on hallucinated or dead domains. Falls back to
    generate_domains_for_subcat whenever StoreLeads cannot serve the niche: no
    token configured, the niche is not consumer e-commerce, or the query errors
    or returns nothing after excluding already-contacted domains.
    """

    async def _run_llm(fn, *a):
        if llm_sem is not None:
            async with llm_sem:
                return await asyncio.to_thread(fn, *a)
        return await asyncio.to_thread(fn, *a)

    async def _llm_fallback() -> list[str]:
        return await _run_llm(generate_domains_for_subcat, subcat, count, exclude)

    if not storeleads.available():
        return await _llm_fallback()

    try:
        filt = await _run_llm(subcat_to_filters, subcat)
    except Exception as e:
        events.emit("campaign.storeleads_filter_error", level="warn",
                    reason=str(e)[:120], subcat=subcat)
        return await _llm_fallback()

    if not filt.applicable or not filt.q.strip():
        return await _llm_fallback()

    q = filt.q.strip()
    category = filt.category.strip()
    try:
        domains, _cursor = await storeleads.search_domains(
            {**_STORELEADS_BASE_FILTERS, "f:cat": category} if category
            else dict(_STORELEADS_BASE_FILTERS),
            q=q, page_size=_STORELEADS_PER_NICHE,
        )
        # The category path is best-effort: the LLM can guess one that does not
        # exist in StoreLeads' taxonomy, which zeros an otherwise-good keyword
        # query. Retry once on the keyword alone before dropping to LLM guessing.
        if not domains and category:
            events.emit("campaign.storeleads_cat_miss", level="info",
                        subcat=subcat, category=category)
            domains, _cursor = await storeleads.search_domains(
                dict(_STORELEADS_BASE_FILTERS), q=q, page_size=_STORELEADS_PER_NICHE
            )
    except Exception as e:
        events.emit("campaign.storeleads_error", level="warn",
                    reason=str(e)[:120], subcat=subcat)
        return await _llm_fallback()

    if exclude:
        domains = [d for d in domains if d not in exclude]
    if not domains:
        # Real store DB had nothing usable for this niche — let the LLM try.
        return await _llm_fallback()

    events.emit("campaign.storeleads_hit", level="info",
                subcat=subcat, count=len(domains), q=filt.q.strip())
    print(f"  [storeleads] {subcat}: {len(domains)} real stores (q='{filt.q.strip()}')",
          flush=True)
    return domains


def generate_domains(
    icp: str,
    count: int = 30,
    variation: str = "",
    exclude_domains: set[str] | None = None,
) -> list[str]:
    """One claude -p call for real company domains matching the ICP.

    `variation` is an optional nudge appended to the prompt so that fanning out
    several calls returns different companies instead of the same top brands.
    `exclude_domains` is passed verbatim into the prompt so the LLM never
    regenerates domains we have already contacted.
    """
    extra = f"\n{variation}" if variation else ""
    exclude_note = ""
    if exclude_domains:
        sample = sorted(exclude_domains)[:500]  # cap prompt length
        exclude_note = (
            f"\n\nDo NOT return any of these domains — they have already been contacted:\n"
            + ", ".join(sample)
        )
    result = llm_mod.parse(
        f"List {count} real company website domains (e.g. 'glossier.com') that fit this "
        f"ideal customer profile: {icp}\n\n"
        "Return actual, real companies. Prefer DTC/e-commerce. No www prefix, no paths."
        + extra
        + exclude_note,
        _DomainList,
    )
    return [d.strip().lower() for d in result.domains if "." in d.strip()]


async def generate_domain_pool(
    icp: str, count: int, llm_sem: asyncio.Semaphore | None = None, label: str = ""
) -> list[str]:
    """Build a deduped pool of ~`count` domains via concurrent claude -p calls.

    The blocking subprocess runs off the event loop (asyncio.to_thread) so the
    calls overlap. `llm_sem` caps how many run at once across all segments. Each
    batch is streamed to the domains file and the terminal the moment it comes
    back, so the slow generation step is visible instead of looking frozen.
    """
    if llm_sem is None:
        llm_sem = asyncio.Semaphore(_LLM_CONCURRENCY)
    n_calls = max(1, math.ceil(count / _DOMAIN_CHUNK))

    async def one(i: int) -> list[str]:
        async with llm_sem:
            try:
                chunk = await asyncio.to_thread(
                    generate_domains, icp, _DOMAIN_CHUNK,
                    _DOMAIN_VARIATIONS[i % len(_DOMAIN_VARIATIONS)],
                )
            except Exception as e:
                events.emit("campaign.domaingen_error", level="warn", reason=str(e)[:120])
                return []
            # Stream the batch as soon as the LLM call returns.
            _write_domains_rows(label, chunk)
            tag = f"[{label}] " if label else ""
            print(f"{tag}generated {len(chunk)} domains (call {i + 1}/{n_calls})", flush=True)
            return chunk

    seen: set[str] = set()
    pool: list[str] = []
    for chunk in await asyncio.gather(*(one(i) for i in range(n_calls))):
        for d in chunk:
            if d not in seen:
                seen.add(d)
                pool.append(d)
    return pool


def generate_variant_b(subject_a: str, body_a: str) -> tuple[str, str]:
    """Ask Claude to write a meaningfully different A/B variant."""
    result = llm_mod.parse(
        "You are an A/B testing expert for cold email outreach. Here is variant A:\n\n"
        f"Subject: {subject_a}\n\n{body_a}\n\n"
        "Write variant B that tests a distinctly different angle or tone. Same sender "
        "context (Stanford/Dartmouth students building AI tools for DTC brands). "
        "Subject must be different. Body must differ in structure or length. "
        "Use {{first_name}} and {{company}} template slots.",
        _VariantTemplate,
    )
    return result.subject, result.body


# ---- Lead sourcing / enrichment ----------------------------------------

def load_leads_csv(path: str, min_score: int = 0) -> list[models.Contact]:
    """Load a pre-exported Clay/Origami CSV into Contact objects."""
    rows = io.read_csv(path, models.Row)
    contacts: list[models.Contact] = []
    for r in rows:
        d = r.model_dump()
        # Clay exports sometimes put the company name in 'company' or 'brand'
        if not d.get("company") and d.get("brand"):
            d["company"] = d["brand"]
        try:
            contacts.append(models.Contact(**d))
        except (ValueError, TypeError) as e:
            events.emit("campaign.bad_lead", level="warn", row=str(d)[:120], reason=str(e))
    return contacts


def _hunter_searches_used(key: str) -> int:
    """Return Hunter's authoritative searches.used counter from the account API."""
    try:
        import urllib.request as _ur
        req = _ur.Request(
            f"https://api.hunter.io/v2/account?api_key={key}",
            headers={"Accept": "application/json"},
        )
        with _ur.urlopen(req, timeout=10) as r:
            return int(json.loads(r.read())["data"]["requests"]["searches"]["used"])
    except Exception:
        return -1

# Generated domains are streamed to a repo-local CSV as each claude -p call
# returns, so the slow generation step is visible (and its rate is measurable,
# which helps diagnose throttling). Set in main(); None = disabled.
_DOMAINS_PATH: str | None = None


def _write_domains_rows(segment: str, domains: list[str]) -> None:
    """Append a batch of freshly-generated domains to the live domains CSV.

    Every domain is logged as it is generated (duplicates included) with a
    timestamp, so the file doubles as a record of how fast generation is going.
    Safe under asyncio: writes happen on the single event-loop thread.
    """
    if not _DOMAINS_PATH or not domains:
        return
    p = Path(_DOMAINS_PATH)
    new = not p.exists() or p.stat().st_size == 0
    try:
        with p.open("a", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            if new:
                w.writerow(["generated_at", "segment", "domain"])
            ts = datetime.now(UTC).isoformat()
            for d in domains:
                w.writerow([ts, segment, d])
    except OSError as e:
        events.emit("campaign.domains_write_failed", level="warn", reason=str(e)[:120])


# Enriched contacts are streamed to a repo-local CSV as they are found, so a
# long run is fully visible (and inspectable) while it is still going. Set once
# in main(); _enrich_batch appends to it. None = disabled (e.g. CSV-leads runs).
_ENRICHED_PATH: str | None = None
_ENRICHED_HEADER = ["enriched_at", "email", "first_name", "last_name", "title",
                    "company", "domain", "email_score", "email_status"]


def _write_enriched_row(domain: str, res: dict) -> None:
    """Append one freshly-enriched contact to the live CSV (no-op if unset).

    Runs inside the single-threaded asyncio loop, so a plain append is safe:
    no two writes interleave. The header is written once, on the first row.
    """
    if not _ENRICHED_PATH:
        return
    p = Path(_ENRICHED_PATH)
    new = not p.exists() or p.stat().st_size == 0
    try:
        with p.open("a", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            if new:
                w.writerow(_ENRICHED_HEADER)
            w.writerow([
                datetime.now(UTC).isoformat(), res.get("email", ""),
                res.get("first_name", ""), res.get("last_name", ""),
                res.get("title", ""), domain.split(".")[0].title(), domain,
                res.get("email_score", ""), res.get("email_status", ""),
            ])
    except OSError as e:
        events.emit("campaign.enriched_write_failed", level="warn", reason=str(e)[:120])


def load_enriched_cache(enriched_dir: Path) -> dict[str, list[dict]]:
    """Read all prior enriched_*.csv files → {domain: [result dicts]}.

    Used to skip Hunter API calls for domains already searched in a previous run.
    The current run's file does not exist yet when this is called, so it is
    naturally excluded.
    """
    cache: dict[str, list[dict]] = {}
    for csv_path in sorted(enriched_dir.glob("enriched_*.csv")):
        try:
            with csv_path.open(encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    domain = (row.get("domain") or "").strip().lower()
                    if not domain:
                        continue
                    cache.setdefault(domain, []).append(row)
        except OSError:
            continue
    return cache


async def _enrich_batch(
    client: httpx.AsyncClient,
    domains: list[str],
    provider: str,
    key: str,
    min_score: int,
    sem: asyncio.Semaphore | None = None,
    enriched_cache: dict | None = None,
    stats: dict | None = None,
) -> list[models.Contact]:
    """Enrich one batch of domains — returns contacts that passed the score filter.

    `sem` caps concurrent provider calls. Pass a shared one so that several
    segments enriching at the same time still respect a single global rate cap.
    `enriched_cache` is a {domain: [result dicts]} map built from prior enriched
    CSVs; domains found there skip the Hunter API call entirely.
    `stats`, if passed, is populated with {"attempted": n, "errors": n} for the
    batch — the caller uses it to drive a credit circuit breaker.
    """
    use_all = provider == "hunter"
    contacts: list[models.Contact] = []
    if sem is None:
        sem = asyncio.Semaphore(3)
    _stats = {"attempted": 0, "errors": 0}

    def _apply_results(domain: str, results: list[dict]) -> None:
        for res in results:
            if not res.get("email"):
                continue
            try:
                score = int(res.get("email_score") or 0)
            except (ValueError, TypeError):
                score = 0
            if score < min_score:
                events.emit("campaign.low_score", domain=domain, score=score)
                continue
            if res.get("email_status") == "accept_all":
                events.emit("campaign.accept_all_skip", level="warn", domain=domain)
                continue
            try:
                contacts.append(models.Contact(
                    email=res["email"],
                    first_name=res.get("first_name", ""),
                    last_name=res.get("last_name", ""),
                    title=res.get("title", ""),
                    company=res.get("company") or domain.split(".")[0].title(),
                    domain=domain,
                ))
            except ValueError as e:
                events.emit("campaign.bad_email", level="warn", email=res.get("email"), reason=str(e))
                continue
            _write_enriched_row(domain, res)
            print(f"  + {res['email']}  ({res.get('email_status', '')})  {domain}", flush=True)

    async def one(domain: str) -> None:
        # Fix 2: use cached results from a prior run — skip the paid Hunter call.
        if enriched_cache and domain in enriched_cache:
            events.emit("campaign.cache_hit", domain=domain)
            _apply_results(domain, enriched_cache[domain])
            return

        async with sem:
            try:
                _stats["attempted"] += 1
                if use_all:
                    # Fix 1: free pre-check — skip if Hunter has no executive emails.
                    exec_count = await findemail_cli._hunter_email_count(client, key, domain)
                    if exec_count == 0:
                        events.emit("campaign.email_count_skip", domain=domain)
                        return
                    results = await findemail_cli._hunter_domain_all(
                        client, key, domain, limit=10, executives_only=True
                    )
                else:
                    single = await findemail_cli._apollo_domain(
                        client, key, domain, limit=10, executives_only=True
                    )
                    results = [single] if single and single.get("email") else []
            except Exception as e:
                _stats["errors"] += 1
                msg = str(e)
                if "429" in msg:
                    events.emit("campaign.rate_limited", level="warn", domain=domain)
                else:
                    events.emit("campaign.enrich_error", level="warn", domain=domain, reason=msg[:120])
                return

        if not results:
            events.emit("campaign.no_contact", domain=domain)
            return

        _apply_results(domain, results)

    await asyncio.gather(*(one(d) for d in domains))
    if stats is not None:
        stats.update(_stats)
    return contacts


async def enrich_domains(
    domains: list[str],
    provider: str,
    key: str,
    min_score: int = 80,
    enriched_cache: dict | None = None,
) -> list[models.Contact]:
    """Enrich all domains at once. Used when --domains is provided (pool already fixed)."""
    async with httpx.AsyncClient(timeout=60) as client:
        return await _enrich_batch(client, domains, provider, key, min_score,
                                   enriched_cache=enriched_cache)


async def source_contacts_incremental(
    domains: list[str],
    provider: str,
    key: str,
    session_token: str,
    limit: int | None,
    min_score: int = 80,
    batch_size: int = 20,
    hunter_sem: asyncio.Semaphore | None = None,
    label: str = "",
    enriched_cache: dict | None = None,
) -> list[models.Contact]:
    """Enrich domains in batches, ledger-checking each batch before continuing.

    Stops as soon as `limit` new contacts are accumulated. This avoids spending
    enrichment credits on contacts that will be discarded after ledger dedup.
    `hunter_sem` is a shared provider-call cap when several segments run at once.
    """
    accumulated: list[models.Contact] = []
    ldg = ledger.Ledger(session_token)

    async with httpx.AsyncClient(timeout=60) as client:
        for i in range(0, len(domains), batch_size):
            batch = domains[i : i + batch_size]
            raw = await _enrich_batch(client, batch, provider, key, min_score, hunter_sem,
                                      enriched_cache=enriched_cache)

            # Ledger-check this batch concurrently.
            sem = asyncio.Semaphore(10)
            new_in_batch: list[tuple[int, models.Contact]] = []

            async def check_one(idx: int, c: models.Contact) -> None:
                async with sem:
                    status = await ldg.check("email", c.email)
                if status == "new":
                    new_in_batch.append((idx, c))

            await asyncio.gather(*(check_one(j, c) for j, c in enumerate(raw)))
            new_in_batch.sort(key=lambda x: x[0])
            accumulated.extend(c for _, c in new_in_batch)

            enriched_so_far = i + len(batch)
            tag = f"[{label}] " if label else ""
            target = f"/{limit}" if limit else ""
            print(
                f"{tag}batch {i // batch_size + 1}: {len(raw)} enriched, "
                f"{len(new_in_batch)} new, {len(accumulated)}{target} sourced "
                f"({enriched_so_far}/{len(domains)} domains tried)",
                flush=True,
            )

            if limit and limit - len(accumulated) <= _FILL_TOLERANCE:
                break

    await ldg.aclose()
    return accumulated


# ---- Domain-count soft filter ------------------------------------------

def load_domain_counts(session_token: str) -> dict[str, int]:
    """One Supabase round-trip → {domain: times_already_contacted}."""
    try:
        r = httpx.get(
            f"{config.supabase_url()}/rest/v1/contacted",
            headers={
                "apikey": config.supabase_anon_key(),
                "Authorization": f"Bearer {session_token}",
            },
            params={"select": "recipient", "channel": "eq.email"},
            timeout=30,
        )
        if r.status_code != 200:
            return {}
        counts: dict[str, int] = {}
        for row in r.json():
            recipient = row.get("recipient", "")
            if "@" in recipient:
                domain = recipient.split("@")[1].lower()
                counts[domain] = counts.get(domain, 0) + 1
        return counts
    except Exception:
        return {}


def filter_by_domain_count(
    items: list,
    domain_counts: dict[str, int],
    max_count: int,
) -> list:
    """Drop items whose domain has already been contacted >= max_count times.

    Works for both Contact objects and plain domain strings.
    """
    if max_count <= 0 or not domain_counts:
        return items

    def _domain(x) -> str:
        if isinstance(x, str):
            return x.lower()
        d = getattr(x, "domain", "") or ""
        if not d:
            email = getattr(x, "email", "")
            d = email.split("@")[-1] if "@" in email else ""
        return d.lower()

    kept, dropped = [], 0
    for item in items:
        if domain_counts.get(_domain(item), 0) >= max_count:
            dropped += 1
        else:
            kept.append(item)
    if dropped:
        print(f"  {dropped} skipped (domain already contacted >= {max_count}x)")
    return kept


# ---- Pipeline: interleave LLM generation with Hunter enrichment ---------

async def source_contacts_pipeline(
    icp: str,
    provider: str,
    key: str,
    session_token: str,
    limit: int,
    min_score: int = 80,
    domain_counts: dict | None = None,
    max_domain_count: int = 0,
    llm_sem: asyncio.Semaphore | None = None,
    hunter_sem: asyncio.Semaphore | None = None,
    label: str = "",
    enriched_cache: dict | None = None,
) -> list[models.Contact]:
    """Generate domains via sub-category decomposition and enrich in a pipeline.

    Phase 1 (one LLM call): decompose the ICP into ~25 narrow niches and persist
    them to ~/.blackwell/subcats/. Subsequent runs load the cache and skip niches
    already searched — only fresh niches get new LLM + Hunter calls.

    Phase 2 (interleaved): while Hunter enriches batch N, the LLM generates
    domains for the next niche (batch N+1). Stops when `limit` new contacts
    clear the ledger dedup check — no wasted credits past that point.
    """
    if llm_sem is None:
        llm_sem = asyncio.Semaphore(_LLM_CONCURRENCY)
    if hunter_sem is None:
        hunter_sem = asyncio.Semaphore(8)

    accumulated: list[models.Contact] = []
    seen_domains: set[str] = set()
    ldg = ledger.Ledger(session_token)
    batch_num = 0
    niche_num = 0
    max_niches = _niche_cap(limit)  # scales with the ask; floor of _MAX_SOURCING_NICHES
    errors_since_progress = 0  # resets whenever a batch yields a new contact
    tag = f"[{label}] " if label else ""

    # ---- Phase 1: load or generate sub-categories ----------------------
    subcat_cache = SubcategoryCache(icp)
    if not subcat_cache.all_labels():
        n_subcats = min(_SUBCAT_COUNT, max(5, math.ceil(limit / 5)))
        print(f"{tag}generating {n_subcats} sub-categories for ICP...", flush=True)
        async with llm_sem:
            subcats = await asyncio.to_thread(generate_subcategories, icp, n_subcats)
        subcat_cache.add(subcats)
        preview = ", ".join(subcats[:5])
        suffix = f" +{len(subcats)-5} more" if len(subcats) > 5 else ""
        print(f"{tag}  {len(subcats)} niches: {preview}{suffix}", flush=True)
    else:
        pending = subcat_cache.unsearched()
        print(f"{tag}loaded sub-category cache — {len(pending)} niches unsearched", flush=True)

    # ---- Inner helpers -------------------------------------------------

    async def _gen_batch() -> tuple[list[str], str]:
        """Pick the next unsearched sub-category and generate domains for it.

        Returns (domains, subcat_label). When all sub-categories are exhausted,
        generates a fresh set (passing existing labels as exclusions) and
        continues. Returns ([], "") only if generation truly fails.
        """
        pending = subcat_cache.unsearched()
        if not pending:
            print(f"{tag}all sub-categories searched — generating more...", flush=True)
            known = subcat_cache.all_labels()
            async with llm_sem:
                new = await asyncio.to_thread(generate_subcategories, icp,
                                              _SUBCAT_COUNT, known)
            fresh = [s for s in new if s not in set(known)]
            if not fresh:
                return [], ""
            subcat_cache.add(fresh)
            pending = fresh

        subcat = pending[0]
        exclude = set(domain_counts.keys()) if domain_counts else None
        # StoreLeads-primary (real stores), LLM-fallback. The dispatcher acquires
        # llm_sem itself only around the LLM calls it makes (filter translation /
        # fallback generation); StoreLeads HTTP needs no LLM slot.
        try:
            domains = await source_domains_for_subcat(
                subcat, _SUBCAT_DOMAIN_COUNT, exclude, llm_sem=llm_sem
            )
            return domains, subcat
        except Exception as e:
            events.emit("campaign.domaingen_error", level="warn",
                        reason=str(e)[:120], subcat=subcat)
            return [], subcat

    async def _ledger_filter(contacts: list[models.Contact]) -> list[models.Contact]:
        sem = asyncio.Semaphore(10)
        new: list[models.Contact] = []

        async def check(c: models.Contact) -> None:
            async with sem:
                if await ldg.check("email", c.email) == "new":
                    new.append(c)

        await asyncio.gather(*(check(c) for c in contacts))
        return new

    # ---- Phase 2: interleaved generation + enrichment ------------------
    try:
        raw_next, next_subcat = await _gen_batch()

        async with httpx.AsyncClient(timeout=60) as client:
            while len(accumulated) < limit:
                current = [d for d in raw_next if d not in seen_domains]
                current_subcat = next_subcat
                seen_domains.update(current)

                if not current:
                    if not current_subcat:  # truly exhausted
                        break
                    # Empty batch (all domains already seen) — advance to next niche.
                    if current_subcat:
                        subcat_cache.mark_searched(current_subcat)
                    raw_next, next_subcat = await _gen_batch()
                    continue

                if domain_counts and max_domain_count > 0:
                    current = filter_by_domain_count(current, domain_counts, max_domain_count)

                # Mark this niche searched now that its domains go to Hunter.
                if current_subcat:
                    niche_num += 1
                    bar = "─" * max(0, 54 - len(current_subcat) - len(tag))
                    print(f"\n{tag}── niche {niche_num} · {current_subcat} {bar}", flush=True)
                    subcat_cache.mark_searched(current_subcat)

                # Fire next niche LLM call concurrently with Hunter enrichment.
                next_gen = asyncio.create_task(_gen_batch())

                batch_stats: dict = {}
                enriched = await _enrich_batch(client, current, provider, key, min_score,
                                               sem=hunter_sem, enriched_cache=enriched_cache,
                                               stats=batch_stats)
                new_contacts = await _ledger_filter(enriched)
                accumulated.extend(new_contacts)
                batch_num += 1
                pct = int(len(accumulated) / limit * 100)
                print(f"{tag}  {len(enriched)} enriched, {len(new_contacts)} new "
                      f"— {len(accumulated)}/{limit} contacts ({pct}%)", flush=True)

                # Credit circuit breaker: if enrichment keeps failing and we have
                # found nothing, stop before another niche burns more paid calls.
                if new_contacts:
                    errors_since_progress = 0
                else:
                    errors_since_progress += batch_stats.get("errors", 0)
                if errors_since_progress >= _MAX_ENRICH_ERRORS_NO_PROGRESS:
                    events.emit("campaign.circuit_break", level="error",
                                reason="enrichment failing with no contacts found — aborting to stop credit burn",
                                errors=errors_since_progress, niches=niche_num)
                    print(f"{tag}  ⚠ circuit breaker: {errors_since_progress} enrichment "
                          f"failures, 0 contacts — aborting run", flush=True)
                    next_gen.cancel()
                    break

                # Absolute backstop against an unbounded niche-generation loop.
                if niche_num >= max_niches:
                    events.emit("campaign.circuit_break", level="warn",
                                reason="reached max niches per sourcing run",
                                niches=niche_num, contacts=len(accumulated))
                    print(f"{tag}  ⚠ reached {niche_num}-niche cap — stopping", flush=True)
                    next_gen.cancel()
                    break

                if limit - len(accumulated) <= _FILL_TOLERANCE:
                    next_gen.cancel()
                    break

                raw_next, next_subcat = await next_gen
    finally:
        await ldg.aclose()

    print(f"\n{tag}sourced {len(accumulated)}/{limit} contacts across {niche_num} niches",
          flush=True)
    return accumulated


# ---- Ledger pre-check --------------------------------------------------

async def _filter_new_contacts(contacts: list[models.Contact], session_token: str) -> list[models.Contact]:
    """Remove contacts already in the ledger so --limit counts actual sends."""
    ldg = ledger.Ledger(session_token)
    sem = asyncio.Semaphore(10)
    results: list[tuple[int, models.Contact]] = []

    async def check_one(i: int, c: models.Contact) -> None:
        async with sem:
            status = await ldg.check("email", c.email)
        if status == "new":
            results.append((i, c))

    try:
        await asyncio.gather(*(check_one(i, c) for i, c in enumerate(contacts)))
    finally:
        await ldg.aclose()

    results.sort(key=lambda x: x[0])
    return [c for _, c in results]


# ---- ICP mix -----------------------------------------------------------

_ICP_MIX_PATH = Path(__file__).parent / "icp_mix.toml"


def _load_mix() -> list[dict]:
    with open(_ICP_MIX_PATH, "rb") as f:
        data = tomllib.load(f)
    return data["segments"]


def _mix_quotas(limit: int, segments: list[dict]) -> list[tuple[dict, int]]:
    """Return (segment, quota) pairs that sum exactly to limit."""
    raw = [(s, s["weight"] * limit) for s in segments]
    quotas = [(s, int(q)) for s, q in raw]
    remainder = limit - sum(q for _, q in quotas)
    # Distribute leftover slots to segments with the largest fractional parts.
    fracs = sorted(range(len(raw)), key=lambda i: -(raw[i][1] % 1))
    for i in range(remainder):
        seg, q = quotas[fracs[i]]
        quotas[fracs[i]] = (seg, q + 1)
    return [(s, q) for s, q in quotas if q > 0]


_DOMAINS_DIR = Path(__file__).parent / "domains"


def _segment_slug(label: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_")


async def _source_from_mix(
    provider: str,
    key: str,
    session_token: str,
    limit: int,
    from_name: str = "",
    min_score: int = 80,
    enrich_concurrency: int = 8,
    domain_counts: dict | None = None,
    max_domain_count: int = 0,
    experiment: bool = False,
    enriched_cache: dict | None = None,
) -> tuple[list[models.OutboxRow], list[models.OutboxRow]]:
    """Source and compose outbox rows across segments per icp_mix.toml.

    All segments are sourced concurrently. Two shared semaphores keep the
    fan-out from overwhelming the providers: `llm_sem` caps concurrent domain
    generation (claude -p subprocesses) and `hunter_sem` caps concurrent
    enrichment calls, both globally across every segment.

    Returns (outbox_a, outbox_b). outbox_b is non-empty only when experiment=True.
    """
    segments = _load_mix()
    quotas = _mix_quotas(limit, segments)
    llm_sem = asyncio.Semaphore(_LLM_CONCURRENCY)
    hunter_sem = asyncio.Semaphore(enrich_concurrency)

    async def source_segment(seg: dict, quota: int) -> tuple[list[models.OutboxRow], list[models.OutboxRow]]:
        label = seg["label"]
        icp = seg["icp"]
        template_path = _ICP_MIX_PATH.parent / seg["template_a"]
        segment_phrase = seg.get("segment_phrase", label.lower())

        domain_file = _DOMAINS_DIR / f"{_segment_slug(label)}.csv"
        if domain_file.exists():
            domain_rows = io.read_csv(str(domain_file), models.Domain)
            domains = [r.domain for r in domain_rows]
            print(f"[{label}] loaded {len(domains)} domains from {domain_file.name}")
            if domain_counts and max_domain_count > 0:
                domains = filter_by_domain_count(domains, domain_counts, max_domain_count)
            print(f"[{label}] {len(domains)} domains; enriching...")
            contacts = await source_contacts_incremental(
                domains, provider, key, session_token,
                limit=quota, min_score=min_score, hunter_sem=hunter_sem, label=label,
                enriched_cache=enriched_cache,
            )
        else:
            print(f"[{label}] target {quota}: pipeline (LLM + Hunter interleaved)...")
            contacts = await source_contacts_pipeline(
                icp, provider, key, session_token,
                limit=quota, min_score=min_score,
                domain_counts=domain_counts, max_domain_count=max_domain_count,
                llm_sem=llm_sem, hunter_sem=hunter_sem, label=label,
                enriched_cache=enriched_cache,
            )
        print(f"[{label}] sourced {len(contacts)} contacts", flush=True)
        subject_a, body_a = load_template(str(template_path))
        extra = {"segment_phrase": segment_phrase}

        if experiment and len(contacts) >= 2:
            mid = max(1, len(contacts) // 2)
            contacts_a, contacts_b = contacts[:mid], contacts[mid:]
            template_b_rel = seg.get("template_b", "")
            if template_b_rel:
                template_b_path = _ICP_MIX_PATH.parent / template_b_rel
                subject_b, body_b = load_template(str(template_b_path))
            else:
                subject_b, body_b = await asyncio.to_thread(generate_variant_b, subject_a, body_a)
            rows_a = compose_outbox(contacts_a, subject_a, body_a, from_name, extra_values=extra)
            rows_b = compose_outbox(contacts_b, subject_b, body_b, from_name, extra_values=extra)
        else:
            rows_a = compose_outbox(contacts, subject_a, body_a, from_name, extra_values=extra)
            rows_b = []

        return rows_a, rows_b

    seg_pairs = await asyncio.gather(*(source_segment(s, q) for s, q in quotas))

    # Concurrent segments can't see each other's not-yet-sent picks in the
    # ledger, so dedup by email across all A and B rows before sending.
    seen: set[str] = set()
    all_a: list[models.OutboxRow] = []
    all_b: list[models.OutboxRow] = []
    for rows_a, rows_b in seg_pairs:
        for r in rows_a:
            if r.email not in seen:
                seen.add(r.email)
                all_a.append(r)
        for r in rows_b:
            if r.email not in seen:
                seen.add(r.email)
                all_b.append(r)
    return all_a, all_b


# ---- Compose -----------------------------------------------------------

def load_template(path: str) -> tuple[str, str]:
    return compose_lib.parse_template(Path(path).read_text(encoding="utf-8"))


# Team schools, Stanford pinned first so "working with a couple from X/Y" always
# reads Stanford-first regardless of who is sending.
_TEAM_SCHOOLS = ["Stanford", "Dartmouth", "Berkeley"]


def school_for_email(email: str) -> tuple[str, str]:
    """Map a sender email to (school, other_schools) for the brand template.

    School is derived from the address domain; other_schools is the rest of the
    team joined by '/'. Unknown domains fall back to Stanford.
    """
    domain = (email or "").rsplit("@", 1)[-1].lower()
    if "dartmouth" in domain:
        school = "Dartmouth"
    elif "berkeley" in domain:
        school = "Berkeley"
    else:
        school = "Stanford"
    others = "/".join(s for s in _TEAM_SCHOOLS if s != school)
    return school, others


def _html_to_text(html: str) -> str:
    """Strip HTML tags to produce a plain-text fallback for email clients."""
    text = re.sub(r"<br\s*/?>", "\n", html, flags=re.IGNORECASE)
    text = re.sub(r"</p>", "\n\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = _html_module.unescape(text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def _text_to_html(text: str) -> str:
    """Convert plain-text email body to Gmail-safe HTML.

    Uses <br><br> for paragraph breaks and a <div> wrapper — avoids <p> tag
    spacing issues and Gmail stripping <body> styles.
    """
    escaped = (
        text.strip()
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
    html_body = escaped.replace("\n\n", "<br><br>").replace("\n", "<br>")
    return (
        '<div style="font-family:Arial,sans-serif;font-size:14px;'
        'line-height:1.6;color:#222">'
        f"{html_body}</div>"
    )


async def _personalize_visibility(
    contacts: list[models.Contact],
    niche: str,
    concurrency: int,
) -> list[models.Contact]:
    """Set each contact's {{personal_line}} from an AI-visibility check.

    Runs the checks concurrently (bounded), and reconstructs each Contact with
    the extra `personal_line` field so it flows through model_dump() into
    compose. visibility.personalize never returns empty, so no row can later
    fail compose on an empty slot. A per-contact failure degrades to that
    contact's safe generic line, never dropping the contact.
    """
    sem = asyncio.Semaphore(max(1, concurrency))

    async def one(c: models.Contact) -> models.Contact:
        company = c.company or (c.domain.split(".")[0].title() if c.domain else "")
        slots = await visibility.personalize_slots(company, niche, domain=c.domain, sem=sem)
        # Every slot (personal_line, niche, competitors) rides on the contact via
        # extra="allow" so any of them can be used as a {{slot}} in the template.
        return models.Contact(**{**c.model_dump(), **slots})

    return await asyncio.gather(*(one(c) for c in contacts))


def compose_outbox(
    contacts: list[models.Contact],
    subject_t: str,
    body_t: str,
    from_name: str = "",
    extra_values: dict | None = None,
) -> list[models.OutboxRow]:
    is_html = body_t.lstrip().startswith("<")
    rows: list[models.OutboxRow] = []
    for c in contacts:
        values = {**c.model_dump(), "from_name": from_name}
        if extra_values:
            values.update(extra_values)
        # 'company' slot: fall back to domain stem if missing
        if not values.get("company") and values.get("domain"):
            values["company"] = values["domain"].split(".")[0].title()
        try:
            rendered_body = compose_lib.render(body_t, values)
            body = _html_to_text(rendered_body) if is_html else rendered_body
            body_html = rendered_body if is_html else _text_to_html(rendered_body)
            rows.append(models.OutboxRow(
                email=c.email,
                subject=compose_lib.render(subject_t, values),
                body=body,
                body_html=body_html,
                **{k: v for k, v in values.items()
                   if k not in ("email", "subject", "body", "body_html")
                   and isinstance(v, (str, int, float, bool))},
            ))
        except compose_lib.TemplateError as e:
            events.emit("campaign.compose_drop", level="warn", email=c.email, reason=str(e))
    return rows


# ---- Send --------------------------------------------------------------

async def _send_batch(
    outbox: list[models.OutboxRow],
    from_: str,
    from_name: str,
    run_id: str,
    run_dir: str,
    dry_run: bool,
    cc: str = "",
    concurrency: int = 8,
) -> dict:
    if dry_run:
        return {"sent": 0, "dry_run": len(outbox), "skipped_ledger": 0, "suppressed": 0,
                "failed": 0, "resumed_skip": 0, "quota_aborted": 0}

    # Get token from gog once; inject so gmail_cli._send_all picks it up.
    token = gog_auth.get_access_token(from_)
    os.environ["TOOLBOX_TOKEN_GMAIL"] = token
    try:
        return await gmail_cli._send_all(
            rows=outbox,
            run_dir=run_dir,
            run_id=run_id,
            skill="campaign",
            from_=from_,
            from_name=from_name,
            reply_to="",
            cc=cc,
            concurrency=concurrency,
            allow_recontact=False,
            sent_already=set(),
        )
    finally:
        os.environ.pop("TOOLBOX_TOKEN_GMAIL", None)


# ---- Campaign log (for reply_scan.py) ----------------------------------

def write_campaign_log(log_path: str, entries: list[dict]) -> None:
    p = Path(log_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as f:
        for entry in entries:
            f.write(json.dumps(entry) + "\n")


# ---- Supabase campaigns write ------------------------------------------

def _write_campaign_to_supabase(
    run_id: str, sender: str, sender_email: str, provider: str,
    template_name: str, icp: str, experiment: bool, sent_count: int,
) -> None:
    try:
        session = auth.session_token()
        r = httpx.post(
            f"{config.supabase_url()}/rest/v1/campaigns",
            headers={
                "apikey": config.supabase_anon_key(),
                "Authorization": f"Bearer {session}",
                "Content-Type": "application/json",
                "Prefer": "resolution=ignore-duplicates,return=minimal",
            },
            json={
                "run_id": run_id, "sender": sender, "sender_email": sender_email,
                "provider": provider, "template_name": template_name,
                "icp_description": icp, "experiment": experiment,
                "sent_count": sent_count,
            },
            timeout=30,
        )
        if r.status_code not in (200, 201):
            events.emit("campaigns.write_failed", level="warn",
                        status=r.status_code, body=r.text[:200])
    except Exception as e:
        events.emit("campaigns.write_error", level="warn", reason=str(e)[:200])


# ---- Finalize (shared by mix and single-ICP paths) --------------------

def _finalize(
    args: argparse.Namespace,
    run_id: str,
    sender_name: str,
    total_sent: int,
    total_dry: int,
    template_name: str,
    icp_label: str,
    outbox_a: list[models.OutboxRow],
    outbox_b: list[models.OutboxRow],
    sent_at: str,
    counts_a: dict,
    counts_b: dict,
    elapsed: float = 0.0,
) -> None:
    if not args.dry_run:
        _write_campaign_to_supabase(
            run_id=run_id,
            sender=sender_name,
            sender_email=args.from_,
            provider=args.provider,
            template_name=template_name,
            icp=icp_label,
            experiment=args.experiment,
            sent_count=total_sent,
        )

    default_log_dir = Path.home() / ".blackwell" / "campaigns"
    default_log_dir.mkdir(parents=True, exist_ok=True)
    log_path = args.log or str(default_log_dir / f"campaign_{run_id[:8]}.jsonl")
    meta_entry = {
        "_meta": True, "run_id": run_id, "sender": sender_name,
        "sender_email": args.from_, "provider": args.provider,
        "template": template_name, "icp": icp_label,
        "experiment": args.experiment, "sent_count": total_sent,
        "sent_at": sent_at,
    }
    contact_entries = (
        [{"email": r.email, "run_id": run_id, "variant": "a", "sent_at": sent_at}
         for r in outbox_a]
        + [{"email": r.email, "run_id": run_id, "variant": "b", "sent_at": sent_at}
           for r in outbox_b]
    )
    write_campaign_log(log_path, [meta_entry] + contact_entries)

    total_skipped = counts_a.get("skipped_ledger", 0) + counts_b.get("skipped_ledger", 0)
    print(f"Result : {total_sent} sent  {total_skipped} skipped")

    def _sum(key: str) -> int:
        return counts_a.get(key, 0) + counts_b.get(key, 0)

    print(f"Breakdown : {total_sent} sent, {total_skipped} skipped (already "
          f"contacted), {_sum('suppressed')} suppressed, {_sum('failed')} failed, "
          f"{total_dry} dry-run")
    print(f"Log    : {log_path}")
    if elapsed:
        print(f"Time   : {elapsed / 60:.1f} min ({elapsed:.0f}s)")


# ---- Preflight ---------------------------------------------------------

def _preflight(from_: str, provider: str) -> None:
    """Validate all credentials before spending any API credits.

    Exits with a clear message on the first failure so the user knows
    exactly what to fix before the run starts.
    """
    errors: list[str] = []

    # 1. Supabase session
    try:
        auth.session_token()
    except Exception as e:
        errors.append(f"Supabase session invalid: {e}\n  Fix: toolbox auth login")

    # 2. Provider key
    if provider not in ("clay", "origami"):
        try:
            key = auth.get_token(provider)
            if not key:
                raise ValueError("empty token")
        except Exception as e:
            env_var = f"TOOLBOX_TOKEN_{provider.upper()}"
            errors.append(
                f"{provider} API key missing or invalid: {e}\n"
                f"  Fix: set {env_var} in credentials/.env"
            )

    # 3. gog Gmail token
    try:
        token = gog_auth.get_access_token(from_)
        if not token:
            raise ValueError("empty token")
        # Probe Gmail API with the token — a bad token returns 401 immediately.
        r = httpx.get(
            "https://gmail.googleapis.com/gmail/v1/users/me/profile",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
        if r.status_code == 401:
            raise ValueError("token rejected by Gmail (401)")
    except Exception as e:
        errors.append(
            f"Gmail (gog) auth failed for {from_}: {e}\n"
            f"  Fix: gog auth add {from_} --services gmail"
        )

    if errors:
        print("\nPreflight failed — fix these before running:\n")
        for err in errors:
            print(f"  {err}\n")
        sys.exit(1)

    print("Preflight OK")


# ---- Main --------------------------------------------------------------

def main() -> None:
    # Stream progress live: line-buffer stdout so every print() flushes on its
    # newline instead of sitting in a block buffer until the run ends. (send.sh
    # also runs python with -u; this also covers a direct `python run.py` call.)
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except (AttributeError, ValueError):
        pass

    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--config", default="",
                        help="Alternative ICP mix TOML (default: icp_mix.toml)")
    parser.add_argument("--icp", default="",
                        help="ICP description: Claude generates target domains from this")
    parser.add_argument("--provider", default="hunter",
                        choices=["hunter", "apollo", "clay", "origami"],
                        help="Lead source (clay/origami require --leads CSV)")
    parser.add_argument("--leads", default="",
                        help="Pre-exported leads CSV from Clay or Origami (has email column)")
    parser.add_argument("--domains", default="",
                        help="Pre-built domains CSV (skips ICP domain generation)")
    parser.add_argument("--template",
                        default=str(Path(__file__).parent / "template_a.md"),
                        help="Template file (frontmatter subject + body)")
    parser.add_argument("--from", dest="from_", required=True,
                        help="Gmail address to send from")
    parser.add_argument("--from-name", default="",
                        help="Display name in the From header")
    parser.add_argument("--school", default="",
                        help="Sender's school for the {{school}} slot (default: derived from --from domain)")
    parser.add_argument("--other-schools", default="",
                        help="Other team schools for the {{other_schools}} slot (default: derived)")
    parser.add_argument("--cc", default="",
                        help="CC list (comma-separated) added to every send — the co-founder CC convention")
    parser.add_argument("--concurrency", type=int, default=8,
                        help="Concurrent Gmail sends and enrichment calls (default 8)")
    parser.add_argument("--experiment", action="store_true",
                        help="A/B mode: split 50/50, Claude writes variant B")
    parser.add_argument("--limit", type=int, default=0,
                        help="Max contacts to send to (0 = no cap)")
    parser.add_argument("--min-score", type=int, default=80,
                        help="Minimum Hunter/Apollo email confidence (0-100)")
    parser.add_argument("--max-domain-count", type=int, default=3,
                        help="Skip domains already contacted this many times (0 = off)")
    parser.add_argument("--segment-phrase", default="",
                        dest="segment_phrase",
                        help="Value for {{segment_phrase}} template slot (used with --leads)")
    parser.add_argument("--personalize-visibility", action="store_true",
                        dest="personalize_visibility",
                        help="Fill {{personal_line}} per brand with an AI-visibility "
                             "check (GEO pilot). One extra LLM call per contact.")
    parser.add_argument("--log", default="",
                        help="Campaign log path for reply tracking (default: /tmp/campaign_<id>.jsonl)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print what would be sent without actually sending")
    parser.add_argument("--skip-preflight", action="store_true",
                        help="Skip credential preflight checks (for server/headless mode)")
    args = parser.parse_args()

    global _ICP_MIX_PATH
    if args.config:
        p = Path(args.config)
        _ICP_MIX_PATH = p if p.is_absolute() else (_REPO_ROOT / p)

    if args.provider in ("clay", "origami") and not args.leads:
        parser.error(f"--provider {args.provider} requires --leads <exported_csv>")
    if not args.icp and not args.leads and not args.domains:
        if not _ICP_MIX_PATH.exists():
            parser.error(
                "Need one of: --icp TEXT, --leads FILE, or --domains FILE\n"
                f"(or add {_ICP_MIX_PATH} to use the default ICP mix)"
            )

    if not args.skip_preflight:
        _preflight(args.from_, args.provider)

    _hunter_before = -1  # set per-path when key is available
    t_start = time.monotonic()
    run_id = str(uuid.uuid4())
    run_dir = tempfile.mkdtemp(prefix=f"campaign_{run_id[:8]}_")
    _banner("Setup")
    print(f"run_id : {run_id}")
    print(f"run_dir: {run_dir}")

    # Stream generated domains and enriched contacts to repo-local CSVs as they
    # happen, so both the slow generation step and enrichment are visible live.
    global _ENRICHED_PATH, _DOMAINS_PATH
    enriched_dir = _REPO_ROOT / "skills" / "campaign" / "enriched"
    enriched_dir.mkdir(parents=True, exist_ok=True)
    _DOMAINS_PATH = str(enriched_dir / f"domains_{run_id[:8]}.csv")
    _ENRICHED_PATH = str(enriched_dir / f"enriched_{run_id[:8]}.csv")
    print(f"domains: {_DOMAINS_PATH} (written live as domains are generated)")
    print(f"emails : {_ENRICHED_PATH} (written live as contacts are enriched)")
    enriched_cache = load_enriched_cache(enriched_dir)
    if enriched_cache:
        print(f"cache  : {len(enriched_cache)} domains from prior runs (Hunter skipped for these)")

    # 1. Source contacts --------------------------------------------------
    session_token = auth.session_token()
    domain_counts = load_domain_counts(session_token)
    if domain_counts and args.max_domain_count > 0:
        print(f"Domain filter: skip any domain contacted >= {args.max_domain_count}x "
              f"({len(domain_counts)} domains in ledger)")

    if args.leads:
        # CSV import: all contacts are known upfront, just ledger-filter.
        contacts = load_leads_csv(args.leads, min_score=args.min_score)
        print(f"Loaded {len(contacts)} contacts from {args.leads}")
        contacts = filter_by_domain_count(contacts, domain_counts, args.max_domain_count)
        print("Checking ledger...")
        contacts = asyncio.run(_filter_new_contacts(contacts, session_token))
        print(f"  {len(contacts)} new (not yet contacted)")
        if args.limit:
            contacts = contacts[: args.limit]
    elif args.domains:
        # Fixed domain list: enrich all upfront, then ledger-filter.
        domain_rows = io.read_csv(args.domains, models.Domain)
        domains = [r.domain for r in domain_rows]
        print(f"Loaded {len(domains)} domains from {args.domains}")
        domains = filter_by_domain_count(domains, domain_counts, args.max_domain_count)
        key = auth.get_token(args.provider)
        print(f"Enriching via {args.provider}...")
        contacts = asyncio.run(
            enrich_domains(domains, args.provider, key, min_score=args.min_score,
                           enriched_cache=enriched_cache)
        )
        print(f"  {len(contacts)} contacts found")
        print("Checking ledger...")
        contacts = asyncio.run(_filter_new_contacts(contacts, session_token))
        print(f"  {len(contacts)} new (not yet contacted)")
        if args.limit:
            contacts = contacts[: args.limit]
    elif args.icp:
        key = auth.get_token(args.provider)
        _hunter_before = _hunter_searches_used(key) if args.provider == "hunter" else -1
        _banner(f"Sourcing contacts  [target: {args.limit or 20}  provider: {args.provider}]")
        contacts = asyncio.run(
            source_contacts_pipeline(
                args.icp, args.provider, key, session_token,
                limit=args.limit or 20, min_score=args.min_score,
                domain_counts=domain_counts, max_domain_count=args.max_domain_count,
                hunter_sem=asyncio.Semaphore(args.concurrency),
                enriched_cache=enriched_cache,
            )
        )
        if args.limit:
            contacts = contacts[: args.limit]
    else:
        # Default: distribute contacts across segments per icp_mix.toml.
        # Each segment uses its own template; outbox rows are returned pre-composed.
        limit = args.limit or 20
        key = auth.get_token(args.provider)
        _banner(f"Sourcing contacts  [target: {limit}  mix: {_ICP_MIX_PATH.name}]")
        outbox_a, outbox_b = asyncio.run(
            _source_from_mix(
                args.provider, key, session_token,
                limit=limit, from_name=args.from_name, min_score=args.min_score,
                enrich_concurrency=args.concurrency,
                domain_counts=domain_counts, max_domain_count=args.max_domain_count,
                experiment=args.experiment,
                enriched_cache=enriched_cache,
            )
        )
        _banner(f"Composed  {len(outbox_a)} variant-A  {len(outbox_b)} variant-B")
        if not outbox_a and not outbox_b:
            print("No new contacts — exiting.")
            sys.exit(0)
        n_mix = len(outbox_a) + len(outbox_b)
        print(f"Drafted : {n_mix} emails", flush=True)
        dry_tag = "  [dry run]" if args.dry_run else ""
        _banner(f"Sending{dry_tag}  {n_mix} emails")
        if args.dry_run:
            print("Sample:")
            for row in (outbox_a + outbox_b)[:5]:
                print(f"  TO: {row.email}")
                print(f"      {row.subject}")
            print()
        sent_at = datetime.now(UTC).isoformat()
        counts_a = asyncio.run(
            _send_batch(outbox_a, args.from_, args.from_name, run_id, run_dir,
                        args.dry_run, args.cc, args.concurrency)
        )
        counts_b = (
            asyncio.run(
                _send_batch(outbox_b, args.from_, args.from_name, run_id, run_dir,
                            args.dry_run, args.cc, args.concurrency)
            )
            if outbox_b else {}
        )
        total_sent = counts_a.get("sent", 0) + counts_b.get("sent", 0)
        total_dry = counts_a.get("dry_run", 0) + counts_b.get("dry_run", 0)
        template_name = "icp_mix"
        sender_name = args.from_name or args.from_.split("@")[0].title()
        icp_label = "ICP mix"
        elapsed = time.monotonic() - t_start
        _finalize(args, run_id, sender_name, total_sent, total_dry, template_name,
                  icp_label, outbox_a, outbox_b, sent_at, counts_a, counts_b, elapsed)
        return

    if not contacts:
        print("No new contacts — exiting.")
        sys.exit(0)

    # 1b. AI-visibility personalization (GEO pilot) -----------------------
    # Fill each brand's {{personal_line}} from a live "does this brand show up
    # when a shopper asks an AI?" check. Off by default; only GEO runs pay the
    # one-LLM-call-per-contact cost. Reconstructing the Contact carries the
    # extra field through model_dump() into compose (Row is extra="allow").
    if args.personalize_visibility:
        _banner(f"Personalizing  [AI-visibility check x{len(contacts)}]")
        contacts = asyncio.run(
            _personalize_visibility(contacts, args.icp or "brands", args.concurrency)
        )

    # 2. Load template A --------------------------------------------------
    _banner("Composing")
    subject_a, body_a = load_template(args.template)

    # 3. Experiment split -------------------------------------------------
    if args.experiment:
        mid = max(1, len(contacts) // 2)
        contacts_a, contacts_b = contacts[:mid], contacts[mid:]
        print("Generating variant B...")
        subject_b, body_b = generate_variant_b(subject_a, body_a)
        print(f"  Variant B subject: {subject_b}")
    else:
        contacts_a, contacts_b = contacts, []
        subject_b = body_b = ""

    # 4. Compose ----------------------------------------------------------
    _school, _other_schools = school_for_email(args.from_)
    extra = {
        "school": args.school or _school,
        "other_schools": args.other_schools or _other_schools,
    }
    if args.segment_phrase:
        extra["segment_phrase"] = args.segment_phrase
    outbox_a = compose_outbox(contacts_a, subject_a, body_a, from_name=args.from_name, extra_values=extra)
    outbox_b = (
        compose_outbox(contacts_b, subject_b, body_b, from_name=args.from_name, extra_values=extra)
        if contacts_b else []
    )
    print(f"  {len(outbox_a)} variant-A  {len(outbox_b)} variant-B")

    n_total = len(outbox_a) + len(outbox_b)
    print(f"Drafted : {n_total} emails", flush=True)
    dry_tag = "  [dry run]" if args.dry_run else ""
    _banner(f"Sending{dry_tag}  {n_total} emails")
    if args.dry_run:
        print("Sample:")
        for row in (outbox_a + outbox_b)[:5]:
            print(f"  TO: {row.email}")
            print(f"      {row.subject}")
        print()

    # 5. Send -------------------------------------------------------------
    sent_at = datetime.now(UTC).isoformat()
    counts_a = asyncio.run(
        _send_batch(outbox_a, args.from_, args.from_name, run_id, run_dir,
                    args.dry_run, args.cc, args.concurrency)
    )
    counts_b = (
        asyncio.run(
            _send_batch(outbox_b, args.from_, args.from_name, run_id, run_dir,
                        args.dry_run, args.cc, args.concurrency)
        )
        if outbox_b else {}
    )

    total_sent = counts_a.get("sent", 0) + counts_b.get("sent", 0)
    total_dry = counts_a.get("dry_run", 0) + counts_b.get("dry_run", 0)
    template_name = Path(args.template).stem
    sender_name = args.from_name or args.from_.split("@")[0].title()
    elapsed = time.monotonic() - t_start
    if _hunter_before >= 0 and args.provider == "hunter":
        _hunter_after = _hunter_searches_used(key)
        if _hunter_after >= 0:
            print(f"Hunter : {max(0, _hunter_after - _hunter_before)} credits used")
            # Absolute account counter snapshots so the orchestrator can compute a
            # campaign-wide total (last sender's `after` minus first sender's
            # `before`) instead of summing per-sender deltas of a shared counter.
            print(f"Hunter-usage : before={_hunter_before} after={_hunter_after}")
    _finalize(args, run_id, sender_name, total_sent, total_dry, template_name,
              args.icp, outbox_a, outbox_b, sent_at, counts_a, counts_b, elapsed)


if __name__ == "__main__":
    main()
    # run.py is a one-shot subprocess: by the time main() returns, every send,
    # ledger write, and log line is already flushed. The sourcing pipeline fires a
    # speculative look-ahead generation on a worker thread that cannot be cancelled
    # (see source_contacts_pipeline); if one is still running it blocks interpreter
    # shutdown (ThreadPoolExecutor.shutdown(wait=True)) and the process never exits,
    # which freezes the wizard's sender queue. Force a clean immediate exit so a
    # stranded thread can't hold the process open. Flush first so the executor reads
    # the final lines before the pipe closes.
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(0)
