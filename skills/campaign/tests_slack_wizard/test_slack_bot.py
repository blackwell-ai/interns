"""Tests for the Slack campaign wizard (slack_bot.py).

Network is fully mocked: agent.plan, agent.render_sample, executor.run_all, and
the thread reply sink are patched, so nothing hits Slack, Claude, Gmail, or
Hunter. Covers the threaded state machine plus bad/missing state, and the
offline WIZARD_TEST_MODE rehearsal in the executor.

Run without pytest:  python skills/campaign/tests_slack_wizard/test_slack_bot.py
Per the repo rule, this folder is temporary and deleted after merge.
"""
import asyncio
import csv
import io
import json
import os
import sys
import traceback
from datetime import datetime
from pathlib import Path
from unittest.mock import patch, MagicMock
from zoneinfo import ZoneInfo

_DUMMY = {
    "ANTHROPIC_API_KEY": "x", "GOOGLE_OAUTH_CLIENT_ID": "x",
    "GOOGLE_OAUTH_CLIENT_SECRET": "x", "TOOLBOX_TOKEN_HUNTER": "x",
    "SUPABASE_URL": "x", "SUPABASE_SECRET_KEY": "x",
    "SLACK_BOT_TOKEN": "xoxb-test", "SLACK_APP_TOKEN": "xapp-test",
    "SLACK_CHANNEL_ID": "C_TEST",
}
for k, v in _DUMMY.items():
    os.environ.setdefault(k, v)

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "toolbox" / "src"))
from skills.campaign.server import slack_bot  # noqa: E402
from skills.campaign.server import agent, executor, triage  # noqa: E402
from toolbox.primitives.gmail import lib as gmail_lib  # noqa: E402


class Logger:
    def exception(self, *a, **k):
        pass


class FakeSlackClient:
    """Replaces app.client so _execute never makes real Slack API calls."""
    def __init__(self):
        self.posted = []    # chat_postMessage kwargs
        self.updated = []   # chat_update kwargs
        self.reactions = [] # (action, name) tuples

    async def chat_postMessage(self, **kwargs):
        self.posted.append(kwargs)
        return {"ts": "scoreboard-ts-1", "ok": True}

    async def chat_update(self, **kwargs):
        self.updated.append(kwargs)
        return {"ok": True}

    async def reactions_add(self, **kwargs):
        self.reactions.append(("add", kwargs.get("name", "")))
        return {"ok": True}

    async def reactions_remove(self, **kwargs):
        self.reactions.append(("remove", kwargs.get("name", "")))
        return {"ok": True}

    async def views_open(self, **kwargs):
        self.views = getattr(self, "views", [])
        self.views.append(kwargs)
        return {"ok": True}


class Collector:
    """Stands in for the wizard's reply sink; records text (and any blocks)."""
    def __init__(self):
        self.msgs = []
        self.blocks = []

    async def __call__(self, text=None, blocks=None):
        self.msgs.append(text or "")
        if blocks:
            self.blocks.append(blocks)

    @property
    def text(self):
        return "\n".join(self.msgs)


def _reset_state():
    slack_bot._reset()
    slack_bot._seen_events.clear()
    slack_bot._bot_user_id = "UBOT"


# Save originals before any test can monkey-patch them.
_orig_agent_plan = agent.plan
_orig_agent_render_sample = agent.render_sample
_orig_agent_school = agent.school_for_email
_orig_agent_csv_template = agent.draft_csv_template
_orig_executor_run_all = executor.run_all


def _restore_mocks():
    """Restore agent/executor callables that _patch() replaces. Call at the top
    of any test that exercises the real agent.plan logic."""
    agent.plan = _orig_agent_plan
    agent.render_sample = _orig_agent_render_sample
    agent.school_for_email = _orig_agent_school
    agent.draft_csv_template = _orig_agent_csv_template
    executor.run_all = _orig_executor_run_all


_SAMPLE_RUNS = [{
    "sender_key": "armaan", "email": "armaan.priyadarshan.29@dartmouth.edu",
    "from_name": "Armaan", "cc": "x", "icp_label": "DTC brands",
    "icp_desc": "DTC skincare brands", "template": "templates/brands.md",
    "n_emails": 20,
}]


def _patch(plan=None, run_all_result="DTC brands via Armaan: 20 sent [OK]"):
    agent.plan = plan or (lambda text, allow_clarify=True: {"runs": _SAMPLE_RUNS, "deferred": 0})
    agent.render_sample = lambda run, **kw: ("Test subject", "Test body")
    agent.school_for_email = lambda email: ("Dartmouth", "Stanford/Berkeley")

    async def fake_run_all(plan_, send_update, set_progress=None, log_line=None):
        if log_line:
            log_line("[Armaan] 20/20 contacts (100%)")
        # Intermediate messages (must NOT advance scoreboard pointer)
        await send_update(":crystal_ball: Armaan begins the work, divining up to 20 leads...")
        await send_update(":sparkles: Armaan: 50% of the leads gathered (10 so far)...")
        # Terminal message (MUST advance scoreboard pointer)
        await send_update(":mage: Armaan: 20 sent.")
        return run_all_result
    executor.run_all = fake_run_all

    # Replace the underlying web client so app.client calls in _execute are intercepted.
    # AsyncApp.client is a read-only property backed by _async_client.
    client = FakeSlackClient()
    slack_bot.app._async_client = client
    return client


def _capture_replies():
    """Patch the thread reply factory so every reply lands in one collector."""
    posted = Collector()
    slack_bot._reply_to = lambda thread_ts=None: posted
    return posted


# ---- tests -----------------------------------------------------------------

async def test_strip_mentions():
    assert slack_bot._strip_mentions("<@U123> 20 emails") == "20 emails"
    assert slack_bot._strip_mentions("<@U1> hi <@U2>") == "hi"
    assert slack_bot._strip_mentions("no mention") == "no mention"
    assert slack_bot._strip_mentions("   <@U1>   ") == ""


async def test_happy_path_plan_then_send():
    _reset_state(); client = _patch()
    slack_bot._state["thread_ts"] = "T_TEST"  # reactions need a non-None ts
    r = Collector()
    await slack_bot._route("20 emails to DTC brands", r)
    assert slack_bot._state["mode"] == "awaiting_preview", slack_bot._state["mode"]
    assert "wizard's plan" in r.text
    assert r.blocks, "preview should carry Block Kit blocks"
    # buttons present
    ids = [e["action_id"] for b in r.blocks[-1] if b.get("type") == "actions"
           for e in b["elements"]]
    assert "wiz_send" in ids and "wiz_cancel" in ids

    await slack_bot._route("send", r)
    assert slack_bot._state["mode"] == "idle", slack_bot._state["mode"]
    # Scoreboard was posted and final update says "Sending complete."
    assert client.posted, "scoreboard must be posted"
    assert client.updated, "scoreboard must be updated on completion"
    assert client.updated[-1]["text"] == "Sending complete."
    # Reactions: ⏳ added at start, removed and ✅ added at end
    reaction_names = [(a, n) for a, n in client.reactions]
    assert ("add", "hourglass_flowing_sand") in reaction_names
    assert ("add", "white_check_mark") in reaction_names


async def test_cancel_from_preview():
    _reset_state(); _patch()
    r = Collector()
    await slack_bot._route("20 emails to DTC brands", r)
    assert slack_bot._state["mode"] == "awaiting_preview"
    r2 = Collector()
    await slack_bot._route("cancel", r2)
    assert slack_bot._state["mode"] == "idle"
    assert "cancelled" in r2.text.lower()


async def test_clarification_flow():
    def plan(text, allow_clarify=True):
        if allow_clarify:
            return {"clarify": "What split, e.g. 60/40?"}
        return {"runs": _SAMPLE_RUNS, "deferred": 0}

    _reset_state(); _patch(plan=plan)
    r = Collector()
    await slack_bot._route("emails to DTC and 3PLs", r)
    assert slack_bot._state["mode"] == "awaiting_clarification"
    assert "split" in r.text.lower()
    r2 = Collector()
    await slack_bot._route("60/40", r2)
    assert slack_bot._state["mode"] == "awaiting_preview"
    assert "wizard's plan" in r2.text


async def test_stop_when_idle():
    _reset_state(); _patch()
    r = Collector()
    await slack_bot._route("stop", r)
    assert slack_bot._state["mode"] == "idle"
    assert "no sending underway" in r.text


async def test_plan_error_resets_state():
    def boom(text, allow_clarify=True):
        raise ValueError("bad json")
    _reset_state(); _patch(plan=boom)
    r = Collector()
    await slack_bot._route("20 emails to DTC brands", r)
    assert slack_bot._state["mode"] == "idle"
    assert "could not read" in r.text


async def test_empty_plan_returns_to_idle():
    _reset_state()
    _patch(plan=lambda text, allow_clarify=True: {"runs": [], "deferred": 0})
    r = Collector()
    await slack_bot._route("0 emails", r)
    assert slack_bot._state["mode"] == "idle"
    assert "No sendings to conjure" in r.text


async def test_send_with_nothing_pending():
    _reset_state(); _patch()
    slack_bot._state["mode"] = "awaiting_preview"
    slack_bot._state["pending_plan"] = None
    r = Collector()
    await slack_bot._route("send", r)
    assert slack_bot._state["mode"] == "idle"
    assert "awaits your word" in r.text


async def test_on_message_ignores_other_channels():
    _reset_state(); _patch()
    event = {"channel": "C_OTHER", "user": "U1", "text": "<@UBOT> 20 emails", "ts": "1"}
    await slack_bot.on_message(event, Logger())
    assert slack_bot._state["mode"] == "idle"
    assert slack_bot._state["thread_ts"] is None


async def test_thread_continuation_needs_no_mention():
    _reset_state(); client = _patch()
    slack_bot._campaigns.clear()
    # First message: a mention starts the session, rooted at ts=1.
    await slack_bot.on_message(
        {"channel": "C_TEST", "user": "U1", "text": "<@UBOT> 20 emails to DTC", "ts": "1"},
        Logger())
    assert slack_bot._state["thread_ts"] == "1"
    assert slack_bot._state["mode"] == "awaiting_preview"
    # Follow-up in the same thread with NO mention advances the machine.
    await slack_bot.on_message(
        {"channel": "C_TEST", "user": "U1", "text": "send", "ts": "2", "thread_ts": "1"},
        Logger())
    assert slack_bot._state["mode"] == "idle"
    assert client.posted, "scoreboard must be posted"
    assert client.updated[-1]["text"] == "Sending complete."


async def test_on_message_dedupes_redelivery():
    _reset_state(); _patch()
    slack_bot._campaigns.clear()
    posted = _capture_replies()
    event = {"channel": "C_TEST", "user": "U1", "text": "<@UBOT> stop",
             "ts": "1", "client_msg_id": "dup1"}
    await slack_bot.on_message(event, Logger())
    first = len(posted.msgs)
    await slack_bot.on_message(event, Logger())
    assert len(posted.msgs) == first


async def test_ignores_non_mention_chatter():
    _reset_state(); _patch()
    slack_bot._campaigns.clear()
    posted = _capture_replies()
    # Idle, no active thread, plain channel message without a mention: ignored.
    await slack_bot.on_message(
        {"channel": "C_TEST", "user": "U1", "text": "lunch?", "ts": "9"}, Logger())
    assert slack_bot._state["mode"] == "idle"
    assert posted.msgs == []


async def test_qa_in_running_thread():
    # A non-command message in a thread with a (running) campaign record is
    # answered from the log via Claude, with no @mention.
    _reset_state(); _patch()
    slack_bot._campaigns.clear()
    slack_bot._campaigns["T"] = {
        "thread_ts": "T", "status": "running", "plan": _SAMPLE_RUNS,
        "log": ["[Armaan] 5/20 contacts (25%)"], "results": None,
        "progress": "25% sourced", "started": 0,
    }
    captured = {}

    def fake_answer(q, **kw):
        captured.update(kw)
        return f"PROGRESS[{kw['status']}]: {q}"
    agent.answer_about_campaign = fake_answer
    posted = _capture_replies()

    await slack_bot.on_message(
        {"channel": "C_TEST", "user": "U1", "text": "how's it going?",
         "ts": "2", "thread_ts": "T"}, Logger())
    assert "PROGRESS[running]" in posted.text
    assert "25% sourced" in captured.get("progress", "")


async def test_qa_after_completion_passes_results():
    _reset_state(); _patch()
    slack_bot._campaigns.clear()
    slack_bot._campaigns["T"] = {
        "thread_ts": "T", "status": "done", "plan": _SAMPLE_RUNS,
        "log": ["[Armaan] Result : 18 sent  2 skipped"], "results": "18 sent",
        "progress": "", "started": 0,
    }
    captured = {}

    def fake_answer(q, **kw):
        captured.update(kw)
        return "It sent 18."
    agent.answer_about_campaign = fake_answer
    posted = _capture_replies()

    await slack_bot.on_message(
        {"channel": "C_TEST", "user": "U1", "text": "how many went out?",
         "ts": "5", "thread_ts": "T"}, Logger())
    assert "It sent 18." in posted.text
    assert captured.get("results") == "18 sent"
    assert "18 sent" in captured.get("log_text", "")


async def test_executor_captures_log_lines():
    os.environ["WIZARD_TEST_MODE"] = "1"
    try:
        lines = []
        await executor.run_campaign(_SAMPLE_RUNS[0], Collector(), log_line=lines.append)
        assert any("starting" in ln for ln in lines), lines
        assert any("Result" in ln for ln in lines), lines
        assert any("finished" in ln for ln in lines), lines
    finally:
        os.environ.pop("WIZARD_TEST_MODE", None)


async def test_executor_test_mode_simulates_send():
    os.environ["WIZARD_TEST_MODE"] = "1"
    try:
        updates = Collector()
        result = await executor.run_campaign(_SAMPLE_RUNS[0], updates)
        assert "20 sent" in result, result
        assert "20 sent" in updates.text, updates.text
    finally:
        os.environ.pop("WIZARD_TEST_MODE", None)


async def test_sender_pinned_routes_all_to_one():
    seg = [{"label": "DTC", "icp": "DTC brands", "weight": 1}]
    runs, deferred = agent._divide(40, seg, ["samarjit"])
    assert runs, "expected at least one run"
    assert all(r["sender_key"] == "samarjit" for r in runs), runs
    assert sum(r["n_emails"] for r in runs) == 40
    assert deferred == 0


async def test_sender_auto_defaults_to_first():
    seg = [{"label": "DTC", "icp": "DTC brands", "weight": 1}]
    runs, _ = agent._divide(40, seg)
    assert runs[0]["sender_key"] == "armaan"


async def test_two_named_senders_split_evenly():
    seg = [{"label": "DTC", "icp": "DTC brands", "weight": 1}]
    runs, deferred = agent._divide(1600, seg, ["ethan", "samarjit"])
    assert {r["sender_key"] for r in runs} == {"ethan", "samarjit"}
    assert "armaan" not in {r["sender_key"] for r in runs}  # excluded
    assert sum(r["n_emails"] for r in runs) == 1600
    assert deferred == 0


async def test_two_named_senders_two_icps():
    segs = [{"label": "DTC", "icp": "DTC brands", "weight": 1},
            {"label": "Retailers", "icp": "retailers", "weight": 1}]
    runs, _ = agent._divide(1600, segs, ["ethan", "samarjit"])
    assert len(runs) == 4  # 2 senders x 2 ICPs
    assert {r["sender_key"] for r in runs} == {"ethan", "samarjit"}
    assert sum(r["n_emails"] for r in runs) == 1600


async def test_named_senders_cap_and_defer():
    seg = [{"label": "DTC", "icp": "DTC brands", "weight": 1}]
    # 2 accounts, 2000 requested -> 1600 capacity, 400 deferred, no Armaan
    runs, deferred = agent._divide(2000, seg, ["ethan", "samarjit"])
    assert {r["sender_key"] for r in runs} == {"ethan", "samarjit"}
    assert sum(r["n_emails"] for r in runs) == 1600
    assert deferred == 400


async def test_resolve_sender():
    assert agent.resolve_sender("Samarjit") == "samarjit"
    assert agent.resolve_sender("ethan") == "ethan"
    assert agent.resolve_sender("Ethan Zhou") == "ethan"          # full name
    assert agent.resolve_sender("ethanpzhou@berkeley.edu") == "ethan"  # email
    assert agent.resolve_sender("nobody") is None
    assert agent.resolve_sender("") is None


async def test_preview_refine_changes_sender():
    seen = {}

    def plan(text, allow_clarify=True):
        seen["text"] = text
        via_ethan = "ethan" in text.lower()
        run = {**_SAMPLE_RUNS[0],
               "from_name": "Ethan" if via_ethan else "Armaan",
               "sender_key": "ethan" if via_ethan else "armaan"}
        return {"runs": [run], "deferred": 0}

    _reset_state(); _patch(plan=plan)
    r = Collector()
    await slack_bot._route("40 emails to DTC brands", r)  # auto -> Armaan
    assert slack_bot._state["mode"] == "awaiting_preview"
    import json as _json
    assert "Armaan" in _json.dumps(r.blocks)

    r2 = Collector()
    await slack_bot._route("send via ethan", r2)  # refine, not a confirm
    assert slack_bot._state["mode"] == "awaiting_preview"  # re-planned, still preview
    assert "ethan" in seen["text"].lower()
    assert "DTC brands" in seen["text"]  # original request was merged in
    assert "Ethan" in _json.dumps(r2.blocks)


async def test_is_triage_detection():
    assert slack_bot._is_triage("which replies need a response?")
    assert slack_bot._is_triage("triage our inboxes")
    assert slack_bot._is_triage("scan emails for replies")
    assert slack_bot._is_triage("who has written back?")
    assert not slack_bot._is_triage("40 emails to DTC brands")
    assert not slack_bot._is_triage("500 to aerospace via samarjit")


async def test_triage_merge_dedupes_by_thread():
    a = {"needs": [{"thread_id": "t1", "who": "x"}], "reroute": [], "gray": []}
    b = {"needs": [{"thread_id": "t1", "who": "x"}],
         "reroute": [{"thread_id": "t2", "who": "y", "reroute_to": "z"}], "gray": []}
    needs, reroute, gray = triage.merge_results([a, b])
    assert len(needs) == 1 and needs[0]["thread_id"] == "t1"
    assert len(reroute) == 1 and reroute[0]["thread_id"] == "t2"
    assert gray == []


async def test_triage_merge_dedupes_by_email():
    # Same person across two different threads (e.g. two campaigns) must collapse
    # to one row, keeping the strongest bucket (needs over gray).
    a = {"needs": [{"thread_id": "t1", "who": "dup@x.com", "priority": "warm"}],
         "reroute": [], "gray": []}
    b = {"needs": [], "reroute": [],
         "gray": [{"thread_id": "t2", "who": "dup@x.com"}]}
    needs, reroute, gray = triage.merge_results([a, b])
    assert len(needs) == 1 and needs[0]["who"] == "dup@x.com"
    assert reroute == [] and gray == []  # the weaker gray copy is dropped


def _all_text(msgs):
    """Concatenate every section block's mrkdwn text across all messages."""
    out = []
    for m in msgs:
        for b in (m.get("blocks") or []):
            if b.get("type") == "section":
                out.append(b["text"]["text"])
    return "\n".join(out)


async def test_triage_format_messages_grouped():
    needs = [{"who": "a@x.com", "priority": "warm", "ask": "wants a call",
              "owner": "armaan.priyadarshan.29@dartmouth.edu", "thread_id": "t"}]
    reroute = [{"who": "b@y.com", "reroute_to": "c@y.com",
                "owner": "ethanpzhou@berkeley.edu", "thread_id": "t2"}]
    msgs = triage.format_messages(needs, reroute, [], [], 60)
    assert "Inbox triage" in msgs[0]["text"]
    assert "1* awaiting reply" in msgs[0]["text"]
    text = _all_text(msgs)
    assert "a@x.com" in text                          # awaiting-reply lists the person
    assert "Armaan" in text and "Ethan" in text       # grouped under owner names
    assert "Awaiting reply" in text and "Reroute" in text
    # reroute is just a per-owner count now (handled autonomously) — no contacts listed
    assert "c@y.com" not in text and "b@y.com" not in text
    # tables are gone — friendlier owner-grouped sections instead
    assert not [b for m in msgs for b in (m.get("blocks") or []) if b.get("type") == "table"]


async def test_triage_priority_ordering():
    needs = [
        {"who": "cold@x.com", "priority": "cold", "owner": "ethanpzhou@berkeley.edu", "thread_id": "1"},
        {"who": "hot@x.com", "priority": "hot", "owner": "ethanpzhou@berkeley.edu", "thread_id": "2"},
        {"who": "warm@x.com", "priority": "warm", "owner": "ethanpzhou@berkeley.edu", "thread_id": "3"},
    ]
    text = _all_text(triage.format_messages(needs, [], [], [], 60))
    # within an owner, hottest appears before warm, which appears before cold
    assert text.index("hot@x.com") < text.index("warm@x.com") < text.index("cold@x.com")


async def test_triage_format_groups_by_owner():
    # Two owners -> owners appear A->Z, each with their own people.
    needs = [
        {"who": "z1@x.com", "priority": "warm", "owner": "ethanpzhou@berkeley.edu", "thread_id": "1"},
        {"who": "a1@x.com", "priority": "warm",
         "owner": "armaan.priyadarshan.29@dartmouth.edu", "thread_id": "2"},
    ]
    text = _all_text(triage.format_messages(needs, [], [], [], 60))
    assert text.index("Armaan") < text.index("Ethan")  # alphabetical by owner


async def test_triage_format_chunks_large_buckets():
    needs = [{"who": f"p{i}@x.com", "priority": "warm",
              "owner": "ethanpzhou@berkeley.edu", "thread_id": str(i)}
             for i in range(200)]
    msgs = triage.format_messages(needs, [], [], [], 60)
    for m in msgs:
        blocks = m.get("blocks") or []
        assert len(blocks) <= 50  # Slack's per-message block limit
        for b in blocks:
            if b.get("type") == "section":
                assert len(b["text"]["text"]) <= 3000  # Slack's section char cap
    text = _all_text(msgs)
    assert all(f"p{i}@x.com" in text for i in range(200))  # nothing dropped


async def test_triage_long_owner_header_appears_once():
    # A single owner with enough rows to overflow one section must still show their
    # name only once (continuation sections carry no header), not "part 1/2".
    reroute = [{"who": f"p{i}@example.com", "reroute_to": f"new{i}@example.com",
                "owner": "ethanpzhou@berkeley.edu", "thread_id": str(i)}
               for i in range(120)]
    msgs = triage.format_messages([], reroute, [], [], 60)
    headers = sum(s["text"]["text"].count(":bust_in_silhouette:")
                  for m in msgs for s in (m.get("blocks") or [])
                  if s.get("type") == "section")
    assert headers == 1  # one owner -> one header, despite the list being split
    assert "part" not in _all_text(msgs).lower()


def _capture_channel():
    posts = []

    async def fake(text=None, blocks=None):
        posts.append(text)
    slack_bot._post_channel = fake
    return posts


def _reset_pester():
    slack_bot._state["mode"] = "idle"
    slack_bot._pester.update({"active": False, "count_date": None,
                              "sent_today": 0, "started_at": None})


async def test_run_reminder_mentions_user():
    from skills.campaign.server import slack_config
    slack_config.SLACK_REMINDER_USER = "U123"
    _reset_pester()
    assert "<@U123>" in slack_bot._run_reminder_text()


async def test_remind_run_skips_when_target_met():
    from skills.campaign.server import slack_config
    posts = _capture_channel()
    _reset_pester()
    slack_bot.record_campaign_sent(slack_config.SLACK_DAILY_TARGET)  # quota filled
    await slack_bot._remind_run()
    assert posts == []                       # no nudge once maxed out
    assert slack_bot._pester["active"] is False


async def test_trivial_send_does_not_silence_nudge():
    """A small send (well under target) must NOT stop the nudge."""
    posts = _capture_channel()
    _reset_pester()
    slack_bot.record_campaign_sent(85)       # trivial vs ~2000 target
    await slack_bot._remind_run()
    assert posts and "85 of" in posts[0]     # still nudges, shows progress
    assert slack_bot._pester["active"] is True


async def test_remind_run_starts_nudge():
    posts = _capture_channel()
    _reset_pester()
    await slack_bot._remind_run()
    assert posts and "maxing out" in posts[0]
    assert slack_bot._pester["active"] is True


async def test_pester_stops_once_target_met():
    posts = _capture_channel()
    _reset_pester()
    slack_bot._pester.update({
        "active": True, "started_at": datetime.now(ZoneInfo("America/Los_Angeles"))})
    slack_bot.record_campaign_sent(99999)    # mid-pester, target is reached
    await slack_bot._pester_run()
    assert posts == []                       # stops nudging
    assert slack_bot._pester["active"] is False


async def test_pester_skips_tick_while_campaign_running():
    """While a campaign is sending, the pester stays active but does not post."""
    posts = _capture_channel()
    _reset_pester()
    slack_bot._pester.update({
        "active": True, "started_at": datetime.now(ZoneInfo("America/Los_Angeles"))})
    slack_bot._state["mode"] = "executing"
    await slack_bot._pester_run()
    assert posts == []                       # no nudge mid-send
    assert slack_bot._pester["active"] is True   # but still on, resumes after
    slack_bot._state["mode"] = "idle"


async def test_pester_renudges_while_active():
    posts = _capture_channel()
    _reset_pester()
    slack_bot._pester.update({
        "active": True, "started_at": datetime.now(ZoneInfo("America/Los_Angeles"))})
    await slack_bot._pester_run()
    assert len(posts) == 1                    # still nudging


async def test_gmail_rate_limit_is_transient():
    # The bug: Gmail returns 403 for per-user rate limits, which were treated as
    # permanent and dropped. They must now classify as transient (retry).
    rate_body = ('{"error":{"code":403,"errors":[{"reason":"rateLimitExceeded"}],'
                 '"message":"User-rate limit exceeded. Queries per minute per user"}}')
    assert gmail_lib.classify_send_error(403, rate_body) is None        # retry
    assert gmail_lib.classify_send_error(429, "Too many requests") is None
    # daily cap stays a hard wall, other 4xx stay permanent
    assert gmail_lib.classify_send_error(403, "Daily user sending limit exceeded") \
        is gmail_lib.QuotaExceeded
    assert gmail_lib.classify_send_error(400, "Invalid To header") \
        is gmail_lib.PermanentSendError
    assert gmail_lib.classify_send_error(403, "insufficient permission") \
        is gmail_lib.PermanentSendError


# ---- _RUN_DONE_RE: only terminal executor messages advance the scoreboard ----

async def test_run_done_re_matches_success():
    assert slack_bot._RUN_DONE_RE.search(":mage: Armaan: 45 sent.")
    assert slack_bot._RUN_DONE_RE.search(":mage: Armaan: 45 sent, 2.0 Hunter credits.")
    assert slack_bot._RUN_DONE_RE.search(":mage: Ethan: 0 sent.")
    assert slack_bot._RUN_DONE_RE.search(":MAGE: Armaan: 10 sent.")  # case-insensitive


async def test_run_done_re_matches_failure():
    assert slack_bot._RUN_DONE_RE.search(
        ":warning: Armaan: the sending faltered (exit 1).")
    assert slack_bot._RUN_DONE_RE.search("Armaan: auth failed — token expired")
    assert slack_bot._RUN_DONE_RE.search("Samarjit: auth failed — OAuth refresh error")


async def test_run_done_re_ignores_intermediate():
    no_match = [
        ":crystal_ball: Armaan begins the work, divining up to 20 leads for DTC brands...",
        ":sparkles: Armaan: 25% of the leads gathered (5 so far)...",
        ":sparkles: Armaan: 100% of the leads gathered (20 so far)...",
        ":scroll: Armaan: 20 scrolls penned, dispatching now...",
        ":warning: Armaan: some error line from stderr[:120]",
        "running...",
        "In all, the sending drew 5 Hunter credits.",
        ":crystal_ball: Armaan dispatching 1 scroll directly to Direct: John at Acme...",
    ]
    for msg in no_match:
        assert not slack_bot._RUN_DONE_RE.search(msg), f"should not match: {msg!r}"


# ---- scoreboard: pointer advances only on run completion --------------------

async def test_scoreboard_only_advances_on_completion():
    """With 2 runs, current_idx must not move until each run's terminal message."""
    _reset_state(); client = _patch()
    slack_bot._state["thread_ts"] = "T1"

    run1 = {**_SAMPLE_RUNS[0], "icp_label": "DTC brands", "n_emails": 20}
    run2 = {**_SAMPLE_RUNS[0], "sender_key": "ethan", "from_name": "Ethan",
            "email": "ethanpzhou@berkeley.edu", "icp_label": "Aerospace", "n_emails": 15}

    updates_before_run1_done = []

    async def two_run_fake(plan_, send_update, set_progress=None, log_line=None):
        # Run 1: 3 intermediate (must not advance pointer)
        await send_update(":crystal_ball: Armaan begins the work, divining 20 leads...")
        await send_update(":sparkles: Armaan: 50% of the leads gathered (10 so far)...")
        await send_update(":scroll: Armaan: 20 scrolls penned, dispatching now...")
        updates_before_run1_done.append(len(client.updated))  # capture count
        # Run 1 done
        await send_update(":mage: Armaan: 20 sent.")
        # Run 2: 1 intermediate then done
        await send_update(":crystal_ball: Ethan begins the work, divining 15 leads...")
        await send_update(":mage: Ethan: 15 sent.")
        return "DTC via Armaan: 20 sent [OK]\nAerospace via Ethan: 15 sent [OK]"

    executor.run_all = two_run_fake
    await slack_bot._execute([run1, run2])

    # Scoreboard must NOT have been updated by any of the 3 intermediate messages
    assert updates_before_run1_done[0] == 0, (
        f"scoreboard updated {updates_before_run1_done[0]} times before run 1 completed "
        "(intermediate messages must not advance the pointer)")

    # After both runs: at least 2 scoreboard updates (one per completed run) + final
    assert len(client.updated) >= 2
    assert client.updated[-1]["text"] == "Sending complete."

    # Reactions correct
    assert ("add", "hourglass_flowing_sand") in client.reactions
    assert ("remove", "hourglass_flowing_sand") in client.reactions
    assert ("add", "white_check_mark") in client.reactions


async def test_scoreboard_marks_failed_run():
    """A faltered run is reflected in the final scoreboard blocks."""
    _reset_state(); client = _patch()
    slack_bot._state["thread_ts"] = "T2"

    async def fail_run(plan_, send_update, set_progress=None, log_line=None):
        await send_update(":warning: Armaan: the sending faltered (exit 1).")
        return "DTC via Armaan: 0 sent [exit 1]"

    executor.run_all = fail_run
    await slack_bot._execute([_SAMPLE_RUNS[0]])

    assert client.updated, "scoreboard must be updated"
    final_blocks = str(client.updated[-1]["blocks"])
    assert "failed" in final_blocks or ":x:" in final_blocks


# ---- _progress_blocks structure ---------------------------------------------

async def test_progress_blocks_initial_state():
    run_statuses = [
        {"run": {"icp_label": "DTC brands", "from_name": "Armaan", "n_emails": 20},
         "state": "running", "sent": None},
        {"run": {"icp_label": "Aerospace", "from_name": "Ethan", "n_emails": 15},
         "state": "queued", "sent": None},
    ]
    blocks = slack_bot._progress_blocks(run_statuses, done=False)
    text = json.dumps(blocks)
    assert "Campaign in progress" in text
    assert "DTC brands" in text
    assert "Aerospace" in text
    assert "starting" in text  # running run with no phase yet
    assert "queued" in text


async def test_progress_blocks_final_state():
    run_statuses = [
        {"run": {"icp_label": "DTC brands", "from_name": "Armaan", "n_emails": 20},
         "state": "done", "sent": 18},
        {"run": {"icp_label": "Aerospace", "from_name": "Ethan", "n_emails": 15},
         "state": "done", "sent": 14},
    ]
    blocks = slack_bot._progress_blocks(run_statuses, done=True)
    text = json.dumps(blocks)
    assert "Complete" in text
    assert "18" in text and "14" in text
    assert "32" in text  # total sent in footer


async def test_progress_blocks_error_state():
    run_statuses = [
        {"run": {"icp_label": "DTC brands", "from_name": "Armaan", "n_emails": 20},
         "state": "failed", "sent": 0},
    ]
    blocks = slack_bot._progress_blocks(run_statuses, done=True)
    text = json.dumps(blocks)
    assert "errors" in text.lower() or "error" in text.lower()
    assert ":x:" in text


# ---- agent direct mode -------------------------------------------------------

async def test_direct_label_single_named():
    label = agent._direct_label(
        [{"first_name": "John", "company": "Acme Corp", "email": "j@acme.com"}])
    assert label == "Direct: John at Acme Corp"


async def test_direct_label_single_email_only():
    label = agent._direct_label(
        [{"email": "j@acme.com", "first_name": "", "company": ""}])
    assert label == "Direct: j@acme.com"


async def test_direct_label_multiple():
    label = agent._direct_label([{"email": "a@x.com"}, {"email": "b@y.com"},
                                  {"email": "c@z.com"}])
    assert "3 contacts" in label


async def test_plan_direct_mode_returns_leads():
    """plan() in direct mode bypasses _divide and returns direct_leads."""
    _restore_mocks()
    mock_resp = MagicMock()
    mock_resp.content = [MagicMock(text=json.dumps({
        "direct": True,
        "leads": [{"email": "john@acme.com", "first_name": "John",
                   "last_name": "Smith", "company": "Acme", "title": "VP",
                   "domain": "acme.com"}],
        "senders": [],
    }))]
    with patch("anthropic.Anthropic") as MockCls:
        MockCls.return_value.messages.create.return_value = mock_resp
        result = agent.plan("email John Smith at Acme, john@acme.com")

    assert "runs" in result and "deferred" in result
    assert result["deferred"] == 0
    run = result["runs"][0]
    assert run["direct_leads"] == [{"email": "john@acme.com", "first_name": "John",
                                    "last_name": "Smith", "company": "Acme",
                                    "title": "VP", "domain": "acme.com"}]
    assert run["n_emails"] == 1
    assert run["sender_key"] == "armaan"  # default first sender
    assert "icp" not in run.get("icp_desc", "direct send")  # not an ICP run


async def test_plan_direct_mode_named_sender():
    """Named sender in direct mode is honoured."""
    _restore_mocks()
    mock_resp = MagicMock()
    mock_resp.content = [MagicMock(text=json.dumps({
        "direct": True,
        "leads": [{"email": "a@b.com", "first_name": "A", "last_name": "",
                   "company": "B", "title": "", "domain": "b.com"}],
        "senders": ["ethan"],
    }))]
    with patch("anthropic.Anthropic") as MockCls:
        MockCls.return_value.messages.create.return_value = mock_resp
        result = agent.plan("email a@b.com via ethan")

    assert result["runs"][0]["sender_key"] == "ethan"


async def test_plan_direct_mode_no_valid_email_clarifies():
    """If Claude fires direct mode but the leads list is empty, we clarify."""
    _restore_mocks()
    mock_resp = MagicMock()
    mock_resp.content = [MagicMock(text=json.dumps({
        "direct": True, "leads": [], "senders": []}))]
    with patch("anthropic.Anthropic") as MockCls:
        MockCls.return_value.messages.create.return_value = mock_resp
        result = agent.plan("email someone")

    assert "clarify" in result
    assert result["clarify"]  # non-empty clarification


async def test_plan_icp_mode_unchanged():
    """Standard ICP requests still produce runs via _divide, no direct_leads."""
    _restore_mocks()
    mock_resp = MagicMock()
    mock_resp.content = [MagicMock(text=json.dumps({
        "total": 100, "segments": [{"label": "DTC", "icp": "DTC brands", "weight": 1}],
        "senders": [], "clarify": "",
    }))]
    with patch("anthropic.Anthropic") as MockCls:
        MockCls.return_value.messages.create.return_value = mock_resp
        result = agent.plan("100 emails to DTC brands")

    assert "runs" in result
    assert not result["runs"][0].get("direct_leads")
    assert result["runs"][0]["icp_desc"] == "DTC brands"


# ---- executor: direct leads writes correct CSV and command ------------------

class _AsyncLines:
    """Minimal async iterator over byte lines, for mocking proc.stdout."""
    def __init__(self, lines):
        self._it = iter(lines)
    def __aiter__(self): return self
    async def __anext__(self):
        try: return next(self._it)
        except StopIteration: raise StopAsyncIteration


async def test_executor_direct_leads_uses_leads_flag():
    """With direct_leads, executor must use --leads/--provider clay, not --icp/hunter."""
    direct_item = {
        **_SAMPLE_RUNS[0],
        "direct_leads": [
            {"email": "john@acme.com", "first_name": "John", "last_name": "Smith",
             "company": "Acme", "title": "VP", "domain": "acme.com"},
            {"email": "jane@beta.io", "first_name": "Jane", "last_name": "",
             "company": "Beta", "title": "CEO", "domain": "beta.io"},
        ],
        "n_emails": 2,
        "icp_desc": "direct send",
    }

    captured_cmd = []
    captured_csv = []

    class FakeProc:
        returncode = 0
        stdout = _AsyncLines([b"Result: 2 sent\n", b"Hunter: 0.0 credits\n"])
        async def wait(self): pass

    async def fake_subproc(*cmd, **kwargs):
        captured_cmd.extend(cmd)
        if "--leads" in cmd:
            path = cmd[list(cmd).index("--leads") + 1]
            captured_csv.append(path)
        return FakeProc()

    os.environ.pop("WIZARD_TEST_MODE", None)
    with patch.object(executor.gmail_auth, "get_access_token", return_value="tok"), \
         patch.object(executor, "_get_supabase_session_token", return_value="sess"), \
         patch("asyncio.create_subprocess_exec", side_effect=fake_subproc):
        updates = Collector()
        await executor.run_campaign(direct_item, updates)

    assert "--leads" in captured_cmd, f"--leads missing from cmd: {captured_cmd}"
    prov_i = list(captured_cmd).index("--provider")
    assert captured_cmd[prov_i + 1] == "clay", "provider must be clay for direct sends"
    assert "--icp" not in captured_cmd, "--icp must not appear for direct sends"

    # Temp CSV must be cleaned up after the run
    if captured_csv:
        assert not Path(captured_csv[0]).exists(), "temp CSV must be deleted after run"


async def test_executor_direct_leads_csv_content():
    """The temp CSV must contain all leads with correct field values."""
    direct_item = {
        **_SAMPLE_RUNS[0],
        "direct_leads": [
            {"email": "john@acme.com", "first_name": "John", "last_name": "Smith",
             "company": "Acme Corp", "title": "VP Eng", "domain": "acme.com"},
        ],
        "n_emails": 1,
        "icp_desc": "direct send",
    }

    captured_csv_path = []

    class FakeProc:
        returncode = 0
        stdout = _AsyncLines([b"Result: 1 sent\n"])
        async def wait(self): pass

    async def fake_subproc(*cmd, **kwargs):
        if "--leads" in cmd:
            path = cmd[list(cmd).index("--leads") + 1]
            captured_csv_path.append(path)
            # Read CSV content BEFORE the process "finishes" (before cleanup)
            with open(path, newline="") as f:
                captured_csv_path.append(list(csv.DictReader(f)))
        return FakeProc()

    os.environ.pop("WIZARD_TEST_MODE", None)
    with patch.object(executor.gmail_auth, "get_access_token", return_value="tok"), \
         patch.object(executor, "_get_supabase_session_token", return_value="sess"), \
         patch("asyncio.create_subprocess_exec", side_effect=fake_subproc):
        await executor.run_campaign(direct_item, Collector())

    assert len(captured_csv_path) >= 2, "CSV path and rows must be captured"
    rows = captured_csv_path[1]
    assert len(rows) == 1
    assert rows[0]["email"] == "john@acme.com"
    assert rows[0]["first_name"] == "John"
    assert rows[0]["company"] == "Acme Corp"
    assert rows[0]["domain"] == "acme.com"


# ---- edit-draft modal --------------------------------------------------------

async def test_editable_draft_keeps_slots():
    """editable_draft returns the template with {{slots}} intact and no HTML."""
    _restore_mocks()
    subject, body = agent.editable_draft(_SAMPLE_RUNS[0])
    assert subject, "subject should come from the frontmatter"
    assert "{{first_name}}" in body, "slots must survive for personalization"
    assert "<p>" not in body and "<br>" not in body, "HTML must be stripped"


async def test_edit_button_in_preview():
    """The preview carries an Edit-draft button alongside Send and Cancel."""
    _restore_mocks()
    _, blocks = slack_bot._preview_blocks(_SAMPLE_RUNS, 0)
    ids = [e["action_id"] for b in blocks if b.get("type") == "actions"
           for e in b["elements"]]
    assert "wiz_edit" in ids and "wiz_send" in ids and "wiz_cancel" in ids


async def test_validate_draft_flags_empties():
    assert set(slack_bot._validate_draft("", "body")) == {"wiz_subj"}
    assert set(slack_bot._validate_draft("subj", "   ")) == {"wiz_body"}
    assert slack_bot._validate_draft("subj", "body") == {}


async def test_apply_draft_edit_repoints_and_renders():
    """An edit writes a temp template, repoints the run, and the sample reflects
    it once filled. _reset then removes the temp file."""
    _restore_mocks()
    _reset_state()
    run = dict(_SAMPLE_RUNS[0])
    slack_bot._state["pending_plan"] = [run]
    slack_bot._state["mode"] = "awaiting_preview"

    changed = slack_bot._apply_draft_edit(
        "New subject for {{company}}",
        "Hi {{first_name}}, an edited pitch for {{company}}.\n\n{{from_name}}")
    assert changed is True
    path = slack_bot._state["draft_template"]
    assert run["template"] == path and Path(path).exists()

    subject, sample = agent.render_sample(run)  # real render fills Alex/Acme
    assert subject == "New subject for Acme Brands"
    assert "edited pitch for Acme Brands" in sample
    assert "Armaan" in sample  # from_name filled from the run

    slack_bot._reset()
    assert not Path(path).exists(), "temp template must be cleaned up on reset"


async def test_apply_draft_edit_no_change_is_noop():
    """Submitting the unchanged template applies no override."""
    _restore_mocks()
    _reset_state()
    run = dict(_SAMPLE_RUNS[0])
    slack_bot._state["pending_plan"] = [run]
    slack_bot._state["mode"] = "awaiting_preview"
    cur_subject, cur_body = agent.editable_draft(run)

    assert slack_bot._apply_draft_edit(cur_subject, cur_body) is False
    assert slack_bot._state["draft_template"] is None
    assert run["template"] == "templates/brands.md"


async def test_draft_override_sticky_across_replan():
    """A hand-edited draft persists when the plan is refined (re-presented)."""
    _reset_state(); _patch()  # render_sample/school patched, no file reads
    fake_path = "/tmp/wiz_draft_test.md"
    slack_bot._state["draft_template"] = fake_path
    run = dict(_SAMPLE_RUNS[0])
    await slack_bot._present_plan(Collector(), [run], 0)
    assert run["template"] == fake_path, "override should re-apply to re-planned runs"
    slack_bot._state["draft_template"] = None  # avoid unlink attempt on real path


# ---- located / sending progress + final credits and time ---------------------

async def test_progress_blocks_climbing_located():
    """A run mid-sourcing shows a climbing located count; the footer tallies it."""
    run_statuses = [
        {"run": {"icp_label": "DTC brands", "from_name": "Armaan", "n_emails": 20},
         "state": "running", "sent": None, "located": 12, "phase": "locating"},
    ]
    text = json.dumps(slack_bot._progress_blocks(run_statuses, done=False))
    assert "12 located..." in text   # per-run line
    assert "*12* located" in text    # footer tally


async def test_progress_blocks_sending_phase():
    """After composing, the run shows a plain sending indicator (no tally)."""
    run_statuses = [
        {"run": {"icp_label": "DTC brands", "from_name": "Armaan", "n_emails": 20},
         "state": "running", "sent": None, "located": 20, "phase": "sending"},
    ]
    text = json.dumps(slack_bot._progress_blocks(run_statuses, done=False))
    assert "sending..." in text


async def test_progress_blocks_done_shows_credits_and_time():
    run_statuses = [
        {"run": {"icp_label": "DTC brands", "from_name": "Armaan", "n_emails": 20},
         "state": "done", "sent": 18, "located": 20, "phase": "sending"},
    ]
    text = json.dumps(
        slack_bot._progress_blocks(run_statuses, done=True, credits="7", elapsed_s=135))
    assert "*18* sent" in text
    assert "7 Hunter credits" in text
    assert "2m 15s" in text


async def test_fmt_duration():
    assert slack_bot._fmt_duration(45) == "45s"
    assert slack_bot._fmt_duration(135) == "2m 15s"
    assert slack_bot._fmt_duration(0) == "0s"


async def test_execute_scoreboard_located_credits_time():
    """End to end: a located update climbs the board, and the final scoreboard
    carries sent count, campaign Hunter credits, and elapsed time."""
    _reset_state(); client = _patch()
    slack_bot._state["thread_ts"] = "TD"

    async def fake(plan_, send_update, set_progress=None, log_line=None):
        await send_update(":mag: Armaan: 12 located...")
        await send_update(":scroll: Armaan: 20 scrolls drafted, sending now...")
        await send_update(":mage: Armaan: 20 sent.")
        await send_update("In all, the sending drew 5 Hunter credits.")
        return "DTC brands via Armaan: 20 sent [OK]"

    executor.run_all = fake
    await slack_bot._execute([dict(_SAMPLE_RUNS[0])])
    assert "12 located" in json.dumps(client.updated)  # climbed at least once
    final = json.dumps(client.updated[-1])
    assert "*20* sent" in final and "5 Hunter credits" in final
    assert client.updated[-1]["text"] == "Sending complete."


async def test_executor_test_mode_emits_located_and_drafted():
    """The rehearsal sim exercises the located counter and the drafting flip."""
    os.environ["WIZARD_TEST_MODE"] = "1"
    try:
        updates = Collector()
        await executor.run_campaign(_SAMPLE_RUNS[0], updates)
        assert "located" in updates.text, updates.text
        assert "scrolls drafted" in updates.text, updates.text
    finally:
        os.environ.pop("WIZARD_TEST_MODE", None)


# ---- per-person personalization from a CSV with extra context ----------------

async def test_direct_schema_captures_context():
    """Direct mode keeps each lead's extra 'context' for later personalization."""
    _restore_mocks()
    mock_resp = MagicMock()
    mock_resp.content = [MagicMock(text=json.dumps({
        "direct": True,
        "leads": [{"email": "dana@glow.co", "first_name": "Dana", "last_name": "",
                   "company": "Glow Co", "title": "Founder", "domain": "glow.co",
                   "context": "Launched a vitamin C serum last month, DTC skincare"}],
        "senders": [],
    }))]
    with patch("anthropic.Anthropic") as MockCls:
        MockCls.return_value.messages.create.return_value = mock_resp
        result = agent.plan("email dana@glow.co — Glow Co, launched a vitamin C serum")
    lead = result["runs"][0]["direct_leads"][0]
    assert lead["context"] == "Launched a vitamin C serum last month, DTC skincare"


async def test_draft_csv_template_validates_slots():
    """A valid generation returns (subject, body); a body missing a required slot
    raises so the caller can fall back to the default template."""
    _restore_mocks()
    good = MagicMock()
    good.content = [MagicMock(text=json.dumps({
        "subject": "quick question on web agents",
        "body": ("Hi {{first_name}},\n\nI'm a student at {{school}} working with a "
                 "couple from {{other_schools}}.\n\nI study how web agents handle "
                 "long tasks and would love your take.\n\nThanks, {{from_name}}")}))]
    with patch("anthropic.Anthropic") as M:
        M.return_value.messages.create.return_value = good
        subject, body = agent.draft_csv_template(
            [{"first_name": "Xiang", "company": "OSU", "context": "Mind2Web"}],
            "ask about web agents", "Dartmouth", "Stanford/Berkeley", "Armaan")
    assert subject and "{{first_name}}" in body and "{{school}}" in body

    bad = MagicMock()
    bad.content = [MagicMock(text=json.dumps({
        "subject": "hi", "body": "Hi {{first_name}}, no school here. {{from_name}}"}))]
    with patch("anthropic.Anthropic") as M:
        M.return_value.messages.create.return_value = bad
        try:
            agent.draft_csv_template([{"first_name": "X"}], "", "Dartmouth",
                                     "Stanford/Berkeley", "Armaan")
            assert False, "should have raised on missing {{school}}"
        except ValueError:
            pass


async def test_draft_csv_template_scrubs_dashes():
    _restore_mocks()
    resp = MagicMock()
    resp.content = [MagicMock(text=json.dumps({
        "subject": "a quick note — for you",
        "body": "Hi {{first_name}} — at {{school}}, {{other_schools}}. {{from_name}}"}))]
    with patch("anthropic.Anthropic") as M:
        M.return_value.messages.create.return_value = resp
        subject, body = agent.draft_csv_template(
            [{"first_name": "X"}], "", "Dartmouth", "Stanford/Berkeley", "Armaan")
    assert "—" not in subject and "—" not in body


async def test_render_for_lead_fills_real_data():
    """A real-recipient render fills the lead's actual fields, no leftover slots."""
    _restore_mocks()
    run = {"email": "armaan.priyadarshan.29@dartmouth.edu", "from_name": "Armaan",
           "template": "templates/brands.md"}
    lead = {"first_name": "Dana", "company": "Glow Co", "domain": "glow.co"}
    subject, body = agent.render_for_lead(run, lead)
    assert "Dana" in body and "Glow Co" in body and "Armaan" in body
    assert "{{" not in body  # every slot resolved


async def test_preview_shows_real_recipients_for_direct():
    """A direct-send preview renders up to 3 real recipients, not a placeholder."""
    _restore_mocks()
    leads = [
        {"email": "dana@glow.co", "first_name": "Dana", "company": "Glow Co",
         "domain": "glow.co"},
        {"email": "rob@trailco.com", "first_name": "Rob", "company": "Trail Co",
         "domain": "trailco.com"},
    ]
    run = {"sender_key": "armaan", "email": "armaan.priyadarshan.29@dartmouth.edu",
           "from_name": "Armaan", "cc": "x", "icp_label": "Direct to 2 contacts",
           "icp_desc": "direct send", "template": "templates/brands.md",
           "n_emails": 2, "direct_leads": leads}
    _, blocks = slack_bot._preview_blocks([run], 0)
    text = json.dumps(blocks)
    assert "Showing 2 of 2" in text
    assert "Dana" in text and "Rob" in text
    assert "Glow Co" in text and "Trail Co" in text


async def test_build_csv_template_installs_editable_override():
    """The generated shared template becomes the run's editable draft override."""
    _restore_mocks(); _reset_state()
    leads = [{"email": "x@osu.edu", "first_name": "Xiang", "company": "OSU",
              "context": "Mind2Web"}]
    run = {"email": "armaan.priyadarshan.29@dartmouth.edu", "from_name": "Armaan",
           "template": "templates/brands.md", "direct_leads": leads, "n_emails": 1}
    slack_bot._state["request_text"] = "ask these researchers about web agents"
    agent.draft_csv_template = lambda *a, **k: (
        "quick question on web agents",
        "Hi {{first_name}}, student at {{school}}. We study agents. Thanks {{from_name}}")

    await slack_bot._build_csv_template([run], Collector())
    path = slack_bot._state["draft_template"]
    assert path and Path(path).exists()
    assert run["template"] == path
    assert "We study agents" in Path(path).read_text()
    slack_bot._reset()
    assert not Path(path).exists()


async def test_build_csv_template_falls_back_on_failure():
    """If generation raises, the run keeps its default template (no override)."""
    _restore_mocks(); _reset_state()
    def boom(*a, **k):
        raise ValueError("model said no")
    agent.draft_csv_template = boom
    run = {"email": "armaan.priyadarshan.29@dartmouth.edu", "from_name": "Armaan",
           "template": "templates/brands.md",
           "direct_leads": [{"email": "x@osu.edu", "first_name": "X"}], "n_emails": 1}
    await slack_bot._build_csv_template([run], Collector())
    assert slack_bot._state["draft_template"] is None
    assert run["template"] == "templates/brands.md"


# ---- deterministic CSV parsing (big uploads must not truncate) ---------------

async def test_parse_contacts_csv_maps_and_builds_context():
    _restore_mocks()
    text = ("Name,Affiliation,Paper,Email,Status,Source\n"
            "Xiang Deng,OSU,Mind2Web,deng@osu.edu,valid,arxiv\n"
            "No Email Person,Nowhere,Nada,,not found,site\n")
    leads = agent.parse_contacts_csv(text)
    assert len(leads) == 1  # the row without an email is skipped
    l = leads[0]
    assert l["email"] == "deng@osu.edu"
    assert l["first_name"] == "Xiang" and l["last_name"] == "Deng"
    assert l["company"] == "OSU" and l["domain"] == "osu.edu"
    # Paper folds into context; Status/Source are operational noise and excluded.
    assert "Paper: Mind2Web" in l["context"]
    assert "Status" not in l["context"] and "Source" not in l["context"]


async def test_parse_contacts_csv_no_email_column_returns_empty():
    _restore_mocks()
    leads = agent.parse_contacts_csv("Name,Company\nAda,Acme\nGrace,Beta\n")
    assert leads == []


async def test_senders_in_text():
    assert agent.senders_in_text("send these via Ethan") == ["ethan"]
    assert agent.senders_in_text("through samarjit and ethan") == ["samarjit", "ethan"]
    assert agent.senders_in_text("just email everyone") == []


async def test_build_direct_plan_honors_named_sender():
    _restore_mocks()
    leads = [{"email": "a@b.com", "first_name": "A", "company": "B"}]
    result = agent.build_direct_plan(leads, ["ethan"])
    run = result["runs"][0]
    assert run["sender_key"] == "ethan"
    assert run["direct_leads"] == leads and run["n_emails"] == 1
    assert run["template"] == agent.DEFAULT_TEMPLATE


async def test_present_csv_leads_builds_template_and_previews():
    """A parsed CSV goes straight to a preview built on an audience-fit shared
    template, with no LLM planning call, honoring a sender named in the message."""
    _restore_mocks(); _reset_state()
    agent.draft_csv_template = lambda *a, **k: (
        "quick question on web agents",
        "Hi {{first_name}}, a student at {{school}}. We study web agents. "
        "Thanks {{from_name}}")
    leads = agent.parse_contacts_csv(
        "Name,Affiliation,Paper,Email\nXiang Deng,OSU,Mind2Web,deng@osu.edu\n")
    r = Collector()
    await slack_bot._present_csv_leads(leads, "email these via ethan", r)
    assert slack_bot._state["mode"] == "awaiting_preview"
    assert "Read 1 contact" in r.text
    blob = json.dumps(r.blocks)
    assert "Xiang" in blob and "We study web agents" in blob
    assert slack_bot._state["pending_plan"][0]["sender_key"] == "ethan"


# ---- edit modal: manual edit + Claude refine ---------------------------------

async def test_edit_modal_has_refine_field():
    modal = slack_bot._edit_modal("subj", "body {{first_name}}", "{}")
    ids = [b.get("block_id") for b in modal["blocks"] if b.get("type") == "input"]
    assert ids == ["wiz_subj", "wiz_body", "wiz_refine"]
    refine = next(b for b in modal["blocks"] if b.get("block_id") == "wiz_refine")
    assert refine.get("optional") is True  # refine is optional, edit alone is fine


async def test_refine_template_preserves_slots_and_scrubs_dashes():
    _restore_mocks()
    resp = MagicMock()
    resp.content = [MagicMock(text=json.dumps({
        "subject": "shorter subject",
        "body": "Hi {{first_name}} — quick one. {{school}} {{from_name}}"}))]
    with patch("anthropic.Anthropic") as M:
        M.return_value.messages.create.return_value = resp
        s, b = agent.refine_template(
            "old", "Hi {{first_name}}, long. {{school}} {{from_name}}", "make it shorter")
    assert "—" not in b
    assert all(slot in b for slot in ("{{first_name}}", "{{school}}", "{{from_name}}"))


async def test_refine_template_raises_when_slot_dropped():
    """If the refinement loses a personalization slot, it raises so the caller
    can keep the pre-refine copy rather than send a broken merge."""
    _restore_mocks()
    resp = MagicMock()
    resp.content = [MagicMock(text=json.dumps({
        "subject": "s", "body": "Hi there, no slots at all."}))]
    with patch("anthropic.Anthropic") as M:
        M.return_value.messages.create.return_value = resp
        try:
            agent.refine_template("s", "Hi {{first_name}} {{from_name}}", "rewrite")
            assert False, "should raise when a slot is dropped"
        except ValueError:
            pass


async def test_install_draft_override_repoints_and_cleans_up():
    _restore_mocks(); _reset_state()
    run = dict(_SAMPLE_RUNS[0])
    slack_bot._state["pending_plan"] = [run]
    path = slack_bot._install_draft_override("New subj", "Body {{first_name}}")
    assert run["template"] == path and Path(path).exists()
    assert "Body {{first_name}}" in Path(path).read_text()
    slack_bot._reset()
    assert not Path(path).exists()


async def _run_all():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = failed = 0
    for t in tests:
        try:
            await t()
            print(f"  PASS {t.__name__}")
            passed += 1
        except Exception:
            print(f"  FAIL {t.__name__}")
            traceback.print_exc()
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
    return failed


if __name__ == "__main__":
    sys.exit(1 if asyncio.run(_run_all()) else 0)
