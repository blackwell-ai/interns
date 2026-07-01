"""Tests for reply persistence into the Supabase replies table.

The morning triage now runs reply_triage_probe with --persist-replies so every
detected inbound reply lands in the `replies` table (dedup on message_id), which
is what reply-rate/sentiment stats read. Before this, ingestion only ran via a
local gog-auth cron that never executed on Railway, so the table was empty.

Covered: only real replies persist (needs message_id + a known sender), the
insert-vs-duplicate count, the no-token no-op, and the epoch->ISO helper. All
dependencies are mocked; no Gmail, no network. Delete once confirmed in prod.

Run:
  cd /Users/shamitd/interns
  PYTHONPATH="$PWD:$PWD/toolbox/src" toolbox/.venv/bin/pytest \
    skills/campaign/tests_reply_ingest/test_reply_persist.py -v
"""
from __future__ import annotations

import pytest

from skills.campaign import reply_triage_probe as probe
from skills.campaign import reply_scan

pytestmark = pytest.mark.asyncio


def _row(mid="m1", who="prospect@acme.co", snippet="sounds great, let's talk"):
    return {"reply_mid": mid, "who": who, "reply_at": "2026-06-20T00:00:00+00:00",
            "subject": "Re: hi", "snippet": snippet, "rendered": "US: ...\nTHEM: ..."}


def _mock_deps(monkeypatch, *, inserted_mids):
    """Mock classify_sentiment (no LLM) and upsert_reply (no DB). upsert returns
    True only for message_ids in `inserted_mids`, False otherwise (duplicate)."""
    monkeypatch.setattr(reply_scan, "classify_sentiment", lambda body: "positive")
    calls = []

    async def fake_upsert(client, token, *, recipient, received_at, subject,
                          snippet, sentiment, run_id, variant, message_id):
        calls.append({"recipient": recipient, "message_id": message_id,
                      "sentiment": sentiment, "received_at": received_at})
        return message_id in inserted_mids

    monkeypatch.setattr(reply_scan, "upsert_reply", fake_upsert)
    return calls


async def test_persists_only_real_replies(monkeypatch):
    monkeypatch.setenv("TOOLBOX_SESSION_TOKEN", "svc")
    rows = [
        _row(mid="m1", who="a@x.co"),
        _row(mid="", who="b@x.co"),           # no message id -> skip
        _row(mid="m3", who="unknown"),        # unknown sender -> skip
        _row(mid="m4", who="d@x.co"),
    ]
    calls = _mock_deps(monkeypatch, inserted_mids={"m1", "m4"})
    inserted = await probe._persist_replies(rows)
    assert inserted == 2                       # only the two valid, non-duplicate rows
    persisted_mids = {c["message_id"] for c in calls}
    assert persisted_mids == {"m1", "m4"}      # skipped the blank + unknown
    assert all(c["sentiment"] == "positive" for c in calls)


async def test_duplicates_not_counted(monkeypatch):
    monkeypatch.setenv("TOOLBOX_SESSION_TOKEN", "svc")
    rows = [_row(mid="m1"), _row(mid="m2")]
    _mock_deps(monkeypatch, inserted_mids={"m1"})   # m2 already in table -> False
    inserted = await probe._persist_replies(rows)
    assert inserted == 1                        # duplicate m2 does not inflate the count


async def test_no_token_is_noop(monkeypatch):
    monkeypatch.delenv("TOOLBOX_SESSION_TOKEN", raising=False)
    monkeypatch.delenv("SUPABASE_SECRET_KEY", raising=False)
    called = {"n": 0}

    async def should_not_run(*a, **k):
        called["n"] += 1
        return True
    monkeypatch.setattr(reply_scan, "upsert_reply", should_not_run)
    monkeypatch.setattr(reply_scan, "classify_sentiment", lambda b: "neutral")
    inserted = await probe._persist_replies([_row()])
    assert inserted == 0 and called["n"] == 0   # no token -> no writes attempted


async def test_received_iso_from_epoch_ms():
    assert probe._received_iso({"internalDate": "1719800000000"}).startswith("2024-07-01")
    assert probe._received_iso(None) == ""
    assert probe._received_iso({"internalDate": "not-a-number"}) == ""


async def test_falls_back_to_now_when_no_reply_at(monkeypatch):
    monkeypatch.setenv("TOOLBOX_SESSION_TOKEN", "svc")
    calls = _mock_deps(monkeypatch, inserted_mids={"m1"})
    row = _row(mid="m1")
    row["reply_at"] = ""                        # missing timestamp
    await probe._persist_replies([row])
    assert calls[0]["received_at"]              # a non-empty now() fallback was used


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-v"]))
