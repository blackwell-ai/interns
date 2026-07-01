"""The wizard's conversation core: the shared session state machine, the flow
that plans and executes a campaign, the reply/triage/Q&A helpers, and the live
scoreboard. This module owns the Bolt `app` and all mutable in-memory state
(`_state`, `_campaigns`, `_pester`); `slack_bot.py` imports `app` to attach the
event/action handlers and `main()`, `schedules.py` imports the state and reply
helpers for the cron jobs, and `blocks.py` draws the messages these post.

Nothing here rebinds `_state` / `_campaigns` / `_pester` (they are only mutated
in place), so `slack_bot.py` can re-export them as shared references and the
tests that poke `slack_bot._state[...]` see the same objects.
"""
import asyncio
import logging
import os
import re
import tempfile
import time
from datetime import datetime
from zoneinfo import ZoneInfo

import httpx
from slack_bolt.async_app import AsyncApp

from . import agent, executor, qa, slack_config, triage, triage_dismiss
from .blocks import _preview_blocks, _progress_blocks

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
                        "wizard/migrations. Nothing was changed.")
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
# max out the daily Gmail outbound (~2100 across senders). The pester *jobs* live
# in schedules.py; this shared counter lives here because _execute updates it.
_pester = {"active": False, "count_date": None, "sent_today": 0, "started_at": None}


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


# ---- draft override ---------------------------------------------------------

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
    # Generate the target niches now so they show in the preview and a human can
    # catch intent drift (e.g. "affiliate marketing" returning Robinhood) before
    # any send. This populates the cache run.py reads, so it is not wasted work.
    niche_preview: list[dict] = []
    if any((p.get("icp_desc") or "").lower() != "direct send" for p in plan_runs):
        await reply(":mag: Scrying the target niches...")
        try:
            niche_preview = await agent.preview_niches(plan_runs)
        except Exception:
            log.exception("niche preview failed")
    _state["niche_preview"] = niche_preview
    fallback, blocks = _preview_blocks(plan_runs, deferred, niche_preview)
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
                   "request_text": "", "deferred": 0, "draft_template": None,
                   "niche_preview": []})


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
