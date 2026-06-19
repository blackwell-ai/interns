"""findemail primitive — find + verify a work email from a name + domain.

Apollo-backed lead enrichment: name + domain → verified work email, or domain →
decision-maker + email. Apollo is the only provider as of 2026-06-18 (see
brain/decisions/2026-06-18-apollo-only-outbound.md); the Hunter and Findymail
adapters were removed. A flow goes name+domain → verified email with one API key
and zero manual steps.

Input  : candidates CSV with `domain` + (`first_name`,`last_name`) or `name`
         (and any passthrough columns, e.g. brand/title).
Output : contacts CSV (models.Contact) with the found email, plus
         `email_score` / `email_status` so downstream/compose can gate on
         confidence. Rows with no email found (or below --min-score) are
         dropped and logged — never guessed.

Auth: core/auth.get_token("apollo") — Supabase connection or the
TOOLBOX_TOKEN_APOLLO env override. No key in argv or the repo.
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


# ---- provider adapter: returns (email, score_0_100, status) ------------------


@_transient
async def _apollo(client: httpx.AsyncClient, key: str, domain: str, first: str, last: str):
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


_PROVIDERS = {"apollo": _apollo}

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


@app.command()
def find(
    in_: str = typer.Option(..., "--in", help="candidates CSV: domain + first_name/last_name or name"),
    out: str = typer.Option(..., "--out", help="contacts CSV with email,email_score,email_status"),
    provider: str = typer.Option("apollo", "--provider", help="apollo"),
    concurrency: int = typer.Option(5, "--concurrency", help="keep low: Apollo rate-limits above ~5 (see harness/learnings/03)"),
    min_score: int = typer.Option(80, "--min-score", help="drop emails below this confidence (0-100)"),
):
    """name + domain -> verified work email (Apollo people match, headless)."""
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
    """Apollo people search (api_search) -> reveal the top decision-maker.

    The old mixed_people/search is deprecated for API callers. api_search returns
    names + titles + ids but no emails (and obfuscated last names), so we reveal
    the top-ranked candidate via people/match (one credit) for the work email.
    """
    hdr = {"X-Api-Key": key, "Content-Type": "application/json"}
    seniorities = (["owner", "founder", "c_suite", "partner", "vp", "head", "director"]
                   if executives_only else [])
    body: dict = {"q_organization_domains_list": [domain], "per_page": limit, "page": 1}
    if seniorities:
        body["person_seniorities"] = seniorities
    r = await client.post("https://api.apollo.io/v1/mixed_people/api_search", headers=hdr, json=body)
    if r.status_code in (429,) or r.status_code >= 500:
        r.raise_for_status()
    if r.status_code != 200:
        return None
    people = (r.json() or {}).get("people") or []
    if not people:
        return None
    people.sort(key=lambda p: _decision_maker_rank(p.get("title", ""), ""))
    top = people[0]
    rr = await client.post("https://api.apollo.io/v1/people/match", headers=hdr,
                           json={"id": top.get("id"), "reveal_personal_emails": False})
    if rr.status_code in (429,) or rr.status_code >= 500:
        rr.raise_for_status()
    if rr.status_code != 200:
        return None
    person = (rr.json() or {}).get("person") or {}
    email = (person.get("email") or "").strip().lower()
    if not email:
        return None
    _APOLLO_SCORE = {"verified": 95, "likely to engage": 70, "guessed": 40}
    status = (person.get("email_status") or "unknown").lower()
    return {
        "email": email,
        "first_name": (person.get("first_name") or "").strip(),
        "last_name": (person.get("last_name") or "").strip(),
        "title": (person.get("title") or top.get("title") or "").strip(),
        "email_score": _APOLLO_SCORE.get(status, 50),
        "email_status": status,
    }


@app.command("find-exec")
def find_exec(
    in_: str = typer.Option(..., "--in", help="domains CSV: just `domain` (+ passthrough e.g. brand)"),
    out: str = typer.Option(..., "--out"),
    concurrency: int = typer.Option(5, "--concurrency", help="keep low: Apollo rate-limits above ~5 (see harness/learnings/03)"),
    min_score: int = typer.Option(80, "--min-score"),
    per_domain: int = typer.Option(10, "--per-domain", help="people fetched per domain"),
    thorough: bool = typer.Option(False, "--thorough", help="limit=25, no seniority filter — better founder precision"),
    cache: str = typer.Option("", "--cache", help="JSONL cache; skip Apollo for domains already seen (incl. misses)"),
    provider: str = typer.Option("apollo", "--provider", help="apollo"),
):
    """domain -> the most senior decision-maker + their verified email (Apollo
    people search). No founder name needed — Apollo finds the person.

    `--cache` makes re-runs and a growing lead bank free (each domain queried
    once, ever). Apollo's exact credit model is pending Armaan's directions.
    """
    if provider not in ("apollo",):
        raise typer.BadParameter(f"find-exec supports apollo, got {provider!r}")
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
                        res = await _apollo_domain(client, key, domain, limit=limit,
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
