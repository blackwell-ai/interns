# handle-replies

**Purpose:** triage replies to cold outreach and schedule calls — autonomously.
Classifies each unread reply, drafts and sends an appropriate response, and
when a lead wants to talk, proposes real open calendar slots and books a
Google Meet on their pick.

**Inputs:** none required — it finds unread replies to the outreach subjects in
the Dartmouth inbox.

**Credentials:** gogcli (Dartmouth account) for Gmail read/reply + Calendar
freebusy/create. Classification and drafting run on headless Claude Code (no
key). Calendar writes go to the Dartmouth primary calendar; co-founders are
CC'd on replies and added as event attendees.

## How it runs

    python3 skills/handle-replies/handle_replies.py            # scan + act
    python3 skills/handle-replies/handle_replies.py --dry-run  # draft only, send nothing

Per unread reply:
- **POSITIVE** → offers 3 real open business-hour slots (next 7 days, pulled
  from `gog calendar freebusy` so it never double-books), sends the reply,
  files an inbox task.
- **QUESTION** → answers briefly from Blackwell context, offers a call, files a
  task.
- **BOOK** (they named/agreed a time) → creates a 30-min Google Meet event with
  the lead + co-founders as attendees (`--with-meet --send-updates all`), sends
  a confirmation.
- **NEGATIVE** → files a task (and flags for `suppress_contact` if they asked to
  stop); no reply.
- **AUTO** (OOO/no-reply) → ignored.

## Guardrails

- Read/reply only within existing reply threads — never initiates new contact
  here (that's `clay-cold-email`).
- Anything ambiguous or high-stakes (pricing negotiation, partnership, legal)
  is filed to `inbox/queue/` for a human rather than answered.
- Slots are business hours (9–5 ET, Mon–Fri), 30 min, spaced ≥2h apart.

## Intended cadence

Run on a schedule (e.g. hourly during the day) while a `clay-cold-email`
campaign is live. Pairs with the autonomous sender — see
`skills/autonomous-outreach/`.

## Changelog

- 2026-06-10: created. Headless reply triage + calendar booking via gogcli.
  Not yet run against live replies — dry-run first.
