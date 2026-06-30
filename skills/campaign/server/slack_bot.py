"""Slack analog of the Telegram campaign wizard (bot.py).

Same campaign planning and execution, driven over Slack Socket Mode. The flow is
thread-based: a user @mentions the wizard once in the configured channel, the
wizard opens a thread and runs the whole exchange there, so follow-up replies in
that thread need no further @mention. The preview carries Send / Cancel buttons
(typed 'send' / 'cancel' still work). Messages are formatted with Block Kit.

Reuses agent.py (Claude planning) and executor.py (campaign runs, incl. the
WIZARD_TEST_MODE rehearsal) unchanged; only the messaging layer differs.

Run with:  python -m skills.campaign.server.slack_bot
"""
import asyncio
import json
import logging
import os
import re
import tempfile
import time
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import httpx
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler
from slack_bolt.async_app import AsyncApp

from skills.campaign import reply_followup

from . import agent, config, executor, gmail_auth, qa, slack_config, triage, triage_dismiss

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    level=logging.INFO,
)
log = logging.getLogger(__name__)

# idle -> awaiting_icp -> [awaiting_clarification] -> awaiting_preview -> executing
# One shared session at a time, pinned to the thread it runs in. thread_ts is the
# root message of the active conversation; replies and updates post into it.
_state: dict = {"mode": "idle", "pending_plan": None, "pending_request": None,
                "running_task": None, "progress": "", "thread_ts": None,
                "deferred": 0, "draft_template": None}

# Slack can redeliver the same event; track handled message ids to stay idempotent.
_seen_events: set[str] = set()

# Per-thread campaign records, keyed by thread_ts. Each holds the captured run
# log plus plan/status/results so the wizard can answer questions in that thread,
# both mid-run and after it finishes. Bounded to avoid unbounded memory growth.
_campaigns: dict[str, dict] = {}
_MAX_LOG_LINES = 4000
_MAX_RECORDS = 30

# Filled at startup from auth.test; used to spot @mentions and skip our own posts.
_bot_user_id: str = ""

_REMINDER = (
    ":mage: The wizard awaits. Tell me how many emails and which ICPs to target, "
    "in plain words, and I shall prepare the sending. For example:\n"
    "  `@email_wizard 2000 emails to DTC brands and 3PLs, 50/50`\n"
    "  `@email_wizard 500 emails to aerospace manufacturers`\n\n"
    "Name a specific account (\"through Samarjit\") and I shall send from it. "
    "Name more than one ICP without a split and I shall ask how to divide them. "
    "Once we are speaking, simply reply in this thread, no need to summon me again.\n\n"
    "Or ask me to *triage replies* (\"which replies need a response?\") and I "
    "shall scan our inboxes for prospects awaiting an answer."
)

app = AsyncApp(token=slack_config.SLACK_BOT_TOKEN)

_MENTION_RE = re.compile(r"<@[A-Z0-9]+>")

# Matches only the terminal send_update from executor (success, failure, or auth
# error). All other send_update calls are intermediate and must NOT advance the
# scoreboard pointer. Defined at module level so tests can import and verify it.
_RUN_DONE_RE = re.compile(
    r":mage:.*\bsent\b"       # ":mage: Armaan: 45 sent."
    r"|the sending faltered"   # ":warning: ...: the sending faltered (exit N)."
    r"|\bauth failed\b",       # "Armaan: auth failed — ..."
    re.I,
)

# Reply-triage is a separate, read-only command. One at a time. thread_ts is the
# last triage's thread, so an unmentioned "drop x@y.com" reply there is understood
# as an edit of that triage.
_triage_state = {"running": False, "thread_ts": None}
_TRIAGE_RE = re.compile(
    r"\b(triage|repl(y|ies)|respond(ed)?|responses?|"
    r"(wrote|written|got)\s+back)\b", re.I)


def _strip_mentions(text: str) -> str:
    """Drop the leading @bot tag (and any other user mentions) from the text."""
    return _MENTION_RE.sub("", text or "").strip()


def _is_triage(text: str) -> bool:
    """True when the message asks to scan inboxes for replies to handle."""
    low = text.lower()
    if _TRIAGE_RE.search(low):
        return True
    return "scan" in low and ("inbox" in low or "email" in low)


async def _start_triage(thread_ts: str | None) -> None:
    """Kick off a read-only inbox triage in the given thread, in the background."""
    reply = _reply_to(thread_ts)
    if _triage_state["running"]:
        await reply("A divination is already underway. One at a time, please.")
        return
    _triage_state["running"] = True
    # Remember the thread so a follow-up "drop x@y.com" reply here, with no
    # @mention, is read as an edit of this triage.
    _triage_state["thread_ts"] = thread_ts
    await reply(":crystal_ball: Peering into the inboxes. This may take a minute...")

    async def go() -> None:
        try:
            for m in await triage.run_triage(reply):
                await reply(m["text"], m.get("blocks"))
        except Exception as e:
            log.exception("triage failed")
            await reply(f"The divination failed: {str(e)[:200]}")
        finally:
            _triage_state["running"] = False

    asyncio.create_task(go())


async def _handle_triage_edit(cmd: dict, reply, by: str = "") -> None:
    """Apply a triage-list edit: dismiss people so they stop surfacing (now and on
    future runs), restore them ('undo'), or show who is dismissed. Read/writes the
    team-wide dismiss list; a missing store is reported, not raised."""
    action, emails = cmd["action"], cmd["emails"]
    try:
        if action == "show":
            rows = await triage_dismiss.list_dismissed()
            if not rows:
                await reply("No one is dismissed from triage right now.")
                return
            lines = [f"• {r['recipient']}" + (f"  —  {r['reason']}" if r.get("reason") else "")
                     for r in rows]
            await reply(f"Dismissed from triage ({len(rows)}):\n" + "\n".join(lines[:50]))
            return
        if action == "undo":
            restored = await triage_dismiss.undismiss(emails)
            if restored:
                await reply("Restored to triage:\n" + "\n".join(f"• {e}" for e in restored))
            else:
                await reply("None of those were on the dismiss list.")
            return
        recorded = await triage_dismiss.dismiss(emails, cmd.get("reason", ""), by)
        if not recorded:
            await reply("I did not catch an email to drop. Try 'drop name@company.com'.")
            return
        bullets = "\n".join(f"• {e}" for e in recorded)
        hint = f"\nSay 'undo {recorded[0]}' to restore."
        await reply(f"Removed {len(recorded)} from triage, now and on future runs:\n"
                    f"{bullets}{hint}")
    except Exception as e:  # noqa: BLE001 - surface store problems, never crash the bot
        msg = str(e)
        if "does not exist" in msg or "42P01" in msg or "404" in msg:
            await reply("The triage dismiss list is not set up yet (its table is "
                        "missing). An admin needs to run the migration in "
                        "server/migrations. Nothing was changed.")
        else:
            log.exception("triage edit failed")
            await reply(f"I could not update the dismiss list: {msg[:200]}")


_QUESTION_RE = re.compile(
    r"^\s*(what|how|why|who|whom|when|where|which|can|could|do|does|did|is|are|"
    r"was|were|will|should|would|has|have|any|tell me|show me|explain)\b",
    re.IGNORECASE)


def _is_question(text: str) -> bool:
    """Cheap, no-LLM gate for unmentioned thread messages: a clear question we
    should try to answer, rather than barging into every thread reply."""
    t = (text or "").strip()
    return bool(t) and (t.endswith("?") or bool(_QUESTION_RE.match(t)))


async def _start_qa(question: str, thread_ts: str | None) -> None:
    """Answer an open-ended question with the read-only Q&A agent, showing a live
    'working on it' message that is edited in place with progress, then the
    answer. Runs in the background so the socket is never blocked."""
    placeholder = await app.client.chat_postMessage(
        channel=slack_config.SLACK_CHANNEL_ID, thread_ts=thread_ts,
        text=":mage: Consulting the scrolls...")
    ts = placeholder["ts"]
    last = [0.0]

    async def on_step(label: str) -> None:
        now = time.monotonic()
        if now - last[0] < 2.0:  # throttle chat.update like the scoreboard does
            return
        last[0] = now
        try:
            await app.client.chat_update(
                channel=slack_config.SLACK_CHANNEL_ID, ts=ts, text=label)
        except Exception:  # noqa: BLE001 - a status redraw is best-effort
            pass

    async def go() -> None:
        try:
            answer = await qa.answer(question, on_step)
        except Exception as e:  # noqa: BLE001
            log.exception("qa failed")
            answer = f"My arts faltered on that one: {str(e)[:200]}"
        try:
            await app.client.chat_update(
                channel=slack_config.SLACK_CHANNEL_ID, ts=ts, text=answer[:3900])
        except Exception:  # noqa: BLE001 - fall back to a fresh message
            await _reply_to(thread_ts)(answer[:3900])

    asyncio.create_task(go())


def _reply_to(thread_ts: str | None):
    """A reply callable bound to a specific thread. Accepts plain text and/or
    Block Kit blocks, and always sends a text fallback for notifications."""
    async def reply(text: str | None = None, blocks: list | None = None) -> None:
        await app.client.chat_postMessage(
            channel=slack_config.SLACK_CHANNEL_ID,
            text=text or " ",
            blocks=blocks,
            thread_ts=thread_ts,
        )

    return reply


def _thread_reply():
    return _reply_to(_state.get("thread_ts"))


async def _post_channel(text: str | None = None, blocks: list | None = None) -> None:
    """Post to the channel root (not a thread) — for scheduled broadcasts."""
    await app.client.chat_postMessage(
        channel=slack_config.SLACK_CHANNEL_ID, text=text or " ", blocks=blocks)


async def _download_slack_file(file_info: dict) -> str | None:
    """Download a Slack file using the bot token. Returns text content or None."""
    url = file_info.get("url_private_download") or file_info.get("url_private")
    if not url:
        return None
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.get(
                url, headers={"Authorization": f"Bearer {slack_config.SLACK_BOT_TOKEN}"})
            r.raise_for_status()
            # Generous cap: CSVs are parsed in full deterministically. The
            # non-CSV (LLM) fallback re-truncates to keep the prompt reasonable.
            return r.text[:500_000]
    except Exception as e:
        log.warning("file download failed: %s", e)
        return None


# Daily "run campaigns" nudge state. It pesters from 5:30pm Pacific every 5 min
# until the day's sent total reaches the target (or a cutoff), then goes quiet.
# The goal is volume: a small send must not silence it, since the team wants to
# max out the daily Gmail outbound (~2100 across senders).
_pester = {"active": False, "count_date": None, "sent_today": 0, "started_at": None}
_PESTER_MAX_HOURS = 4


def _today():
    return datetime.now(ZoneInfo(slack_config.SLACK_SCHEDULE_TZ)).date()


def _roll_day() -> None:
    """Reset today's sent counter when the date changes."""
    today = _today()
    if _pester["count_date"] != today:
        _pester["count_date"] = today
        _pester["sent_today"] = 0


def record_campaign_sent(n: int) -> None:
    """Add a finished campaign's real sent count to today's running total, and
    silence the nudge once the daily target is met. Test-mode rehearsals do not
    call this, so simulated sends never count toward the quota."""
    _roll_day()
    _pester["sent_today"] += max(0, int(n or 0))
    if _pester["sent_today"] >= slack_config.SLACK_DAILY_TARGET:
        _pester["active"] = False


# ---- Block Kit rendering ----------------------------------------------------

def _one_sample_block(title: str, subject: str, body: str) -> dict:
    quoted = "\n".join("> " + ln for ln in body[:2500].splitlines())
    return {"type": "section", "text": {"type": "mrkdwn",
            "text": f"*{title}*\n*Subject:* {subject}\n{quoted}"}}


def _sample_blocks(run: dict) -> list:
    """Preview blocks for a run's email. For a direct send, render up to three of
    the actual recipients (real name, company, and personalized line) so the user
    can check the emails read well. Otherwise show one placeholder sample."""
    school = agent.school_for_email(run["email"])[0]
    leads = run.get("direct_leads") or []
    if leads:
        shown = min(3, len(leads))
        head = {"type": "context", "elements": [{"type": "mrkdwn",
            "text": f"Showing {shown} of {len(leads)} drafted scroll"
                    f"{'s' if len(leads) != 1 else ''}, each with its reader's "
                    f"own details. Skim them before sending."}]}
        out = [head]
        for lead in leads[:shown]:
            subject, body = agent.render_for_lead(run, lead)
            who = (lead.get("first_name") or "").strip()
            company = (lead.get("company") or "").strip()
            tag = " · ".join(x for x in (who, company) if x) or lead.get("email", "")
            out.append(_one_sample_block(
                f"To {tag} (from {run['from_name']}, {school})", subject, body))
        return out
    subject, sample = agent.render_sample(run)
    return [_one_sample_block(
        f"A sample scroll from {run['from_name']} ({school})", subject, sample)]


def _preview_blocks(plan_runs: list[dict], deferred: int) -> tuple[str, list]:
    total = sum(p["n_emails"] for p in plan_runs)
    n_senders = len({p["sender_key"] for p in plan_runs})
    run_lines = "\n".join(
        f"• *{p['icp_label']}* via {p['from_name']}: {p['n_emails']} emails"
        for p in plan_runs
    )

    fallback = f"The wizard's plan: {total} emails across {len(plan_runs)} runs."
    blocks = [
        {"type": "header", "text": {"type": "plain_text",
                                    "text": "\U0001F9D9 The wizard's plan"}},
        {"type": "section", "text": {"type": "mrkdwn",
         "text": f"*{total}* emails  ·  *{len(plan_runs)}* runs  ·  "
                 f"*{n_senders}* sender{'s' if n_senders != 1 else ''}"}},
        {"type": "section", "text": {"type": "mrkdwn", "text": run_lines}},
    ]
    if deferred:
        cap_total = len(agent.SENDERS) * agent.PER_ACCOUNT_DAILY_CAP
        blocks.append({"type": "context", "elements": [{"type": "mrkdwn",
            "text": f":warning: {deferred} emails exceed today's powers "
                    f"({len(agent.SENDERS)} x {agent.PER_ACCOUNT_DAILY_CAP} = "
                    f"{cap_total}/day) and were set aside."}]})
    blocks.append({"type": "divider"})
    blocks += _sample_blocks(plan_runs[0])
    if executor._test_mode():
        blocks.append({"type": "context", "elements": [{"type": "mrkdwn",
            "text": ":test_tube: *Test mode.* The sending is mere illusion. No "
                    "emails depart, no Hunter credits spent."}]})
    blocks.append({"type": "actions", "block_id": "wiz_confirm", "elements": [
        {"type": "button", "action_id": "wiz_send", "style": "primary",
         "text": {"type": "plain_text", "text": "Send ✨"}},
        {"type": "button", "action_id": "wiz_edit",
         "text": {"type": "plain_text", "text": "Edit draft ✏️"}},
        {"type": "button", "action_id": "wiz_cancel", "style": "danger",
         "text": {"type": "plain_text", "text": "Cancel"}},
    ]})
    return fallback, blocks


def _edit_modal(subject: str, body: str, private_metadata: str) -> dict:
    """A modal to revise the scroll. The teammate can hand-edit the subject and
    body directly, and/or describe a change for Claude to apply on top. Pre-filled
    with the current template (slots intact); private_metadata carries the preview
    message coordinates so the submit handler can refresh it."""
    return {
        "type": "modal",
        "callback_id": "wiz_edit_modal",
        "private_metadata": private_metadata,
        "title": {"type": "plain_text", "text": "Edit the scroll"},
        "submit": {"type": "plain_text", "text": "Save"},
        "close": {"type": "plain_text", "text": "Cancel"},
        "blocks": [
            {"type": "input", "block_id": "wiz_subj",
             "label": {"type": "plain_text", "text": "Subject"},
             "element": {"type": "plain_text_input", "action_id": "v",
                         "initial_value": subject}},
            {"type": "input", "block_id": "wiz_body",
             "label": {"type": "plain_text", "text": "Body"},
             "element": {"type": "plain_text_input", "action_id": "v",
                         "multiline": True, "initial_value": body}},
            {"type": "input", "block_id": "wiz_refine", "optional": True,
             "label": {"type": "plain_text", "text": "Or ask Claude to change it"},
             "element": {"type": "plain_text_input", "action_id": "v",
                         "multiline": True,
                         "placeholder": {"type": "plain_text",
                                         "text": "e.g. make it shorter and "
                                                 "mention we build eval tools"}}},
            {"type": "context", "elements": [{"type": "mrkdwn",
             "text": "Edit the text directly, or describe a change above and I "
                     "will apply it. Keep the slots {{first_name}}, {{company}}, "
                     "{{school}}, {{from_name}} so every scroll stays personalized."}]},
        ],
    }


def _write_draft_template(subject: str, body: str) -> str:
    """Write an edited draft to a temp template file (frontmatter subject + a
    plain-text body that run.py renders to HTML) and return its absolute path.
    The executor and render_sample both accept an absolute template path."""
    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".md", prefix="wiz_draft_", delete=False, encoding="utf-8")
    tmp.write(f"---\nsubject: {subject}\n---\n{body}\n")
    tmp.close()
    return tmp.name


def _validate_draft(subject: str, body: str) -> dict:
    """Block-id -> error message for an edited draft, empty when it is valid.
    Shape matches Slack's view-submission `errors` response."""
    errors = {}
    if not subject.strip():
        errors["wiz_subj"] = "The scroll needs a subject."
    if not body.strip():
        errors["wiz_body"] = "The scroll cannot be empty."
    return errors


def _install_draft_override(subject: str, body: str) -> str:
    """Persist a subject/body as a temp template and point every pending run at
    it (replacing any prior override). Returns the temp path."""
    old = _state.get("draft_template")
    if old:
        try:
            os.unlink(old)
        except OSError:
            pass
    path = _write_draft_template(subject.strip(), body.rstrip())
    _state["draft_template"] = path
    for run in _state.get("pending_plan") or []:
        run["template"] = path
    return path


def _apply_draft_edit(subject: str, body: str) -> bool:
    """Persist a hand-edited draft. Returns True when an override was applied,
    False when the text is unchanged from the current template (a no-op Save).
    Caller must validate first."""
    plan_runs = _state.get("pending_plan") or []
    if not plan_runs:
        return False
    cur_subject, cur_body = agent.editable_draft(plan_runs[0])
    if subject.strip() == cur_subject.strip() and body.strip() == cur_body.strip():
        return False  # nothing changed — keep the current template
    _install_draft_override(subject, body)
    return True


_RUN_ICON = {
    "queued":  "",
    "running": ":hourglass_flowing_sand:",
    "done":    ":white_check_mark:",
    "failed":  ":x:",
}


def _fmt_duration(seconds: float) -> str:
    """A short human duration: '45s' or '3m 12s'."""
    s = int(seconds)
    if s < 60:
        return f"{s}s"
    return f"{s // 60}m {s % 60}s"


def _progress_blocks(run_statuses: list[dict], done: bool,
                     credits: str = "", elapsed_s: float | None = None) -> list:
    total_sent = sum(s["sent"] or 0 for s in run_statuses)
    total_located = sum(s.get("located") or 0 for s in run_statuses)
    any_failed = any(s["state"] == "failed" for s in run_statuses)

    if done:
        header_text = "\U0001F9D9 Complete" if not any_failed else "\U0001F9D9 Done (with errors)"
    else:
        header_text = "⚡ Campaign in progress..."

    lines = []
    for s in run_statuses:
        p = s["run"]
        label = f"{p['icp_label']} via {p['from_name']}"
        icon = _RUN_ICON.get(s["state"], "")
        state = s["state"]
        if state == "queued":
            detail = "queued"
        elif state == "running":
            # Sourcing climbs a live "located" count; once composing is done the
            # run moves to a plain "sending..." (we do not tabulate sends live).
            phase = s.get("phase")
            if phase == "sending":
                detail = "sending..."
            elif phase == "locating":
                detail = f"{s.get('located') or 0} located..."
            else:
                detail = "starting..."
        else:
            n = s["sent"] if s["sent"] is not None else 0
            detail = f"{n} sent" if state == "done" else f"{n} sent (failed)"
        prefix = f"{icon} " if icon else "    "
        lines.append(f"{prefix}*{label}*   {detail}")

    n = len(run_statuses)
    if done:
        parts = [f"*{total_sent}* sent"]
        if credits:
            parts.append(f"{credits} Hunter credits")
        if elapsed_s is not None:
            parts.append(_fmt_duration(elapsed_s))
        parts.append(f"{n} run{'s' if n != 1 else ''}")
        stat_line = "  ·  ".join(parts)
    else:
        stat_line = f"*{total_located}* located" if total_located else "preparing..."

    return [
        {"type": "header", "text": {"type": "plain_text", "text": header_text}},
        {"type": "section", "text": {"type": "mrkdwn", "text": "\n".join(lines)}},
        {"type": "divider"},
        {"type": "context", "elements": [{"type": "mrkdwn", "text": stat_line}]},
    ]


# ---- core flow --------------------------------------------------------------

async def _build_csv_template(plan_runs: list[dict], reply) -> None:
    """For a direct/CSV send, draft one shared template that fits the audience
    (student + school intro kept, the rest the model's discretion) and install it
    as the editable draft override. Idempotent: skips if a template (generated or
    hand-edited) already exists. Best-effort: a failure leaves the default."""
    if _state.get("draft_template"):
        return  # already have a template for this session
    run = next((r for r in plan_runs if r.get("direct_leads")), None)
    if not run:
        return
    await reply(":sparkles: Studying your list and drafting a template that fits "
                "this audience. One moment...")
    school, others = agent.school_for_email(run["email"])
    try:
        subject, body = await asyncio.to_thread(
            agent.draft_csv_template, run["direct_leads"],
            _state.get("request_text", ""), school, others, run["from_name"])
    except Exception as e:
        log.warning("csv template generation failed: %s", e)
        return  # fall back to the run's default template
    path = _write_draft_template(subject, body)
    _state["draft_template"] = path
    for r in plan_runs:
        if r.get("direct_leads"):
            r["template"] = path


async def _present_plan(reply, plan_runs: list[dict], deferred: int) -> None:
    """Store the plan and post the formatted preview with Send / Cancel buttons."""
    plan_runs = [p for p in plan_runs if p.get("n_emails", 0) > 0]
    if not plan_runs:
        _reset()
        await reply("No sendings to conjure from that. Try rephrasing your wish.")
        return
    await _build_csv_template(plan_runs, reply)
    # Keep a hand-edited draft sticky across plan refinements ("make it 60",
    # "send via Ethan"): the override template carries only {{slots}}, so it is
    # sender- and ICP-agnostic and applies cleanly to the re-planned runs.
    draft = _state.get("draft_template")
    if draft:
        for p in plan_runs:
            p["template"] = draft
    _state["pending_plan"] = plan_runs
    _state["deferred"] = deferred
    _state["mode"] = "awaiting_preview"
    log.info("plan: %s", [(p["from_name"], p["icp_label"], p["n_emails"])
                          for p in plan_runs])
    fallback, blocks = _preview_blocks(plan_runs, deferred)
    await reply(fallback, blocks)


async def _execute(plan_runs: list[dict]) -> None:
    """Run the confirmed plan, streaming live status into one edited Slack message.
    The record persists so the wizard can answer questions about the run later."""
    _state["mode"] = "executing"
    _state["pending_plan"] = None
    _state["progress"] = ""
    thread = _state.get("thread_ts")

    record = {"thread_ts": thread, "status": "running", "plan": plan_runs,
              "log": [], "results": None, "progress": "", "started": time.time()}
    _register(thread, record)

    def add_log(line: str) -> None:
        record["log"].append(line)
        extra = len(record["log"]) - _MAX_LOG_LINES
        if extra > 0:
            del record["log"][:extra]

    # Per-run scoreboard; runs execute sequentially so we advance a pointer.
    # phase is None -> "locating" (sourcing) -> "sending"; located climbs live.
    run_statuses = [{"run": p, "state": "queued", "sent": None,
                     "located": None, "phase": None} for p in plan_runs]
    if run_statuses:
        run_statuses[0]["state"] = "running"
    current_idx = [0]
    # Campaign-wide Hunter spend, reported once at the end by run_all.
    totals = {"credits": ""}
    # Throttle the live "located" redraws so a fast-sourcing run does not hammer
    # Slack's chat.update rate limit; milestones and the final draw bypass it.
    last_refresh = {"t": 0.0}

    if executor._test_mode():
        await _reply_to(thread)(":test_tube: Test mode. The sending is mere illusion, no "
                                "emails depart and no Hunter credits are spent.")

    # Post the live scoreboard and pin ⏳ to the trigger message.
    prog_resp = await app.client.chat_postMessage(
        channel=slack_config.SLACK_CHANNEL_ID,
        thread_ts=thread,
        text="Sending in progress...",
        blocks=_progress_blocks(run_statuses, done=False),
    )
    progress_ts = prog_resp.get("ts")

    if thread:
        try:
            await app.client.reactions_add(
                channel=slack_config.SLACK_CHANNEL_ID,
                timestamp=thread, name="hourglass_flowing_sand")
        except Exception:
            pass

    async def _refresh_scoreboard(final: bool = False, throttle: bool = False) -> None:
        if not progress_ts:
            return
        if throttle and not final:
            now = time.monotonic()
            if now - last_refresh["t"] < 2.0:
                return  # too soon since the last redraw — value already stored
        last_refresh["t"] = time.monotonic()
        elapsed = time.time() - record["started"] if final else None
        try:
            await app.client.chat_update(
                channel=slack_config.SLACK_CHANNEL_ID,
                ts=progress_ts,
                text="Sending complete." if final else "Sending in progress...",
                blocks=_progress_blocks(run_statuses, done=final,
                                        credits=totals["credits"], elapsed_s=elapsed),
            )
        except Exception as e:
            log.warning("scoreboard update failed: %s", e)

    async def send_update(msg: str) -> None:
        add_log(f"[update] {msg}")
        # Live "located" count for the running run, climbing as leads are sourced.
        # Throttled redraw; the stored value is always current.
        ml = re.search(r"(\d+)\s+located", msg)
        if ml:
            idx = current_idx[0]
            if idx < len(run_statuses):
                run_statuses[idx]["located"] = int(ml.group(1))
                run_statuses[idx]["phase"] = "locating"
                await _refresh_scoreboard(throttle=True)
            return
        # Composing is done -> this run is now sending.
        if re.search(r"scrolls drafted", msg):
            idx = current_idx[0]
            if idx < len(run_statuses):
                run_statuses[idx]["phase"] = "sending"
                await _refresh_scoreboard()
            return
        # Campaign-wide Hunter spend, reported once at the very end.
        mc = re.search(r"drew (\d+) Hunter credits", msg)
        if mc:
            totals["credits"] = mc.group(1)
            return
        if not _RUN_DONE_RE.search(msg):
            return  # intermediate update — logged, scoreboard unchanged
        m = re.search(r"(\d+)\s+sent", msg)
        sent = int(m.group(1)) if m else 0
        failed = bool(re.search(r"faltered|auth failed", msg, re.I))
        idx = current_idx[0]
        if idx < len(run_statuses):
            run_statuses[idx]["state"] = "failed" if failed else "done"
            run_statuses[idx]["sent"] = sent
        current_idx[0] += 1
        nxt = current_idx[0]
        if nxt < len(run_statuses):
            run_statuses[nxt]["state"] = "running"
        await _refresh_scoreboard()

    def set_progress(msg: str) -> None:
        _state["progress"] = msg
        record["progress"] = msg

    task = asyncio.create_task(
        executor.run_all(plan_runs, send_update, set_progress, add_log))
    _state["running_task"] = task
    def _count_today() -> None:
        # Real sends only count toward the daily quota; rehearsals do not.
        if not executor._test_mode():
            record_campaign_sent(sum(s["sent"] or 0 for s in run_statuses))

    try:
        results = await task
    except asyncio.CancelledError:
        record["status"] = "stopped"
        _count_today()
        await _refresh_scoreboard(final=True)
        _reset()
        await _reply_to(thread)("The ritual is halted.")
        return

    record["status"] = "done"
    record["results"] = results
    _count_today()

    # Lock in the final scoreboard and swap ⏳ -> ✅ on the trigger.
    await _refresh_scoreboard(final=True)
    if thread:
        for name, adding in [("hourglass_flowing_sand", False), ("white_check_mark", True)]:
            try:
                fn = app.client.reactions_add if adding else app.client.reactions_remove
                await fn(channel=slack_config.SLACK_CHANNEL_ID, timestamp=thread, name=name)
            except Exception:
                pass

    _reset()


def _reset() -> None:
    # Drop any hand-edited draft override so the next campaign starts from the
    # canonical template, and remove its temp file.
    path = _state.get("draft_template")
    if path:
        try:
            os.unlink(path)
        except OSError:
            pass
    _state.update({"mode": "idle", "pending_plan": None, "pending_request": None,
                   "running_task": None, "progress": "", "thread_ts": None,
                   "request_text": "", "deferred": 0, "draft_template": None})


def _register(thread_ts: str | None, record: dict) -> None:
    """Store a campaign record, evicting the oldest if over the cap."""
    if not thread_ts:
        return
    _campaigns[thread_ts] = record
    if len(_campaigns) > _MAX_RECORDS:
        oldest = sorted(_campaigns.items(), key=lambda kv: kv[1].get("started", 0))
        for key, _ in oldest[: len(_campaigns) - _MAX_RECORDS]:
            _campaigns.pop(key, None)


def _plan_summary(plan: list[dict]) -> str:
    total = sum(p["n_emails"] for p in plan)
    lines = [f"- {p['icp_label']} via {p['from_name']}: {p['n_emails']} emails"
             for p in plan]
    return f"{total} emails across {len(plan)} runs:\n" + "\n".join(lines)


async def _answer(record: dict, question: str, reply) -> None:
    """Answer a question about one campaign via Claude, grounded in its log."""
    log_text = "\n".join(record.get("log", []))[-12000:]
    try:
        ans = await asyncio.to_thread(
            agent.answer_about_campaign, question,
            plan_summary=_plan_summary(record["plan"]),
            status=record["status"], results=record.get("results"),
            progress=record.get("progress", ""), log_text=log_text)
    except Exception as e:
        await reply(f"I cannot find that in the scrolls: {e}")
        return
    await reply(ans)


async def _route(text: str, reply) -> None:
    """State machine shared by the typed flow and (for send/cancel) the buttons."""
    low = text.lower()

    if low == "stop":
        task = _state.get("running_task")
        if _state["mode"] == "idle":
            await reply("There is no sending underway to halt.")
            return
        if task and not task.done():
            task.cancel()
            await reply("Halting the ritual...")
        else:
            _reset()
            await reply("The ritual is halted.")
        return

    if _state["mode"] == "idle":
        if low in ("go", "send", "start", "campaign", ""):
            _state["mode"] = "awaiting_icp"
            await reply(_REMINDER)
        else:
            _state["mode"] = "awaiting_icp"
            await _plan_and_present(text, reply)
        return

    if _state["mode"] == "executing":
        await reply(_state.get("progress")
                    or "The work is underway. I shall speak when it is done.")
        return

    if _state["mode"] == "awaiting_preview":
        if low in ("send", "yes", "y", "go", "confirm"):
            plan_runs = _state.get("pending_plan")
            if not plan_runs:
                _reset()
                await reply("Nothing awaits your word. Summon me anew.")
                return
            await _execute(plan_runs)
        elif low in ("cancel", "no", "n", "abort"):
            _reset()
            await reply("As you wish. The sending is cancelled.")
        else:
            # Anything else is a refinement (change sender, count, or ICP). Merge
            # it with the original request and re-plan, so "send via Ethan" or
            # "make it 60" works instead of being ignored.
            base = _state.get("request_text", "")
            combined = f"{base}\n\nAdjustment: {text}" if base else text
            _state["request_text"] = combined
            await reply(":crystal_ball: Reworking the plan...")
            try:
                result = await asyncio.to_thread(agent.plan, combined, False)
            except Exception as e:
                await reply(f"I could not read that change: {e}\nTry again, or 'cancel'.")
                return
            await _present_plan(reply, result["runs"], result["deferred"])
        return

    if _state["mode"] == "awaiting_clarification":
        combined = f"{_state.get('pending_request', '')}\n\nSplit / details: {text}"
        _state["pending_request"] = None
        _state["request_text"] = combined
        await reply(":crystal_ball: Consulting the scrolls...")
        try:
            result = await asyncio.to_thread(agent.plan, combined, False)
        except Exception as e:
            _reset()
            await reply(f"I could not read that: {e}\nTry again.")
            return
        await _present_plan(reply, result["runs"], result["deferred"])
        return

    await _plan_and_present(text, reply)


async def _present_csv_leads(leads: list[dict], text: str, reply) -> None:
    """Build and present a direct send from a deterministically parsed CSV,
    skipping LLM planning entirely (so a big list cannot truncate)."""
    _state["request_text"] = text
    n = len(leads)
    await reply(f":scroll: Read {n} contact{'s' if n != 1 else ''} from your file. "
                "Preparing the sending...")
    senders = agent.senders_in_text(text)
    result = agent.build_direct_plan(leads, senders)
    await _present_plan(reply, result["runs"], result["deferred"])


async def _plan_and_present(text: str, reply) -> None:
    _state["request_text"] = text
    await reply(":crystal_ball: Consulting the scrolls...")
    try:
        result = await asyncio.to_thread(agent.plan, text)
    except Exception as e:
        _reset()
        await reply(f"I could not read your request: {e}\nTry again.")
        return
    if "clarify" in result:
        _state["pending_request"] = text
        _state["mode"] = "awaiting_clarification"
        await reply(result["clarify"])
        return
    await _present_plan(reply, result["runs"], result["deferred"])


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
        # A fresh @mention. Triage and questions are read-only; a send request
        # starts a (gated) campaign session.
        if is_mention:
            if not csv_leads and _is_triage(text):
                await _start_triage(thread_ts or event.get("ts"))
                return
            # Not a CSV handoff and not a send request -> answer it as a question.
            if not csv_leads and text.strip() and \
                    await qa.classify_intent(text) == "question":
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


# ---- scheduled jobs ---------------------------------------------------------

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


async def _daily_triage() -> None:
    """Scan the inboxes, post the tables, then ping the team. Called at the tail of
    the morning follow-up job so the report is followed by the triage."""
    try:
        await _post_channel(":scroll: Running the daily inbox triage...")
        for m in await triage.run_triage(_post_channel):
            await _post_channel(m["text"], m.get("blocks"))
        await _post_channel("<!channel> these are today's replies worth handling. "
                            "Please take the ones owned by your account.")
        log.info("Daily triage broadcast sent")
    except Exception:
        log.exception("daily triage failed")
        await _post_channel("The morning triage faltered. Check the logs.")


# The sender mailboxes the morning pass scans and sends from (those with a stored
# refresh token on the server).
_FOLLOWUP_ACCOUNTS = list(gmail_auth._SENDER_REFRESH_KEYS.keys())


def _chunk_sections(lines: list[str], limit: int = 2700, cap: int = 60) -> list[dict]:
    """Pack mrkdwn lines into section blocks under Slack's text limit, capping the
    total so one giant morning never blows past Slack's block ceiling."""
    if len(lines) > cap:
        extra = len(lines) - cap
        lines = lines[:cap] + [f"_...and {extra} more_"]
    blocks, buf = [], ""
    for ln in lines:
        if len(buf) + len(ln) + 1 > limit:
            blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": buf.rstrip()}})
            buf = ""
        buf += ln + "\n"
    if buf.strip():
        blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": buf.rstrip()}})
    return blocks


def _morning_report_blocks(results: list[dict]) -> tuple[str, list]:
    """Build the Block Kit morning report from per-account run_morning summaries."""
    sent = [(r["account"], x) for r in results for x in r["sent"]]
    scheduled = [(r["account"], x) for r in results for x in r["scheduled"]]
    drafts = [(r["account"], x) for r in results for x in r["redirect_drafts"]]
    errors = [(r["account"], x) for r in results for x in r["errors"]]

    fallback = (f"Morning follow-ups: {len(sent)} sent, {len(scheduled)} scheduled, "
                f"{len(drafts)} drafts to approve.")
    blocks = [
        {"type": "header", "text": {"type": "plain_text",
                                    "text": "☀️ Morning follow-ups"}},
        {"type": "section", "text": {"type": "mrkdwn",
         "text": f"*{len(sent)}* out-of-office bumps auto-sent  ·  "
                 f"*{len(scheduled)}* scheduled for later  ·  "
                 f"*{len(drafts)}* redirect drafts awaiting approval"
                 + (f"  ·  :warning: *{len(errors)}* errors" if errors else "")}},
    ]

    if sent:
        blocks.append({"type": "divider"})
        blocks.append({"type": "section", "text": {"type": "mrkdwn",
                       "text": f"*Auto-responded now* ({len(sent)})"}})
        lines = [f"• {x['to']}  _({reply_followup.owner_name(acct)})_" for acct, x in sent]
        blocks += _chunk_sections(lines)

    if scheduled:
        scheduled.sort(key=lambda ax: ax[1].get("date", ""))
        blocks.append({"type": "divider"})
        blocks.append({"type": "section", "text": {"type": "mrkdwn",
                       "text": f"*Scheduled to send when they return* ({len(scheduled)})"}})
        lines = [f"• `{x.get('date','?')}`  {x['to']}  _({reply_followup.owner_name(acct)})_"
                 for acct, x in scheduled]
        blocks += _chunk_sections(lines)

    if drafts:
        blocks.append({"type": "divider"})
        blocks.append({"type": "section", "text": {"type": "mrkdwn",
                       "text": f"*Redirect drafts awaiting your approval* ({len(drafts)})"}})
        lines = [f"• {x['to']}  _({reply_followup.owner_name(acct)})_" for acct, x in drafts]
        blocks += _chunk_sections(lines)

    if errors:
        blocks.append({"type": "divider"})
        lines = [f"• {x.get('note','')[:80]} — {x.get('detail','')[:80]}" for _a, x in errors]
        blocks.append({"type": "section", "text": {"type": "mrkdwn",
                       "text": "*Errors*\n" + "\n".join(lines[:20])}})

    return fallback, blocks


async def _morning_followups() -> None:
    """9am Pacific: for each sender, auto-send due out-of-office bumps, hold future
    ones as drafts to send on the day, and stage redirect drafts for approval. Post
    the report, then run the inbox triage so it follows right after."""
    if not slack_config.SLACK_FOLLOWUP_ENABLED:
        await _daily_triage()
        return
    # The contacted ledger is team-wide; read it with the service-role key so the
    # redirect dedup sees every teammate's sends, not just the bot's rows.
    os.environ["TRIAGE_LEDGER_SERVICE_KEY"] = os.environ.get("SUPABASE_SECRET_KEY", "")
    await _post_channel(":sunrise: Running the morning follow-ups...")
    results = []
    for account in _FOLLOWUP_ACCOUNTS:
        try:
            res = await reply_followup.run_morning(
                account, get_token=gmail_auth.get_access_token, auto_send=True)
            results.append(res)
        except Exception as e:  # noqa: BLE001 - one bad account must not stop the rest
            log.exception("morning follow-ups failed for %s", account)
            results.append({"account": account, "sent": [], "scheduled": [],
                            "redirect_drafts": [],
                            "errors": [{"note": account, "detail": str(e)[:150]}]})
    try:
        fallback, blocks = _morning_report_blocks(results)
        await _post_channel(fallback, blocks)
    except Exception:
        log.exception("morning report render failed")
        await _post_channel("The morning follow-ups ran but the report failed to render.")
    # The report is followed by the triage tables.
    await _daily_triage()


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
        scheduler.add_job(_morning_followups, trigger="cron", hour=9, minute=0)
        scheduler.start()
        log.info("Schedules on (%s): run-nudge 17:30 (5m pester OFF), morning 09:00 "
                 "(follow-ups + triage)", slack_config.SLACK_SCHEDULE_TZ)

    handler = AsyncSocketModeHandler(app, slack_config.SLACK_APP_TOKEN)
    log.info("Slack wizard starting (Socket Mode), channel %s",
             slack_config.SLACK_CHANNEL_ID)
    await handler.start_async()


if __name__ == "__main__":
    asyncio.run(main())
