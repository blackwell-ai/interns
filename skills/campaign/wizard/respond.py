"""The /respond reply-review queue: pull each reply-worthy email in turn, show a
Claude draft grounded in the founder's past replies, let them edit it, and send
it in-thread as that founder. Every reply they send is written back to the
`reply_examples` corpus as a gold example, so the drafts compound toward what
founders actually send.

Handlers live in `slack_bot.py`; this module owns the per-user review sessions and
the flow (build the queue, draft, step, send, record). Modal layouts are in
`blocks.py`.

Session state is in memory and per Slack user, so two founders can review at once
without colliding. A review session is short; if the process restarts mid-review
the session is gone and the user simply re-runs /respond. Nothing here is a source
of truth: an unsent email stays in the triage queue, and a sent one drops out on
its own because our reply lands in-thread (the next triage sees us as last sender)
while a genuine new reply from the same prospect correctly re-surfaces. So there is
no persistent "handled" marker to get wrong.
"""
import asyncio
import html as html_mod
import json
import logging

from skills.campaign import reply_followup

from . import agent, blocks, gmail_auth, reply_drafter, reply_examples, triage
from .session import app

log = logging.getLogger(__name__)

# Slack user id -> review session. Each: founder_key, founder_email, queue (needs
# rows), pos, draft (current reply_drafter output), view_id, sent, skipped.
_review_sessions: dict[str, dict] = {}


def _founder_email(founder_key: str) -> str:
    return next((s["email"] for s in agent.SENDERS if s["key"] == founder_key), "")


def _founder_name(founder_key: str) -> str:
    return next((s["from_name"] for s in agent.SENDERS if s["key"] == founder_key),
               founder_key.title())


def _text_to_html(text: str) -> str:
    """Founder-edited plain text -> a simple HTML body for the Gmail message."""
    return html_mod.escape(text).replace("\n", "<br>")


async def _update(view_id: str, view: dict) -> None:
    """Replace a modal in place. Best-effort: a lost race (user closed it) is not
    fatal to the background task."""
    try:
        await app.client.views_update(view_id=view_id, view=view)
    except Exception as e:  # noqa: BLE001
        log.warning("views_update failed: %s", str(e)[:150])


def loading_view(text: str = ":mage: Working...") -> dict:
    return blocks._respond_info_modal("Working", text)


# ---- building and stepping the queue ----------------------------------------

def _review_view(session: dict, note: str = "") -> dict:
    """The review modal for the session's current email, optionally with a
    warning note (e.g. after a failed send) prepended."""
    d = session["draft"]
    row = session["queue"][session["pos"]]
    meta = json.dumps({"user_id": session["user_id"],
                       "thread_id": d.get("thread_id", ""), "pos": session["pos"]})
    view = blocks._respond_review_modal(
        founder_name=_founder_name(session["founder_key"]),
        pos=session["pos"] + 1, total=len(session["queue"]),
        who=row.get("who", d.get("to", "")), subject=d.get("incoming_subject", ""),
        thread_preview=d.get("thread_preview", ""), draft=d.get("draft", ""),
        category=d.get("category", "other"), n_examples=d.get("n_examples", 0),
        private_metadata=meta)
    if note:
        view["blocks"].insert(0, {"type": "context", "elements": [
            {"type": "mrkdwn", "text": f":warning: {note}"}]})
    return view


def _summary(session: dict) -> str:
    return (f"Done. Sent *{session['sent']}* and skipped *{session['skipped']}*. "
            "Nothing else waiting. :sparkles:")


async def _advance_to_next_draftable(session: dict) -> bool:
    """Draft the current queue item, skipping any that cannot be drafted (an
    unreadable thread, or one with no inbound to answer). Returns True when a draft
    is ready in session['draft'], False when the queue is exhausted."""
    while session["pos"] < len(session["queue"]):
        item = session["queue"][session["pos"]]
        try:
            session["draft"] = await reply_drafter.generate_draft(
                session["founder_key"], session["founder_email"], item["thread_id"])
            return True
        except Exception as e:  # noqa: BLE001 - a bad thread must not stall the queue
            log.warning("draft generation failed, skipping thread: %s", str(e)[:120])
            session["pos"] += 1
            session["skipped"] += 1
    return False


async def _present(session: dict) -> None:
    """Draft the next email (showing a loading modal meanwhile) and show it, or the
    done summary if the queue is exhausted."""
    view_id = session["view_id"]
    await _update(view_id, loading_view(":mage: Drafting the reply..."))
    ready = await _advance_to_next_draftable(session)
    if not ready:
        await _update(view_id, blocks._respond_info_modal("All done", _summary(session)))
        _review_sessions.pop(session["user_id"], None)
        return
    await _update(view_id, _review_view(session))


async def build_first(user_id: str, founder_key: str, view_id: str) -> None:
    """Start a review session: pull the founder's awaiting-reply queue and show the
    first draft. Called in the background after the picker is submitted."""
    fe = _founder_email(founder_key)
    session = {"user_id": user_id, "founder_key": founder_key, "founder_email": fe,
               "queue": [], "pos": 0, "draft": None, "view_id": view_id,
               "sent": 0, "skipped": 0}
    _review_sessions[user_id] = session
    await _update(view_id, loading_view(f":crystal_ball: Gathering {_founder_name(founder_key)}'s replies..."))
    try:
        needs = await triage.needs_for_founder(fe)
    except Exception as e:  # noqa: BLE001
        await _update(view_id, blocks._respond_info_modal(
            "Trouble", f"I could not read {_founder_name(founder_key)}'s inbox.\n\n"
                       f"`{str(e)[:200]}`"))
        _review_sessions.pop(user_id, None)
        return
    if not needs:
        await _update(view_id, blocks._respond_info_modal(
            "All clear", f"No replies are waiting for {_founder_name(founder_key)}. :sparkles:"))
        _review_sessions.pop(user_id, None)
        return
    session["queue"] = needs
    await _present(session)


# ---- button actions ---------------------------------------------------------

async def on_skip(user_id: str, view_id: str) -> None:
    session = _review_sessions.get(user_id)
    if not session:
        await _update(view_id, blocks._respond_info_modal(
            "Session ended", "Run `/respond` again to pick up where you left off."))
        return
    session["view_id"] = view_id
    session["pos"] += 1
    session["skipped"] += 1
    session["draft"] = None
    await _present(session)


async def on_regen(user_id: str, view_id: str) -> None:
    session = _review_sessions.get(user_id)
    if not session or not session.get("draft"):
        await _update(view_id, blocks._respond_info_modal(
            "Session ended", "Run `/respond` again."))
        return
    session["view_id"] = view_id
    thread_id = session["draft"].get("thread_id") or session["queue"][session["pos"]]["thread_id"]
    await _update(view_id, loading_view(":mage: Drafting a fresh version..."))
    try:
        session["draft"] = await reply_drafter.generate_draft(
            session["founder_key"], session["founder_email"], thread_id)
        await _update(view_id, _review_view(session))
    except Exception as e:  # noqa: BLE001
        await _update(view_id, _review_view(
            session, note=f"Could not regenerate ({str(e)[:80]}). Kept the previous draft."))


# ---- send (with the feedback-loop write-back) -------------------------------

async def _send_reply(session: dict, body: str) -> tuple[bool, str]:
    """Send the edited body in-thread as the founder, via the reply_followup REST
    helpers (create draft then send). Returns (ok, sent_message_id_or_detail)."""
    d = session["draft"]
    spec = {
        "to": d["to"],
        "subject": d["reply_subject"],
        "body_html": _text_to_html(body),
        "reply_to_message_id": d["reply_to_message_id"],
        "thread_id": d["thread_id"],
        "quote": False,
    }
    try:
        token = await asyncio.to_thread(gmail_auth.get_access_token, session["founder_email"])
    except Exception as e:  # noqa: BLE001
        return False, f"auth failed: {str(e)[:120]}"
    ok, draft_id = await reply_followup.create_draft_api(token, spec, dry_run=False)
    if not ok:
        return False, draft_id
    return await reply_followup.send_draft_api(token, draft_id)


async def _record_gold(session: dict, body: str, sent_id: str) -> None:
    """Feedback loop: store the reply the founder actually sent as a gold example.
    Best-effort; a corpus write must never fail a successful send."""
    d = session["draft"]
    try:
        await reply_examples.add_gold_example(
            founder=session["founder_key"], category=d.get("category", "other"),
            incoming_subject=d.get("incoming_subject", ""),
            incoming_body=d.get("incoming_body", ""),
            reply_body=body, sentiment=d.get("sentiment", "unknown"),
            message_id=sent_id or f"{session['founder_key']}:{d.get('thread_id','')}")
    except Exception as e:  # noqa: BLE001
        log.warning("gold example write failed: %s", str(e)[:150])


async def on_send(user_id: str, view_id: str, body: str) -> None:
    """Send the founder's edited reply, record it as a gold example, and advance.
    On any send failure, nothing is recorded and the email stays in the queue
    (the review modal reappears with the edit intact so they can retry)."""
    session = _review_sessions.get(user_id)
    if not session or not session.get("draft"):
        await _update(view_id, blocks._respond_info_modal(
            "Session ended", "Run `/respond` again."))
        return
    session["view_id"] = view_id
    if not body.strip():
        session["draft"]["draft"] = body
        await _update(view_id, _review_view(session, note="The reply was empty. Nothing was sent."))
        return

    await _update(view_id, loading_view(":envelope_with_arrow: Sending your reply..."))
    ok, detail = await _send_reply(session, body)
    if not ok:
        # Keep the edit, do NOT advance, do NOT record. Let them retry or skip.
        session["draft"]["draft"] = body
        await _update(view_id, _review_view(
            session, note=f"Send failed, nothing left your outbox: {detail}. "
                          "This email is still in your queue."))
        return

    await _record_gold(session, body, detail)  # detail is the sent message id
    session["sent"] += 1
    session["pos"] += 1
    session["draft"] = None
    await _present(session)


# ---- entry ------------------------------------------------------------------

def picker_view() -> dict:
    return blocks._respond_picker_modal()
