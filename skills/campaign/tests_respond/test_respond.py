"""Tests for the /respond reply-review queue and its corpus/harvest logic.

Everything network- or LLM-bound is mocked: Gmail, Claude, Slack views, Supabase.
Covers the awkward cases the task calls out: empty queue, a thread with no prior
inbound to pair, a novel category with no matching examples, a send that fails
partway (must not mark handled or record a gold example), a restart mid-session,
and dedupe on re-harvest.

Run:  toolbox/.venv/bin/python -m pytest skills/campaign/tests_respond -o asyncio_mode=auto

Per the repo rule, this folder is temporary and deleted after merge.
"""
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

_DUMMY = {
    "ANTHROPIC_API_KEY": "x", "GOOGLE_OAUTH_CLIENT_ID": "x",
    "GOOGLE_OAUTH_CLIENT_SECRET": "x", "TOOLBOX_TOKEN_HUNTER": "x",
    "SUPABASE_URL": "https://x.supabase.co", "SUPABASE_SECRET_KEY": "x",
    "SLACK_BOT_TOKEN": "xoxb-test", "SLACK_APP_TOKEN": "xapp-test",
    "SLACK_CHANNEL_ID": "C_TEST",
}
for k, v in _DUMMY.items():
    os.environ.setdefault(k, v)

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "toolbox" / "src"))

from skills.campaign.wizard import respond, reply_examples, reply_drafter  # noqa: E402
from skills.campaign import harvest_reply_examples as harvest  # noqa: E402


# ---- fixtures / helpers -----------------------------------------------------

def _draft(thread_id="T1", to="prospect@acme.com", category="pricing"):
    """A reply_drafter.generate_draft-shaped dict."""
    return {
        "draft": "Hi there, happy to help. Thanks, Armaan",
        "category": category, "sentiment": "positive",
        "incoming_subject": "Question about pricing", "incoming_body": "How much?",
        "reply_subject": "Re: Question about pricing", "to": to,
        "reply_to_message_id": "m_inbound", "thread_id": thread_id,
        "thread_preview": "[Them] How much?", "n_examples": 2,
    }


def _seed_session(user="U1", queue=None, pos=0, draft=None):
    queue = queue if queue is not None else [{"thread_id": "T1", "who": "prospect@acme.com"}]
    session = {
        "user_id": user, "founder_key": "armaan",
        "founder_email": "armaan.priyadarshan.29@dartmouth.edu",
        "queue": queue, "pos": pos, "draft": draft, "view_id": "V1",
        "sent": 0, "skipped": 0,
    }
    respond._review_sessions[user] = session
    return session


@pytest.fixture(autouse=True)
def _clear_sessions():
    respond._review_sessions.clear()
    yield
    respond._review_sessions.clear()


# ---- queue flow -------------------------------------------------------------

async def test_empty_queue_shows_all_clear_and_ends():
    updates = []
    with patch.object(respond, "_update", AsyncMock(side_effect=lambda v, view: updates.append(view))), \
         patch.object(respond.triage, "needs_for_founder", AsyncMock(return_value=[])):
        await respond.build_first("U1", "armaan", "V1")
    assert "U1" not in respond._review_sessions           # session cleaned up
    assert any("clear" in (u["title"]["text"].lower()) for u in updates)


async def test_first_email_drafts_and_shows_review_modal():
    updates = []
    with patch.object(respond, "_update", AsyncMock(side_effect=lambda v, view: updates.append(view))), \
         patch.object(respond.triage, "needs_for_founder",
                      AsyncMock(return_value=[{"thread_id": "T1", "who": "p@acme.com"}])), \
         patch.object(respond.reply_drafter, "generate_draft", AsyncMock(return_value=_draft())):
        await respond.build_first("U1", "armaan", "V1")
    review = [u for u in updates if u.get("callback_id") == "resp_review"]
    assert review, "expected a review modal to be shown"
    assert respond._review_sessions["U1"]["draft"]["thread_id"] == "T1"


async def test_send_success_records_gold_and_advances_to_done():
    _seed_session(queue=[{"thread_id": "T1", "who": "p@acme.com"}], pos=0, draft=_draft())
    gold = AsyncMock(return_value=True)
    updates = []
    with patch.object(respond, "_update", AsyncMock(side_effect=lambda v, view: updates.append(view))), \
         patch.object(respond, "_send_reply", AsyncMock(return_value=(True, "sent_123"))), \
         patch.object(respond.reply_examples, "add_gold_example", gold):
        await respond.on_send("U1", "V1", "My edited reply. Thanks, Armaan")
    # gold example recorded with the EDITED body and the sent message id
    assert gold.await_count == 1
    kwargs = gold.await_args.kwargs
    assert kwargs["reply_body"] == "My edited reply. Thanks, Armaan"
    assert kwargs["message_id"] == "sent_123"
    # queue exhausted -> session removed, a done modal shown
    assert "U1" not in respond._review_sessions
    assert any("done" in u["title"]["text"].lower() for u in updates)


async def test_send_failure_does_not_record_or_advance():
    session = _seed_session(queue=[{"thread_id": "T1", "who": "p@acme.com"}], pos=0, draft=_draft())
    gold = AsyncMock()
    shown = []
    with patch.object(respond, "_update", AsyncMock(side_effect=lambda v, view: shown.append(view))), \
         patch.object(respond, "_send_reply", AsyncMock(return_value=(False, "boom"))), \
         patch.object(respond.reply_examples, "add_gold_example", gold):
        await respond.on_send("U1", "V1", "attempted reply")
    gold.assert_not_awaited()                              # nothing recorded
    assert session["pos"] == 0 and session["sent"] == 0    # not advanced
    assert "U1" in respond._review_sessions                # still in the queue
    # the review modal reappears with the edit preserved and a warning
    review = [u for u in shown if u.get("callback_id") == "resp_review"]
    assert review and review[-1]["blocks"][0]["elements"][0]["text"].startswith(":warning:")
    assert session["draft"]["draft"] == "attempted reply"  # edit kept for retry


async def test_send_with_no_session_is_graceful():
    shown = []
    with patch.object(respond, "_update", AsyncMock(side_effect=lambda v, view: shown.append(view))):
        await respond.on_send("U_missing", "V9", "hello")   # no session (restart)
    assert shown and "ended" in shown[-1]["title"]["text"].lower()


async def test_skip_advances_and_counts():
    session = _seed_session(
        queue=[{"thread_id": "T1", "who": "a@x.com"}, {"thread_id": "T2", "who": "b@x.com"}],
        pos=0, draft=_draft())
    with patch.object(respond, "_update", AsyncMock()), \
         patch.object(respond.reply_drafter, "generate_draft", AsyncMock(return_value=_draft("T2"))):
        await respond.on_skip("U1", "V1")
    assert session["pos"] == 1 and session["skipped"] == 1


async def test_undraftable_thread_is_skipped_not_stuck():
    # generate_draft raises for the only queued thread -> queue drains to done,
    # session removed, no crash (a thread with no inbound to answer, etc.).
    _seed_session(queue=[{"thread_id": "T1", "who": "a@x.com"}], pos=0, draft=None)
    updates = []
    with patch.object(respond, "_update", AsyncMock(side_effect=lambda v, view: updates.append(view))), \
         patch.object(respond.reply_drafter, "generate_draft",
                      AsyncMock(side_effect=ValueError("no inbound message to reply to"))):
        await respond._present(respond._review_sessions["U1"])
    assert "U1" not in respond._review_sessions
    assert any("done" in u["title"]["text"].lower() for u in updates)


# ---- pairing (harvest.extract_pairs) ----------------------------------------

def _m(mid, frm, subject, body):
    return {"_id": mid, "_from": frm, "_subject": subject, "_body": body}


def _patch_gmail_accessors():
    """Make extract_pairs read our simple test-message dicts."""
    return (
        patch.object(harvest.probe, "_addr", lambda m: m["_from"]),
        patch.object(harvest.gmail_lib, "header",
                     lambda m, name: m["_subject"] if name == "Subject" else ""),
        patch.object(harvest.gmail_lib, "extract_text_parts", lambda payload: payload),
        patch.object(harvest, "_text", lambda m: m["_body"]),
    )


def _run_extract(messages):
    team = {"armaan@x.com"}
    # message id lives under 'id' for extract_pairs (reply.get('id'))
    for m in messages:
        m["id"] = m["_id"]
    p1, p2, p3, p4 = _patch_gmail_accessors()
    with p1, p2, p3, p4:
        return harvest.extract_pairs({"messages": messages}, team)


def test_pairing_them_then_us_yields_one_pair():
    pairs = _run_extract([
        _m("i1", "prospect@acme.com", "Q", "how much?"),
        _m("r1", "armaan@x.com", "Re: Q", "here is the price"),
    ])
    assert len(pairs) == 1
    assert pairs[0]["incoming_body"] == "how much?"
    assert pairs[0]["reply_body"] == "here is the price"
    assert pairs[0]["message_id"] == "r1"


def test_first_touch_send_with_no_inbound_makes_no_pair():
    pairs = _run_extract([
        _m("r1", "armaan@x.com", "Cold outreach", "hi, we build X"),
    ])
    assert pairs == []


def test_multi_turn_thread_yields_two_pairs():
    pairs = _run_extract([
        _m("i1", "p@acme.com", "Q", "first question"),
        _m("r1", "armaan@x.com", "Re: Q", "first answer"),
        _m("i2", "p@acme.com", "Re: Q", "second question"),
        _m("r2", "armaan@x.com", "Re: Q", "second answer"),
    ])
    assert [p["message_id"] for p in pairs] == ["r1", "r2"]
    assert pairs[1]["incoming_body"] == "second question"   # nearest preceding inbound


def test_pair_with_empty_body_is_dropped():
    pairs = _run_extract([
        _m("i1", "p@acme.com", "Q", ""),        # empty inbound body
        _m("r1", "armaan@x.com", "Re", "answer"),
    ])
    assert pairs == []


# ---- corpus dedupe on re-harvest (reply_examples.upsert_examples) -----------

async def test_upsert_dedupes_on_message_id():
    # First row inserts (201), an identical message_id comes back as 409 and is
    # not counted -> re-harvest never double-inserts.
    posts = [MagicMock(status_code=201), MagicMock(status_code=409)]

    class _FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, *a, **k):
            return posts.pop(0)

    rows = [
        {"message_id": "r1", "founder": "armaan", "category": "pricing",
         "incoming_subject": "", "incoming_body": "a", "reply_body": "b",
         "sentiment": "positive", "source": "harvest", "is_gold": False},
        {"message_id": "r1", "founder": "armaan", "category": "pricing",
         "incoming_subject": "", "incoming_body": "a", "reply_body": "b",
         "sentiment": "positive", "source": "harvest", "is_gold": False},
    ]
    with patch.object(reply_examples.httpx, "AsyncClient", return_value=_FakeClient()):
        inserted = await reply_examples.upsert_examples(rows)
    assert inserted == 1


# ---- drafter: novel category still gets in-voice examples -------------------

async def test_gather_examples_backfills_when_category_empty():
    # No pricing exemplars, but the founder has other-category ones -> the drafter
    # still retrieves in-voice examples so a novel question gets a sane draft.
    with patch.object(reply_drafter.reply_examples, "retrieve", AsyncMock(return_value=[])), \
         patch.object(reply_drafter.reply_examples, "retrieve_any",
                      AsyncMock(return_value=[{"reply_body": "x"}, {"reply_body": "y"}])):
        examples = await reply_drafter._gather_examples("armaan", "pricing")
    assert len(examples) == 2


def test_reply_subject_does_not_double_prefix():
    assert reply_drafter._reply_subject("Re: hi") == "Re: hi"
    assert reply_drafter._reply_subject("hi") == "Re: hi"
    assert reply_drafter._reply_subject("") == "Re:"


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-o", "asyncio_mode=auto", "-q"]))
