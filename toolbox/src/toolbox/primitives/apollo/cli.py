"""apollo primitive — people search + enrichment against api.apollo.io (new,
spec §5). Key comes from the person's (or org-shared) connection at runtime.
"""

from __future__ import annotations

import asyncio
import sys

import httpx
import typer
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from toolbox.core import auth, events, io, models

APOLLO_API = "https://api.apollo.io/api/v1"

app = typer.Typer(no_args_is_help=True)


@app.callback()
def _group():
    """apollo primitive."""


_transient = retry(
    retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.TransportError)),
    wait=wait_exponential(multiplier=1, max=60),
    stop=stop_after_attempt(6),
    reraise=True,
)


@_transient
async def _people_search(client: httpx.AsyncClient, domain: str, titles: list[str],
                         per_company: int) -> list[dict]:
    r = await client.post(f"{APOLLO_API}/mixed_people/search", json={
        "q_organization_domains_list": [domain],
        "person_titles": titles,
        "page": 1,
        "per_page": per_company,
    })
    if r.status_code == 429 or r.status_code >= 500:
        r.raise_for_status()  # transient → retried
    if r.status_code != 200:
        events.emit("apollo.error", level="warn", domain=domain, status=r.status_code)
        return []
    return r.json().get("people") or []


@app.command()
def enrich(
    in_: str = typer.Option(..., "--in", help="domains.csv"),
    out: str = typer.Option(..., "--out", help="contacts.csv"),
    roles: str = typer.Option("founder,ceo,owner", "--roles", help="comma-separated titles"),
    per_company: int = typer.Option(2, "--per-company"),
    concurrency: int = typer.Option(20, "--concurrency"),
):
    """For each domain, find people matching the roles and pull their emails."""
    domains = io.read_csv(in_, models.Domain)
    titles = [t.strip() for t in roles.split(",") if t.strip()]
    api_key = auth.get_token("apollo")

    async def main() -> list[models.Contact]:
        sem = asyncio.Semaphore(max(1, concurrency))
        contacts: list[models.Contact] = []
        async with httpx.AsyncClient(
            headers={"X-Api-Key": api_key, "Content-Type": "application/json"}, timeout=60
        ) as client:
            async def one(d: models.Domain) -> None:
                async with sem:
                    people = await _people_search(client, d.domain, titles, per_company)
                for p in people:
                    email = (p.get("email") or "").strip().lower()
                    if not email or email.endswith("@domain.com") or "not_unlocked" in email:
                        continue  # Apollo returns placeholders for locked emails
                    try:
                        contacts.append(models.Contact(
                            email=email,
                            first_name=p.get("first_name") or "",
                            last_name=p.get("last_name") or "",
                            name=p.get("name") or "",
                            title=p.get("title") or "",
                            company=(p.get("organization") or {}).get("name") or d.company,
                            domain=d.domain,
                        ))
                    except ValueError:
                        continue
                events.emit("apollo.domain_done", domain=d.domain, people=len(people))

            await asyncio.gather(*(one(d) for d in domains))
        return contacts

    contacts = asyncio.run(main())
    n = io.write_csv(out, contacts)
    events.emit("apollo.enriched", domains=len(domains), contacts=n)
    typer.echo(f"apollo.enrich: {n} contacts from {len(domains)} domains")


if __name__ == "__main__":
    sys.exit(app())
