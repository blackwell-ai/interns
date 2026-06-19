#!/usr/bin/env python3
"""Apollo pattern sourcing — many relevant contacts per domain, minimal credits.

Strategy (per Armaan, 2026-06-18):
  1. Apollo people search (free) returns senior/relevant people at a domain:
     first name + title + obfuscated last name + a person id. No emails, no
     credit spent.
  2. Reveal ONE person via people/match (1 credit) to learn the domain's email
     pattern and get one Apollo-verified address.
  3. Apply the pattern to everyone else's name to derive their emails for free.

Apollo obfuscates last names in free search, so only the first-name part is
free. That means:
  - First-name patterns ({first}, {f}) -> derive the whole company for 1 credit.
  - Last-name patterns ({first}.{last}, {f}{last}, ...) -> the free names are not
    enough; those domains either get skipped or fully revealed (1 credit/person)
    with --reveal-undecidable.

Derived emails are unverified guesses; only the seed is Apollo-verified. They are
marked email_status=pattern_derived so the caller can gate sends and watch
bounces. Output is a Contact CSV ready for `run.py --leads`.

Endpoints (the old mixed_people/search is deprecated for API callers):
  - POST /v1/mixed_people/api_search   (search, free)
  - POST /v1/people/match              (reveal, 1 credit)

Auth: TOOLBOX_TOKEN_APOLLO in the environment (run.py / send.sh load it from
credentials/.env). No key in argv.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
from pathlib import Path

import httpx

# Allow importing the toolbox (for the headless web-search LLM) when run as a
# standalone script from the repo root.
_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT / "toolbox" / "src"))
from toolbox.core import llm as llm_mod  # noqa: E402

SEARCH_URL = "https://api.apollo.io/v1/mixed_people/api_search"
MATCH_URL = "https://api.apollo.io/v1/people/match"

# Decision-maker seniorities we consider "relevant" for DTC outreach. Search is
# free, so we cast a wide senior net and let the caller narrow later.
RELEVANT_SENIORITIES = ["owner", "founder", "c_suite", "partner", "vp", "head", "director"]

# Patterns tried against the one revealed (name, email). Each builder takes
# (first, last, last_initial). Patterns that need only first name or last initial
# can be derived for free (Apollo's search gives the first name + the last
# initial via the obfuscated last name); patterns that need the full last name
# require a web/reveal resolve.
_PATTERNS = [
    ("{first}", lambda f, ln, li: f),
    ("{first}{l}", lambda f, ln, li: f + li),       # emilyw
    ("{first}.{l}", lambda f, ln, li: f + "." + li),
    ("{f}{last}", lambda f, ln, li: f[:1] + ln),
    ("{f}.{last}", lambda f, ln, li: f[:1] + "." + ln),
    ("{first}.{last}", lambda f, ln, li: f + "." + ln),
    ("{first}{last}", lambda f, ln, li: f + ln),
    ("{first}_{last}", lambda f, ln, li: f + "_" + ln),
    ("{first}-{last}", lambda f, ln, li: f + "-" + ln),
    ("{last}", lambda f, ln, li: ln),
    ("{last}.{first}", lambda f, ln, li: ln + "." + f),
    ("{f}", lambda f, ln, li: f[:1]),
]


def _headers() -> dict:
    key = os.environ.get("TOOLBOX_TOKEN_APOLLO", "").strip()
    if not key:
        sys.exit("TOOLBOX_TOKEN_APOLLO not set (load credentials/.env first)")
    return {"X-Api-Key": key, "Content-Type": "application/json", "Cache-Control": "no-cache"}


def search_domain(client: httpx.Client, domain: str, per_page: int = 100,
                  max_pages: int = 2) -> list[dict]:
    """Free people search: relevant senior people at the domain (no emails)."""
    out: list[dict] = []
    for page in range(1, max_pages + 1):
        r = client.post(SEARCH_URL, json={
            "q_organization_domains_list": [domain],
            "person_seniorities": RELEVANT_SENIORITIES,
            "per_page": per_page, "page": page,
        }, timeout=60)
        if r.status_code != 200:
            break
        ppl = r.json().get("people") or []
        out.extend(ppl)
        if len(ppl) < per_page:
            break
    return out


def reveal(client: httpx.Client, person_id: str) -> dict:
    """Reveal one person (1 Apollo credit) -> full name + verified email."""
    r = client.post(MATCH_URL, json={"id": person_id, "reveal_personal_emails": False}, timeout=60)
    if r.status_code != 200:
        return {}
    return r.json().get("person") or {}


def infer_pattern(first: str, last: str, email: str) -> str | None:
    f, ln = (first or "").lower(), (last or "").lower()
    li = ln[:1]
    local = email.split("@")[0].lower()
    for tmpl, build in _PATTERNS:
        val = build(f, ln, li)
        if val and val == local:
            return tmpl
    return None


def apply_pattern(tmpl: str, first: str, last: str, last_initial: str, domain: str) -> str | None:
    f = (first or "").lower()
    ln = (last or "").lower()
    li = (last_initial or (ln[:1] if ln else "")).lower()
    if "{last}" in tmpl and not ln:
        return None  # needs the full last name (only the obfuscated form is free)
    if "{l}" in tmpl and not li:
        return None  # needs at least the last initial
    for t, build in _PATTERNS:
        if t == tmpl:
            local = build(f, ln, li)
            return f"{local}@{domain}" if local else None
    return None


def _rank(title: str) -> int:
    t = (title or "").lower()
    for i, kw in enumerate(("founder", "ceo", "owner", "president", "coo", "cmo")):
        if kw in t:
            return i
    return 99


def _obf_match(candidate_last: str, obfuscated: str) -> bool:
    """Does a candidate last name fit Apollo's obfuscation (e.g. 'Na***n')?"""
    if not obfuscated or "*" not in obfuscated:
        return True  # no constraint available
    c = candidate_last.lower().strip()
    o = obfuscated.lower()
    prefix = o[: o.index("*")]
    suffix = o[o.rindex("*") + 1:]
    return len(c) == len(o) and c.startswith(prefix) and c.endswith(suffix)


def resolve_last_names_web(company: str, domain: str, people: list[dict]) -> dict:
    """One headless web-search call -> {apollo_person_id: full_last_name}.

    For last-name email patterns Apollo's free search hides the last name. We ask
    Claude Code (WebSearch) for the company roster, then match each person by
    first name + the obfuscation constraint. No Apollo credits spent. Best-effort:
    reliability varies; people we cannot resolve are dropped.
    """
    if not people:
        return {}
    roster_req = [{"first_name": p.get("first_name", ""),
                   "last_name_hint": p.get("last_name_obfuscated", ""),
                   "title": p.get("title", "")} for p in people]
    prompt = (
        f"Find the full names and job titles of people on the team at {company} "
        f"(website {domain}). I need the full LAST NAME for each person below; the "
        f"hint shows the first and last letters and the length of the last name:\n"
        f"{json.dumps(roster_req, indent=2)}\n\n"
        "Return ONLY a JSON array of objects with keys first_name, last_name, title."
    )
    try:
        raw = llm_mod.web_search(
            prompt,
            system="Return ONLY a JSON array of {first_name, last_name, title}. No prose, no citations.",
            max_searches=6,
        )
    except Exception:
        return {}
    m = re.search(r"\[.*\]", raw, re.DOTALL)
    if not m:
        return {}
    try:
        roster = json.loads(m.group(0))
    except json.JSONDecodeError:
        return {}
    out: dict = {}
    for p in people:
        first = (p.get("first_name") or "").lower()
        obf = p.get("last_name_obfuscated") or ""
        for cand in roster:
            if (cand.get("first_name", "").lower() == first and cand.get("last_name")
                    and _obf_match(cand["last_name"], obf)):
                out[p["id"]] = cand["last_name"]
                break
    return out


def source_domain(client: httpx.Client, domain: str, max_seed_reveals: int = 3,
                  resolve_web: bool = True, reveal_undecidable: bool = False,
                  reveal_cap: int = 10) -> dict:
    """One domain -> contacts + credits spent. See module docstring for the model."""
    people = search_domain(client, domain)
    result = {"domain": domain, "relevant": len(people), "pattern": None,
              "credits": 0, "web_resolved": 0, "contacts": []}
    if not people:
        return result

    # Reveal the most senior people: every reveal is a real verified contact, and
    # the first seed whose name maps cleanly to its email defines the pattern.
    ordered = sorted(people, key=lambda p: _rank(p.get("title")))
    pattern = None
    revealed: list[tuple[str, dict]] = []
    for cand in ordered[:max_seed_reveals]:
        result["credits"] += 1
        rv = reveal(client, cand["id"])
        if not rv.get("email"):
            continue
        revealed.append((cand["id"], rv))
        pat = infer_pattern(rv.get("first_name", ""), rv.get("last_name", ""), rv["email"])
        if pat:
            pattern = pat
            break
    result["pattern"] = pattern
    if not revealed:
        return result  # no revealable emails on this domain

    contacts: list[dict] = []
    seen = set()

    def add(email, first, last, title, status, score):
        if not email or email in seen:
            return
        seen.add(email)
        contacts.append({
            "email": email, "first_name": first or "", "last_name": last or "",
            "title": title or "", "company": "", "domain": domain,
            "email_score": score, "email_status": status,
        })

    # Every revealed seed is a verified contact (kept even when no pattern emerges).
    revealed_ids = set()
    for _id, rv in revealed:
        revealed_ids.add(_id)
        add(rv["email"].lower(), rv.get("first_name"), rv.get("last_name"),
            rv.get("title"), (rv.get("email_status") or "verified").lower(), 95)

    undecidable = []
    if pattern:
        for p in people:
            if p.get("id") in revealed_ids:
                continue  # already added as a verified seed
            li = (p.get("last_name_obfuscated") or "")[:1]  # last initial is free from search
            email = apply_pattern(pattern, p.get("first_name", ""), p.get("last_name"), li, domain)
            if email:
                add(email, p.get("first_name"), "", p.get("title"), "pattern_derived", 60)
            elif p.get("id"):
                undecidable.append(p)

    # Last-name pattern: recover the missing last names from the web (no Apollo
    # credits), then derive.
    resolved_ids = set()
    if undecidable and resolve_web:
        company_name = (people[0].get("organization") or {}).get("name") or domain.split(".")[0].title()
        resolved = resolve_last_names_web(company_name, domain, undecidable)
        result["web_resolved"] = len(resolved)
        for p in undecidable:
            last = resolved.get(p["id"])
            if not last:
                continue
            email = apply_pattern(pattern, p.get("first_name", ""), last, last[:1], domain)
            if email:
                resolved_ids.add(p["id"])
                add(email, p.get("first_name"), last, p.get("title"), "pattern_derived", 55)

    # Optional paid fallback for any the web could not resolve (1 credit each).
    if reveal_undecidable:
        for p in [u for u in undecidable if u["id"] not in resolved_ids][:reveal_cap]:
            result["credits"] += 1
            rv = reveal(client, p["id"])
            if rv.get("email"):
                add(rv["email"].lower(), rv.get("first_name"), rv.get("last_name"),
                    rv.get("title"), rv.get("email_status") or "verified", 90)

    # Pull company name from the search org block if present.
    org_name = ""
    for p in people:
        org = p.get("organization") or {}
        if org.get("name"):
            org_name = org["name"]
            break
    for c in contacts:
        c["company"] = org_name or domain.split(".")[0].title()

    result["contacts"] = contacts
    return result


_FIELDS = ["email", "first_name", "last_name", "title", "company", "domain",
           "email_score", "email_status"]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--domain", help="single domain to source")
    g.add_argument("--domains", help="CSV/text file of domains (one per line or a 'domain' column)")
    ap.add_argument("--out", required=True, help="output contacts CSV (feed to run.py --leads)")
    ap.add_argument("--no-web-resolve", action="store_true",
                    help="disable the web last-name lookup for last-name-pattern domains")
    ap.add_argument("--reveal-undecidable", action="store_true",
                    help="pay to reveal anyone the web could not resolve (1 credit/person)")
    ap.add_argument("--reveal-cap", type=int, default=10,
                    help="max paid reveals per domain when --reveal-undecidable (default 10)")
    ap.add_argument("--max-seed-reveals", type=int, default=2,
                    help="max reveals to find a seed email per domain (default 2)")
    args = ap.parse_args()

    if args.domain:
        domains = [args.domain.strip()]
    else:
        text = Path(args.domains).read_text()
        domains = []
        for line in text.splitlines():
            d = line.split(",")[0].strip().lower()
            if d and d != "domain":
                domains.append(d)

    all_contacts: list[dict] = []
    total_credits = 0
    with httpx.Client(headers=_headers()) as client:
        for d in domains:
            res = source_domain(client, d, max_seed_reveals=args.max_seed_reveals,
                                resolve_web=not args.no_web_resolve,
                                reveal_undecidable=args.reveal_undecidable,
                                reveal_cap=args.reveal_cap)
            total_credits += res["credits"]
            all_contacts.extend(res["contacts"])
            print(f"[{d}] relevant={res['relevant']} pattern={res['pattern']} "
                  f"web_resolved={res['web_resolved']} contacts={len(res['contacts'])} "
                  f"credits={res['credits']}")

    with open(args.out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=_FIELDS)
        w.writeheader()
        w.writerows(all_contacts)
    print(f"\n{len(all_contacts)} contacts across {len(domains)} domains "
          f"for {total_credits} Apollo credits -> {args.out}")


if __name__ == "__main__":
    main()
