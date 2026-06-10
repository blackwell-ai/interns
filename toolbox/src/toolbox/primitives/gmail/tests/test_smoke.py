"""gmail offline smoke tests — all network mocked (respx).

Covers the claim pattern (claimed/skipped/suppressed), the quota wall, the
resume mirror, dry-run, MIME construction, and bounce parsing.
"""

import base64
import json

import pytest
import respx
from httpx import Response
from typer.testing import CliRunner

from toolbox.core import io, ledger
from toolbox.primitives.gmail import lib
from toolbox.primitives.gmail.cli import app

runner = CliRunner()

SUPABASE = "http://127.0.0.1:54321"
GMAIL_SEND = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"


@pytest.fixture
def run_env(tmp_path, monkeypatch):
    monkeypatch.setenv("TOOLBOX_RUN_DIR", str(tmp_path))
    monkeypatch.setenv("TOOLBOX_RUN_ID", "test-run")
    monkeypatch.setenv("TOOLBOX_SKILL", "test-skill")
    monkeypatch.setenv("TOOLBOX_SESSION_TOKEN", "fake-session")
    monkeypatch.setenv("TOOLBOX_TOKEN_GMAIL", "fake-gmail-token")
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    outbox = tmp_path / "outbox.csv"
    io.write_csv(outbox, [
        __import__("toolbox.core.models", fromlist=["OutboxRow"]).OutboxRow(
            email=e, subject=f"hi {e}", body="body text")
        for e in ("a@x.com", "b@y.com", "c@z.com")
    ])
    return tmp_path, outbox


def _mock_rpcs(claim_results):
    """claim_results: list of return values for successive claim_contact calls."""
    it = iter(claim_results)
    respx.post(f"{SUPABASE}/rest/v1/rpc/claim_contact").mock(
        side_effect=lambda req: Response(200, json=next(it)))
    respx.post(f"{SUPABASE}/rest/v1/rpc/mark_contact").mock(return_value=Response(200, json=None))


@respx.mock
def test_send_happy_path(run_env):
    tmp_path, outbox = run_env
    _mock_rpcs(["claimed", "claimed", "claimed"])
    send_route = respx.post(GMAIL_SEND).mock(return_value=Response(200, json={"id": "m-1"}))

    result = runner.invoke(app, ["send", "--in", str(outbox), "--from", "me@co.com",
                                 "--concurrency", "2"])
    assert result.exit_code == 0, result.output
    assert send_route.call_count == 3
    mirror = list(io.read_jsonl(tmp_path / "ledger.jsonl"))
    assert {m["recipient"] for m in mirror} == {"a@x.com", "b@y.com", "c@z.com"}
    assert all(m["status"] == "sent" for m in mirror)


@respx.mock
def test_send_skips_already_contacted_and_suppressed(run_env):
    tmp_path, outbox = run_env
    _mock_rpcs(["claimed", "skipped", "suppressed"])
    send_route = respx.post(GMAIL_SEND).mock(return_value=Response(200, json={"id": "m-1"}))

    result = runner.invoke(app, ["send", "--in", str(outbox), "--from", "me@co.com",
                                 "--concurrency", "1"])
    assert result.exit_code == 0, result.output
    assert send_route.call_count == 1  # only the claimed one was sent
    events = [json.loads(line) for line in (tmp_path / "events.jsonl").read_text().splitlines()]
    assert sum(1 for e in events if e["event"] == "claim.skipped") == 1
    assert sum(1 for e in events if e["event"] == "claim.suppressed") == 1


@respx.mock
def test_quota_wall_fails_cleanly(run_env):
    tmp_path, outbox = run_env
    _mock_rpcs(["claimed", "claimed", "claimed"])
    respx.post(GMAIL_SEND).mock(
        return_value=Response(403, text="Daily user sending limit exceeded"))

    result = runner.invoke(app, ["send", "--in", str(outbox), "--from", "me@co.com",
                                 "--concurrency", "1"])
    assert result.exit_code == 1  # clean failure, not an infinite retry
    assert "quota" in result.output.lower()
    mirror = list(io.read_jsonl(tmp_path / "ledger.jsonl"))
    assert not [m for m in mirror if m["status"] == "sent"]  # nothing recorded as sent


@respx.mock
def test_resume_skips_mirror_sent(run_env):
    tmp_path, outbox = run_env
    ledger.mirror_append(tmp_path, "email", "a@x.com", "sent", message_id="old")
    _mock_rpcs(["claimed", "claimed"])  # only b and c claim
    send_route = respx.post(GMAIL_SEND).mock(return_value=Response(200, json={"id": "m-2"}))

    result = runner.invoke(app, ["send", "--in", str(outbox), "--from", "me@co.com",
                                 "--concurrency", "1"])
    assert result.exit_code == 0, result.output
    assert send_route.call_count == 2  # a@x.com not re-sent


@respx.mock
def test_dry_run_sends_nothing(run_env):
    tmp_path, outbox = run_env
    respx.post(f"{SUPABASE}/rest/v1/rpc/check_contact").mock(
        return_value=Response(200, json="new"))
    send_route = respx.post(GMAIL_SEND).mock(return_value=Response(200, json={"id": "x"}))

    result = runner.invoke(app, ["send", "--in", str(outbox), "--from", "me@co.com", "--dry-run"])
    assert result.exit_code == 0, result.output
    assert send_route.call_count == 0
    preview = io.read_json(tmp_path / "dryrun" / "gmail.send.json")
    assert len(preview) == 3 and preview[0]["ledger"] == "new"


def test_mime_construction():
    raw = lib.build_raw_message(to="a@x.com", subject="Sub", body="plain",
                                from_address="me@co.com", from_name="Me",
                                reply_to="r@co.com", body_html="<b>html</b>")
    decoded = base64.urlsafe_b64decode(raw).decode()
    for needle in ("To: a@x.com", "Subject: Sub", "Reply-To: r@co.com", "plain", "html"):
        assert needle in decoded


def test_error_classification():
    assert lib.classify_send_error(403, "Daily user sending limit exceeded") is lib.QuotaExceeded
    assert lib.classify_send_error(429, "rateLimitExceeded") is None  # transient → retry
    assert lib.classify_send_error(500, "boom") is None
    assert lib.classify_send_error(400, "invalid to") is lib.PermanentSendError


def test_bounce_parse():
    body = "Final-Recipient: rfc822; <dead@gone.com>\nAction: failed"
    payload = {"mimeType": "message/delivery-status",
               "body": {"data": base64.urlsafe_b64encode(body.encode()).decode()}}
    msg = {"payload": payload, "internalDate": "1700000000000"}
    parsed = lib.parse_bounce(msg)
    assert parsed and parsed[0] == "dead@gone.com"
    assert lib.parse_bounce({"payload": {}, "internalDate": "0"}) is None


def test_address_extraction():
    assert lib.address_of("Jane Doe <Jane@X.com>") == "jane@x.com"
    assert lib.address_of("bare@x.com") == "bare@x.com"


def test_build_raw_message_cc():
    import base64
    from toolbox.primitives.gmail import lib

    raw = lib.build_raw_message(
        to="lead@example.com", subject="s", body="b",
        from_address="me@example.com",
        cc="a@x.com, b@y.com",
    )
    decoded = base64.urlsafe_b64decode(raw.encode()).decode()
    assert "Cc: a@x.com, b@y.com" in decoded
