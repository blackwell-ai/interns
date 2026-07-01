"""Tests for the /respond reply-review deck and its corpus/harvest logic.

Everything network- or LLM-bound is mocked. Covers: the real generate_draft
return shape (the regression that catches an undefined-name / wrong-key send
spec), the deck flow (build + background draft, prev/next nav with edit
preservation, accept-and-send success and partial-failure, restart mid-session,
regenerate), plus the harvest pairing, corpus dedupe, and retrieval fallback.

Run:  toolbox/.venv/bin/python -m pytest skills/campaign/tests_respond -o asyncio_mode=auto

Per the repo rule, this folder is temporary and deleted after merge.
"""
import asyncio
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

from skills.campaign.wizard import respond, reply_examples, reply_drafter, blocks  # noqa: E402
from skills.campaign import harvest_reply_examples as harvest  # noqa: E402


# ---- helpers ----------------------------------------------------------------

def _draft(thread_id="T1"):
    """A reply_drafter.generate_draft-shaped dict (post-fix keys)."""
    return {
        "draft": "Happy to help. Thanks, Armaan", "category": "pricing",
        "sentiment": "positive", "incoming_subject": "Q", "incoming_body": "how much?",
        "reply_subject": "Re: Q", "to": "p@acme.com",
        "reply_to_message_id": "m_" + thread_id, "thread_id": thread_id,
        "thread_preview": "[Them] how much?", "n_examples": 2,
    }


def _seed(user="U1", cards=None):
    cards = cards or [("p@acme.com", "T1")]
    deck = [{"row": {"who": who, "thread_id": tid}, "draft": _draft(tid),
             "edited": None, "draft_status": "ready", "sent": False, "render_nonce": 0}
            for who, tid in cards]
    session = {"user_id": user, "founder_key": "armaan",
               "founder_email": "armaan.priyadarshan.29@dartmouth.edu",
               "deck": deck, "pos": 0, "view_id": "V1", "sent": 0, "skipped": 0,
               "sem": asyncio.Semaphore(4)}
    respond._review_sessions[user] = session
    return session


@pytest.fixture(autouse=True)
def _clear():
    respond._review_sessions.clear()
    yield
    respond._review_sessions.clear()


# ---- the regression: real generate_draft return shape -----------------------

async def test_generate_draft_returns_send_ready_shape():
    """Calls the REAL generate_draft with only Gmail/LLM/Supabase mocked. Guards
    the send-spec contract: it must return `reply_to_message_id` (the Gmail id of
    the inbound), not an undefined/renamed field. This is the test that would have
    caught the shipped NameError."""
    thread = {"messages": [
        {"_from": "armaan.priyadarshan.29@dartmouth.edu", "_subject": "Cold",
         "id": "m1", "payload": "our original pitch"},
        {"_from": "prospect@acme.com", "_subject": "Re: Cold",
         "id": "m_in", "payload": "how much does it cost?"},
    ]}

    class _Resp:
        def raise_for_status(self): pass
        def json(self): return thread

    class _Client:
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def get(self, *a, **k): return _Resp()

    with patch.object(reply_drafter.httpx, "AsyncClient", lambda *a, **k: _Client()), \
         patch.object(reply_drafter.gmail_auth, "get_access_token", MagicMock(return_value="tok")), \
         patch.object(reply_drafter, "_addr", lambda m: m["_from"]), \
         patch.object(reply_drafter.gmail_lib, "header",
                      lambda m, n: m.get("_subject", "") if n == "Subject" else ""), \
         patch.object(reply_drafter.gmail_lib, "extract_text_parts", lambda payload: payload), \
         patch.object(reply_drafter.reply_examples, "classify_category", MagicMock(return_value="pricing")), \
         patch.object(reply_drafter.reply_scan, "classify_sentiment", MagicMock(return_value="positive")), \
         patch.object(reply_drafter.reply_examples, "retrieve", AsyncMock(return_value=[])), \
         patch.object(reply_drafter.reply_examples, "retrieve_any", AsyncMock(return_value=[{"reply_body": "x"}])), \
         patch.object(reply_drafter.voice_cards, "get_card", AsyncMock(return_value="")), \
         patch.object(reply_drafter.llm_mod, "complete", MagicMock(return_value="Drafted. Thanks, Armaan")):
        result = await reply_drafter.generate_draft(
            "armaan", "armaan.priyadarshan.29@dartmouth.edu", "T1")

    assert result["reply_to_message_id"] == "m_in"      # the inbound Gmail id
    assert "anchor_message_id" not in result            # the renamed-away field is gone
    assert result["to"] == "prospect@acme.com"
    assert result["draft"].startswith("Drafted")
    assert result["thread_id"] == "T1"


# ---- deck flow --------------------------------------------------------------

async def test_empty_queue_shows_all_clear():
    updates = []
    with patch.object(respond, "_update", AsyncMock(side_effect=lambda v, view: updates.append(view))), \
         patch.object(respond.triage, "needs_for_founder", AsyncMock(return_value=[])):
        await respond.build_first("U1", "armaan", "V1")
    assert "U1" not in respond._review_sessions
    assert any("clear" in u["title"]["text"].lower() for u in updates)


async def test_build_deck_drafts_all_in_background():
    with patch.object(respond, "_update", AsyncMock()), \
         patch.object(respond.triage, "needs_for_founder",
                      AsyncMock(return_value=[{"thread_id": "T1", "who": "a@x"},
                                              {"thread_id": "T2", "who": "b@x"}])), \
         patch.object(respond.reply_drafter, "generate_draft",
                      AsyncMock(side_effect=lambda fk, fe, tid: _draft(tid))):
        await respond.build_first("U1", "armaan", "V1")
        await asyncio.sleep(0.05)   # let the per-card background draft tasks finish
    deck = respond._review_sessions["U1"]["deck"]
    assert len(deck) == 2 and all(it["draft_status"] == "ready" for it in deck)


async def test_next_moves_forward_and_preserves_edit():
    s = _seed(cards=[("a@x", "T1"), ("b@x", "T2")])
    with patch.object(respond, "_update", AsyncMock()):
        await respond.on_nav("U1", "V1", +1, "my half-written reply")
    assert s["pos"] == 1
    assert s["deck"][0]["edited"] == "my half-written reply"   # saved on the way out
    with patch.object(respond, "_update", AsyncMock()):
        await respond.on_nav("U1", "V1", -1, None)
    assert s["pos"] == 0


async def test_accept_send_records_gold_and_advances():
    _seed(cards=[("a@x", "T1")])
    gold = AsyncMock(return_value=True)
    with patch.object(respond, "_update", AsyncMock()), \
         patch.object(respond, "_send_reply", AsyncMock(return_value=(True, "sent_1"))), \
         patch.object(respond.reply_examples, "add_gold_example", gold):
        await respond.on_send("U1", "V1", "my edited reply. Thanks, Armaan")
    assert gold.await_count == 1
    assert gold.await_args.kwargs["reply_body"] == "my edited reply. Thanks, Armaan"
    assert gold.await_args.kwargs["message_id"] == "sent_1"
    assert "U1" not in respond._review_sessions          # single card, all sent -> done


async def test_send_failure_keeps_card_and_records_nothing():
    s = _seed(cards=[("a@x", "T1")])
    gold = AsyncMock()
    with patch.object(respond, "_update", AsyncMock()), \
         patch.object(respond, "_send_reply", AsyncMock(return_value=(False, "boom"))), \
         patch.object(respond.reply_examples, "add_gold_example", gold):
        await respond.on_send("U1", "V1", "attempted reply")
    gold.assert_not_awaited()
    assert s["deck"][0]["sent"] is False
    assert "U1" in respond._review_sessions
    assert s["deck"][0]["edited"] == "attempted reply"   # edit kept for retry


async def test_send_with_no_session_is_graceful():
    shown = []
    with patch.object(respond, "_update", AsyncMock(side_effect=lambda v, view: shown.append(view))):
        await respond.on_send("U_missing", "V9", "hello")
    assert shown and "ended" in shown[-1]["title"]["text"].lower()


async def test_regenerate_redrafts_current_and_clears_edit():
    s = _seed(cards=[("a@x", "T1")])
    with patch.object(respond, "_update", AsyncMock()), \
         patch.object(respond.reply_drafter, "generate_draft", AsyncMock(return_value=_draft("T1b"))):
        await respond.on_regen("U1", "V1", "a stale partial edit")
    assert s["deck"][0]["draft_status"] == "ready"
    assert s["deck"][0]["edited"] is None                # regen discards the old edit
    assert s["deck"][0]["draft"]["thread_id"] == "T1b"


# ---- thread transcript rendering --------------------------------------------

def _all_text(view_blocks):
    out = []
    for b in view_blocks:
        if b.get("type") == "section":
            out.append(b["text"]["text"])
        elif b.get("type") == "context":
            out += [e["text"] for e in b["elements"]]
    return "\n".join(out)


def test_deck_modal_renders_full_thread_when_present():
    thread = [
        {"who": "you", "when": "Jun 20, 2026 at 9:00 AM", "text": "Would you be open to a quick call?"},
        {"who": "them", "when": "Jun 21, 2026 at 2:14 PM", "text": "Sure, what does it cost?"},
    ]
    view = blocks._respond_deck_modal(
        founder_name="Armaan", pos=1, total=1, sent=0, skipped=0, ready=1,
        who="p@acme.com", subject="Re: Q", their_message="Sure, what does it cost?",
        body="Happy to help.", category="pricing", n_examples=2, mode="review",
        can_prev=False, can_next=False, private_metadata="{}",
        thread=thread, thread_hidden=3, gmail_url="https://mail.google.com/x")
    text = _all_text(view["blocks"])
    assert "Conversation" in text
    assert "Would you be open to a quick call?" in text   # our earlier message shown
    assert "Sure, what does it cost?" in text             # their reply shown
    assert "Armaan" in text and "p@acme.com" in text      # both parties labeled
    assert "replying to this" in text                     # the answered message is marked
    assert "3 earlier messages hidden" in text            # older-thread note


def test_deck_modal_falls_back_to_single_message_without_thread():
    view = blocks._respond_deck_modal(
        founder_name="Armaan", pos=1, total=1, sent=0, skipped=0, ready=1,
        who="p@acme.com", subject="Re: Q", their_message="Just the one message.",
        body="ok", category="other", n_examples=0, mode="review",
        can_prev=False, can_next=False, private_metadata="{}")
    text = _all_text(view["blocks"])
    assert "Their reply" in text and "Just the one message." in text


# ---- harvest pairing (harvest.extract_pairs) --------------------------------

def _run_extract(messages):
    for m in messages:
        m["id"] = m["_id"]
    with patch.object(harvest.probe, "_addr", lambda m: m["_from"]), \
         patch.object(harvest.gmail_lib, "header",
                      lambda m, name: m["_subject"] if name == "Subject" else ""), \
         patch.object(harvest, "_text", lambda m: m["_body"]):
        return harvest.extract_pairs({"messages": messages}, {"armaan@x.com"})


def _m(mid, frm, subject, body):
    return {"_id": mid, "_from": frm, "_subject": subject, "_body": body}


def test_pairing_them_then_us_yields_one_pair():
    pairs = _run_extract([_m("i1", "p@acme.com", "Q", "how much?"),
                          _m("r1", "armaan@x.com", "Re: Q", "the price")])
    assert len(pairs) == 1 and pairs[0]["message_id"] == "r1"


def test_first_touch_send_makes_no_pair():
    assert _run_extract([_m("r1", "armaan@x.com", "Cold", "hi we build X")]) == []


def test_multi_turn_yields_two_pairs():
    pairs = _run_extract([_m("i1", "p@acme.com", "Q", "q1"),
                          _m("r1", "armaan@x.com", "Re", "a1"),
                          _m("i2", "p@acme.com", "Re", "q2"),
                          _m("r2", "armaan@x.com", "Re", "a2")])
    assert [p["message_id"] for p in pairs] == ["r1", "r2"]
    assert pairs[1]["incoming_body"] == "q2"


# ---- corpus dedupe on re-harvest --------------------------------------------

async def test_upsert_dedupes_on_message_id():
    posts = [MagicMock(status_code=201), MagicMock(status_code=409)]

    class _FakeClient:
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def post(self, *a, **k): return posts.pop(0)

    rows = [{"message_id": "r1", "founder": "armaan", "category": "pricing",
             "incoming_subject": "", "incoming_body": "a", "reply_body": "b",
             "sentiment": "positive", "source": "harvest", "is_gold": False}] * 2
    with patch.object(reply_examples.httpx, "AsyncClient", return_value=_FakeClient()):
        assert await reply_examples.upsert_examples(rows) == 1


# ---- drafter helpers --------------------------------------------------------

async def test_gather_examples_backfills_when_category_empty():
    with patch.object(reply_drafter.reply_examples, "retrieve", AsyncMock(return_value=[])), \
         patch.object(reply_drafter.reply_examples, "retrieve_any",
                      AsyncMock(return_value=[{"reply_body": "x"}, {"reply_body": "y"}])):
        assert len(await reply_drafter._gather_examples("armaan", "pricing")) == 2


def test_reply_subject_does_not_double_prefix():
    assert reply_drafter._reply_subject("Re: hi") == "Re: hi"
    assert reply_drafter._reply_subject("hi") == "Re: hi"
    assert reply_drafter._reply_subject("") == "Re:"


def test_text_to_html_linkifies_urls_and_markdown():
    url = "https://cal.com/team/blackwell/30-min?overlayCalendar=true"
    # a markdown link hyperlinks the visible word, not the raw URL
    md = respond._text_to_html(f"grab a time [here]({url})")
    assert f'<a href="{url}">here</a>' in md and "[here]" not in md
    # a bare URL is still linked
    assert f'<a href="{url}">{url}</a>' in respond._text_to_html(f"book: {url}")
    # non-url text is still escaped and newline-converted
    assert respond._text_to_html("a & b\nc") == "a &amp; b<br>c"


def test_extract_message_falls_back_when_model_editorializes():
    """A first-touch email has nothing to strip, and the fast model sometimes
    replies with a meta refusal ("I'm an AI assistant...") instead of the text.
    That must be caught and replaced with the raw cleaned body, never shown."""
    body = "Hi Hassan,\n\nWe build eval tooling for AI teams. Open to a quick call?\n\nArmaan"
    meta = ("I'm an AI assistant, so I don't have the ability to identify which part "
            "is a reply. The text you've provided appears to be a complete original "
            "outreach email. If you have an actual email reply, please provide it.")
    with patch.object(reply_drafter.llm_mod, "complete", MagicMock(return_value=meta)):
        out = reply_drafter._extract_message(body)
    assert "AI assistant" not in out and "please provide" not in out
    assert "eval tooling" in out            # the real message survives via the fallback


def test_extract_message_keeps_genuine_text():
    """A normal extraction result is returned as-is (no false meta trip)."""
    body = "Sure, what does it cost?\n\nOn Jun 1 Armaan wrote:\n> hi"
    with patch.object(reply_drafter.llm_mod, "complete",
                      MagicMock(return_value="Sure, what does it cost?")):
        assert reply_drafter._extract_message(body) == "Sure, what does it cost?"


def test_clean_reply_strips_quoted_thread_and_html():
    raw = (
        "Hey,\n\nHappy to discuss on a call.\n\n"
        "On Sun, Jun 21, 2026 at 11:45 PM Armaan <a@x.edu> wrote:\n"
        "> Hi Hassan,\n> Would you be open to a quick call?\n\n"
        "--\nBest,\nHassan Arshad\n\n<div dir=\"ltr\">Hey,<div>ignore me</div></div>"
    )
    cleaned = reply_drafter._clean_reply(raw)
    assert cleaned == "Hey,\n\nHappy to discuss on a call."
    assert "wrote:" not in cleaned and ">" not in cleaned and "<div" not in cleaned


def test_clean_reply_handles_html_quote_mobile_and_outlook():
    # gmail HTML quote container
    assert reply_drafter._clean_reply(
        'Sounds good.<div class="gmail_quote">On Mon X wrote: old stuff</div>') == "Sounds good."
    # mobile signature + quoted original
    assert reply_drafter._clean_reply(
        "Yes let's talk.\n\nSent from my iPhone\n\nOn Jun 1 A wrote:\n> hi") == "Yes let's talk."
    # outlook From/Sent header block
    assert reply_drafter._clean_reply(
        "Interested.\n\nFrom: Armaan\nSent: Monday\nTo: me\n> old") == "Interested."


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-o", "asyncio_mode=auto", "-q"]))
