"""Tests for the Gmail add-on HTTP endpoint (wizard/addon_api.py): the shared-secret
auth gate, the founder check, the per-founder rate limit, and the draft payload shape.
Nothing hits Gmail, Supabase, or the LLM.

Run:  toolbox/.venv/bin/python -m pytest skills/campaign/tests_addon -o asyncio_mode=auto
Per the repo rule, this folder is temporary and deleted after merge.
"""
import os
import sys
from pathlib import Path

import pytest
from aiohttp import web

_DUMMY = {
    "ANTHROPIC_API_KEY": "x", "GOOGLE_OAUTH_CLIENT_ID": "x",
    "GOOGLE_OAUTH_CLIENT_SECRET": "x", "TOOLBOX_TOKEN_HUNTER": "x",
    "SUPABASE_URL": "https://supa.test", "SUPABASE_SECRET_KEY": "svc",
    "SLACK_BOT_TOKEN": "xoxb-test", "SLACK_APP_TOKEN": "xapp-test",
    "SLACK_CHANNEL_ID": "C_TEST",
}
for k, v in _DUMMY.items():
    os.environ.setdefault(k, v)

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "toolbox" / "src"))

from skills.campaign.wizard import addon_api, agent  # noqa: E402

_FOUNDER_EMAIL = agent.SENDERS[0]["email"]
_FOUNDER_KEY = agent.SENDERS[0]["key"]


_SECRET = "test-shared-secret"


class _Req:
    def __init__(self, headers):
        self.headers = headers


def _req(secret=_SECRET, user=_FOUNDER_EMAIL):
    """A request with the shared-secret Authorization and the X-Addon-User email."""
    headers = {}
    if secret is not None:
        headers["Authorization"] = "Bearer " + secret
    if user is not None:
        headers["X-Addon-User"] = user
    return _Req(headers)


def setup_function(_):
    addon_api._rl.clear()
    os.environ["ADDON_SHARED_SECRET"] = _SECRET


# ---- pure helpers -----------------------------------------------------------

def test_founder_for_matches_known_email_case_insensitively():
    assert addon_api._founder_for(_FOUNDER_EMAIL.upper())["key"] == _FOUNDER_KEY
    assert addon_api._founder_for("nobody@example.com") is None
    assert addon_api._founder_for("") is None
    assert addon_api._founder_for(None) is None


def test_rate_limit_blocks_after_max():
    who = "someone@dartmouth.edu"
    for _ in range(addon_api._RL_MAX):
        assert addon_api._rate_ok(who) is True
    assert addon_api._rate_ok(who) is False  # one past the cap


def test_draft_payload_omits_raw_incoming_body():
    d = {"draft": "hi", "category": "pricing", "n_examples": 3, "to": "p@co.com",
         "incoming_subject": "Q", "incoming_clean": "their words",
         "incoming_body": "SECRET raw body with quoted history", "thread_id": "t1"}
    out = addon_api._draft_payload(d)
    assert out["draft"] == "hi" and out["category"] == "pricing"
    assert out["who"] == "p@co.com" and out["their_message"] == "their words"
    assert "incoming_body" not in out
    assert "SECRET" not in str(out)


# ---- the auth gate ----------------------------------------------------------

@pytest.mark.asyncio
async def test_auth_rejects_missing_credential():
    with pytest.raises(web.HTTPUnauthorized):
        await addon_api._auth(_req(secret=None))


@pytest.mark.asyncio
async def test_auth_rejects_wrong_secret():
    with pytest.raises(web.HTTPUnauthorized):
        await addon_api._auth(_req(secret="not-the-secret"))


@pytest.mark.asyncio
async def test_auth_rejects_when_backend_secret_unset():
    os.environ.pop("ADDON_SHARED_SECRET", None)
    with pytest.raises(web.HTTPUnauthorized):
        await addon_api._auth(_req())


@pytest.mark.asyncio
async def test_auth_rejects_non_founder_email():
    with pytest.raises(web.HTTPForbidden):
        await addon_api._auth(_req(user="stranger@example.com"))


@pytest.mark.asyncio
async def test_auth_rejects_missing_email():
    with pytest.raises(web.HTTPForbidden):
        await addon_api._auth(_req(user=None))


@pytest.mark.asyncio
async def test_auth_accepts_founder_with_valid_secret():
    founder = await addon_api._auth(_req())
    assert founder["key"] == _FOUNDER_KEY


@pytest.mark.asyncio
async def test_auth_rate_limits_a_founder():
    for _ in range(addon_api._RL_MAX):
        await addon_api._auth(_req())
    with pytest.raises(web.HTTPTooManyRequests):
        await addon_api._auth(_req())
