"""domains primitive — web-search domain sourcing (port of source_domains
internals, provider swapped: OpenAI hosted web_search → Anthropic web_search
server tool).

Two-stage, like the original: (1) LLM drafts diverse search queries for the
segment; (2) each query runs a web search and a structured extraction of
company domains. Dedup + exclusion filtering happen here; deliverability is
verify.check's job downstream.
"""

from __future__ import annotations

import asyncio
import sys

import typer
from pydantic import BaseModel

from toolbox.core import events, io, models

app = typer.Typer(no_args_is_help=True)


@app.callback()
def _group():
    """domains primitive."""


class _Queries(BaseModel):
    queries: list[str]


class _Found(BaseModel):
    class Item(BaseModel):
        company_name: str
        domain: str
        source_url: str = ""

    retailers: list[Item]


@app.command()
def source(
    query: str = typer.Option(..., "--query", help="segment description, e.g. 'DTC yoga apparel stores'"),
    count: int = typer.Option(100, "--count", help="target number of domains"),
    out: str = typer.Option(..., "--out"),
    exclude: str = typer.Option("", "--exclude", help="comma-separated exclusions (e.g. marketplaces)"),
    concurrency: int = typer.Option(4, "--concurrency"),
    model: str = typer.Option("", "--model"),
):
    """segment description -> domains.csv (domain, company, source, segment)."""
    from toolbox.core import llm

    n_queries = max(3, min(15, count // 10))
    queries = llm.parse(
        f"Generate {n_queries} diverse web-search queries a human would type into Google to find "
        f"companies in this segment: {query!r}. Vary the angle: listicles, directories, 'best X' "
        f"articles, funding databases, press. Exclude: {exclude or 'nothing'}.",
        _Queries, model=model or None,
    ).queries

    seen: set[str] = set()
    rows: list[models.Domain] = []
    sem = asyncio.Semaphore(max(1, concurrency))

    async def run_query(q: str) -> None:
        if len(rows) >= count:
            return
        async with sem:
            text = await asyncio.to_thread(
                llm.web_search,
                f"Find companies matching: {query!r} using the search query {q!r}. "
                f"List every company you find with its website domain. Exclude: {exclude or 'nothing'}.",
                model=model or None,
            )
            found = await asyncio.to_thread(
                llm.parse,
                "Extract every (company_name, domain, source_url) from this research text. "
                "domain is the bare website domain (no http://, no path). Skip marketplaces, "
                "aggregators and anything matching the exclusions: "
                f"{exclude or 'none'}.\n\n{text[:6000]}",
                _Found,
            )
        for item in found.retailers:
            try:
                d = models.Domain(domain=item.domain, company=item.company_name,
                                  source=item.source_url, segment=query)
            except ValueError:
                continue
            if d.domain not in seen and len(rows) < count:
                seen.add(d.domain)
                rows.append(d)
        events.emit("domains.query_done", query=q, total=len(rows))

    async def main():
        await asyncio.gather(*(run_query(q) for q in queries))

    asyncio.run(main())
    n = io.write_csv(out, rows)
    events.emit("domains.sourced", count=n, target=count)
    typer.echo(f"domains.source: {n}/{count} domains")


if __name__ == "__main__":
    sys.exit(app())
