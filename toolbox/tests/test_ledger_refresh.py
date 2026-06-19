"""Offline regression test: the ledger refreshes an expired session JWT.

A long campaign (sourcing/sending 1000+ contacts) outlives the token the
Ledger was constructed with. On a 401 the ledger must fetch a fresh token and
retry, or the run dies partway — which is exactly what a 1000-contact Apollo
send hit the first time (401 on the first ledger check after the token expired).
"""

from __future__ import annotations

import sys
from pathlib import Path

import httpx
import pytest
import respx

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from toolbox.core import auth, ledger


@pytest.mark.asyncio
@respx.mock
async def test_rpc_force_refreshes_token_on_401(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "anon-key")
    monkeypatch.setattr(auth, "force_refresh", lambda stale="": "fresh-token")

    route = respx.post("https://test.supabase.co/rest/v1/rpc/check_contact").mock(
        side_effect=[
            httpx.Response(401, json={"message": "JWT expired"}),
            httpx.Response(200, json="new"),
        ]
    )
    led = ledger.Ledger("stale-token")
    try:
        result = await led.check("email", "Person@Example.com")
    finally:
        await led.aclose()

    assert result == "new"
    assert route.call_count == 2  # 401, then retried after force-refresh
    assert led._token == "fresh-token"


@pytest.mark.asyncio
@respx.mock
async def test_rpc_no_retry_loop_when_token_unchanged(monkeypatch):
    """If the refresh yields no new token, surface the 401 (no infinite retry)."""
    monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "anon-key")
    monkeypatch.setattr(auth, "force_refresh", lambda stale="": "stale-token")  # unchanged

    route = respx.post("https://test.supabase.co/rest/v1/rpc/check_contact").mock(
        return_value=httpx.Response(401, json={"message": "JWT expired"})
    )
    led = ledger.Ledger("stale-token")
    try:
        with pytest.raises(httpx.HTTPStatusError):
            await led.check("email", "a@b.com")
    finally:
        await led.aclose()

    assert route.call_count == 1  # no retry when the token did not change


@pytest.mark.asyncio
@respx.mock
async def test_rpc_retries_transient_transport_error(monkeypatch):
    """A connection blip under load is retried, not fatal."""
    monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "anon-key")

    route = respx.post("https://test.supabase.co/rest/v1/rpc/check_contact").mock(
        side_effect=[
            httpx.ConnectError("connection reset"),
            httpx.Response(200, json="new"),
        ]
    )
    led = ledger.Ledger("tok")
    try:
        result = await led.check("email", "a@b.com")
    finally:
        await led.aclose()

    assert result == "new"
    assert route.call_count == 2
