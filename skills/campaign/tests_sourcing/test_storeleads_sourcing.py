"""Tests for StoreLeads-primary domain sourcing (with LLM fallback).

The sourcing step now pulls real, live store domains from StoreLeads instead of
asking Claude to guess company names, falling back to LLM generation whenever
StoreLeads cannot serve a niche. These tests cover the dispatcher branches plus
the HTTP client itself.

Covered:
  - storeleads.search_domains: URL/params, www stripping, no-token, 429 retry.
  - source_domains_for_subcat: token-absent fallback, happy path, not-applicable
    fallback, empty-result fallback, HTTP-error fallback, exclude filtering.

These cover boundaries, nulls, and bad state per the harness test rule. Delete
this folder once the next large run confirms StoreLeads sourcing in production.

Run:
  cd /Users/shamitd/interns
  PYTHONPATH="$PWD:$PWD/toolbox/src" toolbox/.venv/bin/pytest \
    skills/campaign/tests_sourcing/test_storeleads_sourcing.py -v
"""

from __future__ import annotations

import asyncio

import httpx
import pytest
import respx

from skills.campaign import run as camp
from skills.campaign import storeleads

_SEARCH = "https://storeleads.app/json/api/v1/all/domain"

# Every test in this module is async; strict-mode pytest-asyncio needs the marker.
pytestmark = pytest.mark.asyncio


def _filters(applicable=True, q="maternity clothing", category="/Apparel"):
    return camp._SubcatFilters(applicable=applicable, q=q, category=category)


# --------------------------------------------------------------------------- #
# storeleads.search_domains — the HTTP client
# --------------------------------------------------------------------------- #

@respx.mock
async def test_search_strips_www_and_reads_cursor():
    route = respx.get(_SEARCH).mock(return_value=httpx.Response(200, json={
        "domains": [
            {"name": "www.kindredbravely.com"},
            {"name": "hatchcollection.com"},
            {"name": ""},  # skipped — no name
        ],
        "has_next_page": True,
        "next_cursor": "CUR123",
        "total": 65,
    }))
    domains, cursor = await storeleads.search_domains(
        {"f:cc": "US"}, q="maternity clothing", token="testkey")
    assert domains == ["kindredbravely.com", "hatchcollection.com"]
    assert cursor == "CUR123"
    # Auth + key params reached the API.
    req = route.calls.last.request
    assert req.headers["Authorization"] == "Bearer testkey"
    assert "maternity+clothing" in str(req.url) or "maternity%20clothing" in str(req.url)
    # ':' in the filter key is percent-encoded; the server decodes it back to f:cc.
    assert "f%3Acc=US" in str(req.url)


@respx.mock
async def test_search_no_next_page_returns_none_cursor():
    respx.get(_SEARCH).mock(return_value=httpx.Response(200, json={
        "domains": [{"name": "foo.com"}], "has_next_page": False,
        "next_cursor": "ignored", "total": 1,
    }))
    domains, cursor = await storeleads.search_domains({}, q="x", token="testkey")
    assert domains == ["foo.com"]
    assert cursor is None  # cursor only surfaced when has_next_page is true


async def test_search_no_token_returns_empty(monkeypatch):
    monkeypatch.setattr(storeleads, "get_token", lambda: None)
    domains, cursor = await storeleads.search_domains({}, q="x")
    assert domains == [] and cursor is None


@respx.mock
async def test_search_retries_once_on_429():
    route = respx.get(_SEARCH).mock(side_effect=[
        httpx.Response(429, headers={"Retry-After": "0"}, json={}),
        httpx.Response(200, json={"domains": [{"name": "bar.com"}],
                                  "has_next_page": False}),
    ])
    domains, _ = await storeleads.search_domains({}, q="x", token="testkey")
    assert domains == ["bar.com"]
    assert route.call_count == 2


# --------------------------------------------------------------------------- #
# source_domains_for_subcat — the StoreLeads-first / LLM-fallback dispatcher
# --------------------------------------------------------------------------- #

def _patch_llm_fallback(monkeypatch, marker=("llm-fallback.com",)):
    """Make the LLM fallback observable and deterministic."""
    monkeypatch.setattr(camp, "generate_domains_for_subcat",
                        lambda subcat, count, exclude=None: list(marker))


async def test_fallback_when_no_token(monkeypatch):
    monkeypatch.setattr(camp.storeleads, "available", lambda: False)
    _patch_llm_fallback(monkeypatch)
    out = await camp.source_domains_for_subcat("DTC maternity clothing")
    assert out == ["llm-fallback.com"]


async def test_storeleads_happy_path(monkeypatch):
    monkeypatch.setattr(camp.storeleads, "available", lambda: True)
    monkeypatch.setattr(camp, "subcat_to_filters", lambda s: _filters())
    _patch_llm_fallback(monkeypatch)  # must NOT be used

    async def fake_search(filters, **kw):
        assert filters.get("f:ds") == "Active"   # base filter applied
        assert filters.get("f:cat") == "/Apparel"  # category threaded through
        assert kw["q"] == "maternity clothing"
        return (["kindredbravely.com", "hatchcollection.com"], "CUR")

    monkeypatch.setattr(camp.storeleads, "search_domains", fake_search)
    out = await camp.source_domains_for_subcat("DTC maternity clothing")
    assert out == ["kindredbravely.com", "hatchcollection.com"]


async def test_fallback_when_not_applicable(monkeypatch):
    monkeypatch.setattr(camp.storeleads, "available", lambda: True)
    monkeypatch.setattr(camp, "subcat_to_filters",
                        lambda s: _filters(applicable=False, q=""))
    _patch_llm_fallback(monkeypatch)

    async def fake_search(*a, **k):  # should not be reached
        raise AssertionError("search_domains called for non-applicable niche")

    monkeypatch.setattr(camp.storeleads, "search_domains", fake_search)
    out = await camp.source_domains_for_subcat("3PL fulfillment providers")
    assert out == ["llm-fallback.com"]


async def test_bad_category_retries_without_it(monkeypatch):
    """A hallucinated category zeros the query; retry on the keyword alone."""
    monkeypatch.setattr(camp.storeleads, "available", lambda: True)
    monkeypatch.setattr(camp, "subcat_to_filters",
                        lambda s: _filters(q="pet supplements", category="/Pet Supplies"))
    _patch_llm_fallback(monkeypatch)  # must NOT be used — StoreLeads salvages it

    calls = []

    async def fake_search(filters, **kw):
        calls.append(filters)
        if "f:cat" in filters:          # first attempt with the bad category
            return ([], None)
        return (["nativepet.com", "petreleaf.com"], None)  # keyword-only retry

    monkeypatch.setattr(camp.storeleads, "search_domains", fake_search)
    out = await camp.source_domains_for_subcat("DTC pet supplements")
    assert out == ["nativepet.com", "petreleaf.com"]
    assert len(calls) == 2                       # retried exactly once
    assert "f:cat" in calls[0] and "f:cat" not in calls[1]


async def test_fallback_when_storeleads_empty(monkeypatch):
    monkeypatch.setattr(camp.storeleads, "available", lambda: True)
    monkeypatch.setattr(camp, "subcat_to_filters", lambda s: _filters())
    _patch_llm_fallback(monkeypatch)

    async def fake_search(filters, **kw):
        return ([], None)

    monkeypatch.setattr(camp.storeleads, "search_domains", fake_search)
    out = await camp.source_domains_for_subcat("DTC maternity clothing")
    assert out == ["llm-fallback.com"]


async def test_fallback_when_storeleads_errors(monkeypatch):
    monkeypatch.setattr(camp.storeleads, "available", lambda: True)
    monkeypatch.setattr(camp, "subcat_to_filters", lambda s: _filters())
    _patch_llm_fallback(monkeypatch)

    async def fake_search(filters, **kw):
        raise httpx.ConnectError("boom")

    monkeypatch.setattr(camp.storeleads, "search_domains", fake_search)
    out = await camp.source_domains_for_subcat("DTC maternity clothing")
    assert out == ["llm-fallback.com"]


async def test_exclude_filters_already_contacted(monkeypatch):
    monkeypatch.setattr(camp.storeleads, "available", lambda: True)
    monkeypatch.setattr(camp, "subcat_to_filters", lambda s: _filters())
    _patch_llm_fallback(monkeypatch)

    async def fake_search(filters, **kw):
        return (["keep.com", "skip.com", "also-keep.com"], None)

    monkeypatch.setattr(camp.storeleads, "search_domains", fake_search)
    out = await camp.source_domains_for_subcat(
        "DTC maternity clothing", exclude={"skip.com"})
    assert out == ["keep.com", "also-keep.com"]


async def test_all_excluded_falls_back(monkeypatch):
    monkeypatch.setattr(camp.storeleads, "available", lambda: True)
    monkeypatch.setattr(camp, "subcat_to_filters", lambda s: _filters())
    _patch_llm_fallback(monkeypatch)

    async def fake_search(filters, **kw):
        return (["dup.com"], None)

    monkeypatch.setattr(camp.storeleads, "search_domains", fake_search)
    out = await camp.source_domains_for_subcat(
        "DTC maternity clothing", exclude={"dup.com"})
    assert out == ["llm-fallback.com"]  # nothing left after exclude -> LLM
