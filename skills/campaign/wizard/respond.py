"""The /respond reply-review deck: a founder pulls up their reply-worthy emails as
a deck they can page through. Each card shows who we are answering, their reply,
and an editable Claude draft grounded in the founder's past replies. They edit,
Accept & send (in-thread, as that founder), or move Prev/Next. Every reply they
send is written back to the `reply_examples` corpus as a gold example.

Drafts are generated in the background in parallel as soon as the queue is built,
and a card refreshes in place the moment its own draft lands, so navigation is
instant and a fresh card never shows the previous one's text. Cards still drafting
show a loading state.

Handlers live in `slack_bot.py`; modal layout in `blocks.py`. Session state is in
memory, per Slack user. A restart mid-review just means re-running /respond.
"""
import asyncio
import html as html_mod
import json
import logging
import re

from skills.campaign import reply_followup

from . import agent, blocks, gmail_auth, reply_drafter, reply_examples, triage
from .session import app

log = logging.getLogger(__name__)

# Slack user id -> review session.
_review_sessions: dict[str, dict] = {}

# How many drafts to generate at once. Gmail + Opus per draft, so keep it modest
# to stay under rate limits while still filling the deck quickly.
_DRAFT_CONCURRENCY = 6

_URL_RE = re.compile(r"(https?://[^\s<>]+)")
_MD_LINK_RE = re.compile(r"\[([^\]]+)\]\((https?://[^\s)]+)\)")


def _founder_email(founder_key: str) -> str:
    return next((s["email"] for s in agent.SENDERS if s["key"] == founder_key), "")


def _founder_name(founder_key: str) -> str:
    return next((s["from_name"] for s in agent.SENDERS if s["key"] == founder_key),
               founder_key.title())


def _linkify_plain(seg: str) -> str:
    """Escape a plain segment and turn any bare URLs in it into links."""
    out = []
    for i, part in enumerate(_URL_RE.split(seg)):
        if i % 2 == 1:
            out.append(f'<a href="{html_mod.escape(part, quote=True)}">{html_mod.escape(part)}</a>')
        else:
            out.append(html_mod.escape(part).replace("\n", "<br>"))
    return "".join(out)


def _text_to_html(text: str) -> str:
    """Founder-edited text -> an HTML body. Markdown links `[here](url)` become an
    anchor on the visible word (so the scheduling link reads as "here" instead of a
    raw URL); any remaining bare URLs are linked too."""
    text = text or ""
    out, idx = [], 0
    for m in _MD_LINK_RE.finditer(text):
        out.append(_linkify_plain(text[idx:m.start()]))
        label, url = m.group(1), m.group(2)
        out.append(f'<a href="{html_mod.escape(url, quote=True)}">{html_mod.escape(label)}</a>')
        idx = m.end()
    out.append(_linkify_plain(text[idx:]))
    return "".join(out)


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
    # A block id that changes with the card and each redraft, so Slack always shows
    # the current draft as the input value instead of caching a prior one.
    body_block_id = f"resp_body_{pos}_{it['render_nonce']}"
    return blocks._respond_deck_modal(
        founder_name=_founder_name(session["founder_key"]),
        pos=pos + 1, total=len(deck),
        sent=session["sent"], skipped=session["skipped"], ready=_ready_count(session),
        who=row.get("who", d.get("to", "")),
        subject=d.get("incoming_subject", ""),
        received=d.get("received", ""),
        gmail_url=d.get("gmail_url", ""),
        their_message=d.get("incoming_clean", ""),
        body=body, category=d.get("category", "other"),
        n_examples=d.get("n_examples", 0), mode=mode,
        can_prev=pos > 0, can_next=pos < len(deck) - 1,
        private_metadata=meta, body_block_id=body_block_id)


async def _show(session: dict) -> None:
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
    card, and start drafting the whole deck in the background."""
    fe = _founder_email(founder_key)
    session = {"user_id": user_id, "founder_key": founder_key, "founder_email": fe,
               "deck": [], "pos": 0, "view_id": view_id, "sent": 0, "skipped": 0,
               "sem": asyncio.Semaphore(_DRAFT_CONCURRENCY)}
    _review_sessions[user_id] = session
    name = _founder_name(founder_key)
    await _update(view_id, loading_view(
        f":mag: *Step 1 of 2: reading {name}'s inbox.*\n\nScanning every reply from "
        "people we've emailed and picking the ones still waiting on us. This takes "
        "about 30 seconds. I'll then draft each one and you can review them here."))
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
                        "draft_status": "pending", "sent": False, "render_nonce": 0}
                       for r in needs]
    await _show(session)
    # Draft everything in the background. Card 0 is kicked first so it lands soonest.
    for i in range(len(session["deck"])):
        asyncio.create_task(_draft_card(session, i))


async def _draft_card(session: dict, i: int) -> None:
    """Draft one card if it still needs it, then refresh the view if the founder is
    sitting on that card. Deduped via the status flag so it is safe to call again
    on navigation. Cards that fail are marked so the founder can Regenerate."""
    if _review_sessions.get(session["user_id"]) is not session:
        return
    it = session["deck"][i]
    if it["draft_status"] != "pending":
        return  # already drafting, ready, or failed
    it["draft_status"] = "drafting"
    async with session["sem"]:
        if _review_sessions.get(session["user_id"]) is not session:
            return
        try:
            it["draft"] = await reply_drafter.generate_draft(
                session["founder_key"], session["founder_email"], it["row"]["thread_id"])
            it["draft_status"] = "ready"
        except Exception as e:  # noqa: BLE001 - one bad thread must not stall the deck
            it["draft_status"] = "failed"
            log.warning("draft generation failed for a thread: %s", str(e)[:120])
    it["render_nonce"] += 1
    if _review_sessions.get(session["user_id"]) is session and session["pos"] == i:
        await _show(session)


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
    # If we landed on a card that has not been drafted yet, make sure it is (a
    # no-op if it is already drafting/ready); it will refresh itself when ready.
    asyncio.create_task(_draft_card(session, session["pos"]))


async def on_regen(user_id: str, view_id: str, edited: str | None) -> None:
    session = _review_sessions.get(user_id)
    if not session:
        await _update(view_id, blocks._respond_info_modal("Session ended", "Run `/respond` again."))
        return
    session["view_id"] = view_id
    it = session["deck"][session["pos"]]
    it["draft_status"] = "pending"
    it["edited"] = None
    await _show(session)  # shows the drafting state
    await _draft_card(session, session["pos"])  # redraft + refresh when ready


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
        await _show(session)  # stale submit (already sent, or not ready) — redraw
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
    asyncio.create_task(_draft_card(session, session["pos"]))


def _with_note(session: dict, note: str) -> dict:
    view = _render(session)
    view["blocks"].insert(0, {"type": "context", "elements": [
        {"type": "mrkdwn", "text": f":warning: {note}"}]})
    return view
