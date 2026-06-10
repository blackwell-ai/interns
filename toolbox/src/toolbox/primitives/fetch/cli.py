"""fetch primitive — pull web sources into the run folder (M4: proves the
harness is brain infrastructure, not an outreach feature).

Read-only in the outside world, per the researcher charter. Reddit URLs get
`.json` appended automatically (Reddit's public JSON endpoints).
"""

from __future__ import annotations

import asyncio
import sys

import httpx
import typer
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from toolbox.core import events, io

app = typer.Typer(no_args_is_help=True)


@app.callback()
def _group():
    """fetch primitive."""


_transient = retry(
    retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.TransportError)),
    wait=wait_exponential(multiplier=1, max=30),
    stop=stop_after_attempt(4),
    reraise=True,
)


@_transient
async def _get(client: httpx.AsyncClient, url: str) -> httpx.Response:
    r = await client.get(url)
    if r.status_code == 429 or r.status_code >= 500:
        r.raise_for_status()
    return r


@app.command()
def urls(
    in_: str = typer.Option(..., "--in", help="CSV with a 'url' column (e.g. watchlist sources)"),
    out: str = typer.Option(..., "--out", help="pages.jsonl: {url, status, text}"),
    concurrency: int = typer.Option(8, "--concurrency"),
    max_chars: int = typer.Option(20000, "--max-chars"),
):
    import csv as _csv
    from pathlib import Path

    with Path(in_).open(encoding="utf-8", newline="") as f:
        sources = [row["url"].strip() for row in _csv.DictReader(f) if row.get("url", "").strip()]

    async def main() -> list[dict]:
        sem = asyncio.Semaphore(max(1, concurrency))
        headers = {"User-Agent": "blackwell-research-bot/0.1 (read-only watchlist sweep)"}
        results: list[dict] = []
        async with httpx.AsyncClient(headers=headers, timeout=30, follow_redirects=True) as client:
            async def one(url: str) -> None:
                fetch_url = url
                if "reddit.com/r/" in url and not url.endswith(".json"):
                    fetch_url = url.rstrip("/") + "/.json?limit=25"
                async with sem:
                    try:
                        r = await _get(client, fetch_url)
                        results.append({"url": url, "status": r.status_code,
                                        "text": r.text[:max_chars]})
                    except Exception as e:
                        results.append({"url": url, "status": 0, "text": "", "error": str(e)[:200]})
                events.emit("fetch.url_done", url=url)

            await asyncio.gather(*(one(u) for u in sources))
        return results

    results = asyncio.run(main())
    from pathlib import Path as _P

    p = _P(out)
    if p.exists():
        p.unlink()
    for rec in results:
        io.append_jsonl(out, rec)
    events.emit("fetch.done", count=len(results))
    typer.echo(f"fetch.urls: {len(results)} sources fetched")


if __name__ == "__main__":
    sys.exit(app())
