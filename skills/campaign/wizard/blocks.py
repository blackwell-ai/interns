"""Block Kit rendering for the Slack wizard.

Pure builders: every function here takes plain data (plans, run statuses, leads,
follow-up results) and returns Slack Block Kit dicts. No conversation state, no
`app`, no network. `session.py` and `schedules.py` call these to draw messages;
keeping them here means the layout can be read and changed in one place.
"""
from skills.campaign import reply_followup, visibility

from . import agent, executor


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


def _niche_blocks(niche_preview: list[dict]) -> list:
    """Render the target niches (and a few sample domains) so a teammate can spot
    intent drift before confirming. Niche labels are capped per ICP to stay under
    Slack's 3000-char section limit; sample domains go in a context line."""
    blocks: list = []
    for np in niche_preview:
        if not np.get("niches"):
            continue
        shown = np["niches"][:14]
        more = len(np["niches"]) - len(shown)
        niche_str = ", ".join(shown) + (f"  _+{more} more_" if more > 0 else "")
        blocks.append({"type": "section", "text": {"type": "mrkdwn",
            "text": f"*Target niches — {np['label']}:*\n{niche_str}"}})
        for s in np.get("samples", []):
            blocks.append({"type": "context", "elements": [{"type": "mrkdwn",
                "text": f"e.g. _{s['niche']}_: " + ", ".join(s["domains"])}]})
    if blocks:
        blocks.append({"type": "context", "elements": [{"type": "mrkdwn",
            "text": ":eyes: Check these match your target. If a niche or sample "
                    "looks off, hit Cancel and rephrase before sending."}]})
    return blocks


def _preview_blocks(plan_runs: list[dict], deferred: int,
                    niche_preview: list[dict] | None = None) -> tuple[str, list]:
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
    if niche_preview:
        blocks += _niche_blocks(niche_preview)
    if deferred:
        cap_total = len(agent.SENDERS) * agent.PER_ACCOUNT_DAILY_CAP
        blocks.append({"type": "context", "elements": [{"type": "mrkdwn",
            "text": f":warning: {deferred} emails exceed today's powers "
                    f"({len(agent.SENDERS)} x {agent.PER_ACCOUNT_DAILY_CAP} = "
                    f"{cap_total}/day) and were set aside."}]})
    blocks.append({"type": "divider"})
    blocks += _sample_blocks(plan_runs[0])
    if any(p.get("geo") for p in plan_runs):
        names = ["first_name", "company", *visibility.SLOTS]
        listed = ", ".join("`{{" + n + "}}`" for n in names)
        blocks.append({"type": "context", "elements": [{"type": "mrkdwn",
            "text": ":sparkles: GEO fields you can use in the copy (hit *Edit "
                    f"draft*): {listed}. Each is filled per brand at send time."}]})
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


# ---- /respond review queue modals -------------------------------------------

def _respond_picker_modal() -> dict:
    """First modal of /respond: pick whose inbox to work. A founder picker every
    time keeps it simple (no Slack-user-to-founder mapping) and lets anyone drive
    any founder's queue."""
    options = [{"text": {"type": "plain_text", "text": f"{s['from_name']} ({s['email']})"},
                "value": s["key"]} for s in agent.SENDERS]
    return {
        "type": "modal",
        "callback_id": "resp_pick",
        "title": {"type": "plain_text", "text": "Respond to replies"},
        "submit": {"type": "plain_text", "text": "Start"},
        "close": {"type": "plain_text", "text": "Cancel"},
        "blocks": [
            {"type": "input", "block_id": "resp_founder",
             "label": {"type": "plain_text", "text": "Whose replies?"},
             "element": {"type": "static_select", "action_id": "v",
                         "placeholder": {"type": "plain_text", "text": "Pick a founder"},
                         "options": options}},
            {"type": "context", "elements": [{"type": "mrkdwn",
             "text": "I will pull up each reply-worthy email in turn with a draft "
                     "grounded in your past replies. You edit and send in-thread."}]},
        ],
    }


def _respond_info_modal(title: str, text: str) -> dict:
    """A no-input modal (loading / done / error): just a message and a Close."""
    return {
        "type": "modal",
        "callback_id": "resp_info",
        "title": {"type": "plain_text", "text": title[:24]},
        "close": {"type": "plain_text", "text": "Close"},
        "blocks": [{"type": "section", "text": {"type": "mrkdwn", "text": text[:2900]}}],
    }


def _message_sections(text: str, cap_chars: int = 18000) -> list[dict]:
    """Split a (possibly long) message into quoted section blocks, each under
    Slack's 3000-char-per-block limit, so the modal scrolls through the whole
    thing instead of truncating. Only a pathologically huge blob is capped."""
    text = (text or "").strip() or "(no message text)"
    if len(text) > cap_chars:
        text = text[:cap_chars].rstrip() + "\n… (truncated)"
    # Quote each line, hard-splitting any single line that alone exceeds the limit.
    pieces: list[str] = []
    for ln in text.splitlines() or [""]:
        s = "> " + ln
        while len(s) > 2800:
            pieces.append(s[:2800])
            s = "> " + s[2800:]
        pieces.append(s)
    blocks, buf = [], ""
    for p in pieces:
        if buf and len(buf) + len(p) + 1 > 2800:
            blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": buf}})
            buf = ""
        buf = (buf + "\n" + p) if buf else p
    if buf:
        blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": buf}})
    return blocks


def _respond_deck_modal(*, founder_name: str, pos: int, total: int, sent: int,
                        skipped: int, ready: int, who: str, subject: str,
                        their_message: str, body: str, category: str,
                        n_examples: int, mode: str, can_prev: bool, can_next: bool,
                        private_metadata: str, received: str = "",
                        body_block_id: str = "resp_body") -> dict:
    """One card in the reply-review deck. `mode` selects the state:
      review  - draft ready: editable reply + Accept & send (submit)
      pending - still drafting this one (no submit)
      sent    - already sent this session (read-only, no submit)
      failed  - could not draft (no submit; Regenerate offered)
    Prev/Next page through the whole deck; edits are captured on every button."""
    counters = f"{pos} of {total}"
    tallies = []
    if sent:
        tallies.append(f":white_check_mark: {sent} sent")
    if skipped:
        tallies.append(f":fast_forward: {skipped} skipped")
    if ready < total:
        tallies.append(f":hourglass_flowing_sand: {ready}/{total} drafted")
    tail = ("  ·  " + "  ·  ".join(tallies)) if tallies else ""

    hdr = f"*To:* {who or '(unknown)'}\n*Subject:* {subject or '(none)'}"
    if received:
        hdr += f"\n*Replied:* {received}"
    blocks: list = [
        {"type": "context", "elements": [{"type": "mrkdwn",
         "text": f":mage: *{founder_name}*  ·  {counters}{tail}"}]},
        {"type": "section", "text": {"type": "mrkdwn", "text": hdr}},
        {"type": "section", "text": {"type": "mrkdwn", "text": "*Their reply*"}},
        # The message is split across as many blocks as it needs; the modal scrolls.
        *_message_sections(their_message),
        {"type": "divider"},
    ]

    submit = None
    if mode == "review":
        src = (f"drafted from {n_examples} of your past repl"
               f"{'y' if n_examples == 1 else 'ies'} (category: {category})"
               if n_examples else "no past examples yet, so this is a plain first draft")
        blocks.append({"type": "input", "block_id": body_block_id,
                       "label": {"type": "plain_text", "text": "Your reply"},
                       "element": {"type": "plain_text_input", "action_id": "v",
                                   "multiline": True, "initial_value": body[:2900]}})
        blocks.append({"type": "context", "elements": [{"type": "mrkdwn", "text": f":sparkles: {src}"}]})
        submit = "Accept & send ✨"
    elif mode == "pending":
        blocks.append({"type": "section", "text": {"type": "mrkdwn",
                       "text": f":hourglass_flowing_sand: *Step 2 of 2: drafting replies* "
                               f"({ready} of {total} ready).\n\nThis card is still "
                               "drafting. It will fill in here on its own, or hit Next "
                               "to review one that is already done."}})
    elif mode == "sent":
        blocks.append({"type": "section", "text": {"type": "mrkdwn",
                       "text": ":white_check_mark: *Sent.*\n"
                               + "\n".join("> " + ln for ln in body.splitlines())[:2600]}})
    else:  # failed
        blocks.append({"type": "section", "text": {"type": "mrkdwn",
                       "text": ":warning: Could not draft this one. Hit Regenerate to "
                               "retry, or Next to move on."}})

    nav: list = []
    if can_prev:
        nav.append({"type": "button", "action_id": "resp_prev",
                    "text": {"type": "plain_text", "text": "◀ Prev"}})
    if can_next:
        nav.append({"type": "button", "action_id": "resp_next",
                    "text": {"type": "plain_text", "text": "Next ▶"}})
    if mode in ("review", "failed"):
        nav.append({"type": "button", "action_id": "resp_regen",
                    "text": {"type": "plain_text", "text": "Regenerate ♻️"}})
    if nav:
        blocks.append({"type": "actions", "block_id": "resp_actions", "elements": nav})

    view = {
        "type": "modal",
        "callback_id": "resp_review",
        "private_metadata": private_metadata,
        "title": {"type": "plain_text", "text": "Review replies"},
        "close": {"type": "plain_text", "text": "Close"},
        "blocks": blocks,
    }
    if submit:
        view["submit"] = {"type": "plain_text", "text": submit}
    return view


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
