"""findemail primitive — find + verify a work email from a name + domain.

This is the *headless* equivalent of Clay's "find work email" enrichment:
Clay itself has no API to drive its enrichment recipe (the waterfall lives in
a Clay table configured in the UI), but the providers Clay waterfalls across
— Hunter, Findymail, Enrow — expose clean REST APIs. This primitive calls one
of them directly, so a flow can go name+domain → verified email with one API
key and zero manual steps.

Input  : candidates CSV with `domain` + (`first_name`,`last_name`) or `name`
         (and any passthrough columns, e.g. brand/title).
Output : contacts CSV (models.Contact) with the found email, plus
         `email_score` / `email_status` so downstream/compose can gate on
         confidence. Rows with no email found (or below --min-score) are
         dropped and logged — never guessed.

Providers (--provider): `hunter` (default) | `findymail` | `apollo`.
Auth: core/auth.get_token("hunter"|"findymail"|"apollo") — Supabase connection or the
TOOLBOX_TOKEN_<PROVIDER> env override. No key in argv or the repo.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import httpx
import typer
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from toolbox.core import auth, events, io, models

app = typer.Typer(no_args_is_help=True)


@app.callback()
def _group():
    """findemail primitive."""


_transient = retry(
    retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.TransportError)),
    wait=wait_exponential(multiplier=1, max=60),
    stop=stop_after_attempt(6),
    reraise=True,
)


def _split_name(row: models.Row) -> tuple[str, str]:
    first = (getattr(row, "first_name", "") or "").strip()
    last = (getattr(row, "last_name", "") or "").strip()
    if first:
        return first, last
    full = (getattr(row, "name", "") or "").strip()
    if full:
        parts = full.split()
        return parts[0], " ".join(parts[1:])
    return "", ""


# ---- provider adapters: each returns (email, score_0_100, status) -----------


@_transient
async def _hunter(client: httpx.AsyncClient, key: str, domain: str, first: str, last: str):
    r = await client.get(
        "https://api.hunter.io/v2/email-finder",
        params={"domain": domain, "first_name": first, "last_name": last, "api_key": key},
    )
    if r.status_code in (429,) or r.status_code >= 500:
        r.raise_for_status()  # transient → retried
    if r.status_code != 200:
        return "", 0, f"http_{r.status_code}"
    data = r.json().get("data") or {}
    email = (data.get("email") or "").strip().lower()
    score = int(data.get("score") or 0)
    status = (data.get("verification") or {}).get("status") or "unknown"
    return email, score, status


@_transient
async def _findymail(client: httpx.AsyncClient, key: str, domain: str, first: str, last: str):
    name = f"{first} {last}".strip()
    r = await client.post(
        "https://app.findymail.com/api/search/name",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={"name": name, "domain": domain},
    )
    if r.status_code in (429,) or r.status_code >= 500:
        r.raise_for_status()
    if r.status_code != 200:
        return "", 0, f"http_{r.status_code}"
    contact = (r.json() or {}).get("contact") or {}
    email = (contact.get("email") or "").strip().lower()
    # Findymail only returns verified/deliverable emails → treat as high score.
    return email, (90 if email else 0), "valid" if email else "not_found"


@_transient
async def _apollo(client: httpx.AsyncClient, key: str, domain: str, first: str, last: str):
    name = f"{first} {last}".strip()
    r = await client.post(
        "https://api.apollo.io/v1/people/match",
        headers={"X-Api-Key": key, "Content-Type": "application/json"},
        json={"first_name": first, "last_name": last, "organization_domain": domain,
              "reveal_personal_emails": False},
    )
    if r.status_code in (429,) or r.status_code >= 500:
        r.raise_for_status()
    if r.status_code != 200:
        return "", 0, f"http_{r.status_code}"
    person = (r.json() or {}).get("person") or {}
    email = (person.get("email") or "").strip().lower()
    status = (person.get("email_status") or "unavailable").lower()
    _APOLLO_SCORE = {"verified": 95, "likely to engage": 70, "guessed": 40}
    score = _APOLLO_SCORE.get(status, 0)
    return email, score, status


_PROVIDERS = {"hunter": _hunter, "findymail": _findymail, "apollo": _apollo}

# Seniority/role ranking for picking the decision-maker out of a domain search.
_ROLE_RANK = ("founder", "owner", "ceo", "chief executive", "president",
              "co-founder", "cofounder", "partner", "head", "vp", "director")


def _decision_maker_rank(position: str, seniority: str) -> int:
    p = (position or "").lower()
    for i, kw in enumerate(_ROLE_RANK):
        if kw in p:
            return i
    if (seniority or "").lower() == "executive":
        return len(_ROLE_RANK)
    return len(_ROLE_RANK) + 1


@_transient
async def _hunter_domain(client: httpx.AsyncClient, key: str, domain: str,
                         limit: int = 10, executives_only: bool = True):
    """Domain search → pick the most senior decision-maker + their email.

    Credit cost = ceil(emails_returned / 10): limit=10 → 1 credit, limit=25 → 3.
    Default (limit=10 + seniority=executive) is the efficient setting — 1 credit
    and the returned set is execs only. `--thorough` (limit=25, no seniority
    filter) sees more emails so a lower-confidence FOUNDER isn't cut off, at 3
    credits. See harness/learnings/05.
    """
    params = {"domain": domain, "api_key": key, "limit": limit, "type": "personal"}
    if executives_only:
        params["seniority"] = "executive"
    r = await client.get("https://api.hunter.io/v2/domain-search", params=params)
    if r.status_code in (429,) or r.status_code >= 500:
        r.raise_for_status()
    if r.status_code != 200:
        return None
    emails = (r.json().get("data") or {}).get("emails") or []
    candidates = [e for e in emails if (e.get("value") or "").strip()]
    if not candidates:
        return None
    candidates.sort(key=lambda e: (_decision_maker_rank(e.get("position", ""), e.get("seniority", "")),
                                   -(e.get("confidence") or 0)))
    best = candidates[0]
    return {
        "email": best["value"].strip().lower(),
        "first_name": (best.get("first_name") or "").strip(),
        "last_name": (best.get("last_name") or "").strip(),
        "title": (best.get("position") or "").strip(),
        "email_score": int(best.get("confidence") or 0),
        "email_status": (best.get("verification") or {}).get("status") or "unknown",
    }


@app.command()
def find(
    in_: str = typer.Option(..., "--in", help="candidates CSV: domain + first_name/last_name or name"),
    out: str = typer.Option(..., "--out", help="contacts CSV with email,email_score,email_status"),
    provider: str = typer.Option("hunter", "--provider", help="hunter | findymail | apollo"),
    concurrency: int = typer.Option(5, "--concurrency", help="keep low: Hunter rate-limits above ~5 (see harness/learnings/03)"),
    min_score: int = typer.Option(80, "--min-score", help="drop emails below this confidence (hunter score)"),
):
    """name + domain -> verified work email (Clay's find-work-email, headless)."""
    if provider not in _PROVIDERS:
        raise typer.BadParameter(f"unknown provider {provider!r}; one of {sorted(_PROVIDERS)}")
    rows = io.read_csv(in_, models.Row)
    key = auth.get_token(provider)
    adapter = _PROVIDERS[provider]

    async def main() -> list[models.Contact]:
        sem = asyncio.Semaphore(max(1, concurrency))
        found: list[models.Contact] = []
        async with httpx.AsyncClient(timeout=60) as client:
            async def one(row: models.Row) -> None:
                domain = (getattr(row, "domain", "") or "").strip().lower()
                first, last = _split_name(row)
                if not domain or not first:
                    events.emit("findemail.skip_input", level="warn",
                                reason="missing domain or name", domain=domain)
                    return
                async with sem:
                    email, score, status = await adapter(client, key, domain, first, last)
                if not email:
                    events.emit("findemail.not_found", domain=domain, name=f"{first} {last}".strip())
                    return
                if score < min_score:
                    events.emit("findemail.low_score", email=email, score=score, status=status)
                    return
                passthrough = {
                    k: v for k, v in row.model_dump().items()
                    if k not in ("email",) and isinstance(v, str | int | float | bool)
                }
                try:
                    found.append(models.Contact(
                        **{**passthrough, "email": email, "first_name": first, "last_name": last,
                           "domain": domain, "email_score": score, "email_status": status}
                    ))
                except ValueError as e:
                    events.emit("findemail.bad_email", level="warn", email=email, reason=str(e))
                    return
                events.emit("findemail.found", email=email, score=score, status=status)

            await asyncio.gather(*(one(r) for r in rows))
        return found

    contacts = asyncio.run(main())
    n = io.write_csv(out, contacts)
    events.emit("findemail.done", provider=provider, input=len(rows), found=n)
    typer.echo(f"findemail.find: {n}/{len(rows)} verified emails via {provider}")


def _load_cache(path: str) -> dict[str, dict]:
    """domain -> cached row (incl. misses, marked email_status='no_exec')."""
    cache: dict[str, dict] = {}
    if path and Path(path).exists():
        for r in io.read_jsonl(path):
            if r.get("domain"):
                cache[r["domain"].lower()] = r
    return cache


@_transient
async def _apollo_domain(client: httpx.AsyncClient, key: str, domain: str,
                         limit: int = 10, executives_only: bool = True):
    """Apollo people search by domain — equivalent of Hunter domain search."""
    titles = (["CEO", "Founder", "Co-Founder", "President", "Chief Executive",
               "CMO", "Chief Marketing", "VP Marketing", "Head of Marketing"]
              if executives_only else [])
    body: dict = {
        "organization_domains": [domain],
        "per_page": limit,
        "page": 1,
    }
    if titles:
        body["person_titles"] = titles
    r = await client.post(
        "https://api.apollo.io/v1/mixed_people/search",
        headers={"X-Api-Key": key, "Content-Type": "application/json"},
        json=body,
    )
    if r.status_code in (429,) or r.status_code >= 500:
        r.raise_for_status()
    if r.status_code != 200:
        return None
    people = (r.json() or {}).get("people") or []
    candidates = [p for p in people if (p.get("email") or "").strip()
                  and (p.get("email_status") or "") not in ("invalid", "unavailable")]
    if not candidates:
        return None
    _APOLLO_SCORE = {"verified": 95, "likely to engage": 70, "guessed": 40}
    candidates.sort(key=lambda p: (
        _decision_maker_rank(p.get("title", ""), ""),
        -_APOLLO_SCORE.get((p.get("email_status") or "").lower(), 0),
    ))
    best = candidates[0]
    return {
        "email": best["email"].strip().lower(),
        "first_name": (best.get("first_name") or "").strip(),
        "last_name": (best.get("last_name") or "").strip(),
        "title": (best.get("title") or "").strip(),
        "email_score": _APOLLO_SCORE.get((best.get("email_status") or "").lower(), 50),
        "email_status": (best.get("email_status") or "unknown").lower(),
    }


@app.command("find-exec")
def find_exec(
    in_: str = typer.Option(..., "--in", help="domains CSV: just `domain` (+ passthrough e.g. brand)"),
    out: str = typer.Option(..., "--out"),
    concurrency: int = typer.Option(5, "--concurrency", help="keep low: Hunter rate-limits above ~5 (see harness/learnings/03)"),
    min_score: int = typer.Option(80, "--min-score"),
    per_domain: int = typer.Option(10, "--per-domain", help="emails fetched per domain; cost = ceil(n/10) credits"),
    thorough: bool = typer.Option(False, "--thorough", help="limit=25, no seniority filter (3 credits) — better founder precision"),
    cache: str = typer.Option("", "--cache", help="JSONL cache; skip Hunter/Apollo for domains already seen (incl. misses)"),
    provider: str = typer.Option("hunter", "--provider", help="hunter | apollo"),
):
    """domain -> the most senior decision-maker + their verified email (Hunter
    domain-search). No founder name needed — Hunter finds the person.

    Credit-efficient by default: 1 Hunter credit/domain (limit=10, execs only).
    `--thorough` spends 3/domain to avoid cutting off a lower-confidence founder.
    `--cache` makes re-runs and a growing lead bank free (each domain queried
    once, ever). See harness/learnings/05 for the cost model.
    """
    if provider not in ("hunter", "apollo"):
        raise typer.BadParameter(f"find-exec supports hunter | apollo, got {provider!r}")
    limit = 25 if thorough else per_domain
    execs_only = not thorough
    rows = io.read_csv(in_, models.Row)
    key = auth.get_token(provider)
    cached = _load_cache(cache)
    cache_hits = 0

    async def main() -> tuple[list[models.Contact], list[dict]]:
        sem = asyncio.Semaphore(max(1, concurrency))
        found: list[models.Contact] = []
        new_cache_rows: list[dict] = []
        nonlocal cache_hits

        async with httpx.AsyncClient(timeout=60) as client:
            async def one(row: models.Row) -> None:
                nonlocal cache_hits
                domain = (getattr(row, "domain", "") or "").strip().lower()
                if not domain:
                    return
                passthrough = {
                    k: v for k, v in row.model_dump().items()
                    if k not in ("email", "first_name", "last_name", "title")
                    and isinstance(v, str | int | float | bool)
                }
                if domain in cached:           # never re-pay for a known domain
                    cache_hits += 1
                    res = cached[domain]
                else:
                    async with sem:
                        domain_fn = _apollo_domain if provider == "apollo" else _hunter_domain
                        res = await domain_fn(client, key, domain, limit=limit,
                                              executives_only=execs_only)
                    new_cache_rows.append({"domain": domain, **(res or {"email_status": "no_exec"})})
                if not res or not res.get("email"):
                    events.emit("findemail.no_exec", domain=domain)
                    return
                if int(res.get("email_score") or 0) < min_score:
                    events.emit("findemail.low_score", domain=domain, **res)
                    return
                try:
                    found.append(models.Contact(**{
                        **passthrough, "domain": domain,
                        "email": res["email"], "first_name": res.get("first_name", ""),
                        "last_name": res.get("last_name", ""), "title": res.get("title", ""),
                        "email_score": res.get("email_score", 0),
                        "email_status": res.get("email_status", ""),
                    }))
                except (ValueError, KeyError) as e:
                    events.emit("findemail.bad_email", level="warn", reason=str(e))
                    return
                events.emit("findemail.found", domain=domain, email=res["email"],
                            title=res.get("title", ""), score=res.get("email_score", 0))

            await asyncio.gather(*(one(r) for r in rows))
        return found, new_cache_rows

    contacts, new_cache_rows = asyncio.run(main())
    if cache:
        for rec in new_cache_rows:
            io.append_jsonl(cache, rec)
    n = io.write_csv(out, contacts)
    events.emit("findemail.done", provider=f"{provider}-domain", input=len(rows), found=n,
                cache_hits=cache_hits, billed=len(new_cache_rows))
    typer.echo(f"findemail.find-exec: {n}/{len(rows)} decision-makers found "
               f"(cache hits: {cache_hits}, {provider}-queried: {len(rows) - cache_hits})")


if __name__ == "__main__":
    sys.exit(app())
