"""Tests for the 'how many sent today' wizard stat (server/qa.py).

Network is fully mocked: httpx.AsyncClient is patched, so nothing hits Supabase.
Covers the date-boundary math (a late-yesterday send must NOT count), the
Content-Range parser, the count + remaining shaping, the status-column fallback,
and the read-failure path.

Run:  toolbox/.venv/bin/python -m pytest skills/campaign/tests_stats -o asyncio_mode=auto
Per the repo rule, this folder is temporary and deleted after merge.
"""
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

_DUMMY = {
    "ANTHROPIC_API_KEY": "x", "GOOGLE_OAUTH_CLIENT_ID": "x",
    "GOOGLE_OAUTH_CLIENT_SECRET": "x", "TOOLBOX_TOKEN_HUNTER": "x",
    "SUPABASE_URL": "https://supa.test", "SUPABASE_SECRET_KEY": "svc",
}
for k, v in _DUMMY.items():
    os.environ.setdefault(k, v)

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "toolbox" / "src"))
from skills.campaign.server import qa  # noqa: E402


# ---- date-boundary math (pure) ----------------------------------------------

def test_local_midnight_utc_is_pacific_midnight():
    # 2026-06-29 10:00 PDT (= 17:00 UTC). Pacific (UTC-7 in summer) midnight that
    # day is 2026-06-29 00:00 PDT == 2026-06-29 07:00 UTC.
    now = datetime(2026, 6, 29, 17, 0, tzinfo=timezone.utc)
    with patch.dict(os.environ, {"SLACK_SCHEDULE_TZ": "America/Los_Angeles"}):
        cutoff = qa._local_midnight_utc(now=now)
    assert cutoff == datetime(2026, 6, 29, 7, 0, tzinfo=timezone.utc)


def test_boundary_excludes_late_yesterday_includes_early_today():
    now = datetime(2026, 6, 29, 17, 0, tzinfo=timezone.utc)
    with patch.dict(os.environ, {"SLACK_SCHEDULE_TZ": "America/Los_Angeles"}):
        cutoff = qa._local_midnight_utc(now=now)
    late_yesterday = datetime(2026, 6, 29, 6, 0, tzinfo=timezone.utc)   # 23:00 PDT y'day
    early_today = datetime(2026, 6, 29, 7, 1, tzinfo=timezone.utc)      # 00:01 PDT today
    assert late_yesterday < cutoff      # must NOT count toward today
    assert early_today >= cutoff        # must count


# ---- Content-Range parser (pure) --------------------------------------------

def test_parse_count():
    assert qa._parse_count("0-0/1234") == 1234
    assert qa._parse_count("*/0") == 0
    assert qa._parse_count("0-24/25") == 25
    assert qa._parse_count(None) is None
    assert qa._parse_count("") is None
    assert qa._parse_count("0-0/*") is None     # unknown total


# ---- count + shaping (httpx mocked) -----------------------------------------

class _Resp:
    def __init__(self, status_code, content_range=None):
        self.status_code = status_code
        self.headers = {"content-range": content_range} if content_range else {}


def _fake_http(script):
    """A patched AsyncClient class whose .get() pops responses from a shared
    list, so the status-column fallback (which opens a second client) keeps
    walking the same script."""
    class _Fake:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def get(self, *a, **k):
            return script.pop(0)

    return _Fake


async def test_sent_today_counts_and_computes_remaining():
    script = [_Resp(200, "0-0/47")]
    with patch.dict(os.environ, {"SLACK_DAILY_TARGET": "2000"}), \
            patch.object(qa.httpx, "AsyncClient", _fake_http(script)):
        out = json.loads(await qa._sent_today())
    assert out["sent"] == 47
    assert out["target"] == 2000
    assert out["remaining"] == 1953
    assert not script  # one query, no fallback


async def test_sent_today_remaining_never_negative():
    script = [_Resp(200, "0-0/2500")]
    with patch.dict(os.environ, {"SLACK_DAILY_TARGET": "2000"}), \
            patch.object(qa.httpx, "AsyncClient", _fake_http(script)):
        out = json.loads(await qa._sent_today())
    assert out["sent"] == 2500
    assert out["remaining"] == 0


async def test_status_column_missing_falls_back_to_counting_all():
    # First (status=eq.sent) query 400s -> retry without the filter succeeds.
    script = [_Resp(400), _Resp(200, "0-0/12")]
    with patch.object(qa.httpx, "AsyncClient", _fake_http(script)):
        out = json.loads(await qa._sent_today())
    assert out["sent"] == 12
    assert not script  # both the filtered attempt and the fallback ran


async def test_read_failure_returns_error():
    script = [_Resp(500), _Resp(500)]  # filtered + fallback both fail
    with patch.object(qa.httpx, "AsyncClient", _fake_http(script)):
        out = json.loads(await qa._sent_today())
    assert "error" in out
    assert "sent" not in out
