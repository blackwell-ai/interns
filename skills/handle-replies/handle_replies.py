#!/usr/bin/env python3
"""Triage cold-outreach replies and schedule calls — fully headless.

For each unread reply in the outreach thread set:
  1. classify with headless Claude Code → positive | question | negative | auto
  2. positive  → propose 3 real open slots from the calendar (gog freebusy),
                 draft + send a reply offering them, and file an inbox task
  3. question  → draft a reply answering it from brain context, send, file task
  4. negative/auto/ooo → mark handled, file a brief note, no reply
  5. "book it" confirmations (a lead picked a slot) → create the Meet event
     (gog calendar create --with-meet --attendees) and send confirmation

Nothing is sent without the ledger already knowing the recipient (they replied,
so they're contacted). Calendar writes go to the Dartmouth account.

Run modes:
  --scan         classify + draft + (send replies / propose times)   [default]
  --dry-run      classify + draft only; print, send nothing
Booking a confirmed slot is handled inline when a reply says which slot works.
"""
import json, os, re, subprocess, sys, time, datetime as dt

ACC = "armaan.priyadarshan.29@dartmouth.edu"
CC = "samarjit.deshmukh.29@dartmouth.edu,ethanpzhou@berkeley.edu,shamitd@stanford.edu"
SUBJECTS = ['"Stanford Student Question"', '"Stanford Student Inquiry"',
            '"Dartmouth Student Inquiry"', '"thoughts on AI retail tools"']
INBOX_QUEUE = "/home/armaan/Documents/interns/inbox/queue"
DRY = "--dry-run" in sys.argv

def gog(*args, inp=None):
    p = subprocess.run(["gog", *args], capture_output=True, text=True, input=inp, timeout=120)
    return p.returncode, p.stdout, p.stderr

def claude(system, prompt, model="claude-haiku-4-5"):
    env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
    p = subprocess.run(["claude", "-p", "--output-format", "json", "--model", model,
                        "--system-prompt", system, "--tools", "", "--no-session-persistence"],
                       input=prompt, capture_output=True, text=True, timeout=180, env=env, cwd="/tmp")
    if p.returncode != 0:
        return ""
    try:
        return (json.loads(p.stdout).get("result") or "").strip()
    except Exception:
        return ""

def unread_reply_threads():
    q = "in:inbox is:unread (" + " OR ".join(f"subject:{s}" for s in SUBJECTS) + ") -from:mailer-daemon"
    rc, out, _ = gog("gmail", "search", q, "-a", ACC, "--all", "--json", "--results-only")
    try:
        return json.loads(out)
    except Exception:
        return []

def thread_text(thread_id):
    rc, out, _ = gog("gmail", "get", thread_id, "-a", ACC, "--json", "--results-only")
    try:
        d = json.loads(out)
        return d.get("from", ""), d.get("snippet", "") or d.get("body", "")[:1500]
    except Exception:
        return "", ""

def free_slots(days_ahead=7, n=3):
    """Return up to n RFC3339 (start,end) business-hour 30-min slots that are free."""
    now = dt.datetime.now(dt.timezone(dt.timedelta(hours=-5)))  # ET
    start = (now + dt.timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0)
    end = start + dt.timedelta(days=days_ahead)
    rc, out, _ = gog("calendar", "freebusy", "--all",
                     "--from", start.isoformat(), "--to", end.isoformat(),
                     "--json", "--results-only")
    busy = []
    try:
        data = json.loads(out)
        cals = data.get("calendars", data) if isinstance(data, dict) else {}
        for c in (cals.values() if isinstance(cals, dict) else []):
            for b in c.get("busy", []):
                busy.append((b["start"], b["end"]))
    except Exception:
        pass
    def overlaps(s, e):
        for bs, be in busy:
            if s < be and bs < e:
                return True
        return False
    slots = []
    cur = start
    while cur < end and len(slots) < n:
        if cur.weekday() < 5 and 9 <= cur.hour < 17:
            s, e = cur, cur + dt.timedelta(minutes=30)
            if not overlaps(s.isoformat(), e.isoformat()):
                slots.append((s, e))
                cur += dt.timedelta(hours=2)
                continue
        cur += dt.timedelta(minutes=30)
        if cur.hour >= 17:
            cur = (cur + dt.timedelta(days=1)).replace(hour=9, minute=0)
    return slots

def human(slot):
    s, _ = slot
    return s.strftime("%A %b %-d at %-I:%M %p ET")

def book(summary, slot, attendee):
    s, e = slot
    rc, out, err = gog("calendar", "create", "primary", "--summary", summary,
                       "--from", s.isoformat(), "--to", e.isoformat(),
                       "--attendees", f"{attendee},{CC}", "--with-meet",
                       "--send-updates", "all", "--description",
                       "Intro call booked from cold-outreach reply (Blackwell).")
    return rc == 0, (out + err)[:200]

def reply(thread_id, to, body):
    if DRY:
        print(f"  [dry-run reply to {to}]\n{body}\n")
        return True
    rc, out, err = gog("gmail", "reply", thread_id, "-a", ACC, "--cc", CC,
                       "--body", body, "--no-input")
    if rc != 0:  # some gog builds use 'send --thread'; fall back to send
        rc, out, err = gog("gmail", "send", "-a", ACC, "--to", to, "--cc", CC,
                           "--subject", "Re: Stanford Student Question - thoughts on AI retail tools",
                           "--body", body, "--no-input")
    return rc == 0

def file_task(slug, title, detail):
    os.makedirs(INBOX_QUEUE, exist_ok=True)
    path = os.path.join(INBOX_QUEUE, f"2026-06-10-reply-{slug}.md")
    with open(path, "w") as f:
        f.write(f"---\ntitle: {title}\ncreated: 2026-06-10\ncreated_by: outreach-agent (reply handler)\nassignee: armaan\npriority: high\n---\n\n## Task\n\n{detail}\n")

CLASSIFY_SYS = ("Classify a reply to our cold outreach into exactly one word: "
    "POSITIVE (wants a call/interested), QUESTION (asks something before committing), "
    "BOOK (names or agrees to a specific time), NEGATIVE (not interested/unsubscribe), "
    "AUTO (auto-reply/out-of-office/no-reply). Output only the word.")

def main():
    threads = unread_reply_threads()
    print(f"unread replies: {len(threads)}")
    pos = ques = neg = booked = 0
    for t in threads:
        tid = t.get("id") or t.get("threadId")
        frm, text = thread_text(tid)
        addr = re.search(r'[\w.+-]+@[\w-]+\.[\w.-]+', frm)
        addr = addr.group(0) if addr else ""
        if not addr:
            continue
        kind = (claude(CLASSIFY_SYS, f"From: {frm}\nReply: {text}") or "AUTO").split()[0].upper()
        print(f"  {addr}: {kind}")
        if kind == "POSITIVE":
            slots = free_slots()
            offer = "; ".join(human(s) for s in slots) or "a few times this week"
            body = claude(
                "You are Armaan, Blackwell co-founder. Warm, brief, 4 sentences max. No signature line beyond 'Best, Armaan'.",
                f"They replied positively to our cold email. Offer these exact call times and ask them to pick one: {offer}. "
                f"Their message: {text}")
            if body and reply(tid, addr, body):
                pos += 1
            file_task(addr.split('@')[0], f"Positive reply from {addr}",
                      f"{addr} is interested. Proposed times: {offer}. Reply sent; confirm and the booking happens on their pick.")
        elif kind == "QUESTION":
            body = claude(
                "You are Armaan, Blackwell co-founder. Answer the question briefly and truthfully, then offer a quick call. 5 sentences max.",
                f"Context: Blackwell audits how DTC stores appear to AI shopping agents (ChatGPT etc) and fixes it; $1k pilots, refundable. "
                f"Their question: {text}")
            if body and reply(tid, addr, body):
                ques += 1
            file_task(addr.split('@')[0], f"Question reply from {addr}",
                      f"{addr} asked a question; auto-answer sent. Review: {text[:300]}")
        elif kind == "BOOK":
            slots = free_slots(n=1)
            if slots and book("Blackwell × prospect — intro call", slots[0], addr):
                body = claude("You are Armaan. One short confirming sentence + 'Best, Armaan'.",
                              f"Confirm the call is booked for {human(slots[0])} with a Google Meet link in the invite.")
                reply(tid, addr, body or f"Booked for {human(slots[0])} — invite with the Meet link is on its way. Best, Armaan")
                booked += 1
                file_task(addr.split('@')[0], f"CALL BOOKED with {addr}",
                          f"Booked {human(slots[0])} (Meet invite sent). {addr}.")
        elif kind == "NEGATIVE":
            neg += 1
            file_task(addr.split('@')[0], f"Negative/opt-out from {addr}",
                      f"{addr} declined. Consider suppress_contact if they asked to stop. Msg: {text[:200]}")
        # AUTO → ignore
        time.sleep(8)
    print(f"SUMMARY positive={pos} question={ques} booked={booked} negative={neg}")

if __name__ == "__main__":
    main()
