"""storeleads primitive — e-commerce store search against storeleads.app (new,
spec §5). Filters by platform/category/country; emits domains.csv compatible
with apollo.enrich.
"""

from __future__ import annotations

import sys

import httpx
import typer
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from toolbox.core import auth, events, io, models

API = "https://storeleads.app/json/api/v1/all/domain"

app = typer.Typer(no_args_is_help=True)


@app.callback()
def _group():
    """storeleads primitive."""


_transient = retry(
    retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.TransportError)),
    wait=wait_exponential(multiplier=1, max=60),
    stop=stop_after_attempt(6),
    reraise=True,
)


@_transient
def _page(client: httpx.Client, params: dict) -> dict:
    r = client.get(API, params=params)
    if r.status_code == 429 or r.status_code >= 500:
        r.raise_for_status()
    r.raise_for_status()
    return r.json()


@app.command()
def search(
    out: str = typer.Option(..., "--out"),
    platform: str = typer.Option("shopify", "--platform"),
    category: str = typer.Option("", "--category", help="StoreLeads category filter"),
    country: str = typer.Option("US", "--country"),
    count: int = typer.Option(100, "--count"),
    segment: str = typer.Option("", "--segment", help="label written to the segment column"),
):
    """Find stores -> domains.csv."""
    api_key = auth.get_token("storeleads")
    rows: list[models.Domain] = []
    seen: set[str] = set()
    after = ""
    with httpx.Client(headers={"Authorization": f"Bearer {api_key}"}, timeout=60) as client:
        while len(rows) < count:
            params: dict = {"bq": _build_query(platform, category, country),
                            "page_size": min(100, count - len(rows))}
            if after:
                params["page_after"] = after
            data = _page(client, params)
            domains = data.get("domains") or []
            if not domains:
                break
            for d in domains:
                name = (d.get("name") or "").strip().lower()
                if not name or name in seen:
                    continue
                try:
                    rows.append(models.Domain(
                        domain=name,
                        company=d.get("title") or d.get("merchant_name") or "",
                        source="storeleads",
                        segment=segment or category or platform,
                    ))
                    seen.add(name)
                except ValueError:
                    continue
            after = domains[-1].get("name", "")
            if len(domains) < params["page_size"]:
                break
    n = io.write_csv(out, rows[:count])
    events.emit("storeleads.searched", count=n)
    typer.echo(f"storeleads.search: {n} stores")


def _build_query(platform: str, category: str, country: str) -> str:
    clauses = []
    if platform:
        clauses.append(f'platform:"{platform}"')
    if category:
        clauses.append(f'cat:"{category}"')
    if country:
        clauses.append(f'cc:"{country}"')
    return " AND ".join(clauses)


if __name__ == "__main__":
    sys.exit(app())
