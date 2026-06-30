"""Tests for reply_followup.py (the redirect + OOO draft stager).

Pure logic only: parsing, naming, draft-body rendering, the plan_drafts decision
machine, and idempotency. No Gmail, no gog, no network. The orchestration
(collect_rows / existing_drafts / create_draft) is thin I/O over the probe and
gog and is exercised by hand against a real account, not here.

Run without pytest:  python skills/campaign/tests_followup/test_reply_followup.py
Per the repo rule, this folder is temporary and deleted after merge.
"""
import base64
import os
import sys
import traceback
from datetime import date
from pathlib import Path

# The probe import chain needs these to exist; dummy values are fine offline.
for k in ("ANTHROPIC_API_KEY", "SUPABASE_URL", "SUPABASE_SECRET_KEY",
          "TOOLBOX_TOKEN_HUNTER"):
    os.environ.setdefault(k, "x")

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "toolbox" / "src"))
from skills.campaign import reply_followup as rf  # noqa: E402


# ---- parse_contact ---------------------------------------------------------

def test_parse_contact_name_and_email():
    name, email = rf.parse_contact("Katie Smith <katie.s@acme.com>")
    assert name == "Katie Smith"
    assert email == "katie.s@acme.com"


def test_parse_contact_email_only():
    name, email = rf.parse_contact("katie.s@acme.com")
    assert email == "katie.s@acme.com"
    assert name == ""


def test_parse_contact_name_only():
    name, email = rf.parse_contact("Katie in procurement")
    assert email == ""
    assert "Katie" in name


def test_parse_contact_empty():
    assert rf.parse_contact("") == ("", "")
    assert rf.parse_contact(None) == ("", "")


def test_parse_contact_email_uppercased_is_normalised():
    _name, email = rf.parse_contact("Reach KATIE.S@ACME.COM")
    assert email == "katie.s@acme.com"


# ---- first_name_from -------------------------------------------------------

def test_first_name_from_display():
    assert rf.first_name_from("Katie Smith") == "Katie"


def test_first_name_from_display_with_angle_addr():
    assert rf.first_name_from("Katie Smith <k@x.com>") == "Katie"


def test_first_name_from_bare_email():
    assert rf.first_name_from("katie.s@acme.com") == "Katie"


def test_first_name_from_empty_is_safe():
    assert rf.first_name_from("") == "there"
    assert rf.first_name_from(None) == "there"


# ---- owner name / school ---------------------------------------------------

def test_owner_name_known():
    assert rf.owner_name("ethanpzhou@berkeley.edu") == "Ethan"


def test_owner_name_unknown_falls_back_to_local():
    assert rf.owner_name("jane.doe@somewhere.com") == "Jane"


def test_owner_school_known():
    school, others = rf.owner_school("ethanpzhou@berkeley.edu")
    assert school == "Berkeley"
    assert "Stanford" in others and "Dartmouth" in others and "Berkeley" not in others


def test_owner_school_dartmouth_by_domain():
    assert rf.owner_school("someone@dartmouth.edu")[0] == "Dartmouth"


# ---- draft body rendering --------------------------------------------------

def test_referral_body_names_referrer_and_new_contact():
    subject, body = rf.render_referral("Katie", "ethanpzhou@berkeley.edu", "Dalton")
    assert subject  # redirect is a fresh email, needs a subject
    assert "Hi Katie" in body
    assert "Dalton pointed me your way" in body
    assert "Berkeley" in body
    assert "Thanks, Ethan" in body


def test_referral_body_handles_missing_referrer():
    _subject, body = rf.render_referral("Katie", "ethanpzhou@berkeley.edu", "")
    assert "colleague of yours" in body


def test_ask_email_is_in_thread_no_subject():
    subject, body = rf.render_ask_email("Dalton", "Katie", "armaan.priyadarshan.29@dartmouth.edu")
    assert subject == ""  # threads onto the existing conversation
    assert "Hi Dalton" in body
    assert "Katie" in body
    assert "best email" in body
    assert "Thanks, Armaan" in body


def test_ooo_bump_is_in_thread_no_subject():
    subject, body = rf.render_ooo_bump("Jenna", "samarjit.deshmukh.29@dartmouth.edu")
    assert subject == ""
    assert "Hi Jenna" in body
    assert "Thanks, Samarjit" in body


def test_no_draft_body_has_em_or_en_dash():
    bodies = [
        rf.render_referral("Katie", "ethanpzhou@berkeley.edu", "Dalton")[1],
        rf.render_ask_email("Dalton", "Katie", "armaan.priyadarshan.29@dartmouth.edu")[1],
        rf.render_ooo_bump("Jenna", "samarjit.deshmukh.29@dartmouth.edu")[1],
    ]
    for b in bodies:
        assert "—" not in b and "–" not in b, "house style: no em/en dashes"


# ---- latest_inbound_id -----------------------------------------------------

def _msg(mid, frm):
    return {"id": mid, "payload": {"headers": [{"name": "From", "value": frm}]}}


def test_latest_inbound_id_picks_last_them():
    ours = {"armaan.priyadarshan.29@dartmouth.edu"}
    msgs = [
        _msg("m1", "armaan.priyadarshan.29@dartmouth.edu"),
        _msg("m2", "prospect@acme.com"),
        _msg("m3", "armaan.priyadarshan.29@dartmouth.edu"),
        _msg("m4", "prospect@acme.com"),
    ]
    assert rf.latest_inbound_id(msgs, ours) == "m4"


def test_latest_inbound_id_none_when_all_ours():
    ours = {"armaan.priyadarshan.29@dartmouth.edu"}
    msgs = [_msg("m1", "armaan.priyadarshan.29@dartmouth.edu")]
    assert rf.latest_inbound_id(msgs, ours) == ""


# ---- plan_drafts: the decision machine -------------------------------------

def _row(**kw):
    base = {"tid": "T1", "owner": "ethanpzhou@berkeley.edu", "who": "dalton@acme.com",
            "prospect_name": "Dalton Reed", "subject": "Re: hi",
            "latest_inbound_id": "M1", "pitch_msg_id": "PITCH1",
            "pitch_thread_id": "PT1", "action": "none", "confidence": "clear",
            "reroute_to": "", "category": "genuine", "ooo_until": ""}
    base.update(kw)
    return base


def test_plan_redirect_with_email_drafts_to_new_contact():
    rows = [_row(action="reroute", reroute_to="Katie Smith <katie.s@acme.com>")]
    specs, skipped = rf.plan_drafts(rows, set(), set())
    assert len(specs) == 1 and not skipped
    s = specs[0]
    assert s["kind"] == "redirect"
    assert s["to"] == "katie.s@acme.com"
    assert s["subject"]            # fresh email
    assert s["thread_id"] == ""    # not in the old thread
    assert "Katie" in s["body_html"]


def test_plan_redirect_name_only_asks_original_sender_in_thread():
    rows = [_row(action="reroute", reroute_to="Katie in procurement")]
    specs, skipped = rf.plan_drafts(rows, set(), set())
    assert len(specs) == 1 and not skipped
    s = specs[0]
    assert s["kind"] == "ask_email"
    assert s["to"] == "dalton@acme.com"   # reply addressed to the original sender
    assert s["thread_id"] == "T1"
    assert s["reply_to_message_id"] == "M1"
    assert "Dalton" in s["body_html"]  # greets the original sender


def test_plan_ooo_drafts_in_thread_bump_with_date_note():
    rows = [_row(category="ooo", ooo_until="2026-07-03")]
    specs, _ = rf.plan_drafts(rows, set(), set())
    assert len(specs) == 1
    s = specs[0]
    assert s["kind"] == "ooo"
    # Anchored to our SENT pitch thread (the auto-reply thread is detached), quoting
    # the pitch so context travels inline.
    assert s["thread_id"] == "PT1"
    assert s["reply_to_message_id"] == "PITCH1"
    assert s["quote"] is True
    assert s["to"] == "dalton@acme.com"   # bump addressed to the prospect
    assert "2026-07-03" in s["note"]


def test_plan_ooo_falls_back_to_autoreply_when_no_sent_pitch():
    # No pitch on record: bump the auto-reply thread, and do not quote the robot.
    rows = [_row(category="ooo", pitch_msg_id="", pitch_thread_id="")]
    specs, _ = rf.plan_drafts(rows, set(), set())
    assert specs[0]["thread_id"] == "T1"            # auto-reply thread fallback
    assert specs[0]["reply_to_message_id"] == "M1"  # latest inbound fallback
    assert specs[0]["quote"] is False


def test_plan_ask_email_quotes_the_referral():
    rows = [_row(action="reroute", reroute_to="Katie in procurement")]
    specs, _ = rf.plan_drafts(rows, set(), set())
    assert specs[0]["reply_to_message_id"] == "M1"  # their referral message
    assert specs[0]["quote"] is True


def test_plan_redirect_does_not_quote():
    rows = [_row(action="reroute", reroute_to="katie.s@acme.com")]
    specs, _ = rf.plan_drafts(rows, set(), set())
    assert not specs[0].get("quote")  # fresh cold email, nothing to quote


def test_plan_redirect_skipped_when_already_contacted():
    # Same ledger check the campaign runs: do not cold-touch an existing contact.
    rows = [_row(action="reroute", reroute_to="Katie <katie.s@acme.com>")]
    specs, skipped = rf.plan_drafts(rows, set(), set(), contacted={"katie.s@acme.com"})
    assert not specs
    assert len(skipped) == 1 and "already contacted" in skipped[0]["skip"]


def test_plan_redirect_contacted_check_is_case_insensitive():
    rows = [_row(action="reroute", reroute_to="KATIE.S@ACME.COM")]
    specs, skipped = rf.plan_drafts(rows, set(), set(), contacted={"katie.s@acme.com"})
    assert not specs and len(skipped) == 1


def test_plan_redirect_proceeds_when_not_contacted():
    rows = [_row(action="reroute", reroute_to="katie.s@acme.com")]
    specs, _ = rf.plan_drafts(rows, set(), set(), contacted={"someone.else@acme.com"})
    assert len(specs) == 1 and specs[0]["to"] == "katie.s@acme.com"


def test_plan_ooo_not_affected_by_contacted_set():
    # The OOO prospect is in the ledger by definition (we emailed them); the
    # contacted check must not suppress their bump.
    rows = [_row(category="ooo")]
    specs, _ = rf.plan_drafts(rows, set(), set(), contacted={"dalton@acme.com"})
    assert len(specs) == 1 and specs[0]["kind"] == "ooo"


def test_plan_ooo_skipped_when_already_followed_up():
    # The time-relative signal: we already sent something after this OOO.
    rows = [_row(category="ooo", already_followed_up=True)]
    specs, skipped = rf.plan_drafts(rows, set(), set())
    assert not specs
    assert len(skipped) == 1 and "already followed up" in skipped[0]["skip"]


def test_plan_ooo_bumps_when_not_yet_followed_up():
    rows = [_row(category="ooo", already_followed_up=False)]
    specs, _ = rf.plan_drafts(rows, set(), set())
    assert len(specs) == 1 and specs[0]["kind"] == "ooo"


def test_plan_redirect_skipped_when_new_contact_already_emailed():
    # in:sent signal: we already emailed the new contact (ledger may not know).
    rows = [_row(action="reroute", reroute_to="katie.s@acme.com",
                 new_contact_emailed=True)]
    specs, skipped = rf.plan_drafts(rows, set(), set())
    assert not specs
    assert len(skipped) == 1 and "already emailed" in skipped[0]["skip"]


def test_plan_redirect_proceeds_when_new_contact_not_emailed():
    rows = [_row(action="reroute", reroute_to="katie.s@acme.com",
                 new_contact_emailed=False)]
    specs, _ = rf.plan_drafts(rows, set(), set())
    assert len(specs) == 1 and specs[0]["to"] == "katie.s@acme.com"


def test_plan_skips_borderline_handled_upstream():
    # collect_rows filters borderline reroutes; plan_drafts trusts its input, so a
    # row with no actionable shape produces nothing.
    rows = [_row(action="none", category="genuine")]
    specs, skipped = rf.plan_drafts(rows, set(), set())
    assert not specs and not skipped


def test_plan_idempotent_on_existing_thread():
    # OOO dedupes on the pitch thread it bumps, not the auto-reply thread.
    rows = [_row(category="ooo")]
    specs, skipped = rf.plan_drafts(rows, {"PT1"}, set())
    assert not specs
    assert len(skipped) == 1 and "already" in skipped[0]["skip"]


def test_plan_idempotent_on_existing_recipient():
    rows = [_row(action="reroute", reroute_to="katie.s@acme.com")]
    specs, skipped = rf.plan_drafts(rows, set(), {"katie.s@acme.com"})
    assert not specs
    assert len(skipped) == 1


def test_plan_dedupes_two_redirects_to_same_email_in_one_run():
    rows = [
        _row(tid="T1", action="reroute", reroute_to="katie.s@acme.com"),
        _row(tid="T2", action="reroute", reroute_to="Katie <katie.s@acme.com>"),
    ]
    specs, skipped = rf.plan_drafts(rows, set(), set())
    assert len(specs) == 1      # second is a dup recipient
    assert len(skipped) == 1


def test_plan_dedupes_two_ooo_in_same_thread_in_one_run():
    rows = [_row(tid="T9", category="ooo"), _row(tid="T9", category="ooo")]
    specs, skipped = rf.plan_drafts(rows, set(), set())
    assert len(specs) == 1
    assert len(skipped) == 1


def test_plan_mixed_batch_routes_each_correctly():
    rows = [
        _row(tid="A", action="reroute", reroute_to="x@new.com"),
        _row(tid="B", action="reroute", reroute_to="Bob with no email"),
        _row(tid="C", category="ooo", ooo_until="next week"),
    ]
    specs, _ = rf.plan_drafts(rows, set(), set())
    kinds = sorted(s["kind"] for s in specs)
    assert kinds == ["ask_email", "ooo", "redirect"]


def test_inthread_drafts_always_carry_a_recipient():
    # gog does not auto-fill To on a reply, so every staged draft must name one or
    # the sent message would go nowhere.
    rows = [
        _row(tid="A", action="reroute", reroute_to="x@new.com"),
        _row(tid="B", action="reroute", reroute_to="Bob no email"),
        _row(tid="C", category="ooo"),
    ]
    specs, _ = rf.plan_drafts(rows, set(), set())
    for s in specs:
        assert s["to"], f"{s['kind']} draft has no recipient"


def test_plan_uses_correct_owner_per_row():
    rows = [_row(owner="samarjit.deshmukh.29@dartmouth.edu", category="ooo")]
    specs, _ = rf.plan_drafts(rows, set(), set())
    assert specs[0]["owner"] == "samarjit.deshmukh.29@dartmouth.edu"
    assert "Samarjit" in specs[0]["body_html"]


# ---- parse_followup_date ---------------------------------------------------

_TODAY = date(2026, 6, 26)


def test_parse_date_iso():
    assert rf.parse_followup_date("2026-07-03", _TODAY) == date(2026, 7, 3)


def test_parse_date_iso_with_time_suffix():
    assert rf.parse_followup_date("2026-07-03T09:00:00", _TODAY) == date(2026, 7, 3)


def test_parse_date_empty_is_none():
    assert rf.parse_followup_date("", _TODAY) is None
    assert rf.parse_followup_date(None, _TODAY) is None


def test_parse_date_vague_phrase_is_none():
    assert rf.parse_followup_date("next week", _TODAY) is None
    assert rf.parse_followup_date("Thursday", _TODAY) is None


# ---- plan_morning: the autonomous policy -----------------------------------

def test_morning_ooo_due_past_date_sends():
    rows = [_row(category="ooo", ooo_until="2026-06-22")]  # before today
    acts = rf.plan_morning(rows, {}, {}, set(), _TODAY)
    assert len(acts) == 1 and acts[0]["action"] == "send_ooo"


def test_morning_ooo_no_date_sends_now():
    rows = [_row(category="ooo", ooo_until="")]
    acts = rf.plan_morning(rows, {}, {}, set(), _TODAY)
    assert acts[0]["action"] == "send_ooo"


def test_morning_ooo_future_date_schedules():
    rows = [_row(category="ooo", ooo_until="2026-07-10")]
    acts = rf.plan_morning(rows, {}, {}, set(), _TODAY)
    assert acts[0]["action"] == "schedule_ooo"
    assert acts[0]["send_after"] == date(2026, 7, 10)


def test_morning_ooo_already_followed_up_skips():
    rows = [_row(category="ooo", already_followed_up=True)]
    acts = rf.plan_morning(rows, {}, {}, set(), _TODAY)
    assert acts[0]["action"] == "skip"


def test_morning_ooo_due_reuses_existing_held_draft():
    # A future bump staged earlier, now due: send the held draft, do not re-create.
    rows = [_row(category="ooo", ooo_until="2026-06-20")]
    acts = rf.plan_morning(rows, {"PT1": "draft_abc"}, {}, set(), _TODAY)
    assert acts[0]["action"] == "send_ooo"
    assert acts[0]["existing_draft_id"] == "draft_abc"


def test_morning_redirect_never_sends_only_drafts():
    rows = [_row(action="reroute", reroute_to="katie.s@acme.com")]
    acts = rf.plan_morning(rows, {}, {}, set(), _TODAY)
    assert acts[0]["action"] == "draft_redirect"
    assert acts[0]["spec"] is not None


def test_morning_redirect_already_contacted_skips():
    rows = [_row(action="reroute", reroute_to="katie.s@acme.com")]
    acts = rf.plan_morning(rows, {}, {}, {"katie.s@acme.com"}, _TODAY)
    assert acts[0]["action"] == "skip"


def test_morning_redirect_existing_draft_is_pending_not_recreated():
    rows = [_row(action="reroute", reroute_to="katie.s@acme.com")]
    acts = rf.plan_morning(rows, {}, {"katie.s@acme.com": "d1"}, set(), _TODAY)
    assert acts[0]["action"] == "draft_redirect"
    assert acts[0]["existing_draft_id"] == "d1" and acts[0]["spec"] is None


def test_morning_name_only_redirect_drafts_ask():
    rows = [_row(action="reroute", reroute_to="Katie in procurement")]
    acts = rf.plan_morning(rows, {}, {}, set(), _TODAY)
    assert acts[0]["action"] == "draft_ask"


def test_morning_mixed_batch_routes_each():
    rows = [
        _row(tid="A", category="ooo", ooo_until="2026-06-01"),    # due -> send
        _row(tid="B", category="ooo", ooo_until="2026-08-01",
             pitch_thread_id="PTB"),                              # future -> schedule
        _row(tid="C", action="reroute", reroute_to="x@new.com"),  # redirect -> draft
    ]
    acts = rf.plan_morning(rows, {}, {}, set(), _TODAY)
    kinds = sorted(a["action"] for a in acts)
    assert kinds == ["draft_redirect", "schedule_ooo", "send_ooo"]


# ---- _build_raw: MIME for the Gmail API ------------------------------------

def _parse_raw(raw_b64):
    """Return (the email.message.Message, decoded-text-of-all-parts)."""
    import email
    msg = email.message_from_bytes(base64.urlsafe_b64decode(raw_b64.encode()))
    text = ""
    for part in msg.walk():
        if part.get_content_maintype() == "multipart":
            continue
        payload = part.get_payload(decode=True)
        if payload:
            text += payload.decode("utf-8", "replace")
    return msg, text


def test_build_raw_sets_recipient_and_subject():
    spec = {"to": "katie@acme.com", "subject": "Hello", "body_html": "<p>Hi</p>"}
    msg, _ = _parse_raw(rf._build_raw(spec, {}))
    assert msg["To"] == "katie@acme.com"
    assert msg["Subject"] == "Hello"


def test_build_raw_threads_with_anchor_message_id():
    spec = {"to": "x@y.com", "subject": "", "body_html": "<p>Hi</p>"}
    msg, _ = _parse_raw(rf._build_raw(spec, {"message_id": "<abc@mail>"}))
    assert msg["In-Reply-To"] == "<abc@mail>"
    assert msg["References"] == "<abc@mail>"


def test_build_raw_includes_quote_when_requested():
    spec = {"to": "x@y.com", "subject": "", "body_html": "<p>Bump</p>", "quote": True}
    anchor = {"message_id": "<a@b>", "from": "Pitch Sender <p@s.com>",
              "date": "Mon, 1 Jun 2026", "body": "Original pitch text here"}
    _msg, text = _parse_raw(rf._build_raw(spec, anchor))
    assert "Original pitch text here" in text
    assert "wrote:" in text


def test_build_raw_no_quote_when_not_requested():
    spec = {"to": "x@y.com", "subject": "", "body_html": "<p>Bump</p>"}
    anchor = {"message_id": "<a@b>", "body": "should not appear"}
    _msg, text = _parse_raw(rf._build_raw(spec, anchor))
    assert "should not appear" not in text


# ---- runner ----------------------------------------------------------------

def _run_all():
    fns = [v for k, v in sorted(globals().items())
           if k.startswith("test_") and callable(v)]
    passed = failed = 0
    for fn in fns:
        try:
            fn()
            print(f"  PASS {fn.__name__}")
            passed += 1
        except Exception:
            print(f"  FAIL {fn.__name__}")
            traceback.print_exc()
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
    return failed


if __name__ == "__main__":
    sys.exit(1 if _run_all() else 0)
