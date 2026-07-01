"""Slack front end for the campaign wizard: the Bolt event/action/view handlers,
the `main()` startup, and the schedule wiring. The conversation logic lives in
`session.py`, the Block Kit rendering in `blocks.py`, and the cron jobs in
`schedules.py`. This module is the only one Slack calls into directly.

The flow is thread-based: a user @mentions the wizard once in the configured
channel, the wizard opens a thread and runs the whole exchange there, so
follow-up replies in that thread need no further @mention. The preview carries
Send / Edit / Cancel buttons (typed 'send' / 'cancel' still work).

For navigability this file also re-exports the names that tests and other
modules reach for as `slack_bot.<name>` (they now live in session/blocks/
schedules). Run with:  python -m skills.campaign.wizard.launch
"""
import asyncio
import json
import logging
from datetime import datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler
from zoneinfo import ZoneInfo

from . import (agent, geo_test, qa, respond, schedules, session, slack_config,
               triage_dismiss)
# The Bolt app and the conversation state/flow live in session.py; import the
# app to attach handlers and the helpers the handlers call. These imports double
# as the re-export surface: `slack_bot._state`, `slack_bot._route`, etc. still
# resolve for the tests and for callers that predate the split.
from .session import (  # noqa: F401
    _RUN_DONE_RE,
    _answer,
    _apply_draft_edit,
    _build_csv_template,
    _campaigns,
    _download_slack_file,
    _execute,
    _handle_triage_edit,
    _install_draft_override,
    _is_question,
    _is_triage,
    _pester,
    _post_channel,
    _present_csv_leads,
    _present_plan,
    _reply_to,
    _reset,
    _roll_day,
    _route,
    _seen_events,
    _start_qa,
    _start_triage,
    _state,
    _strip_mentions,
    _thread_reply,
    _triage_state,
    _validate_draft,
    app,
    record_campaign_sent,
)
from .blocks import (  # noqa: F401
    _edit_modal,
    _fmt_duration,
    _preview_blocks,
    _progress_blocks,
)

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    level=logging.INFO,
)
log = logging.getLogger(__name__)

# Filled at startup from auth.test; used to spot @mentions and skip our own posts.
# Lives here (not in session) because a test rebinds `slack_bot._bot_user_id` and
# `on_message` below must read that same name.
_bot_user_id: str = ""


# ---- Slack event + action handlers ------------------------------------------

@app.event("app_mention")
async def _ignore_app_mention(event, logger) -> None:
    # The message handler below covers mentions too (message.channels fires for
    # them). This no-op just keeps Bolt from logging the mention as unhandled.
    return


@app.event("message")
async def on_message(event, logger) -> None:
    if event.get("channel") != slack_config.SLACK_CHANNEL_ID:
        return
    subtype = event.get("subtype", "")
    if subtype and subtype != "file_share":
        return  # joins, edits, deletions — but let file uploads through
    if event.get("bot_id"):
        return
    if not event.get("user") or event.get("user") == _bot_user_id:
        return

    event_id = event.get("client_msg_id") or event.get("ts", "")
    if event_id in _seen_events:
        return
    _seen_events.add(event_id)

    raw = event.get("text", "")
    is_mention = bool(_bot_user_id) and f"<@{_bot_user_id}>" in raw
    text = _strip_mentions(raw)

    # If a file was attached, try to parse it as a contact CSV deterministically
    # (no LLM, so a large list never truncates). Parsed leads become a direct
    # send; an unparseable file falls back to appending its text for the planner.
    csv_leads: list[dict] | None = None
    files = event.get("files", [])
    if files and (is_mention or _state.get("thread_ts") == event.get("thread_ts")):
        content = await _download_slack_file(files[0])
        if content:
            csv_leads = agent.parse_contacts_csv(content) or None
            if not csv_leads:
                fname = files[0].get("name", "file")
                text = f"{text}\n\n[Attached: {fname}]\n{content[:20_000]}".strip()
    thread_ts = event.get("thread_ts")
    active = _state.get("thread_ts")

    try:
        # A thread with a campaign record: 'stop' cancels a live run, anything
        # else is a question answered from the run's log (works mid-run and after
        # completion), without needing an @mention.
        record = _campaigns.get(thread_ts) if thread_ts else None
        if record:
            if text.strip().lower() == "stop":
                await _route("stop", _reply_to(thread_ts))
            elif text.strip():
                await _answer(record, text, _reply_to(thread_ts))
            return
        # Triage list edits: "drop jane@x.com — not our market", "undo jane@x.com",
        # "show dismissed". Works as an unmentioned reply in the active triage
        # thread, or via an explicit @mention anywhere. Requires a real email (for
        # dismiss/undo) so a normal question or send is never hijacked.
        in_triage_thread = bool(thread_ts) and thread_ts == _triage_state.get("thread_ts")
        if (is_mention or in_triage_thread) and not csv_leads:
            cmd = triage_dismiss.parse_command(text)
            if cmd["action"]:
                await _handle_triage_edit(
                    cmd, _reply_to(thread_ts or event.get("ts")),
                    by=event.get("user", ""))
                return
        # Continuation inside the active planning thread: no @mention needed.
        if active and thread_ts == active:
            if csv_leads:
                await _present_csv_leads(csv_leads, text, _thread_reply())
            else:
                await _route(text, _thread_reply())
            return
        # A fresh @mention. One intent classifier decides send vs triage vs
        # question, so a question that merely mentions "replies"/"responses" (e.g.
        # "what did the aerospace folks say") reaches the Q&A loop instead of being
        # swallowed by a keyword-matched full-inbox triage. CSV handoffs always go
        # to the gated send path. Both triage and Q&A are read-only.
        if is_mention:
            # GEO test: source a live brand, run the real visibility check, and
            # post the finished email so the per-brand comparison line can be
            # read before any campaign. Read-only; checked before the classifier
            # so "geo test ..." is never read as a send or a question.
            if not csv_leads and geo_test.is_geo_test(text):
                await geo_test.run(text, _reply_to(thread_ts or event.get("ts")))
                return
            if not csv_leads and text.strip():
                intent = await qa.classify_intent(text)
                if intent == "triage":
                    await _start_triage(thread_ts or event.get("ts"))
                    return
                if intent == "question":
                    await _start_qa(text, thread_ts or event.get("ts"))
                    return
            if _state["mode"] != "idle" and active:
                await app.client.chat_postMessage(
                    channel=slack_config.SLACK_CHANNEL_ID,
                    thread_ts=thread_ts or event.get("ts"),
                    text=":mage: I am mid-sending in another thread. Tend to it "
                         "there, or say 'stop' there to end it.")
                return
            _state["thread_ts"] = thread_ts or event.get("ts")
            if csv_leads:
                await _present_csv_leads(csv_leads, text, _thread_reply())
            else:
                await _route(text, _thread_reply())
            return
        # An unmentioned message in some other thread: if it reads as a question,
        # answer it (read-only Q&A) instead of ignoring it.
        if thread_ts and _is_question(text):
            await _start_qa(text, thread_ts)
            return
        # Otherwise it's normal channel chatter: ignore.
    except Exception:
        logger.exception("message handler failed")
        if thread_ts:
            await _reply_to(thread_ts)("My arts faltered. Check the logs.")


async def _strip_buttons(body, note: str) -> None:
    """Remove the Send/Cancel buttons from a clicked preview and add a note, so
    it cannot be double-tapped and the outcome is visible."""
    msg = body.get("message", {})
    blocks = [b for b in msg.get("blocks", []) if b.get("block_id") != "wiz_confirm"]
    blocks.append({"type": "context", "elements": [{"type": "mrkdwn", "text": note}]})
    await app.client.chat_update(
        channel=body["channel"]["id"], ts=msg["ts"],
        text="Campaign plan", blocks=blocks)


@app.action("wiz_send")
async def on_send(ack, body, logger) -> None:
    await ack()
    if _state["mode"] != "awaiting_preview":
        return  # stale or already handled
    plan_runs = _state.get("pending_plan")
    await _strip_buttons(body, ":rocket: Confirmed. The sending begins.")
    if not plan_runs:
        _reset()
        return
    await _execute(plan_runs)


@app.action("wiz_cancel")
async def on_cancel(ack, body, logger) -> None:
    await ack()
    if _state["mode"] != "awaiting_preview":
        return
    await _strip_buttons(body, ":x: Cancelled.")
    _reset()


@app.action("wiz_edit")
async def on_edit(ack, body, logger) -> None:
    """Open the edit-draft modal, pre-filled from the previewed run's template."""
    await ack()
    if _state["mode"] != "awaiting_preview":
        return  # stale preview
    plan_runs = _state.get("pending_plan")
    if not plan_runs:
        return
    subject, draft = agent.editable_draft(plan_runs[0])
    meta = json.dumps({"channel": body["channel"]["id"],
                       "message_ts": body["message"]["ts"]})
    try:
        await app.client.views_open(
            trigger_id=body["trigger_id"],
            view=_edit_modal(subject, draft, meta))
    except Exception as e:
        log.warning("views_open failed: %s", e)


@app.view("wiz_edit_modal")
async def on_edit_submit(ack, body, view, logger) -> None:
    """Apply the modal: take the hand-edited subject/body, then (if the teammate
    described a change) have Claude refine it on top, install the result as the
    template override, and refresh the preview."""
    values = view["state"]["values"]
    subject = values["wiz_subj"]["v"]["value"] or ""
    draft = values["wiz_body"]["v"]["value"] or ""
    refine = (values.get("wiz_refine", {}).get("v", {}).get("value") or "").strip()
    errors = _validate_draft(subject, draft)
    if errors:
        await ack(response_action="errors", errors=errors)
        return
    await ack()
    if _state["mode"] != "awaiting_preview":
        return  # session moved on while the modal was open

    thread = _reply_to(_state.get("thread_ts"))
    if refine:
        # Manual edits are the base; Claude applies the requested change on top.
        await thread(":sparkles: Refining the draft as you asked, one moment...")
        try:
            subject, draft = await asyncio.to_thread(
                agent.refine_template, subject, draft, refine)
        except Exception as e:
            log.warning("refine failed: %s", e)
            await thread("I could not refine that cleanly (it would have dropped a "
                         "personalization slot), so I kept your edits instead.")
        _install_draft_override(subject, draft)
    elif not _apply_draft_edit(subject, draft):
        return  # nothing changed — leave the preview as is

    plan_runs = _state.get("pending_plan") or []
    meta = json.loads(view.get("private_metadata") or "{}")
    if not meta.get("message_ts"):
        return
    fallback, blocks = _preview_blocks(plan_runs, _state.get("deferred", 0))
    try:
        await app.client.chat_update(
            channel=meta["channel"], ts=meta["message_ts"],
            text=fallback, blocks=blocks)
    except Exception as e:
        log.warning("preview refresh after edit failed: %s", e)


# ---- /respond reply-review queue --------------------------------------------
# A founder runs /respond, picks whose inbox to work, and steps through each
# reply-worthy email with a Claude draft grounded in their past replies, editing
# and sending in-thread. Flow + per-user session state live in `respond.py`; these
# handlers just translate Slack events into calls on it. Slash commands and modal
# interactions are NOT channel-gated, so the queue works from anywhere.
#
# One-time Slack app config this depends on: register the `/respond` slash command
# and enable Interactivity, both delivered over Socket Mode (no Request URL). See
# ARCHITECTURE.md "Where to change X".


@app.command("/respond")
async def on_respond_command(ack, body, logger) -> None:
    await ack()
    try:
        await app.client.views_open(
            trigger_id=body["trigger_id"], view=respond.picker_view())
    except Exception as e:  # noqa: BLE001
        log.warning("respond views_open failed: %s", e)


@app.view("resp_pick")
async def on_respond_pick(ack, body, view, logger) -> None:
    """Founder picked. Update the modal to a loading state, then build their queue
    and show the first draft in the background."""
    sel = (view["state"]["values"].get("resp_founder", {})
           .get("v", {}).get("selected_option"))
    if not sel:
        await ack(response_action="errors",
                  errors={"resp_founder": "Pick a founder to start."})
        return
    founder_key = sel["value"]
    await ack(response_action="update", view=respond.loading_view())
    user_id = body["user"]["id"]
    view_id = body["view"]["id"]
    asyncio.create_task(respond.build_first(user_id, founder_key, view_id))


def _read_reply(values: dict) -> str | None:
    """The founder's reply text from a modal's state. The block id is dynamic
    (resp_body_<pos>_<nonce>) so Slack never caches a prior card's text, so we
    match by prefix. None when the current card has no editable input."""
    for bid, fields in (values or {}).items():
        if bid.startswith("resp_body"):
            return fields.get("v", {}).get("value")
    return None


def _current_edit(body) -> str | None:
    return _read_reply((body.get("view", {}).get("state", {}) or {}).get("values", {}))


@app.action("resp_prev")
async def on_respond_prev(ack, body, logger) -> None:
    await ack()
    asyncio.create_task(respond.on_nav(
        body["user"]["id"], body["view"]["id"], -1, _current_edit(body)))


@app.action("resp_next")
async def on_respond_next(ack, body, logger) -> None:
    await ack()
    asyncio.create_task(respond.on_nav(
        body["user"]["id"], body["view"]["id"], +1, _current_edit(body)))


@app.action("resp_regen")
async def on_respond_regen(ack, body, logger) -> None:
    await ack()
    asyncio.create_task(respond.on_regen(
        body["user"]["id"], body["view"]["id"], _current_edit(body)))


@app.view("resp_review")
async def on_respond_send(ack, body, view, logger) -> None:
    """Accept & send. Update the modal to a loading state, then send the edited
    reply in-thread and advance to the next card in the background."""
    body_text = _read_reply(view["state"]["values"]) or ""
    await ack(response_action="update", view=respond.loading_view())
    user_id = body["user"]["id"]
    view_id = body["view"]["id"]
    asyncio.create_task(respond.on_send(user_id, view_id, body_text))


# ---- run-campaigns nudge (scheduled) ----------------------------------------
# These live here, not in schedules.py, because their tests patch
# `slack_bot._post_channel` and the functions must resolve that name from this
# module's globals. The shared pester counter and `_roll_day` live in session.

_PESTER_MAX_HOURS = 4


def _run_reminder_text() -> str:
    who = f"<@{slack_config.SLACK_REMINDER_USER}> " if slack_config.SLACK_REMINDER_USER else ""
    _roll_day()
    sent = _pester["sent_today"]
    target = slack_config.SLACK_DAILY_TARGET
    remaining = max(0, target - sent)
    return (f":mage: {who}we are at {sent} of ~{target} emails today, about "
            f"{remaining} short of maxing out the day. Mention me with the volume "
            f"and ICPs, for example `@email_wizard 2000 to DTC brands`. I'll keep "
            f"nudging until we hit the target.")


async def _remind_run() -> None:
    """5:30pm Pacific: start the daily nudge unless the send target is already met."""
    _roll_day()
    if _pester["sent_today"] >= slack_config.SLACK_DAILY_TARGET:
        log.info("Run-nudge skipped: daily target already met (%d sent)",
                 _pester["sent_today"])
        return
    _pester["active"] = True
    _pester["started_at"] = datetime.now(ZoneInfo(slack_config.SLACK_SCHEDULE_TZ))
    if _state.get("mode") != "executing":
        await _post_channel(_run_reminder_text())
    log.info("Run-nudge started (%d of %d sent)", _pester["sent_today"],
             slack_config.SLACK_DAILY_TARGET)


async def _pester_run() -> None:
    """Every 5 min: re-nudge while active, until the target is met or the cutoff."""
    if not _pester["active"]:
        return
    _roll_day()
    if _pester["sent_today"] >= slack_config.SLACK_DAILY_TARGET:
        _pester["active"] = False
        return
    started = _pester["started_at"]
    if started and datetime.now(started.tzinfo) - started > timedelta(hours=_PESTER_MAX_HOURS):
        _pester["active"] = False
        log.info("Run-nudge stopped at cutoff")
        return
    if _state.get("mode") == "executing":
        return  # a campaign is sending right now; skip this tick, stay active
    await _post_channel(_run_reminder_text())


# ---- startup ----------------------------------------------------------------

async def main() -> None:
    global _bot_user_id
    auth = await app.client.auth_test()
    _bot_user_id = auth["user_id"]
    log.info("Authenticated as %s (%s)", auth.get("user"), _bot_user_id)

    if slack_config.SLACK_SCHEDULES_ENABLED:
        tz = ZoneInfo(slack_config.SLACK_SCHEDULE_TZ)
        scheduler = AsyncIOScheduler(timezone=tz)
        # 5:30pm: start the run-campaigns nudge (one-shot for now).
        scheduler.add_job(_remind_run, trigger="cron", hour=17, minute=30)
        # Temporarily disabled: the every-5-min re-nudge was too noisy. Re-enable
        # when we want the pester loop back.
        # scheduler.add_job(_pester_run, trigger="interval", minutes=5)
        # 9:00am: morning follow-ups (auto-send due OOO bumps, stage the rest) and
        # then the inbox triage broadcast, so the report is followed by the tables.
        scheduler.add_job(schedules._morning_followups, trigger="cron", hour=9, minute=0)
        scheduler.start()
        log.info("Schedules on (%s): run-nudge 17:30 (5m pester OFF), morning 09:00 "
                 "(follow-ups + triage)", slack_config.SLACK_SCHEDULE_TZ)

    handler = AsyncSocketModeHandler(app, slack_config.SLACK_APP_TOKEN)
    log.info("Slack wizard starting (Socket Mode), channel %s",
             slack_config.SLACK_CHANNEL_ID)
    await handler.start_async()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
