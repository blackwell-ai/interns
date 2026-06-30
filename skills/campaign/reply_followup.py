#!/usr/bin/env python3
"""Follow up the mechanical reply cases: redirects and out-of-office.

Two modes over the same detection (the triage from reply_triage_probe.py):

  - CLI default: draft-only. Stages Gmail drafts for review, sends nothing.
  - run_morning (the Slack 9am job): auto-sends out-of-office bumps that are due,
    holds future bumps as drafts to send on the return date, and stages redirects
    as drafts for human approval.

All Gmail I/O goes through the REST API with an injected bearer token, so the same
code runs from the CLI (gog-minted token) and on Railway (refresh-token exchange),
where the gog binary is absent.

In draft-only mode it writes a Gmail DRAFT (never sends) for review:

  - redirect with an email ("reach katie@acme.com instead") -> a fresh draft to
    the new contact with a referral opener and our pitch.
  - redirect naming a person but no email -> an in-thread draft back to the
    original sender asking for the best email. No Hunter credits spent guessing.
  - out-of-office -> an in-thread draft bump, with the stated return date surfaced
    in the report so you send it once they are back.

Nothing is sent. Every action is a draft you approve in Gmail. Re-running is safe:
a thread (or new-contact address) that already has a draft is skipped.

Usage:
  python3 skills/campaign/reply_followup.py --account you@blackwell.com --ledger
  python3 skills/campaign/reply_followup.py --account you@blackwell.com --ledger --dry-run
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import html as html_mod
import json
import os
import re
import sys
import time
from datetime import date, datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate
from pathlib import Path

import httpx

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))
sys.path.insert(0, str(_REPO_ROOT / "toolbox" / "src"))

from skills.campaign import gog_auth
from skills.campaign import reply_triage_probe as probe
from toolbox.primitives.gmail import lib as gmail_lib

# Default token source for the CLI (local gog keyring). The Slack wizard injects
# the server's refresh-token exchange instead, since gog is not on Railway.
_DEFAULT_GET_TOKEN = gog_auth.get_access_token


# Team roster: first name + school per sender, so a referral draft signs off
# correctly and names the right school. Mirrors SENDERS in server/agent.py and
# TEAM in reply_triage_probe.py.
_ROSTER = {
    "armaan.priyadarshan.29@dartmouth.edu": ("Armaan", "Dartmouth"),
    "samarjit.deshmukh.29@dartmouth.edu": ("Samarjit", "Dartmouth"),
    "ethanpzhou@berkeley.edu": ("Ethan", "Berkeley"),
    "shamitd@stanford.edu": ("Shamit", "Stanford"),
    "shamit.dsouza@gmail.com": ("Shamit", "Stanford"),
}
_ALL_SCHOOLS = ["Stanford", "Dartmouth", "Berkeley"]

_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")


# ---- pure helpers (no I/O, unit tested) ----------------------------------

def owner_name(email: str) -> str:
    """First name to sign a draft from, for a team sender email."""
    email = (email or "").strip().lower()
    if email in _ROSTER:
        return _ROSTER[email][0]
    local = email.split("@")[0]
    return (re.split(r"[._\-]", local)[0] or local).capitalize()


def owner_school(email: str) -> tuple[str, str]:
    """(school, other_schools) for a team sender, mirroring agent.school_for_email."""
    email = (email or "").strip().lower()
    if email in _ROSTER:
        school = _ROSTER[email][1]
    else:
        domain = email.rsplit("@", 1)[-1]
        if "dartmouth" in domain:
            school = "Dartmouth"
        elif "berkeley" in domain:
            school = "Berkeley"
        else:
            school = "Stanford"
    others = " and ".join(s for s in _ALL_SCHOOLS if s != school)
    return school, others


def first_name_from(value: str) -> str:
    """Best-effort first name from a display name or a bare email address."""
    value = (value or "").strip()
    if not value:
        return "there"
    # Strip an angle-bracket address if present: "Katie Smith <k@x.com>".
    name = re.sub(r"<[^>]+>", "", value).strip().strip('"').strip()
    if name and "@" not in name:
        return name.split()[0]
    # Fall back to the local part of an email.
    m = _EMAIL_RE.search(value)
    if m:
        local = m.group(0).split("@")[0]
        return (re.split(r"[._\-]", local)[0] or local).capitalize()
    return "there"


def parse_contact(reroute_to: str) -> tuple[str, str]:
    """Split a free-text reroute target into (name, email). Either may be ''.

    Handles 'Katie Smith <katie.s@acme.com>', 'katie.s@acme.com', and a bare
    'Katie Smith' with no address.
    """
    text = (reroute_to or "").strip()
    email = ""
    m = _EMAIL_RE.search(text)
    if m:
        email = m.group(0).strip().lower()
        text = text.replace(m.group(0), "")
    name = re.sub(r"[<>(),;:]", " ", text)
    name = re.sub(r"\s+", " ", name).strip().strip('"').strip()
    return name, email


def latest_inbound_id(messages: list[dict], our_addrs: set[str]) -> str:
    """Gmail message id of the most recent message NOT from us, for in-thread reply
    targeting. '' if the thread has no inbound message."""
    for m in reversed(messages or []):
        if probe._addr(m) not in our_addrs:
            return m.get("id", "")
    return ""


def last_outbound_id(messages: list[dict], our_addrs: set[str]) -> str:
    """Gmail message id of our most recent message in the thread (our original
    pitch on a plain OOO thread). '' if we never sent into this thread. Anchoring
    a bump here, with a quote, carries our pitch inline so context never depends on
    the recipient's client threading the auto-reply correctly."""
    for m in reversed(messages or []):
        if probe._addr(m) in our_addrs:
            return m.get("id", "")
    return ""


def render_referral(new_first: str, owner_email: str, referrer_first: str) -> tuple[str, str]:
    """A complete, sendable referral pitch to a newly named contact."""
    school, others = owner_school(owner_email)
    owner = owner_name(owner_email)
    intro = (f"{referrer_first} pointed me your way" if referrer_first
             else "I was pointed your way by a colleague of yours")
    body = (
        f"<p>Hi {new_first},</p>"
        f"<p>{intro}, so I'll keep this short.</p>"
        f"<p>I'm a student at {school} (working with a couple from {others}) "
        f"digging into what's difficult for teams like yours about getting "
        f"products in front of the right people.</p>"
        f"<p>We're backed by YC and have worked with folks at brands like "
        f"Public Goods and Good Molecules.</p>"
        f"<p>Would you be open to a quick 10-minute call? If not, even a "
        f"one-sentence reply on your biggest headache would help. Totally fine "
        f"if this isn't relevant.</p>"
        f"<p>Thanks, {owner}</p>"
    )
    return "Stanford Student Question", body


def render_ask_email(referrer_first: str, contact_name: str, owner_email: str) -> tuple[str, str]:
    """An in-thread reply to the original sender asking for the referred email.
    Subject is '' because it threads onto the existing conversation."""
    owner = owner_name(owner_email)
    who = contact_name or "them"
    ref = referrer_first or "there"
    body = (
        f"<p>Hi {ref},</p>"
        f"<p>Thanks for pointing me to {who}. What's the best email to reach "
        f"{who} on? Happy to take it from there.</p>"
        f"<p>Thanks, {owner}</p>"
    )
    return "", body


def render_ooo_bump(prospect_first: str, owner_email: str) -> tuple[str, str]:
    """An in-thread bump for someone who was out of office. Subject '' (threads)."""
    owner = owner_name(owner_email)
    body = (
        f"<p>Hi {prospect_first},</p>"
        f"<p>Circling back now that you're likely back at your desk. No rush at "
        f"all, but if a quick 10-minute call makes sense I'd welcome it. Even a "
        f"one-line reply on your biggest headache would help.</p>"
        f"<p>Thanks, {owner}</p>"
    )
    return "", body


def parse_followup_date(ooo_until: str, today: date) -> date | None:
    """Resolve an out-of-office return value to a calendar date, or None when it
    is empty or a vague phrase we cannot pin down ('next week', 'Thursday'). None
    means we have no firm date to wait for, so the caller treats the bump as due."""
    s = (ooo_until or "").strip()
    if not s:
        return None
    try:
        return datetime.strptime(s[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


# ---- spec builders (one source of truth for both planners) ----------------

def _referral_spec(r: dict, name: str, email: str) -> dict:
    new_first = first_name_from(name or email)
    referrer = first_name_from(r.get("prospect_name") or r["who"])
    subject, body = render_referral(new_first, r["owner"], referrer)
    return {"kind": "redirect", "owner": r["owner"], "to": email,
            "subject": subject, "body_html": body, "thread_id": "",
            "reply_to_message_id": "", "quote": False,
            "note": f"referral to {new_first} <{email}>"}


def _ask_spec(r: dict, name: str) -> dict:
    prospect_first = first_name_from(r.get("prospect_name") or r["who"])
    subject, body = render_ask_email(prospect_first, name, r["owner"])
    return {"kind": "ask_email", "owner": r["owner"], "to": r["who"],
            "subject": subject, "body_html": body, "thread_id": r["tid"],
            "reply_to_message_id": r.get("latest_inbound_id", ""), "quote": True,
            "note": f"ask {r['who']} for {name or 'the'} email"}


def _ooo_spec(r: dict) -> dict:
    prospect_first = first_name_from(r.get("prospect_name") or r["who"])
    pitch_msg = r.get("pitch_msg_id", "")
    bump_thread = r.get("pitch_thread_id") or r["tid"]
    anchor = pitch_msg or r.get("latest_inbound_id", "")
    subject, body = render_ooo_bump(prospect_first, r["owner"])
    until = r.get("ooo_until", "")
    return {"kind": "ooo", "owner": r["owner"], "to": r["who"],
            "subject": subject, "body_html": body, "thread_id": bump_thread,
            "reply_to_message_id": anchor, "quote": bool(pitch_msg),
            "note": f"bump {r['who']}"
                    + (f" (back {until}); send after then" if until else "")}


def plan_drafts(rows: list[dict], existing_threads, existing_to,
                contacted: set[str] | None = None) -> tuple[list[dict], list[dict]]:
    """Decide what to stage. Pure: takes triage rows + existing-draft sets/maps,
    returns (specs, skipped). Idempotent: a thread (in-thread cases) or recipient
    address (redirect case) already drafted is skipped.

    `contacted` is the set of addresses already in the Supabase contacted ledger
    (the same one the campaign dedupes against). A redirect whose new contact is
    already in it is skipped: someone on the team has emailed them, so a referral
    would be a second cold touch.
    """
    contacted = contacted or set()
    specs: list[dict] = []
    skipped: list[dict] = []
    planned_to: set[str] = set()      # dedupe redirects within this run too
    planned_threads: set[str] = set()

    for r in rows:
        tid = r["tid"]

        if r["action"] == "reroute":
            name, email = parse_contact(r.get("reroute_to", ""))
            if email:
                if email.lower() in contacted:
                    skipped.append({**r, "skip": f"already contacted {email}"})
                    continue
                if r.get("new_contact_emailed"):
                    skipped.append({**r, "skip": f"already emailed {email}"})
                    continue
                if email in existing_to or email in planned_to:
                    skipped.append({**r, "skip": f"draft already to {email}"})
                    continue
                planned_to.add(email)
                specs.append(_referral_spec(r, name, email))
            else:
                if tid in existing_threads or tid in planned_threads:
                    skipped.append({**r, "skip": "thread already has a draft"})
                    continue
                planned_threads.add(tid)
                specs.append(_ask_spec(r, name))

        elif r.get("category") == "ooo":
            if r.get("already_followed_up"):
                skipped.append({**r, "skip": "already followed up after this OOO"})
                continue
            bump_thread = r.get("pitch_thread_id") or tid
            if bump_thread in existing_threads or bump_thread in planned_threads:
                skipped.append({**r, "skip": "pitch thread already has a draft"})
                continue
            planned_threads.add(bump_thread)
            specs.append(_ooo_spec(r))

    return specs, skipped


def plan_morning(rows: list[dict], by_thread: dict, by_to: dict,
                 contacted: set[str], today: date) -> list[dict]:
    """The autonomous-morning policy (pure). Unlike plan_drafts (draft everything),
    this decides per row whether to SEND now, SCHEDULE for a future return date, or
    DRAFT for human approval, and threads through existing drafts so a held bump is
    sent once due. Returns a list of actions; run_morning executes the I/O.

    Each action has `action` in {send_ooo, schedule_ooo, draft_redirect, draft_ask,
    skip}, the `spec` to create when needed, an `existing_draft_id` (or ""), and for
    scheduling a `send_after` date.
    """
    actions: list[dict] = []
    planned_to: set[str] = set()
    planned_threads: set[str] = set()

    for r in rows:
        tid = r["tid"]
        if r["action"] == "reroute":
            # Per the rollout decision, redirects are never auto-sent. They are
            # staged as drafts for a human to approve (a referral can carry a
            # mismatched name onto a brand-new cold contact).
            name, email = parse_contact(r.get("reroute_to", ""))
            if email:
                if email.lower() in contacted or r.get("new_contact_emailed"):
                    actions.append({"action": "skip", "who": r["who"],
                                    "reason": f"already emailed {email}"})
                    continue
                if email in by_to or email in planned_to:
                    actions.append({"action": "draft_redirect", "owner": r["owner"],
                                    "to": email, "existing_draft_id": by_to.get(email, ""),
                                    "spec": None, "note": f"referral to {email} (draft pending)"})
                    continue
                planned_to.add(email)
                actions.append({"action": "draft_redirect", "owner": r["owner"],
                                "to": email, "existing_draft_id": "",
                                "spec": _referral_spec(r, name, email),
                                "note": f"referral to {email}"})
            else:
                if tid in by_thread or tid in planned_threads:
                    actions.append({"action": "draft_ask", "owner": r["owner"],
                                    "to": r["who"], "existing_draft_id": by_thread.get(tid, ""),
                                    "spec": None, "note": f"ask {r['who']} (draft pending)"})
                    continue
                planned_threads.add(tid)
                actions.append({"action": "draft_ask", "owner": r["owner"],
                                "to": r["who"], "existing_draft_id": "",
                                "spec": _ask_spec(r, name), "note": f"ask {r['who']}"})

        elif r.get("category") == "ooo":
            if r.get("already_followed_up"):
                actions.append({"action": "skip", "who": r["who"],
                                "reason": "already followed up after this OOO"})
                continue
            bump_thread = r.get("pitch_thread_id") or tid
            if bump_thread in planned_threads:
                continue
            planned_threads.add(bump_thread)
            existing = by_thread.get(bump_thread, "")
            due_date = parse_followup_date(r.get("ooo_until", ""), today)
            is_due = due_date is None or due_date <= today
            spec = _ooo_spec(r)
            if is_due:
                actions.append({"action": "send_ooo", "owner": r["owner"],
                                "to": r["who"], "existing_draft_id": existing,
                                "spec": spec, "send_after": due_date,
                                "note": spec["note"]})
            else:
                actions.append({"action": "schedule_ooo", "owner": r["owner"],
                                "to": r["who"], "existing_draft_id": existing,
                                "spec": spec, "send_after": due_date,
                                "note": f"bump {r['who']} scheduled for {due_date.isoformat()}"})

    return actions


# ---- I/O: read existing drafts, create + send via the Gmail API ----------
# Everything goes through the Gmail REST API with an injected bearer token, so the
# same code runs from the CLI (gog-minted token) and the Slack wizard on Railway
# (refresh-token exchange), where the gog binary is not installed.

async def existing_drafts(token: str) -> tuple[dict[str, str], dict[str, str]]:
    """Return ({thread_id: draft_id}, {to_address: draft_id}) for drafts already in
    the mailbox, so we never stage a duplicate and can send a held draft when due.
    Thread ids are free from the list; recipient addresses need a metadata fetch."""
    by_thread: dict[str, str] = {}
    by_to: dict[str, str] = {}
    async with httpx.AsyncClient(
        headers={"Authorization": f"Bearer {token}"}, timeout=60
    ) as gmail:
        r = await gmail.get(f"{gmail_lib.api_base()}/drafts",
                            params={"maxResults": 500})
        r.raise_for_status()
        drafts = r.json().get("drafts") or []
        sem = asyncio.Semaphore(10)

        async def detail(d):
            did = d.get("id")
            if not did:
                return
            async with sem:
                try:
                    rr = await gmail.get(f"{gmail_lib.api_base()}/drafts/{did}",
                                         params={"format": "metadata"})
                    rr.raise_for_status()
                except Exception:  # noqa: BLE001 - a flaky draft must not abort dedupe
                    return
                msg = rr.json().get("message") or {}
                if tid := msg.get("threadId"):
                    by_thread.setdefault(tid, did)
                to_hdr = gmail_lib.header(msg, "To")
                for m in _EMAIL_RE.findall(to_hdr or ""):
                    by_to.setdefault(m.lower(), did)

        await asyncio.gather(*(detail(d) for d in drafts))
    return by_thread, by_to


async def _anchor_headers(gmail: httpx.AsyncClient, msg_id: str,
                          want_quote: bool) -> dict:
    """Fetch the message we are replying to: its RFC Message-ID (for threading),
    plus From/Date/body when we need to quote it."""
    fmt = "full" if want_quote else "metadata"
    try:
        m = await gmail_lib.get_message(gmail, msg_id, fmt=fmt)
    except Exception:  # noqa: BLE001
        return {}
    out = {"message_id": gmail_lib.header(m, "Message-ID") or gmail_lib.header(m, "Message-Id")}
    if want_quote:
        out["from"] = gmail_lib.header(m, "From")
        out["date"] = gmail_lib.header(m, "Date")
        out["body"] = gmail_lib.extract_text_parts(m.get("payload") or {}).strip()
    return out


def _build_raw(spec: dict, anchor: dict) -> str:
    """Build a base64url RFC822 message for the Gmail API from a draft spec.
    Adds In-Reply-To/References for threading and an HTML quote of the original
    when requested."""
    body_html = spec["body_html"]
    if spec.get("quote") and anchor.get("body"):
        quoted = html_mod.escape(anchor["body"]).replace("\n", "<br>")
        attribution = ""
        if anchor.get("date") and anchor.get("from"):
            attribution = (f"On {html_mod.escape(anchor['date'])}, "
                           f"{html_mod.escape(anchor['from'])} wrote:<br>")
        body_html += (f'<br><br><div class="gmail_quote">{attribution}'
                      f'<blockquote class="gmail_quote" style="margin:0 0 0 .8ex;'
                      f'border-left:1px solid #ccc;padding-left:1ex">{quoted}'
                      f'</blockquote></div>')
    plain = re.sub(r"<[^>]+>", "", body_html.replace("<br>", "\n"))
    msg = MIMEMultipart("alternative")
    msg["To"] = spec.get("to", "")
    if spec.get("subject"):
        msg["Subject"] = spec["subject"]
    msg["Date"] = formatdate(localtime=True)
    ref = anchor.get("message_id")
    if ref:
        msg["In-Reply-To"] = ref
        msg["References"] = ref
    msg.attach(MIMEText(plain, "plain", "utf-8"))
    msg.attach(MIMEText(body_html, "html", "utf-8"))
    return base64.urlsafe_b64encode(msg.as_bytes()).decode()


async def create_draft_api(token: str, spec: dict, dry_run: bool) -> tuple[bool, str]:
    """Create one Gmail draft via the API. Returns (ok, draft_id_or_detail).
    Never sends. On dry_run, builds the message but does not POST."""
    async with httpx.AsyncClient(
        headers={"Authorization": f"Bearer {token}"}, timeout=60
    ) as gmail:
        anchor = {}
        if spec.get("reply_to_message_id"):
            anchor = await _anchor_headers(gmail, spec["reply_to_message_id"],
                                           want_quote=bool(spec.get("quote")))
        try:
            raw = _build_raw(spec, anchor)
        except Exception as e:  # noqa: BLE001
            return False, f"compose failed: {str(e)[:120]}"
        if dry_run:
            return True, "dry-run (not created)"
        message: dict = {"raw": raw}
        if spec.get("thread_id"):
            message["threadId"] = spec["thread_id"]
        try:
            r = await gmail.post(f"{gmail_lib.api_base()}/drafts",
                                 json={"message": message})
            r.raise_for_status()
        except Exception as e:  # noqa: BLE001
            return False, f"draft create failed: {str(e)[:150]}"
        return True, r.json().get("id", "")


async def send_draft_api(token: str, draft_id: str) -> tuple[bool, str]:
    """Send an existing draft by id. This is the autonomous send path."""
    async with httpx.AsyncClient(
        headers={"Authorization": f"Bearer {token}"}, timeout=60
    ) as gmail:
        try:
            r = await gmail.post(f"{gmail_lib.api_base()}/drafts/send",
                                 json={"id": draft_id})
            r.raise_for_status()
        except Exception as e:  # noqa: BLE001
            return False, f"send failed: {str(e)[:150]}"
        return True, r.json().get("id", "")




# ---- orchestration -------------------------------------------------------

async def collect_rows(account: str, since_days: int, max_threads: int,
                       use_ledger: bool, concurrency: int,
                       get_token=None) -> list[dict]:
    """Run the probe's fetch + triage and return actionable rows (reroute / ooo),
    each carrying the thread data the drafter needs. `get_token(account)->str`
    defaults to the gog keyring (CLI); the wizard injects the server exchange."""
    get_token = get_token or _DEFAULT_GET_TOKEN
    our_addrs: set[str] = set(probe.TEAM)
    our_addrs.add(account.lower())
    token = get_token(account)

    async with httpx.AsyncClient(
        headers={"Authorization": f"Bearer {token}"}, timeout=60
    ) as gmail:
        gsem = asyncio.Semaphore(concurrency)
        thread_ids, _n, _scope = await probe._candidate_threads(
            gmail, our_addrs, {}, use_ledger, since_days, 0, max_threads, gsem)

        async def fetch(tid):
            async with gsem:
                return tid, await probe.get_thread(gmail, tid)
        fetched = await asyncio.gather(*(fetch(t) for t in thread_ids))

    prepared = []
    for tid, th in fetched:
        msgs = th.get("messages") or []
        rendered, _last = probe.render_thread(msgs, our_addrs)
        owner = next((probe._addr(m) for m in msgs if probe._addr(m) in our_addrs), account)
        other = next((probe._addr(m) for m in msgs if probe._addr(m) not in our_addrs), "unknown")
        other_name = next((gmail_lib.header(m, "From") for m in msgs
                           if probe._addr(m) not in our_addrs), "")
        subject = gmail_lib.header(msgs[0], "Subject") if msgs else ""
        prepared.append({"tid": tid, "rendered": rendered, "owner": owner,
                         "who": other, "prospect_name": other_name, "subject": subject,
                         "latest_inbound_id": latest_inbound_id(msgs, our_addrs),
                         "our_pitch_id": last_outbound_id(msgs, our_addrs)})

    use_api = bool(os.environ.get("ANTHROPIC_API_KEY"))
    asem = asyncio.Semaphore(concurrency)
    if use_api:
        async with httpx.AsyncClient(timeout=60) as api:
            verdicts = await asyncio.gather(
                *(probe.triage_api(api, asem, p["rendered"]) for p in prepared))
    else:
        verdicts = await asyncio.gather(
            *(probe.triage_cli(asem, p["rendered"]) for p in prepared))

    rows = []
    for p, v in zip(prepared, verdicts):
        # Only the two mechanical cases. Skip borderline reroutes so a shaky read
        # never auto-drafts to the wrong person.
        is_reroute = v.action == "reroute" and v.confidence == "clear"
        is_ooo = v.category == "ooo"
        if not (is_reroute or is_ooo):
            continue
        # Stage only the threads this account owns (it originally emailed the
        # prospect). The same reply is visible in several CC'd inboxes; letting
        # each account draft only its own threads keeps one run per sender
        # complete and non-overlapping, and keeps the duplicate check (which reads
        # this account's drafts) correct. Other owners are picked up when you run
        # for them.
        if p["owner"].lower() != account.lower():
            continue
        rows.append({**p, "action": v.action, "confidence": v.confidence,
                     "reroute_to": v.reroute_to, "category": v.category,
                     "ooo_until": v.ooo_until})

    # Enrich the actionable rows with the state needed to avoid re-doing a
    # follow-up we have already done. The signals are time-relative and read from
    # Gmail's own record, so they hold whether a draft was sent by hand or by a
    # scheduler.
    reroute_rows = [r for r in rows if r.get("action") == "reroute"]
    ooo_rows = [r for r in rows if r.get("category") == "ooo"]
    if reroute_rows or ooo_rows:
        async with httpx.AsyncClient(
            headers={"Authorization": f"Bearer {token}"}, timeout=60
        ) as gmail:
            esem = asyncio.Semaphore(concurrency)

            async def _date_and_thread(mid: str) -> tuple[int, str]:
                try:
                    m = await gmail_lib.get_message(gmail, mid, fmt="metadata")
                    return int(m.get("internalDate") or 0), m.get("threadId", "")
                except Exception:  # noqa: BLE001
                    return 0, ""

            async def enrich_ooo(r):
                async with esem:
                    # Every send to this prospect (newest first).
                    sent_ids = await probe.list_all(gmail, f"in:sent to:{r['who']}", cap=10)
                    if not sent_ids:
                        return  # no pitch on record; plan_drafts falls back
                    # Timestamp of the out-of-office we are reacting to.
                    ar_date, _ = await _date_and_thread(r.get("latest_inbound_id", ""))
                    metas = await asyncio.gather(*(_date_and_thread(s) for s in sent_ids))
                    # The oldest send is the original pitch; anchor the bump there.
                    r["pitch_msg_id"] = sent_ids[-1]
                    r["pitch_thread_id"] = metas[-1][1]
                    # Already handled if we sent ANYTHING to them after this OOO
                    # bounced back (the pitch itself is dated before it, so it never
                    # counts; a prior bump, sent by hand or scheduler, does).
                    if ar_date and any(d > ar_date for d, _t in metas):
                        r["already_followed_up"] = True

            async def enrich_reroute(r):
                _name, email = parse_contact(r.get("reroute_to", ""))
                if not email:
                    return
                async with esem:
                    # Have we already emailed this new contact from this account?
                    # Catches a referral sent earlier that the ledger would not know
                    # about (a manual send writes nothing to `contacted`).
                    if await probe.list_all(gmail, f"in:sent to:{email}", cap=1):
                        r["new_contact_emailed"] = True

            await asyncio.gather(
                *(enrich_ooo(r) for r in ooo_rows),
                *(enrich_reroute(r) for r in reroute_rows),
            )
    return rows


async def run(account: str, since_days: int, max_threads: int, use_ledger: bool,
              concurrency: int, dry_run: bool, as_json: bool) -> None:
    t0 = time.perf_counter()
    rows = await collect_rows(account, since_days, max_threads, use_ledger, concurrency)
    token = gog_auth.get_access_token(account)
    threads, tos = await existing_drafts(token)
    # The same contacted ledger the campaign dedupes against, so a referral never
    # cold-touches someone the team has already emailed. Set TRIAGE_LEDGER_SERVICE_KEY
    # to see the whole team ledger; otherwise it is the caller's own rows.
    try:
        contacted = await probe.fetch_contacted()
    except Exception as e:  # noqa: BLE001 - degrade to no ledger rather than abort
        log_msg = f"(could not load contacted ledger: {str(e)[:80]}; skipping that check)"
        print(log_msg)
        contacted = set()
    specs, skipped = plan_drafts(rows, threads, tos, contacted)

    results = []
    for spec in specs:
        # Each draft is created with the owning account's token, so it lands in
        # the right mailbox even when several owners appear in one scan.
        otoken = token if spec["owner"] == account else gog_auth.get_access_token(spec["owner"])
        ok, detail = await create_draft_api(otoken, spec, dry_run)
        results.append({**spec, "ok": ok, "detail": detail})

    if as_json:
        print(json.dumps({
            "account": account, "dry_run": dry_run,
            "found": len(rows), "staged": sum(1 for r in results if r["ok"]),
            "skipped": len(skipped),
            "drafts": [{"kind": r["kind"], "owner": r["owner"], "to": r["to"],
                        "note": r["note"], "ok": r["ok"], "detail": r["detail"]}
                       for r in results],
            "skips": [{"who": s["who"], "why": s["skip"]} for s in skipped],
        }))
        return

    staged = sum(1 for r in results if r["ok"])
    failed = sum(1 for r in results if not r["ok"])
    verb = "Would stage" if dry_run else "Staged"
    print(f"\nAccount: {account}   actionable: {len(rows)}   "
          f"{verb}: {staged}   failed: {failed}   skipped (already drafted): {len(skipped)}")
    print(f"Time: {time.perf_counter() - t0:.1f}s\n")

    by_kind = {"redirect": "REDIRECTS (draft to the new contact)",
               "ask_email": "REDIRECTS, NAME ONLY (ask the sender for the email)",
               "ooo": "OUT OF OFFICE (in-thread bump, send after they return)"}
    for kind, title in by_kind.items():
        items = [r for r in results if r["kind"] == kind]
        if not items:
            continue
        print("=" * 78)
        print(title)
        print("=" * 78)
        for r in items:
            mark = "ok" if r["ok"] else "FAIL"
            print(f"  [{mark}] {r['note']}   (from {owner_name(r['owner'])})")
            if not r["ok"]:
                print(f"         -> {r['detail']}")
        print()

    if skipped:
        print(f"Skipped {len(skipped)} thread(s) that already have a draft.")
    if not dry_run and staged:
        print("\nReview and send these in Gmail. Nothing was sent.")


async def run_morning(account: str, today: date | None = None, get_token=None,
                      auto_send: bool = True, since_days: int = 60,
                      concurrency: int = 8) -> dict:
    """The autonomous daily pass for one account, used by the Slack 9am job.

    Auto-sends out-of-office bumps that are due (return date passed, or no firm
    date), holds future bumps as drafts to send on the day, and stages redirects as
    drafts for human approval. Idempotent across runs via Gmail's own state.
    Returns a structured summary for the Slack report. When auto_send is False it
    is a pure preview: it sends and creates nothing.
    """
    today = today or date.today()
    get_token = get_token or _DEFAULT_GET_TOKEN
    token = get_token(account)
    rows = await collect_rows(account, since_days, 0, True, concurrency,
                              get_token=get_token)
    by_thread, by_to = await existing_drafts(token)
    try:
        contacted = await probe.fetch_contacted()
    except Exception:  # noqa: BLE001 - degrade rather than abort the morning run
        contacted = set()
    actions = plan_morning(rows, by_thread, by_to, contacted, today)

    out: dict = {"account": account, "today": today.isoformat(), "sent": [],
                 "scheduled": [], "redirect_drafts": [], "skipped": [], "errors": []}

    async def ensure_draft(a: dict) -> str:
        """Reuse an existing draft, or create one. Returns a draft id, or '' on
        failure / preview."""
        if a.get("existing_draft_id"):
            return a["existing_draft_id"]
        if not a.get("spec"):
            return ""
        ok, res = await create_draft_api(token, a["spec"], dry_run=not auto_send)
        if not ok:
            out["errors"].append({"note": a["note"], "detail": res})
            return ""
        return res if auto_send else ""

    for a in actions:
        act = a["action"]
        if act == "skip":
            out["skipped"].append({"who": a["who"], "reason": a["reason"]})
        elif act == "send_ooo":
            if not auto_send:
                out["sent"].append({"to": a["to"], "note": a["note"], "preview": True})
                continue
            draft_id = await ensure_draft(a)
            if not draft_id:
                continue
            ok, res = await send_draft_api(token, draft_id)
            if ok:
                out["sent"].append({"to": a["to"], "note": a["note"]})
            else:
                out["errors"].append({"note": a["note"], "detail": res})
        elif act == "schedule_ooo":
            await ensure_draft(a)  # hold a draft so it can be sent on the day
            out["scheduled"].append({"to": a["to"], "note": a["note"],
                                     "date": a.get("send_after").isoformat()
                                     if a.get("send_after") else ""})
        elif act in ("draft_redirect", "draft_ask"):
            await ensure_draft(a)  # stage (or reuse) the approval draft
            out["redirect_drafts"].append({"to": a["to"], "note": a["note"]})
    return out


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--account", required=True, help="Gmail account to scan and draft from")
    ap.add_argument("--since-days", type=int, default=60, help="Inbox lookback window")
    ap.add_argument("--max", type=int, default=0, dest="max_threads",
                    help="Cap threads triaged (0 = no cap)")
    ap.add_argument("--ledger", action="store_true",
                    help="Scope to prospect replies via the contacted ledger (recommended)")
    ap.add_argument("--concurrency", type=int, default=8, help="Parallel requests")
    ap.add_argument("--dry-run", action="store_true",
                    help="Plan and show drafts without creating them")
    ap.add_argument("--json", action="store_true", dest="as_json", help="JSON output")
    ap.add_argument("--morning", action="store_true",
                    help="Run the autonomous morning pass (auto-send due OOO bumps)")
    ap.add_argument("--no-send", action="store_true",
                    help="With --morning: preview only, send and create nothing")
    args = ap.parse_args()
    if args.morning:
        res = asyncio.run(run_morning(args.account, auto_send=not args.no_send,
                                      since_days=args.since_days,
                                      concurrency=args.concurrency))
        print(json.dumps(res, indent=2))
        return
    asyncio.run(run(args.account, args.since_days, args.max_threads, args.ledger,
                    args.concurrency, args.dry_run, args.as_json))


if __name__ == "__main__":
    main()
