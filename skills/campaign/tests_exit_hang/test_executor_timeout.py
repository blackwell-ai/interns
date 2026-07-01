"""Regression tests for the sender-queue freeze (run.py hung after sending).

Reproduces the production incident: a run.py subprocess prints its full summary
("Result : N sent") but never exits, because a stranded, uncancellable look-ahead
worker thread holds the interpreter open. Before the fix, executor.run_campaign
read the subprocess's stdout with no timeout, so it blocked forever and every
later sender stayed queued. The fix gives the read loop an inactivity timeout:
once the result is reported, a healthy process exits within seconds, so anything
silent past _DONE_GRACE_S is killed and the queue advances.

Network/auth are fully faked; no subprocess is actually spawned. Covers:
  1. hung-after-summary  → killed during grace, queue advances, sends counted
  2. healthy EOF         → returns normally, no false-positive kill
  3. stalled mid-source  → killed during the longer active window, reported

Run:  python -m pytest skills/campaign/tests_exit_hang -q
Per the repo rule, this folder is temporary and deleted after merge.
"""
import asyncio
import os

import pytest

from skills.campaign.wizard import executor


# ---- Fakes -------------------------------------------------------------

class FakeStdout:
    """Yields queued byte-lines, then either EOF (b"") or hangs until cancelled."""

    def __init__(self, lines, then_eof):
        self._lines = list(lines)
        self._then_eof = then_eof

    async def readline(self):
        if self._lines:
            return self._lines.pop(0)
        if self._then_eof:
            return b""              # process closed stdout — clean exit
        await asyncio.sleep(3600)   # never-EOF hang; wait_for cancels this


class FakeProc:
    """Minimal stand-in for an asyncio subprocess."""

    def __init__(self, lines, then_eof):
        self.stdout = FakeStdout(lines, then_eof)
        # A process that hit EOF has already exited 0; a hanging one has no code
        # until we kill it.
        self.returncode = 0 if then_eof else None
        self._killed = asyncio.Event()

    def kill(self):
        self.returncode = -9
        self._killed.set()

    async def wait(self):
        if self.returncode is None:
            await self._killed.wait()
        return self.returncode


def _item():
    return {
        "n_emails": 15, "sender_key": "armaan", "from_name": "Armaan",
        "icp_desc": "DTC brands", "icp_label": "DTC brands",
        "email": "armaan@example.com", "template": "templates/brands.md", "cc": "",
    }


def _patch_common(monkeypatch, proc):
    monkeypatch.delenv("WIZARD_TEST_MODE", raising=False)
    monkeypatch.setattr(executor.gmail_auth, "get_access_token", lambda email: "tok")
    monkeypatch.setattr(executor, "_get_supabase_session_token", lambda: "sess")

    async def fake_create(*a, **k):
        return proc
    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_create)


async def _run(monkeypatch, proc):
    updates = []

    async def send_update(text):
        updates.append(text)

    _patch_common(monkeypatch, proc)
    # Bound the test: if the fix regressed, run_campaign would block forever, so
    # wait_for converts that into a clear failure instead of a hung suite.
    result = await asyncio.wait_for(
        executor.run_campaign(_item(), send_update), timeout=10
    )
    return result, updates


SUMMARY = [
    b"34/34 contacts (100%)\n",
    b"Drafted : 15 emails\n",
    b"Result : 15 sent  0 skipped\n",
    b"Time   : 0.3 min (18s)\n",
]


@pytest.mark.asyncio
async def test_hung_after_summary_is_killed_and_queue_advances(monkeypatch):
    monkeypatch.setattr(executor, "_DONE_GRACE_S", 0.3)
    proc = FakeProc(SUMMARY, then_eof=False)  # prints summary, then hangs

    loop = asyncio.get_event_loop()
    t0 = loop.time()
    result, updates = await _run(monkeypatch, proc)
    elapsed = loop.time() - t0

    # It returned (did not freeze) shortly after the grace window, not after 3600s.
    assert elapsed < 5, f"run_campaign took {elapsed:.1f}s — likely still blocking"
    assert "15 sent" in result
    assert "hung exit" in result            # status records the forced kill
    assert any("hung on exit" in u for u in updates)
    assert proc.returncode == -9            # we actually killed it


@pytest.mark.asyncio
async def test_healthy_exit_is_not_killed(monkeypatch):
    monkeypatch.setattr(executor, "_DONE_GRACE_S", 0.3)
    proc = FakeProc(SUMMARY, then_eof=True)  # prints summary, then clean EOF

    result, updates = await _run(monkeypatch, proc)

    assert "15 sent [OK]" in result
    assert any(":mage:" in u and "15 sent" in u for u in updates)
    assert not any("hung" in u or "stalled" in u for u in updates)


@pytest.mark.asyncio
async def test_stall_mid_sourcing_is_killed(monkeypatch):
    # No summary line ever arrives; the run goes silent during sourcing.
    monkeypatch.setattr(executor, "_ACTIVE_GAP_S", 0.3)
    proc = FakeProc([b"10/34 contacts (29%)\n"], then_eof=False)

    result, updates = await _run(monkeypatch, proc)

    assert "0 sent" in result               # nothing was reported sent
    assert "exit -9" in result
    assert any("stalled with no output" in u for u in updates)
