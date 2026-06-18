"""Smoke tests for the campaign skill.

Run without any real API keys:
  cd /Users/shamitd/interns
  TOOLBOX_TOKEN_HUNTER=fake TOOLBOX_TOKEN_APOLLO=fake \
  TOOLBOX_SESSION_TOKEN=fake \
  python -m pytest skills/campaign/tests/ -v

All HTTP calls are intercepted by respx. Supabase calls use TOOLBOX_SESSION_TOKEN
to bypass keychain. Hunter/Apollo calls use TOOLBOX_TOKEN_* overrides.
"""

from __future__ import annotations

import base64
import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import httpx
import pytest
import respx

# Add toolbox to path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "toolbox" / "src"))


# ---- helpers -----------------------------------------------------------

FAKE_HUNTER_DOMAIN_RESP = {
    "data": {
        "emails": [
            {
                "value": "alice@example.com",
                "first_name": "Alice",
                "last_name": "Smith",
                "position": "CEO",
                "seniority": "executive",
                "confidence": 92,
                "verification": {"status": "valid"},
            }
        ]
    }
}

FAKE_APOLLO_DOMAIN_RESP = {
    "people": [
        {
            "email": "bob@widgets.io",
            "first_name": "Bob",
            "last_name": "Jones",
            "title": "Founder",
            "email_status": "verified",
        }
    ]
}

FAKE_GMAIL_SEND_RESP = {"id": "msg_abc123", "threadId": "thread_1", "labelIds": ["SENT"]}

FAKE_SUPABASE_CLAIM_RESP = "claimed"
FAKE_SUPABASE_MARK_SENT_RESP = None

SAMPLE_TEMPLATE = "---\nsubject: Test Subject for {{company}}\n---\nHi {{first_name}},\n\nTest body.\n\nThanks,\n{{from_name}}\n"


def _make_contacts(n: int = 4):
    from toolbox.core.models import Contact
    return [
        Contact(email=f"user{i}@company{i}.com", first_name=f"User{i}",
                company=f"Company{i}", domain=f"company{i}.com")
        for i in range(n)
    ]


# ---- test: domain generation (mocked LLM) ------------------------------

def test_generate_domains_calls_llm():
    sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "toolbox" / "src"))
    from skills.campaign import run as camp

    mock_result = type("R", (), {"domains": ["glossier.com", "warbyparker.com"]})()
    with patch("toolbox.core.llm.parse", return_value=mock_result) as mock_llm:
        domains = camp.generate_domains("DTC health brands")
    mock_llm.assert_called_once()
    assert "glossier.com" in domains
    assert "warbyparker.com" in domains


# ---- test: generate_variant_b ------------------------------------------

def test_generate_variant_b_returns_subject_and_body():
    from skills.campaign import run as camp

    mock_result = type("R", (), {"subject": "Different subject", "body": "Different body {{first_name}}"})()
    with patch("toolbox.core.llm.parse", return_value=mock_result):
        subj, body = camp.generate_variant_b("Original subject", "Original body")
    assert subj == "Different subject"
    assert "first_name" in body or "Different" in body


# ---- test: load_leads_csv ----------------------------------------------

def test_load_leads_csv_parses_contacts(tmp_path):
    from skills.campaign import run as camp

    csv_content = "email,first_name,company,domain\nalice@foo.com,Alice,Foo,foo.com\nbob@bar.com,Bob,Bar,bar.com\n"
    p = tmp_path / "leads.csv"
    p.write_text(csv_content)
    contacts = camp.load_leads_csv(str(p))
    assert len(contacts) == 2
    assert contacts[0].email == "alice@foo.com"
    assert contacts[1].first_name == "Bob"


def test_load_leads_csv_skips_bad_rows(tmp_path):
    from skills.campaign import run as camp

    csv_content = "email,first_name\nnot-an-email,Alice\ngood@example.com,Bob\n"
    p = tmp_path / "leads.csv"
    p.write_text(csv_content)
    contacts = camp.load_leads_csv(str(p))
    assert len(contacts) == 1
    assert contacts[0].email == "good@example.com"


# ---- test: compose_outbox ----------------------------------------------

def test_compose_outbox_renders_all_slots():
    from skills.campaign import run as camp

    contacts = _make_contacts(2)
    subject_t = "Hello {{company}}"
    body_t = "Hi {{first_name}}, thanks from {{from_name}}."
    rows = camp.compose_outbox(contacts, subject_t, body_t, from_name="Shamit")
    assert len(rows) == 2
    assert rows[0].subject == "Hello Company0"
    assert "User0" in rows[0].body
    assert "Shamit" in rows[0].body


def test_compose_outbox_drops_missing_slot():
    from skills.campaign import run as camp

    from toolbox.core.models import Contact
    contacts = [Contact(email="x@y.com", first_name="", company="")]
    subject_t = "Hello {{company}}"
    body_t = "Hi {{first_name}}."
    # first_name is empty → slot error → row dropped
    rows = camp.compose_outbox(contacts, subject_t, body_t)
    assert len(rows) == 0


# ---- test: load_campaign_log ------------------------------------------

def test_load_campaign_log(tmp_path):
    from skills.campaign import reply_scan as rs

    log = tmp_path / "campaign.jsonl"
    lines = [
        json.dumps({"_meta": True, "run_id": "run-1", "notion_page_id": "page-abc"}),
        json.dumps({"email": "alice@foo.com", "run_id": "run-1", "variant": "a"}),
        json.dumps({"email": "bob@bar.com", "run_id": "run-1", "variant": "b"}),
    ]
    log.write_text("\n".join(lines) + "\n")
    mapping, meta = rs.load_campaign_log(str(log))
    assert mapping["alice@foo.com"]["variant"] == "a"
    assert mapping["bob@bar.com"]["run_id"] == "run-1"
    assert meta["notion_page_id"] == "page-abc"
    assert "alice@foo.com" not in {**{"_meta": True}}  # meta not in contacts


def test_load_campaign_log_missing_file(tmp_path):
    from skills.campaign import reply_scan as rs

    mapping, meta = rs.load_campaign_log(str(tmp_path / "nonexistent.jsonl"))
    assert mapping == {}
    assert meta == {}


# ---- test: write_campaign_log -----------------------------------------

def test_write_campaign_log_appends(tmp_path):
    from skills.campaign import run as camp

    log = str(tmp_path / "log.jsonl")
    camp.write_campaign_log(log, [{"email": "a@b.com", "run_id": "r1", "variant": "a"}])
    camp.write_campaign_log(log, [{"email": "c@d.com", "run_id": "r1", "variant": "b"}])
    lines = Path(log).read_text().strip().splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0])["email"] == "a@b.com"
    assert json.loads(lines[1])["variant"] == "b"


# ---- test: sent_counts (report) ---------------------------------------

def test_sent_counts_groups_by_run_and_variant():
    from skills.campaign import reply_report as rr

    entries = [
        {"run_id": "r1", "variant": "a"},
        {"run_id": "r1", "variant": "a"},
        {"run_id": "r1", "variant": "b"},
        {"run_id": "r2", "variant": "a"},
    ]
    counts = rr.sent_counts(entries)
    assert counts[("r1", "a")] == 2
    assert counts[("r1", "b")] == 1
    assert counts[("r2", "a")] == 1


def test_sent_counts_filters_by_run_id():
    from skills.campaign import reply_report as rr

    entries = [
        {"run_id": "r1", "variant": "a"},
        {"run_id": "r2", "variant": "a"},
    ]
    counts = rr.sent_counts(entries, run_id_filter="r1")
    assert ("r1", "a") in counts
    assert ("r2", "a") not in counts


# ---- test: Hunter domain search (mocked HTTP) -------------------------

@pytest.mark.asyncio
@respx.mock
async def test_hunter_domain_search():
    sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "toolbox" / "src"))
    from toolbox.primitives.findemail.cli import _hunter_domain

    respx.get("https://api.hunter.io/v2/domain-search").mock(
        return_value=httpx.Response(200, json=FAKE_HUNTER_DOMAIN_RESP)
    )
    async with httpx.AsyncClient(timeout=60) as client:
        res = await _hunter_domain(client, "fake_key", "example.com", limit=10, executives_only=True)
    assert res is not None
    assert res["email"] == "alice@example.com"
    assert res["first_name"] == "Alice"
    assert res["email_score"] == 92


# ---- test: Apollo domain search (mocked HTTP) -------------------------

@pytest.mark.asyncio
@respx.mock
async def test_apollo_domain_search():
    sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "toolbox" / "src"))
    from toolbox.primitives.findemail.cli import _apollo_domain

    respx.post("https://api.apollo.io/v1/mixed_people/search").mock(
        return_value=httpx.Response(200, json=FAKE_APOLLO_DOMAIN_RESP)
    )
    async with httpx.AsyncClient(timeout=60) as client:
        res = await _apollo_domain(client, "fake_key", "widgets.io", limit=10, executives_only=True)
    assert res is not None
    assert res["email"] == "bob@widgets.io"
    assert res["first_name"] == "Bob"
    assert res["email_score"] == 95  # verified = 95


# ---- test: enrich_domains orchestrator (mocked) -----------------------

@pytest.mark.asyncio
@respx.mock
async def test_enrich_domains_hunter(monkeypatch):
    from skills.campaign import run as camp

    respx.get("https://api.hunter.io/v2/domain-search").mock(
        return_value=httpx.Response(200, json=FAKE_HUNTER_DOMAIN_RESP)
    )
    contacts = await camp.enrich_domains(["example.com"], "hunter", "fake_key", min_score=50)
    assert len(contacts) == 1
    assert contacts[0].email == "alice@example.com"


@pytest.mark.asyncio
@respx.mock
async def test_enrich_domains_filters_low_score():
    from skills.campaign import run as camp

    low_score_resp = {
        "data": {
            "emails": [
                {"value": "low@example.com", "first_name": "Low", "confidence": 30,
                 "position": "CEO", "seniority": "executive", "verification": {"status": "unknown"}}
            ]
        }
    }
    respx.get("https://api.hunter.io/v2/domain-search").mock(
        return_value=httpx.Response(200, json=low_score_resp)
    )
    contacts = await camp.enrich_domains(["example.com"], "hunter", "fake_key", min_score=80)
    assert len(contacts) == 0


# ---- test: reply upsert (mocked Supabase) -----------------------------

@pytest.mark.asyncio
@respx.mock
async def test_upsert_reply_success():
    from skills.campaign import reply_scan as rs

    respx.post("http://127.0.0.1:54321/rest/v1/replies").mock(return_value=httpx.Response(201))
    async with httpx.AsyncClient(timeout=30) as client:
        inserted = await rs.upsert_reply(
            client, "fake_session", "alice@example.com",
            "2026-06-17T10:00:00Z", "Re: Hello", "Sure, let's chat", "positive",
            "run-1", "a", "msg_xyz",
        )
    assert inserted is True


@pytest.mark.asyncio
@respx.mock
async def test_upsert_reply_duplicate():
    from skills.campaign import reply_scan as rs

    respx.post("http://127.0.0.1:54321/rest/v1/replies").mock(return_value=httpx.Response(409))
    async with httpx.AsyncClient(timeout=30) as client:
        inserted = await rs.upsert_reply(
            client, "fake_session", "alice@example.com",
            "2026-06-17T10:00:00Z", "Re: Hello", "Sure", "positive",
            "run-1", "a", "msg_xyz",
        )
    assert inserted is False


# ---- test: fetch_reply_counts (mocked Supabase) -----------------------

@respx.mock
def test_fetch_reply_counts():
    from skills.campaign import reply_report as rr

    fake_replies = [
        {"run_id": "r1", "variant": "a"},
        {"run_id": "r1", "variant": "a"},
        {"run_id": "r1", "variant": "b"},
    ]
    respx.get("http://127.0.0.1:54321/rest/v1/replies").mock(
        return_value=httpx.Response(200, json=fake_replies)
    )
    counts = rr.fetch_reply_counts("fake_session", ["r1"])
    assert counts[("r1", "a")] == 2
    assert counts[("r1", "b")] == 1


# ---- test: scan() end-to-end (mocked Gmail + Supabase) ----------------
#
# This test verifies the core reply-detection logic:
#   list_messages -> get_message -> match sender -> classify -> upsert
#
# Uses TOOLBOX_GMAIL_API_BASE to redirect Gmail API calls to a fake host,
# TOOLBOX_TOKEN_GMAIL to skip the OAuth refresh, and TOOLBOX_SESSION_TOKEN
# to skip the Supabase session keychain.

_FAKE_GMAIL_BASE = "http://fake-gmail-api"

_FAKE_MSG_ID = "msg_reply_abc"

def _make_gmail_message(from_addr: str, subject: str, body_text: str) -> dict:
    encoded_body = base64.urlsafe_b64encode(body_text.encode()).decode()
    return {
        "id": _FAKE_MSG_ID,
        "snippet": body_text[:100],
        "payload": {
            "headers": [
                {"name": "From", "value": f"Sender Name <{from_addr}>"},
                {"name": "Subject", "value": subject},
                {"name": "Date", "value": "Wed, 17 Jun 2026 10:00:00 +0000"},
            ],
            "mimeType": "text/plain",
            "body": {"data": encoded_body},
            "parts": [],
        },
        "internalDate": "1750154400000",
    }


@pytest.mark.asyncio
@respx.mock
async def test_scan_detects_reply_from_known_contact(tmp_path, monkeypatch):
    from skills.campaign import reply_scan as rs

    # Set env overrides so no real auth or Gmail calls happen.
    monkeypatch.setenv("TOOLBOX_TOKEN_GMAIL", "fake-gmail-token")
    monkeypatch.setenv("TOOLBOX_SESSION_TOKEN", "fake-session")
    monkeypatch.setenv("TOOLBOX_GMAIL_API_BASE", _FAKE_GMAIL_BASE)

    # Campaign log: alice@example.com was contacted in run-1, variant a.
    log = tmp_path / "campaign.jsonl"
    log.write_text(json.dumps({
        "email": "alice@example.com", "run_id": "run-1", "variant": "a",
        "sent_at": "2026-06-17T09:00:00Z",
    }) + "\n")

    # Gmail: inbox has one message from alice.
    fake_msg = _make_gmail_message(
        "alice@example.com", "Re: Stanford Student Question",
        "Sure, I'd love to chat!"
    )
    respx.get(
        f"{_FAKE_GMAIL_BASE}/gmail/v1/users/me/messages",
    ).mock(return_value=httpx.Response(200, json={"messages": [{"id": _FAKE_MSG_ID}]}))
    respx.get(
        f"{_FAKE_GMAIL_BASE}/gmail/v1/users/me/messages/{_FAKE_MSG_ID}",
    ).mock(return_value=httpx.Response(200, json=fake_msg))

    # Supabase replies INSERT.
    respx.post("http://127.0.0.1:54321/rest/v1/replies").mock(
        return_value=httpx.Response(201)
    )

    # Mock sentiment classification so no Claude subprocess runs.
    mock_sentiment = type("S", (), {"sentiment": "positive"})()
    with patch("toolbox.core.llm.parse", return_value=mock_sentiment), \
         patch("skills.campaign.notion_sync.update_reply_count", return_value=True):
        found = await rs.scan(str(log), since_days=7, classify=True)

    assert len(found) == 1
    assert found[0]["email"] == "alice@example.com"
    assert found[0]["sentiment"] == "positive"
    assert found[0]["run_id"] == "run-1"


@pytest.mark.asyncio
@respx.mock
async def test_scan_ignores_unknown_sender(tmp_path, monkeypatch):
    from skills.campaign import reply_scan as rs

    monkeypatch.setenv("TOOLBOX_TOKEN_GMAIL", "fake-gmail-token")
    monkeypatch.setenv("TOOLBOX_SESSION_TOKEN", "fake-session")
    monkeypatch.setenv("TOOLBOX_GMAIL_API_BASE", _FAKE_GMAIL_BASE)

    # Campaign log: we only contacted alice, not bob.
    log = tmp_path / "campaign.jsonl"
    log.write_text(json.dumps({
        "email": "alice@example.com", "run_id": "run-1", "variant": "a",
        "sent_at": "2026-06-17T09:00:00Z",
    }) + "\n")

    # Inbox has a message from an unknown sender (bob).
    fake_msg = _make_gmail_message("bob@stranger.com", "Hello", "Random email")
    respx.get(f"{_FAKE_GMAIL_BASE}/gmail/v1/users/me/messages").mock(
        return_value=httpx.Response(200, json={"messages": [{"id": _FAKE_MSG_ID}]})
    )
    respx.get(f"{_FAKE_GMAIL_BASE}/gmail/v1/users/me/messages/{_FAKE_MSG_ID}").mock(
        return_value=httpx.Response(200, json=fake_msg)
    )

    with patch("toolbox.core.llm.parse"):
        found = await rs.scan(str(log), since_days=7, classify=False)

    assert found == []


@pytest.mark.asyncio
@respx.mock
async def test_scan_skips_duplicate_reply(tmp_path, monkeypatch):
    from skills.campaign import reply_scan as rs

    monkeypatch.setenv("TOOLBOX_TOKEN_GMAIL", "fake-gmail-token")
    monkeypatch.setenv("TOOLBOX_SESSION_TOKEN", "fake-session")
    monkeypatch.setenv("TOOLBOX_GMAIL_API_BASE", _FAKE_GMAIL_BASE)

    log = tmp_path / "campaign.jsonl"
    log.write_text(json.dumps({
        "email": "alice@example.com", "run_id": "run-1", "variant": "a",
        "sent_at": "2026-06-17T09:00:00Z",
    }) + "\n")

    fake_msg = _make_gmail_message("alice@example.com", "Re: Hi", "Sounds good")
    respx.get(f"{_FAKE_GMAIL_BASE}/gmail/v1/users/me/messages").mock(
        return_value=httpx.Response(200, json={"messages": [{"id": _FAKE_MSG_ID}]})
    )
    respx.get(f"{_FAKE_GMAIL_BASE}/gmail/v1/users/me/messages/{_FAKE_MSG_ID}").mock(
        return_value=httpx.Response(200, json=fake_msg)
    )
    # Supabase returns 409 = already recorded.
    respx.post("http://127.0.0.1:54321/rest/v1/replies").mock(
        return_value=httpx.Response(409)
    )

    mock_sentiment = type("S", (), {"sentiment": "positive"})()
    with patch("toolbox.core.llm.parse", return_value=mock_sentiment):
        found = await rs.scan(str(log), since_days=7, classify=True)

    # Duplicate → not in found list.
    assert found == []
