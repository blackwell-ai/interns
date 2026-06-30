#!/usr/bin/env python3
"""StoreLeads REST client — source real e-commerce store domains for a niche.

Replaces LLM domain-guessing in the campaign sourcing step with a query against
the StoreLeads database of real, live online stores (Shopify, WooCommerce,
BigCommerce, ...). This is the same API the StoreLeads MCP wraps; we call it
directly over HTTP so the headless pipeline (run.py, send.sh, the Railway
server) can use it with no MCP present.

Why this beats Claude guessing domains:
  - every domain is a confirmed live store, so no Hunter credit is spent
    enriching a hallucinated or dead domain;
  - the result set is real and paginated, so a niche is no longer capped at the
    ~20 names Claude can recall before it starts inventing;
  - results can be ranked by estimated sales / store rank so the best-fit stores
    are enriched first.

Auth: TOOLBOX_TOKEN_STORELEADS (Bearer). The key is read via toolbox auth, never
placed in argv or written to the repo.

API: https://storeleads.app/api  (List Domains endpoint, f: filter params)
"""
from __future__ import annotations

import asyncio

import httpx

from toolbox.core import auth, events

# List Domains endpoint. f: filter params + q + sort + page_size + cursor.
_BASE = "https://storeleads.app/json/api/v1/all/domain"
_DEFAULT_FIELDS = "name,platform,estimated_sales,rank,country_code"

# Memoize the token lookup. When TOOLBOX_TOKEN_STORELEADS is unset, auth.get_token
# makes a Supabase round-trip that 404s; caching the (possibly empty) result keeps
# the no-token fallback path from doing that on every single niche.
_token_cache: str | None = None
_token_loaded = False


def get_token() -> str | None:
    """Return the StoreLeads API key, or None if not configured."""
    global _token_cache, _token_loaded
    if _token_loaded:
        return _token_cache
    try:
        tok = auth.get_token("storeleads")
        _token_cache = tok or None
    except Exception:
        _token_cache = None
    _token_loaded = True
    return _token_cache


def available() -> bool:
    """True when a StoreLeads key is configured (so the pipeline can use it)."""
    return bool(get_token())


def _strip_www(name: str) -> str:
    """StoreLeads returns 'www.brand.com'; Hunter wants the bare 'brand.com'."""
    n = name.strip().lower()
    return n[4:] if n.startswith("www.") else n


async def search_domains(
    filters: dict,
    *,
    q: str = "",
    sort: str = "-er,rank",
    page_size: int = 50,
    cursor: str | None = None,
    fields: str = _DEFAULT_FIELDS,
    token: str | None = None,
    client: httpx.AsyncClient | None = None,
) -> tuple[list[str], str | None]:
    """Query StoreLeads List Domains. Returns (domains_without_www, next_cursor).

    `filters` uses StoreLeads f: keys, e.g. {"f:cc": "US", "f:ermin": 2000000}.
    `q` is a free-text keyword query. `sort` defaults to estimated-sales desc with
    rank as the tiebreak so the strongest stores come first.

    Returns ([], None) when no token is configured. Honours a single Retry-After
    on HTTP 429 (StoreLeads rate-limits Pro/Elite at ~2 req/s). Raises
    httpx.HTTPError on other transport/HTTP failures so callers can fall back.
    """
    key = token or get_token()
    if not key:
        return [], None

    params: dict[str, object] = dict(filters)
    if q:
        params["q"] = q
    if sort:
        params["sort"] = sort
    if page_size:
        params["page_size"] = page_size
    if fields:
        params["fields"] = fields
    if cursor:
        params["cursor"] = cursor

    headers = {"Authorization": f"Bearer {key}", "Accept": "application/json"}

    async def _do(c: httpx.AsyncClient) -> httpx.Response:
        r = await c.get(_BASE, params=params, headers=headers, timeout=30)
        if r.status_code == 429:
            wait = float(r.headers.get("Retry-After", "1") or "1")
            await asyncio.sleep(min(wait, 5.0))
            r = await c.get(_BASE, params=params, headers=headers, timeout=30)
        r.raise_for_status()
        return r

    if client is not None:
        resp = await _do(client)
    else:
        async with httpx.AsyncClient() as c:
            resp = await _do(c)

    data = resp.json()
    domains = [_strip_www(d["name"]) for d in data.get("domains", []) if d.get("name")]
    next_cursor = data.get("next_cursor") if data.get("has_next_page") else None
    events.emit("storeleads.search", level="info",
                q=q, returned=len(domains), total=data.get("total"))
    return domains, next_cursor
