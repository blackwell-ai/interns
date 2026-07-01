# Reply follow-up: stage drafts for redirects and out-of-office

What it does, how it decides, and how to run it. Covers `reply_followup.py`.
Status as of June 26, 2026: working, draft-only, on command. It writes Gmail
drafts and never sends.

## What it answers

The triage (`reply_triage_probe.py`) tells you which replies need an action. This
takes the two cases a human handles the same way every time and writes the draft
for you, so the only thing left is to read it and hit send.

- A redirect that gives an email ("reach katie.s@acme.com instead") becomes a
  fresh draft to that contact with a referral opener and our pitch.
- A redirect that names a person but no email becomes an in-thread draft back to
  the original sender asking for the best address. No Hunter credits are spent
  guessing the email.
- An out-of-office reply becomes a bump on our original pitch (not on the
  auto-reply, see below), quoting that pitch, and the report surfaces the stated
  return date so you send it once they are back.

It does not touch the `reply` bucket (a real person waiting on a real answer).
Those still need a human to write the response. This is only the mechanical tail.

A redirect to someone already in the Supabase `contacted` ledger is skipped. This
is the same email-level check the campaign runs before any send (`contacted`,
channel email), so a referral never becomes a second cold touch on a person the
team has already emailed. The check applies to redirects only: an out-of-office
prospect is in the ledger by definition (we emailed them), and bumping them is the
whole point, so the ledger never suppresses a bump.

## Why draft-only

Every action is a Gmail draft you approve. Nothing is sent by the tool. Two
reasons. First, a misread redirect would otherwise email the wrong person, and a
sent email cannot be recalled. Second, an out-of-office bump is useful only after
the person is back, and a human holding the send button is the simplest way to get
the timing right without a scheduler. Auto-sending on the return date is the
obvious next version; it needs a scheduled job that runs `gog gmail drafts send`.

## How it works

1. Scope and triage. It reuses the probe end to end: the same contacted-ledger
   scoping, the same full-thread fetch, the same one-LLM-call-per-thread triage.
   It keeps only clear reroutes and any thread the model marked `category=ooo`.
   Borderline reroutes are dropped so a shaky read never drafts to the wrong
   person.
2. Plan. `plan_drafts` is pure: given the triage rows and the set of drafts that
   already exist, it returns one spec per draft to create. It is idempotent. An
   in-thread case whose thread already holds a draft is skipped; a redirect whose
   new contact already has a draft is skipped; duplicates within a single run are
   collapsed too.
3. Create. Each draft is written with `gog gmail drafts create`, authenticated
   with the owning account's token (minted by `gog_auth`), so a draft always lands
   in the mailbox of whoever originally emailed the prospect. In-thread replies use
   `--reply-to-message-id`, which sets the threading headers and the thread in one
   flag, and the recipient is set explicitly because gog does not auto-fill it on a
   reply.

## The 9am morning job (Slack wizard)

`wizard/slack_bot.py` runs a scheduled job at 9am Pacific (`SLACK_FOLLOWUP_ENABLED`,
default on) that calls `run_morning` for each sender mailbox, then posts a Block Kit
report, then the inbox triage tables right after.

Per the rollout decision, the morning pass is selective about what it sends:

- Out-of-office bumps are auto-sent when due (the return date has passed, or no firm
  date was given). A bump whose return date is still in the future is held as a
  draft and sent on the day: each morning re-derives the date and sends the held
  draft once it arrives. Gmail drafts are the schedule queue; there is no separate
  store and no native Gmail scheduled send (the API has none).
- Redirects are never auto-sent. They are staged as drafts for a human to approve,
  because a referral is a fresh cold email to a new contact and the triage can pair
  a wrong name with an address. The report lists them as awaiting approval.

The report shows who was auto-responded to, what is scheduled for later (with
dates), and the redirect drafts awaiting approval. It runs on Railway, so all draft
create/send goes through the Gmail REST API (`create_draft_api`, `send_draft_api`),
not the gog binary, with tokens from the server refresh-token exchange.

## Not redoing a follow-up we already did

A draft prevents a duplicate only until it is sent. Once sent it is no longer a
draft, so the draft check alone would let the next run re-stage it. The fix is to
read Gmail's own record, and to make the out-of-office check time-relative.

Out-of-office. The signal is not "have we ever emailed this prospect" (the pitch
always says yes), it is "have we sent them anything AFTER the timestamp of the
out-of-office message we are reacting to." The pitch is dated before that
auto-reply, so it never counts; a prior bump (sent by hand or by a scheduler) is
dated after, so it does. This also handles a long back-and-forth that later goes
out of office: every earlier message is before this auto-reply, so only an actual
post-OOO send suppresses the bump. And a second, later out-of-office on the same
thread has a newer timestamp, so it earns its own bump. Implemented in
`collect_rows` as `already_followed_up` (compares each `in:sent` message's
`internalDate` to the auto-reply's).

Redirects. The dedup key is the new contact, a different person from the prospect,
so there is no timestamp subtlety. A referral is skipped when the new contact is in
the `contacted` ledger (team-wide) or already appears in this account's `in:sent`
(catches a referral sent by hand, which writes nothing to the ledger).

Two signals, not one. A queued bump that has not fired yet is still a draft (we
cannot use Gmail's native scheduled send), so the draft check covers it; once it
fires, the sent-after check covers it. There is no window where neither applies.

Limit: the `in:sent` checks are per-account, so they see only the account running
the tool. Cross-account suppression of a referral relies on the shared `contacted`
ledger, not `in:sent`.

## Out-of-office bumps reply to our pitch, not the auto-reply

An out-of-office auto-reply does not thread onto the email we sent. It arrives as
its own separate thread, so that thread holds only the robot message and none of
our pitch. Measured across a sample of 17 OOO replies, 17 of 17 were detached this
way, and `in:sent to:<prospect>` found our actual pitch in all 17. So the bump
must not reply to the auto-reply; it would be following up on a robot with no
context.

Instead, for each OOO the tool looks up our original sent pitch with
`in:sent to:<prospect>`, replies in that thread, and quotes the pitch with
`--quote` so the original travels inline regardless of how the recipient's client
threads. The auto-reply is used only to learn who to bump and the return date. If
no sent pitch is on record (rare), it falls back to the auto-reply thread and does
not quote.

Gotcha that hid this at first: `threads.get` returns draft messages as part of the
thread. After a first staging pass, each staged draft counted as one of "our"
messages in its thread, which made detached auto-replies look like they contained
our pitch. Always exclude drafts (and read `in:sent` directly) when reasoning about
what we actually sent.

## How to run it

From the repo root. Requires a valid `gog` token for the account and
`ANTHROPIC_API_KEY` for the fast triage path.

```bash
# see what it would stage, create nothing
python3 skills/campaign/reply_followup.py --account you@blackwell.com --ledger --dry-run

# stage the drafts for real (still nothing is sent)
python3 skills/campaign/reply_followup.py --account you@blackwell.com --ledger
```

Flags that matter:

- `--ledger` scopes to prospect replies via the contacted ledger. Recommended.
- `--dry-run` plans and prints the drafts without creating them. Use it first.
- `--since-days` is the lookback window, default 60.
- `--max` caps threads triaged (0 = no cap). Useful to bound cost on a first look.
- `--json` emits a machine summary instead of the text report.

Re-running is safe. The idempotency check means a second run only adds drafts for
threads and contacts that do not already have one.

## What was validated

Run June 26, 2026 across the three sender inboxes, draft-only. Triage extracted
redirects (drafted to the new contact, or an in-thread ask when only a name was
given) and out-of-office threads with return dates correctly read (calendar dates
like `2026-07-02` and phrases like `Thursday`). Real drafts were created, verified,
and deleted: an OOO bump was confirmed to land in our sent-pitch thread (not the
detached auto-reply thread), to quote our actual original pitch inline, and to
carry the prospect as the recipient. Spot checks across five orphaned OOO cases all
landed in the pitch thread. No email was sent at any point.

## Known limits and next steps

- Draft-only by design. There is no scheduled send yet, so an out-of-office bump
  waits on a human to send it after the return date. The report shows the date.
  Neither gog nor the Gmail API can schedule a send (scheduled send is a Gmail
  client feature, not in the API), so any automated timing would have to be our own
  job that runs `gog gmail drafts send <id>` on the date.
- The referral pitch is generic on purpose ("teams like yours") so it needs no
  company-name guess. Personalize before sending if you want.
- Redirect contacts given as a bare name are not resolved to an email by sourcing
  (that would cost Hunter credits); the tool asks the original sender instead.
- It inherits the probe's one real limit: it only sees replies from the address we
  emailed, so a reply from an assistant or alias is missed.

## Files

- `reply_followup.py` is the stager. Pure decision logic (`plan_drafts`, the body
  renderers, parsing) is unit-tested in `tests_followup/`.
- It reuses `reply_triage_probe.py` (triage), `gog_auth` (tokens), and the
  `contacted` ledger. The probe gained one field, `ooo_until`, for the return date.
