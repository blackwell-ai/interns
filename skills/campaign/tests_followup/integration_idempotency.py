#!/usr/bin/env python3
"""Live idempotency proof for the morning follow-up, on a controlled address only.

Sends REAL email, but only to a +alias of our own sender mailbox (delivered back to
us), never a prospect, and trashes everything it creates at the end. It proves the
two things that matter for autonomy:

  1. The send path works end to end (a due out-of-office bump actually goes out,
     anchored to our pitch and quoting it, in the pitch thread).
  2. We do not resend: once the bump is sent, the time-relative dedup
     (`already_followed_up`) flips, so a second pass skips that person.

The out-of-office reference timestamp is anchored to the pitch's own server time
(pitch + 1 ms), so the proof is independent of the local clock and needs no second
mailbox. This drives the real send + dedup machinery directly with a hand-built
row, which is the part that must hold against live Gmail state.

Run:  python3 skills/campaign/tests_followup/integration_idempotency.py
"""
from __future__ import annotations

import asyncio
import sys
import time
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "toolbox" / "src"))

import httpx  # noqa: E402

from skills.campaign import reply_followup as rf  # noqa: E402
from skills.campaign import reply_triage_probe as probe  # noqa: E402
from toolbox.primitives.gmail import lib as gmail_lib  # noqa: E402

SENDER = "ethanpzhou@berkeley.edu"
STAMP = int(time.time())
PROSPECT = f"ethanpzhou+fuptest{STAMP}@berkeley.edu"   # +alias, delivered to us
MARK = f"FUPTEST-{STAMP}"


def _client(token):
    return httpx.AsyncClient(headers={"Authorization": f"Bearer {token}"}, timeout=60)


async def _send(token, to, subject, body, thread_id="", reply_to="", quote=False):
    spec = {"to": to, "subject": subject, "body_html": f"<p>{body}</p>",
            "thread_id": thread_id, "reply_to_message_id": reply_to, "quote": quote}
    ok, draft_id = await rf.create_draft_api(token, spec, dry_run=False)
    assert ok, f"draft create failed: {draft_id}"
    ok2, sent_id = await rf.send_draft_api(token, draft_id)
    assert ok2, f"send failed: {sent_id}"
    return sent_id


async def _internal_date(g, mid):
    m = await gmail_lib.get_message(g, mid, fmt="metadata")
    return int(m.get("internalDate") or 0), m.get("threadId", "")


async def _already_followed_up(g, prospect, ref_date):
    """Re-derive the dedup signal exactly as collect_rows does."""
    sent_ids = await probe.list_all(g, f"in:sent to:{prospect}", cap=10)
    for sid in sent_ids:
        d, _t = await _internal_date(g, sid)
        if d > ref_date:
            return True
    return False


async def _trash_all(token):
    n = 0
    async with _client(token) as g:
        ids = await probe.list_all(g, f'"{MARK}"', cap=80)
        for mid in ids:
            r = await g.post(f"{gmail_lib.api_base()}/messages/{mid}/trash")
            if r.status_code == 200:
                n += 1
    print(f"  cleaned {n} message(s)")


async def main() -> int:
    token = rf.gog_auth.get_access_token(SENDER)
    failures = []

    def check(name, cond):
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
        if not cond:
            failures.append(name)

    try:
        print(f"Marker: {MARK}\n1. Plant a pitch to a controlled +alias")
        pitch_subject = f"Berkeley student question {MARK}"
        await _send(token, PROSPECT, pitch_subject,
                    f"I understand your time is important. Our original pitch. {MARK}")
        await asyncio.sleep(4)

        async with _client(token) as g:
            sent = await probe.list_all(g, f"in:sent to:{PROSPECT}", cap=5)
            check("exactly one prior send to this address (the pitch)", len(sent) == 1)
            pitch_id = sent[-1]
            pitch_date, pitch_thread = await _internal_date(g, pitch_id)
            # The OOO reference: just after our pitch, clock-independent.
            ref_date = pitch_date + 1

            print("2. First pass: dedup says not-yet-followed-up -> SEND")
            before = await _already_followed_up(g, PROSPECT, ref_date)
            check("already_followed_up is False before the bump", before is False)
            row = {"tid": "synthetic", "owner": SENDER, "who": PROSPECT,
                   "prospect_name": "Alex", "subject": pitch_subject,
                   "latest_inbound_id": "", "pitch_msg_id": pitch_id,
                   "pitch_thread_id": pitch_thread, "action": "none",
                   "confidence": "clear", "reroute_to": "", "category": "ooo",
                   "ooo_until": "2026-06-20", "already_followed_up": before}
            actions = rf.plan_morning([row], {}, {}, set(), date(2026, 6, 26))
            check("plan_morning chose send_ooo", actions[0]["action"] == "send_ooo")

            spec = actions[0]["spec"]
            ok, did = await rf.create_draft_api(token, spec, dry_run=False)
            ok2, bump_id = await rf.send_draft_api(token, did)
            check("the bump was sent", ok and ok2)

        await asyncio.sleep(4)
        print("3. Bump landed, in the pitch thread, quoting the pitch")
        async with _client(token) as g:
            bm = await gmail_lib.get_message(g, bump_id, fmt="full")
            bthread = bm.get("threadId", "")
            bbody = gmail_lib.extract_text_parts(bm.get("payload") or {})
            check("bump is in the pitch thread", bthread == pitch_thread)
            check("bump quotes our pitch", "I understand your time is important" in bbody)
            check("bump addressed to the prospect",
                  PROSPECT.split("@")[0] in gmail_lib.header(bm, "To"))

            print("4. Second pass: dedup flips -> SKIP (no resend)")
            after = await _already_followed_up(g, PROSPECT, ref_date)
            check("already_followed_up is True after the bump", after is True)
            row2 = dict(row, already_followed_up=after)
            actions2 = rf.plan_morning([row2], {}, {}, set(), date(2026, 6, 26))
            check("plan_morning now chose skip", actions2[0]["action"] == "skip")
            check("skip reason names the OOO follow-up",
                  "already followed up" in actions2[0].get("reason", ""))

    finally:
        print("\nCleanup:")
        await _trash_all(token)

    print(f"\n{'ALL PASSED' if not failures else 'FAILURES: ' + ', '.join(failures)}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
