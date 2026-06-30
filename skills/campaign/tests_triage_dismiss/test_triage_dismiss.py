"""Tests for the triage dismiss list (server/triage_dismiss.py), the triage
filter (server/triage.apply_dismissals), and the Slack edit handler
(server/slack_bot._handle_triage_edit).

Network is fully mocked: httpx.AsyncClient and the store calls are patched, so
nothing hits Supabase or Slack. Covers command parsing, the all-buckets filter,
the PostgREST store calls, and the handler's replies (incl. the missing-table
message).

Run:  toolbox/.venv/bin/python -m pytest skills/campaign/tests_triage_dismiss -o asyncio_mode=auto
Per the repo rule, this folder is temporary and deleted after merge.
"""
import os
import sys
from pathlib import Path
from unittest.mock import patch

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
from skills.campaign.server import triage, triage_dismiss  # noqa: E402
from skills.campaign.server import slack_bot  # noqa: E402


# ---- command parsing (pure) --------------------------------------------------

def test_parse_dismiss_with_two_emails_and_reason():
    cmd = triage_dismiss.parse_command("drop jane@acme.com, bob@foo.io — not our ICP")
    assert cmd["action"] == "dismiss"
    assert cmd["emails"] == ["jane@acme.com", "bob@foo.io"]
    assert "icp" in cmd["reason"].lower()


def test_parse_dedupes_and_lowercases():
    cmd = triage_dismiss.parse_command("remove Jane@Acme.com and jane@acme.com please")
    assert cmd["action"] == "dismiss"
    assert cmd["emails"] == ["jane@acme.com"]


def test_parse_undo():
    cmd = triage_dismiss.parse_command("undo jane@acme.com")
    assert cmd["action"] == "undo"
    assert cmd["emails"] == ["jane@acme.com"]


def test_parse_show():
    assert triage_dismiss.parse_command("show dismissed")["action"] == "show"
    assert triage_dismiss.parse_command("who have we removed?")["action"] == "show"


def test_parse_send_request_with_email_is_not_a_dismiss():
    # An address with no dismiss verb must fall through (action None), so normal
    # campaign requests and questions are never hijacked.
    assert triage_dismiss.parse_command("send 40 to jane@acme.com style brands")["action"] is None
    assert triage_dismiss.parse_command("what can you do?")["action"] is None


def test_parse_dismiss_verb_without_email_is_inert():
    # "drop" with no email (e.g. "drop 40 emails to DTC") must not dismiss.
    assert triage_dismiss.parse_command("drop 40 emails to DTC brands")["action"] is None


# ---- the all-buckets filter (pure) -------------------------------------------

def _row(who, bucket):
    return {"who": who, "_bucket": bucket}


def test_apply_dismissals_removes_from_all_three_buckets():
    needs = [_row("jane@acme.com", "needs"), _row("keep@x.com", "needs")]
    reroute = [_row("jane@acme.com", "reroute")]
    gray = [_row("JANE@ACME.COM", "gray"), _row("other@y.com", "gray")]
    n, rr, g = triage.apply_dismissals(needs, reroute, gray, {"jane@acme.com"})
    assert [r["who"] for r in n] == ["keep@x.com"]
    assert rr == []                                   # removed from reroute too
    assert [r["who"] for r in g] == ["other@y.com"]   # case-insensitive match


def test_apply_dismissals_empty_set_is_passthrough():
    needs = [_row("a@x.com", "needs")]
    n, rr, g = triage.apply_dismissals(needs, [], [], set())
    assert n == needs


# ---- store calls (httpx mocked) ----------------------------------------------

class _Resp:
    def __init__(self, status=200, json_data=None):
        self.status_code = status
        self._json = json_data if json_data is not None else []
        self.text = ""
        self.content = b"x" if json_data else b""

    def json(self):
        return self._json


def _fake_client(get=None, post=None, patch_=None):
    class _C:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def get(self, *a, **k):
            return get

        async def post(self, *a, **k):
            return post

        async def patch(self, *a, **k):
            return patch_

    return _C


async def test_load_dismissed_parses_rows():
    resp = _Resp(200, [{"recipient": "jane@acme.com"}, {"recipient": "BOB@foo.io"}])
    with patch.object(triage_dismiss.httpx, "AsyncClient", _fake_client(get=resp)):
        out = await triage_dismiss.load_dismissed()
    assert out == {"jane@acme.com", "bob@foo.io"}


async def test_load_dismissed_swallows_errors():
    # A missing table (404) or any failure must yield an empty set, never raise,
    # so triage keeps working before the migration is applied.
    with patch.object(triage_dismiss.httpx, "AsyncClient", _fake_client(get=_Resp(404))):
        assert await triage_dismiss.load_dismissed() == set()


async def test_dismiss_posts_and_returns_canonical():
    with patch.object(triage_dismiss.httpx, "AsyncClient", _fake_client(post=_Resp(201))):
        out = await triage_dismiss.dismiss(["Jane@Acme.com", "bob@foo.io"], "no fit", "U1")
    assert out == ["jane@acme.com", "bob@foo.io"]


async def test_dismiss_raises_on_bad_status():
    import pytest
    with patch.object(triage_dismiss.httpx, "AsyncClient", _fake_client(post=_Resp(400))):
        with pytest.raises(RuntimeError):
            await triage_dismiss.dismiss(["jane@acme.com"])


async def test_undismiss_returns_existing():
    resp = _Resp(200, [{"recipient": "jane@acme.com"}])
    with patch.object(triage_dismiss.httpx, "AsyncClient", _fake_client(patch_=resp)):
        out = await triage_dismiss.undismiss(["jane@acme.com", "ghost@x.com"])
    assert out == ["jane@acme.com"]


# ---- the Slack edit handler --------------------------------------------------

class _Reply:
    def __init__(self):
        self.msgs = []

    async def __call__(self, text=None, blocks=None):
        self.msgs.append(text or "")


async def test_handler_dismiss_confirms_with_undo_hint():
    async def fake_dismiss(emails, reason, by):
        return ["jane@acme.com"]
    reply = _Reply()
    with patch.object(slack_bot.triage_dismiss, "dismiss", fake_dismiss):
        await slack_bot._handle_triage_edit(
            {"action": "dismiss", "emails": ["jane@acme.com"], "reason": ""}, reply, "U1")
    joined = "\n".join(reply.msgs)
    assert "Removed 1" in joined
    assert "undo jane@acme.com" in joined


async def test_handler_reports_missing_table():
    async def boom(emails, reason, by):
        raise RuntimeError('relation "triage_dismissed" does not exist')
    reply = _Reply()
    with patch.object(slack_bot.triage_dismiss, "dismiss", boom):
        await slack_bot._handle_triage_edit(
            {"action": "dismiss", "emails": ["jane@acme.com"], "reason": ""}, reply)
    assert "not set up yet" in "\n".join(reply.msgs)


async def test_handler_show_empty():
    async def empty():
        return []
    reply = _Reply()
    with patch.object(slack_bot.triage_dismiss, "list_dismissed", empty):
        await slack_bot._handle_triage_edit({"action": "show", "emails": []}, reply)
    assert "No one is dismissed" in "\n".join(reply.msgs)
