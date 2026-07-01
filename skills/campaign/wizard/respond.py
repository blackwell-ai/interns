"""The /respond reply-review deck: a founder pulls up their reply-worthy emails as
a deck they can page through. Each card shows who we are answering, their message,
and an editable Claude draft grounded in the founder's past replies. They edit,
Accept & send (in-thread, as that founder), or move Prev/Next. Every reply they
send is written back to the `reply_examples` corpus as a gold example.

To make navigation instant, the whole deck is drafted in the background in
parallel as soon as the queue is built, so by the time the founder pages forward
the next card is usually ready. Cards still drafting show a loading state.

Handlers live in `slack_bot.py`; modal layout in `blocks.py`. Session state is in
memory, per Slack user, so two founders can review at once. A restart mid-review
just means re-running /respond. Nothing here is a source of truth: an unsent email
stays in the triage queue, and a sent one drops out on its own (our reply lands
in-thread, so the next triage sees us as last sender).
"""
import asyncio
import html as html_mod
import json
import logging

from skills.campaign import reply_followup

from . import agent, blocks, gmail_auth, reply_drafter, reply_examples, triage
from .session import app

log = logging.getLogger(__name__)

# Slack user id -> review session.
_review_sessions: dict[str, dict] = {}

# How many drafts to generate at once in the background. Gmail + Opus per draft,
# so keep it modest to stay under rate limits while still filling the deck fast.
_DRAFT_CONCURRENCY = 5


def _founder_email(founder_key: str) -> str:
    return next((s["email"] for s in agent.SENDERS if s["key"] == founder_key), "")


def _founder_name(founder_key: str) -> str:
    return next((s["from_name"] for s in agent.SENDERS if s["key"] == founder_key),
               founder_key.title())


def _text_to_html(text: str) -> str:
    return html_mod.escape(text).replace("\n", "<br>")


async def _update(view_id: str, view: dict) -> None:
    """Replace a modal in place. Best-effort: a lost race (user closed it) is fine."""
    try:
        await app.client.views_update(view_id=view_id, view=view)
    except Exception as e:  # noqa: BLE001
        log.warning("views_update failed: %s", str(e)[:150])


def picker_view() -> dict:
    return blocks._respond_picker_modal()


def loading_view(text: str = ":mage: Working...") -> dict:
    return blocks._respond_info_modal("Working", text)


# ---- rendering --------------------------------------------------------------

def _ready_count(session: dict) -> int:
    return sum(1 for it in session["deck"]
               if it["draft_status"] in ("ready", "failed") or it["sent"])


def _render(session: dict) -> dict:
    """Build the modal for the session's current card."""
    deck = session["deck"]
    pos = session["pos"]
    it = deck[pos]
    row = it["row"]
    d = it.get("draft") or {}

    if it["sent"]:
        mode, body = "sent", (it.get("edited") or d.get("draft", ""))
    elif it["draft_status"] == "ready":
        mode, body = "review", (it.get("edited") if it.get("edited") is not None
                                else d.get("draft", ""))
    elif it["draft_status"] == "failed":
        mode, body = "failed", ""
    else:
        mode, body = "pending", ""

    meta = json.dumps({"user_id": session["user_id"], "pos": pos,
                       "thread_id": row.get("thread_id", "")})
    return blocks._respond_deck_modal(
        founder_name=_founder_name(session["founder_key"]),
        pos=pos + 1, total=len(deck),
        sent=session["sent"], skipped=session["skipped"], ready=_ready_count(session),
        who=row.get("who", d.get("to", "")),
        subject=d.get("incoming_subject", ""),
        thread_preview=d.get("thread_preview", ""),
        body=body, category=d.get("category", "other"),
        n_examples=d.get("n_examples", 0), mode=mode,
        can_prev=pos > 0, can_next=pos < len(deck) - 1,
        private_metadata=meta)


async def _show(session: dict) -> None:
    """Render the current card. Remember which card a loading screen is waiting on,
    so the background drafter can refresh it in place when the draft lands."""
    it = session["deck"][session["pos"]]
    session["loading_pos"] = session["pos"] if (
        it["draft_status"] == "pending" and not it["sent"]) else None
    await _update(session["view_id"], _render(session))


def _save_edit(session: dict, edited: str | None) -> None:
    """Persist the founder's in-progress edit for the current card so paging away
    and back keeps it. Only meaningful while the card is an editable draft."""
    if edited is None:
        return
    it = session["deck"][session["pos"]]
    if it["draft_status"] == "ready" and not it["sent"]:
        it["edited"] = edited


# ---- building the deck + background drafting --------------------------------

async def build_first(user_id: str, founder_key: str, view_id: str) -> None:
    """Pull the founder's awaiting-reply queue, build the deck, show the first
    card, and kick off drafting the whole deck in the background."""
    fe = _founder_email(founder_key)
    session = {"user_id": user_id, "founder_key": founder_key, "founder_email": fe,
               "deck": [], "pos": 0, "view_id": view_id, "sent": 0, "skipped": 0,
               "loading_pos": None, "draft_task": None}
    _review_sessions[user_id] = session
    await _update(view_id, loading_view(
        f":crystal_ball: Gathering {_founder_name(founder_key)}'s replies..."))
    try:
        needs = await triage.needs_for_founder(fe)
    except Exception as e:  # noqa: BLE001
        await _update(view_id, blocks._respond_info_modal(
            "Trouble", f"I could not read {_founder_name(founder_key)}'s inbox.\n\n`{str(e)[:200]}`"))
        _review_sessions.pop(user_id, None)
        return
    if not needs:
        await _update(view_id, blocks._respond_info_modal(
            "All clear", f"No replies are waiting for {_founder_name(founder_key)}. :sparkles:"))
        _review_sessions.pop(user_id, None)
        return
    session["deck"] = [{"row": r, "draft": None, "edited": None,
                        "draft_status": "pending", "sent": False} for r in needs]
    await _show(session)
    session["draft_task"] = asyncio.create_task(_draft_all(session))


async def _draft_all(session: dict) -> None:
    """Draft every card in the background, in parallel. As each lands, refresh the
    view only if the founder is currently sitting on that card's loading screen."""
    sem = asyncio.Semaphore(_DRAFT_CONCURRENCY)
    fk, fe = session["founder_key"], session["founder_email"]

    async def one(i: int) -> None:
        async with sem:
            if _review_sessions.get(session["user_id"]) is not session:
                return  # session ended or replaced; stop working
            it = session["deck"][i]
            try:
                it["draft"] = await reply_drafter.generate_draft(
                    fk, fe, it["row"]["thread_id"])
                it["draft_status"] = "ready"
            except Exception as e:  # noqa: BLE001 - one bad thread must not stall the deck
                it["draft_status"] = "failed"
                log.warning("draft generation failed for a thread: %s", str(e)[:120])
        if session.get("loading_pos") == i and _review_sessions.get(session["user_id"]) is session:
            await _show(session)

    await asyncio.gather(*(one(i) for i in range(len(session["deck"]))))


# ---- navigation -------------------------------------------------------------

async def on_nav(user_id: str, view_id: str, delta: int, edited: str | None) -> None:
    session = _review_sessions.get(user_id)
    if not session:
        await _update(view_id, blocks._respond_info_modal(
            "Session ended", "Run `/respond` again to start over."))
        return
    session["view_id"] = view_id
    _save_edit(session, edited)
    session["pos"] = max(0, min(len(session["deck"]) - 1, session["pos"] + delta))
    await _show(session)


async def on_regen(user_id: str, view_id: str, edited: str | None) -> None:
    session = _review_sessions.get(user_id)
    if not session:
        await _update(view_id, blocks._respond_info_modal("Session ended", "Run `/respond` again."))
        return
    session["view_id"] = view_id
    _save_edit(session, edited)
    it = session["deck"][session["pos"]]
    it["draft_status"] = "pending"
    it["edited"] = None
    await _show(session)
    try:
        it["draft"] = await reply_drafter.generate_draft(
            session["founder_key"], session["founder_email"], it["row"]["thread_id"])
        it["draft_status"] = "ready"
    except Exception as e:  # noqa: BLE001
        it["draft_status"] = "failed"
        log.warning("regenerate failed: %s", str(e)[:120])
    await _show(session)


# ---- accept & send (with the feedback-loop write-back) ----------------------

async def _send_reply(session: dict, body: str) -> tuple[bool, str]:
    """Send the edited body in-thread as the founder, via reply_followup's REST
    helpers (create draft then send). Returns (ok, sent_message_id_or_detail)."""
    d = session["deck"][session["pos"]]["draft"]
    spec = {
        "to": d["to"], "subject": d["reply_subject"],
        "body_html": _text_to_html(body),
        "reply_to_message_id": d["reply_to_message_id"],
        "thread_id": d["thread_id"], "quote": False,
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
    d = session["deck"][session["pos"]]["draft"]
    try:
        await reply_examples.add_gold_example(
            founder=session["founder_key"], category=d.get("category", "other"),
            incoming_subject=d.get("incoming_subject", ""),
            incoming_body=d.get("incoming_body", ""),
            reply_body=body, sentiment=d.get("sentiment", "unknown"),
            message_id=sent_id or f"{session['founder_key']}:{d.get('thread_id','')}")
    except Exception as e:  # noqa: BLE001
        log.warning("gold example write failed: %s", str(e)[:150])


def _next_unsent(session: dict) -> int | None:
    """Index of the next not-yet-sent card after the current one (wrapping once),
    or None when every card has been sent."""
    n = len(session["deck"])
    for step in range(1, n + 1):
        j = (session["pos"] + step) % n
        if not session["deck"][j]["sent"]:
            return j
    return None


async def on_send(user_id: str, view_id: str, body: str) -> None:
    """Accept & send the current card. On any send failure nothing is recorded and
    the card stays put (the review modal reappears with the edit intact to retry)."""
    session = _review_sessions.get(user_id)
    if not session:
        await _update(view_id, blocks._respond_info_modal("Session ended", "Run `/respond` again."))
        return
    session["view_id"] = view_id
    it = session["deck"][session["pos"]]
    if it["sent"] or it["draft_status"] != "ready":
        await _show(session)  # stale submit (already sent, or not ready) — just redraw
        return
    it["edited"] = body
    if not body.strip():
        await _update(view_id, _render(session))  # empty; leave them on the card
        return

    await _update(view_id, loading_view(":envelope_with_arrow: Sending your reply..."))
    ok, detail = await _send_reply(session, body)
    if not ok:
        # Edit preserved, nothing sent, nothing recorded; let them retry or move on.
        await _update(view_id, _with_note(session, f"Send failed, nothing left your outbox: {detail}"))
        return

    await _record_gold(session, body, detail)
    it["sent"] = True
    session["sent"] += 1
    nxt = _next_unsent(session)
    if nxt is None:
        await _update(view_id, blocks._respond_info_modal(
            "All done", f"Sent *{session['sent']}*. Nothing else to answer. :sparkles:"))
        _review_sessions.pop(user_id, None)
        return
    session["pos"] = nxt
    await _show(session)


def _with_note(session: dict, note: str) -> dict:
    view = _render(session)
    view["blocks"].insert(0, {"type": "context", "elements": [
        {"type": "mrkdwn", "text": f":warning: {note}"}]})
    return view
