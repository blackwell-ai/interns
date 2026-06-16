"""fetch primitive — pull web sources into the run folder (M4: proves the
harness is brain infrastructure, not an outreach feature).

Read-only in the outside world, per the researcher charter.

Reddit blocks server/cloud IPs on its public endpoints (403 on `.json`, 429 on
`.rss`). So when a `reddit` connection exists, Reddit URLs are read through the
authenticated API (`oauth.reddit.com`, app-only token), which is allowed from
any IP at ~100 req/min. With no connection, we fall back to the public
`.json` endpoint (works only from a residential IP). Everything else
(e.g. the Hacker News Algolia API) is fetched plainly.
"""

from __future__ import annotations

import asyncio
import re
import sys

import httpx
import typer
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from toolbox.core import events, io

app = typer.Typer(no_args_is_help=True)

_UA = "blackwell-research-bot/0.1 (read-only watchlist sweep)"
_SUBREDDIT_RE = re.compile(r"reddit\.com(/r/[^/?#]+)", re.I)


@app.callback()
def _group():
    """fetch primitive."""


# Patient enough to ride out a rate-limit window (Reddit throttles anonymous
# reads hard): ~1+2+4+8+16+30+30 ≈ 90s across attempts before giving up.
_transient = retry(
    retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.TransportError)),
    wait=wait_exponential(multiplier=1, max=30),
    stop=stop_after_attempt(7),
    reraise=True,
)


@_transient
async def _get(client: httpx.AsyncClient, url: str, headers: dict | None = None) -> httpx.Response:
    r = await client.get(url, headers=headers)
    if r.status_code == 429 or r.status_code >= 500:
        r.raise_for_status()
    return r


def _reddit_app_token() -> str | None:
    """App-only bearer token via client_credentials, or None if no connection.

    The stored `reddit` secret is `client_id:client_secret` (register a free app
    at reddit.com/prefs/apps). Never logged, never placed in argv.
    """
    from toolbox.core import auth

    try:
        secret = auth.get_token("reddit")
    except Exception:
        return None
    client_id, _, client_secret = secret.partition(":")
    if not client_id or not client_secret:
        return None
    try:
        r = httpx.post(
            "https://www.reddit.com/api/v1/access_token",
            data={"grant_type": "client_credentials"},
            auth=(client_id, client_secret),
            headers={"User-Agent": _UA},
            timeout=30,
        )
        r.raise_for_status()
        return r.json().get("access_token")
    except Exception:
        return None


@app.command()
def urls(
    in_: str = typer.Option(..., "--in", help="CSV with a 'url' column (e.g. watchlist sources)"),
    out: str = typer.Option(..., "--out", help="pages.jsonl: {url, status, text, label}"),
    concurrency: int = typer.Option(8, "--concurrency"),
    max_chars: int = typer.Option(20000, "--max-chars"),
    limit: int = typer.Option(25, "--limit", help="items per Reddit listing"),
):
    import csv as _csv
    from pathlib import Path

    sources: list[tuple[str, str]] = []
    with Path(in_).open(encoding="utf-8", newline="") as f:
        for row in _csv.DictReader(f):
            u = (row.get("url") or "").strip()
            if u:
                sources.append((u, (row.get("label") or "").strip()))

    needs_reddit = any("reddit.com/r/" in u for u, _ in sources)
    bearer = _reddit_app_token() if needs_reddit else None
    if needs_reddit:
        events.emit("fetch.reddit_auth", authenticated=bool(bearer))

    def _plan(url: str) -> tuple[str, dict | None]:
        """Return (fetch_url, extra_headers) for one source URL."""
        m = _SUBREDDIT_RE.search(url)
        if m and bearer:
            path = m.group(1).rstrip("/")
            return (f"https://oauth.reddit.com{path}/hot?limit={limit}&raw_json=1",
                    {"Authorization": f"bearer {bearer}", "User-Agent": _UA})
        if m and not url.endswith(".rss"):
            # Public RSS works from a residential IP without a key (Reddit's
            # `.json` is IP-blocked and the API now needs pre-approval, but the
            # Atom feed is not gated). Run the cron on a residential machine.
            return (url.rstrip("/") + f"/.rss?limit={limit}", None)
        return (url, None)

    async def main() -> list[dict]:
        sem = asyncio.Semaphore(max(1, concurrency))
        headers = {"User-Agent": _UA}
        results: list[dict] = []
        async with httpx.AsyncClient(headers=headers, timeout=30, follow_redirects=True) as client:
            async def one(url: str, label: str) -> None:
                fetch_url, extra = _plan(url)
                async with sem:
                    try:
                        r = await _get(client, fetch_url, headers=extra)
                        results.append({"url": url, "label": label, "status": r.status_code,
                                        "text": r.text[:max_chars]})
                    except Exception as e:
                        results.append({"url": url, "label": label, "status": 0,
                                        "text": "", "error": str(e)[:200]})
                events.emit("fetch.url_done", url=url)

            await asyncio.gather(*(one(u, lbl) for u, lbl in sources))
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
