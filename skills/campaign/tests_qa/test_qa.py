"""Tests for the agentic Q&A module (server/qa.py) and its routing helpers.

Network is fully mocked: anthropic.AsyncAnthropic and the tool dispatch / httpx
are patched, so nothing hits Claude, Gmail, or Supabase. Covers the tool-use
loop, the iteration cap, intent classification, account resolution, the
read-only-toolset guard, the stats aggregation math, and the question heuristic.

Run:  toolbox/.venv/bin/python -m pytest skills/campaign/tests_qa -o asyncio_mode=auto
Per the repo rule, this folder is temporary and deleted after merge.
"""
import os
import sys
import types
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
from skills.campaign.server import qa  # noqa: E402
from skills.campaign.server import slack_bot  # noqa: E402


# ---- fake anthropic plumbing -------------------------------------------------

def _text_block(text):
    return types.SimpleNamespace(type="text", text=text)


def _tool_block(name, inp, id="tu_1"):
    return types.SimpleNamespace(type="tool_use", name=name, input=inp, id=id)


def _resp(content, stop_reason):
    return types.SimpleNamespace(content=content, stop_reason=stop_reason)


class _FakeMessages:
    def __init__(self, script):
        self._script = list(script)
        self.calls = 0

    async def create(self, **kwargs):
        self.calls += 1
        if self._script:
            return self._script.pop(0)
        # default: a terminal text answer so a loop always ends
        return _resp([_text_block("done")], "end_turn")


class _FakeAnthropic:
    last = None

    def __init__(self, *a, **k):
        self.messages = _FakeMessages(_FakeAnthropic.script)
        _FakeAnthropic.last = self.messages


def _use_fake(script):
    _FakeAnthropic.script = script
    return patch.object(qa.anthropic, "AsyncAnthropic", _FakeAnthropic)


# ---- the tool-use loop -------------------------------------------------------

async def test_answer_runs_tool_then_returns_text():
    script = [
        _resp([_tool_block("read_doc", {"name": "SKILL"})], "tool_use"),
        _resp([_text_block("Behold, here is the answer.")], "end_turn"),
    ]
    steps = []

    async def on_step(label):
        steps.append(label)

    with _use_fake(script), \
            patch.object(qa, "_run_tool", side_effect=_fake_run_tool) as rt:
        out = await qa.answer("what can you do?", on_step)

    assert out == "Behold, here is the answer."
    assert rt.await_count == 1                 # the one tool was executed
    assert steps and "reading" in steps[0].lower()  # progress was reported


async def _fake_run_tool(name, inp):
    return "TOOL_OUTPUT"


async def test_answer_immediate_text_no_tools():
    script = [_resp([_text_block("No tools needed.")], "end_turn")]
    with _use_fake(script):
        out = await qa.answer("hi")
    assert out == "No tools needed."


async def test_answer_iteration_cap():
    # Model that never stops asking for tools must terminate at MAX_ITERS with a
    # graceful fallback rather than looping forever.
    always_tool = [_resp([_tool_block("read_doc", {"name": "SKILL"})], "tool_use")
                   for _ in range(qa.MAX_ITERS + 5)]
    with _use_fake(always_tool), patch.object(qa, "_run_tool", side_effect=_fake_run_tool):
        out = await qa.answer("loop forever")
    assert _FakeAnthropic.last.calls == qa.MAX_ITERS  # capped
    assert "could not" in out.lower() or out  # returned a string, did not hang


async def test_tool_error_is_fed_back_not_raised():
    async def boom(name, inp):
        raise RuntimeError("kaboom")

    script = [
        _resp([_tool_block("search_inbox", {"query": "x"})], "tool_use"),
        _resp([_text_block("Handled the error.")], "end_turn"),
    ]
    with _use_fake(script), patch.object(qa, "_run_tool", side_effect=boom):
        out = await qa.answer("did anyone reply?")
    assert out == "Handled the error."  # the loop survived a tool blowing up


# ---- intent classification ---------------------------------------------------

async def test_classify_send():
    with _use_fake([_resp([_text_block("send")], "end_turn")]):
        assert await qa.classify_intent("40 to DTC brands via Ethan") == "send"


async def test_classify_question():
    with _use_fake([_resp([_text_block("question")], "end_turn")]):
        assert await qa.classify_intent("what's our reply rate?") == "question"


async def test_classify_defaults_to_question_on_failure():
    class _Boom:
        def __init__(self, *a, **k):
            self.messages = self
        async def create(self, **k):
            raise RuntimeError("api down")
    with patch.object(qa.anthropic, "AsyncAnthropic", _Boom):
        assert await qa.classify_intent("anything") == "question"


# ---- pure helpers ------------------------------------------------------------

def test_resolve_accounts_all():
    emails = qa._resolve_accounts("all")
    assert len(emails) == len(qa.agent.SENDERS)


def test_resolve_accounts_by_name():
    assert qa._resolve_accounts("ethan") == ["ethanpzhou@berkeley.edu"]


def test_resolve_accounts_raw_email():
    assert qa._resolve_accounts("someone@x.com") == ["someone@x.com"]


def test_toolset_is_read_only():
    # Security invariant: the Q&A agent can never send, draft, or delete.
    names = {t["name"] for t in qa._TOOLS}
    assert names == set(qa._DISPATCH)             # schema and dispatch agree
    forbidden = ("send", "draft", "delete", "reply", "write", "create", "update")
    assert not any(any(f in n for f in forbidden) for n in names)


def test_is_question_heuristic():
    assert slack_bot._is_question("how many did we send?")
    assert slack_bot._is_question("did Nathan reply")
    assert slack_bot._is_question("what can you do?")
    assert not slack_bot._is_question("send 40 to DTC brands")
    assert not slack_bot._is_question("")


# ---- stats aggregation -------------------------------------------------------

class _FakeResp:
    def __init__(self, data):
        self.status_code = 200
        self._data = data

    def json(self):
        return self._data


class _FakeHTTP:
    """Returns campaigns then replies in call order, matching _campaign_stats."""
    def __init__(self, *a, **k):
        self._queue = [
            _FakeResp([{"sent_count": 100}, {"sent_count": 50}]),   # campaigns
            _FakeResp([{"sentiment": "positive"}, {"sentiment": "positive"},
                       {"sentiment": "neutral"}]),                   # replies
        ]

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def get(self, *a, **k):
        return self._queue.pop(0)


async def test_campaign_stats_math():
    with patch.object(qa.httpx, "AsyncClient", _FakeHTTP):
        import json
        out = json.loads(await qa._campaign_stats(7))
    assert out["sent"] == 150
    assert out["replies"] == 3
    assert out["reply_rate_pct"] == 2.0          # 3 / 150 = 2.0%
    assert out["sentiment"]["positive"] == 2
