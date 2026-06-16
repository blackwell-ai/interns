"""extract primitive — explode fetched listing payloads into per-item records.

`fetch.urls` returns one row per source URL (a whole subreddit listing or an
HN Algolia search blob). The researcher's "filter hard" bar is a per-post
judgment, and a digest is built from individual posts — so we need one record
per post/story, not one per page. No existing primitive turns a listing
payload into per-item records, so this is its own small primitive.

Read-only in the outside world: this only parses bytes already fetched.

Supported payloads (auto-detected by shape, then by URL):
  * Reddit listing JSON  — public `.json` or authenticated `oauth.reddit.com`
    both return the same `{data: {children: [{data: {...}}]}}` shape.
  * Hacker News Algolia  — `{hits: [{...}]}` from hn.algolia.com.
"""

from __future__ import annotations

import html
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import typer

from toolbox.core import events, io

_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(s: str) -> str:
    return " ".join(_TAG_RE.sub(" ", html.unescape(s or "")).split())


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]  # drop the Atom XML namespace

app = typer.Typer(no_args_is_help=True)


@app.callback()
def _group():
    """extract primitive."""


def _clip(text: str, n: int) -> str:
    text = " ".join((text or "").split())
    return text[:n]


def _reddit_items(payload: dict, label: str, max_chars: int) -> list[dict]:
    items: list[dict] = []
    children = (payload.get("data") or {}).get("children") or []
    for c in children:
        d = c.get("data") or {}
        if d.get("stickied"):  # pinned mod posts are rarely signal
            continue
        title = d.get("title") or ""
        body = d.get("selftext") or ""
        permalink = d.get("permalink") or ""
        sub = d.get("subreddit") or ""
        items.append({
            "source": f"r/{sub}" if sub else (label or "reddit"),
            "label": label,
            "title": title,
            "url": f"https://www.reddit.com{permalink}" if permalink else (d.get("url") or ""),
            "link": d.get("url") or "",
            "text": _clip(f"{title}\n\n{body}", max_chars),
            "author": d.get("author") or "",
            "score": d.get("score"),
            "comments": d.get("num_comments"),
            "ts": d.get("created_utc"),
        })
    return items


def _hn_items(payload: dict, label: str, max_chars: int) -> list[dict]:
    items: list[dict] = []
    for h in payload.get("hits") or []:
        oid = h.get("objectID") or ""
        title = h.get("title") or h.get("story_title") or ""
        body = h.get("story_text") or h.get("comment_text") or ""
        if not title and not body:
            continue
        items.append({
            "source": "Hacker News",
            "label": label,
            "title": title,
            "url": f"https://news.ycombinator.com/item?id={oid}" if oid else (h.get("url") or ""),
            "link": h.get("url") or "",
            "text": _clip(f"{title}\n\n{body}", max_chars),
            "author": h.get("author") or "",
            "score": h.get("points"),
            "comments": h.get("num_comments"),
            "ts": h.get("created_at"),
        })
    return items


def _reddit_rss_items(text: str, label: str, max_chars: int) -> list[dict]:
    """Parse Reddit's public Atom feed (`/r/<sub>/.rss`) into per-post records.

    The key-free path: `.json` is IP-blocked and the API needs pre-approval, but
    the Atom feed is not gated. It carries title, link, author, and the post body
    (as escaped HTML); it does not carry score or comment counts.
    """
    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        return []
    items: list[dict] = []
    for entry in root.iter():
        if _local(entry.tag) != "entry":
            continue
        d: dict = {}
        for child in entry:
            tag = _local(child.tag)
            if tag == "title":
                d["title"] = child.text or ""
            elif tag == "link":
                d["url"] = child.get("href") or ""
            elif tag == "content":
                d["body"] = _strip_html(child.text or "")
            elif tag == "category":
                d["sub"] = child.get("label") or child.get("term") or ""
            elif tag == "published":
                d["ts"] = child.text or ""
            elif tag == "author":
                for a in child:
                    if _local(a.tag) == "name":
                        d["author"] = a.text or ""
        title = d.get("title", "")
        if not title:
            continue
        sub = d.get("sub") or label
        items.append({
            "source": sub if sub.startswith("r/") else (label or "reddit"),
            "label": label,
            "title": title,
            "url": d.get("url", ""),
            "link": "",
            "text": _clip(f"{title}\n\n{d.get('body', '')}", max_chars),
            "author": (d.get("author") or "").removeprefix("/u/"),
            "score": None,
            "comments": None,
            "ts": d.get("ts"),
        })
    return items


def _parse_page(rec: dict, max_chars: int) -> list[dict]:
    """Return per-item records for one fetched page, or [] if not parseable."""
    if rec.get("status") and rec.get("status") != 200:
        return []
    raw = rec.get("text") or ""
    url = rec.get("url") or ""
    label = rec.get("label") or ""
    if raw.lstrip().startswith("<"):  # Reddit public RSS is Atom XML, not JSON
        return _reddit_rss_items(raw, label, max_chars)
    try:
        payload = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return []
    # Detect by shape first (robust to oauth vs public host), then URL as a hint.
    if isinstance(payload, dict) and "hits" in payload:
        return _hn_items(payload, label, max_chars)
    if isinstance(payload, dict) and isinstance(payload.get("data"), dict):
        return _reddit_items(payload, label, max_chars)
    if "algolia" in url or "ycombinator" in url:
        return _hn_items(payload if isinstance(payload, dict) else {}, label, max_chars)
    return []


@app.command()
def items(
    in_: str = typer.Option(..., "--in", help="pages.jsonl from fetch.urls"),
    out: str = typer.Option(..., "--out", help="items.jsonl: one record per post/story"),
    max_chars: int = typer.Option(4000, "--max-chars", help="cap per-item text length"),
):
    if not Path(in_).exists():
        raise typer.BadParameter(f"input file not found: {in_}")
    p = Path(out)
    if p.exists():
        p.unlink()

    pages = 0
    skipped: list[str] = []
    total = 0
    for rec in io.read_jsonl(in_):
        pages += 1
        page_items = _parse_page(rec, max_chars)
        if not page_items:
            skipped.append(rec.get("url", "?"))
            continue
        for it in page_items:
            io.append_jsonl(out, it)
            total += 1

    events.emit("extract.done", pages=pages, items=total, unparsed=len(skipped))
    if skipped:
        # Never silently drop a source — surface what failed to parse.
        typer.echo(f"extract.items: {total} items from {pages} pages "
                   f"({len(skipped)} unparsed: {', '.join(skipped[:5])})")
    else:
        typer.echo(f"extract.items: {total} items from {pages} pages")


if __name__ == "__main__":
    sys.exit(app())
