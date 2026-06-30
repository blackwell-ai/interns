# Always-on campaign wizard (Slack)

The wizard is a Slack front end to the campaign pipeline. You tell it how many
emails to send and to which ICPs in plain English, it plans the split across
senders, shows a preview with a sample email, and on your confirmation runs the
same `run.py` campaign the CLI uses. (A Telegram front end existed earlier; it
was removed once the team moved to Slack only.)

## Architecture

For the full structural map (module responsibilities, the core flows, invariants,
and a "where to change X" index for fixes), see `ARCHITECTURE.md`. Keep that file
current when the architecture changes. The summary below is the short version.

The planning and execution modules are messaging-agnostic:

- `agent.py` reads a natural-language request with Claude and returns a
  structured plan (total, ICP segments, weights), then `_divide()` does the
  sender and daily-cap arithmetic. No platform code.
- `executor.py` runs each planned campaign as a `run.py` subprocess and reports
  progress through two callbacks, `send_update` (async) and `set_progress`.
- `gmail_auth.py` exchanges a stored refresh token for a Gmail access token per
  sender.

The Slack messaging layer is `slack_bot.py`, using `slack_bolt` over Socket
Mode. It holds a five-state conversation machine:

```
idle -> awaiting_icp -> [awaiting_clarification] -> awaiting_preview -> executing
```

`launch.py` is the entrypoint; it starts the Slack bot. One Docker image runs
the `slack_wiz` service.

## Slack specifics

- The conversation is **thread-based**. A user `@email_wizard`s the bot once in
  the configured channel; the wizard opens a thread on that message and runs the
  whole exchange there. Inside its active thread it reads every message, so
  follow-ups need no further @mention. Messages elsewhere in the channel, and
  mentions outside the active thread, are ignored.
- The preview carries **Send / Edit draft / Cancel buttons** (Block Kit
  interactive elements). Typed `send` / `cancel` in the thread still work as a
  fallback.
- **Edit draft** opens a modal pre-filled with the template's subject and body
  (slots intact). You can revise it two ways, together or separately: hand-edit
  the subject/body text directly, and/or type a free-text instruction in the "ask
  Claude to change it" field ("make it shorter", "mention we build eval tools",
  "more casual"). On save, the manual edits are the base and Claude applies the
  instruction on top with the latest Opus model, preserving every `{{slot}}` (it
  raises and keeps your manual edits if a refinement would drop one). The result
  is installed as the template override, points every run at it, and refreshes the
  preview; click Edit again to iterate. The override is sticky across plan
  refinements and cleaned up on reset. An empty subject or body is blocked with an
  inline modal error. See `editable_draft` / `refine_template` (agent.py) and
  `on_edit_submit` / `_install_draft_override` (slack_bot.py).
- **CSV / direct sends use an audience-fit shared template.** Drop a CSV (or
  paste a table) and `@email_wizard`. An attached file is parsed
  **deterministically in code** (`agent.parse_contacts_csv`, no LLM) so a large
  list never truncates: it maps common headers (name/email/company/affiliation/
  title) and folds every other non-empty column (a bio, paper, notes) into a
  per-lead `context`. Operational columns (status, source, score, url) are
  excluded; only rows with a valid email are kept. A pasted table that is not a
  clean CSV falls back to Claude extraction (which also captures `context`).
  The wizard then drafts **one shared template that fits the audience** with the
  latest Opus model (`agent.draft_csv_template`): the student-and-school
  self-intro is kept (high signal, written as `{{school}}` / `{{other_schools}}`
  slots), and the rest of the body and the ask are the model's discretion, fit to
  who the recipients are (researchers vs operators vs founders read very
  differently) and to any instruction in the message. It is grounded in the lead
  `context` and follows the humanizer rules (no em dashes, no fake-AI filler). The
  generated template becomes the editable draft override, so **Edit draft** works
  on it and it is mail-merged across the whole list via `{{first_name}}` /
  `{{company}}`. If generation fails or drops the required slots, the send falls
  back to `brands.md`. The preview shows up to **three real recipients** so you
  can check the copy before sending. See `draft_csv_template` / `render_for_lead`
  (agent.py) and `_build_csv_template` / `_sample_blocks` (slack_bot.py).
- Messages are formatted with **Block Kit** (header, sections, the sample email
  in a quote block, context lines).
- **Live scoreboard.** Once a campaign starts, one message is posted and edited
  in place. Each run shows its phase: a climbing `N located...` count while
  sourcing leads, then `sending...` once composing is done (sends are not
  tabulated live), then `N sent` when finished. The footer shows the running
  `located` total, and on completion the final sent count, the campaign's Hunter
  credit spend, elapsed time, and run count. Located redraws are throttled (~2s)
  to respect Slack's `chat.update` rate limit; the stored count is always
  current. See `_progress_blocks` and `_refresh_scoreboard` (slack_bot.py).
- **Ask questions in the thread.** Each run's full output is captured into a
  per-thread record. Any non-command message in a campaign thread is answered by
  Claude, grounded strictly in that run's log, both mid-run ("what's the
  progress?") and after ("how many sent, and why were some skipped?"). `stop`
  still cancels a live run. Records are bounded (last 30 threads, last 4000 log
  lines each) and live in memory, so they reset when the service restarts.
- It is scoped to one channel, `SLACK_CHANNEL_ID`. One campaign at a time: a new
  mention while a thread is live gets a "busy" reply rather than starting a
  second session.
- Transport is Socket Mode, a persistent WebSocket worker with no public URL,
  which is the closest analog to Telegram long polling. Interactivity (buttons)
  is delivered over the same socket, so no Request URL is needed.

### One-time Slack app setup

In the Slack app config (https://api.slack.com/apps, the email_wizard app):

1. OAuth and Permissions, bot token scopes: `chat:write`, `channels:read`,
   `channels:history`, `app_mentions:read`. Install or reinstall to the
   workspace to get the `xoxb-` bot token.
2. Basic Information, App-Level Tokens: generate a token with `connections:write`
   to get the `xapp-` app token.
3. Socket Mode: enable it.
4. Event Subscriptions: enable, then subscribe to the bot events
   `message.channels` (thread replies without a mention) and `app_mention`
   (entry point). Save, reinstall if prompted.
5. Interactivity and Shortcuts: toggle on (no Request URL needed under Socket
   Mode). This enables the Send / Edit draft / Cancel buttons and the edit modal.
6. Invite the bot to the target channel once: `/invite @email_wizard`.

## Deployment (Railway)

Railway project `campaign_wiz` runs the `slack_wiz` service off this repo and
Dockerfile. Redeploy after a code change:

```bash
railway up --service slack_wiz --ci
```

### Environment variables

Campaign execution: `ANTHROPIC_API_KEY`, `GOOGLE_OAUTH_CLIENT_ID`,
`GOOGLE_OAUTH_CLIENT_SECRET`, `TOOLBOX_TOKEN_HUNTER`, `SUPABASE_URL`,
`SUPABASE_SECRET_KEY`, optionally `SUPABASE_BOT_REFRESH_TOKEN`, and
`GMAIL_REFRESH_TOKEN_{ARMAAN,SAMARJIT,ETHAN}`.

Slack: `SLACK_BOT_TOKEN` (xoxb), `SLACK_APP_TOKEN` (xapp), `SLACK_CHANNEL_ID`.
Optional `SLACK_REMINDER_ENABLED` to post the daily reminder into the channel
(off by default so it stays quiet in a shared channel). `WIZARD_PLATFORM` is no
longer read (the dispatcher was removed); leaving it set is harmless.

## Constraints and gotchas

- Only one Socket Mode instance of the Slack app may run at a time. Two instances
  (for example a local dev run plus the Railway service) both receive every event
  and both reply, producing duplicate messages. Stop one before starting another.
- The Gmail refresh tokens live only on Railway, not in `credentials/.env`, so a
  local run can plan and preview but cannot actually send. That makes local a safe
  place to test the conversation without sending email.
- Replying `send` in the deployed Slack wizard sends real email. Use `cancel` for
  tests.

## Changelog

- 2026-06-27: Agentic project Q&A. The wizard now answers open-ended questions in
  Slack ("did Nathan reply?", "reply rate this week?", "what can you do?") via a
  Claude tool-use loop (`qa.py`) over a READ-ONLY toolset (`read_doc`,
  `search_inbox`, `read_email_thread`, `lookup_contact`, `campaign_stats`). It
  engages on an @mention that is not a send or triage request (decided by
  `qa.classify_intent`) and on an unmentioned question in any other thread in the
  channel (`_is_question`). A live placeholder message is edited in place with
  progress while it works, then with the answer. Sending stays exclusively on the
  gated preview path; the Q&A loop can never send, draft, or delete. See
  `ARCHITECTURE.md` flow 3 and the read-only invariant.
- 2026-06-27: Triage fixes and the 5-min pester paused. (1) The triage report now
  collapses to one row per person: after the existing thread dedupe it dedupes by
  email so someone with several threads (e.g. two campaigns) is listed once,
  keeping their strongest signal (needs > reroute > gray, hottest priority).
  (2) Each bucket is grouped by owner A->Z and rendered as short bulleted lists
  with a priority emoji (and the ask inline) instead of a wide 3-column table, so
  it is far easier to skim; `format_messages` in `triage.py`. (3) The triage
  prompt (`reply_triage_probe.py` `_SYSTEM`) now treats a message that merely
  confirms/accepts a meeting we proposed, or any finalizing/closing line with no
  question or new ask, as `none` even when THEM sent last. (4) The every-5-min
  run-campaigns re-nudge (`_pester_run`) is commented out in `slack_bot.py`; the
  one-shot 17:30 reminder and 9:00am morning job still fire. Re-enable by
  uncommenting the interval job.
- 2026-06-26: Run-campaigns nudge is now volume-based. It used to go quiet the
  moment any campaign ran, so a trivial send silenced it for the day. It now
  tracks the day's real sent total (`record_campaign_sent`, called with the
  finished count; test-mode rehearsals do not count) and keeps nudging from
  5:30pm until that total reaches `SLACK_DAILY_TARGET` (default 2000) or the 4h
  cutoff. It also skips a tick while a campaign is actively sending. The nudge
  text shows progress ("we are at N of ~2000 today"). Replaced `mark_campaign_ran`
  with `record_campaign_sent` and the `last_run_date` flag with a `sent_today`
  counter that resets daily.
- 2026-06-26: Edit modal gained a Claude refine field, and generated emails are
  shorter. The edit modal now takes a free-text "ask Claude to change it"
  instruction alongside the manual subject/body fields; on save it applies the
  manual edits then has Opus refine per the instruction, preserving every
  `{{slot}}` (`agent.refine_template`, validated; falls back to the manual edits
  if a slot would be dropped). The CSV template prompt was tightened to at most
  three short paragraphs / ~90 words.
- 2026-06-26: Audience-fit shared template for CSV / direct sends. Replaced the
  earlier "brands.md plus an appended per-person line" approach (which misfit
  non-DTC audiences) with one shared template drafted by Opus to fit the CSV's
  audience: the student-and-school self-intro is kept as `{{school}}` slots, the
  rest is the model's discretion. It becomes the editable draft override, is
  mail-merged across the list, and falls back to `brands.md` if it drops a
  required slot. Removed `draft_personal_lines`, `_personalize_direct`, and
  `templates/brands_personalized.md`; added `agent.draft_csv_template` and
  `slack_bot._build_csv_template`.
- 2026-06-26: Deterministic CSV parsing for uploads. A big uploaded CSV used to
  break planning (Claude was asked to echo every row as JSON and truncated at
  max_tokens, raising "Unterminated string"). Attached files are now parsed in
  code (`agent.parse_contacts_csv` + `build_direct_plan`, reached via
  `slack_bot._present_csv_leads`), so any size works and no planning tokens are
  spent re-typing the list. The download cap was raised to 500k chars (CSVs read
  in full; the non-CSV LLM fallback re-truncates). The planner's max_tokens was
  also raised to 8192 for pasted (non-file) tables.
- 2026-06-26: Per-person personalization for CSV / direct sends. Claude now
  captures any extra per-lead context from an uploaded CSV; when present, the
  wizard writes a tailored, human-sounding opening line per recipient with the
  latest Opus model and uses `brands_personalized.md` (a `{{personal_line}}`
  slot). The preview renders up to three real recipients so the user can sanity
  check the copy. The line reaches the send via the temp CSV plus run.py's
  existing arbitrary-column mail-merge. New: `agent.draft_personal_lines`,
  `agent.render_for_lead`, `slack_bot._personalize_direct`, `_sample_blocks`.
- 2026-06-26: Slack-only. The Telegram front end (`bot.py`), its `launch.py`
  dispatcher, and the Telegram/reminder vars in `config.py` were removed; the
  team uses Slack only. `launch.py` now starts the Slack bot directly and
  `WIZARD_PLATFORM` is no longer read.
- 2026-06-26: Scoreboard shows located, sending, and a final summary. While a
  run sources leads the scoreboard climbs a live `N located...` count (driven by
  `run.py`'s per-step sourcing lines, throttled to ~2s); after composing it
  shows a plain `sending...` (sends are not tabulated live); on completion the
  footer reports the sent count, the campaign's Hunter credit spend, and elapsed
  time. Replaced the earlier `0 / N sent` footer that sat frozen during sending.
- 2026-06-26: Edit-draft modal. The preview gained an "Edit draft" button that
  opens a modal to hand-edit the scroll's subject and body (slots preserved);
  the edit becomes a temp template override for the run.
- 2026-06-26: Scheduled jobs (Pacific). 5:30pm a run-campaigns nudge @-mentions
  `SLACK_REMINDER_USER` and re-nudges every 5 min until a campaign runs that day
  (or a 4h cutoff); a campaign starting calls `mark_campaign_ran` to stop it.
  10:00am runs the inbox triage and broadcasts the tables plus an `@channel`
  nudge. Controlled by `SLACK_SCHEDULES_ENABLED` (default on) and
  `SLACK_SCHEDULE_TZ` (default America/Los_Angeles).
- 2026-06-26: Multi-sender selection and preview refinement. The planner now
  extracts a list of senders ("via Ethan and Samarjit") and `_divide` uses
  exactly the named accounts, splitting across them and capping at their combined
  daily limit. In the preview, any reply that is not send/cancel is treated as an
  adjustment (change sender, count, ICP), merged with the request and re-planned.
- 2026-06-25: Triage accuracy and output. A reply only counts as "awaiting our
  reply" when the prospect sent the last message (prompt rule plus a deterministic
  last-sender guard). The contacted ledger is now read with the service-role key
  so triage sees the whole team ledger, not just the bot's rows. Output is Slack
  `table` blocks, one per bucket (Awaiting reply / Reroute / Worth a glance),
  ordered by an LLM hot/warm/cold priority, chunked under Slack's 100-row limit.
- 2026-06-25: Sender selection, concise completion, and reply triage. The
  planner now honors a named sender ("through Samarjit"). The completion message
  dropped its code block. New read-only triage command: ask "which replies need
  a response?" and the wizard scans the sender inboxes (via the existing probe,
  run per account with Gmail tokens minted from the refresh tokens) and reports
  which prospect replies await an answer, which reroute to a new contact, and
  which need a glance. Lives in `server/triage.py` and `reply_triage_probe.py
  --json`.
- 2026-06-25: Wizard voice and live progress. The wizard's messages and Claude
  answers now use a light wizard persona. The executor pushes proactive progress
  into the thread (a "begins divining" note, sourcing updates each 25%, "scrolls
  penned", per-sender done), so a run is no longer a black box. Telegram shares
  the executor's progress lines.
- 2026-06-25: In-thread Q&A. The executor now forwards every run line (plus
  per-sender start/finish milestones) through a `log_line` callback; the Slack
  wizard captures it per thread and answers questions about the run via
  `agent.answer_about_campaign` (Claude), mid-run and after. `run.py` gained a
  Breakdown line (sent/skipped/suppressed/failed). Telegram unaffected.
- 2026-06-25: Slack wizard UX upgrade. Thread-based conversation (mention once,
  then reply in-thread with no mention), Block Kit formatting, and Send / Cancel
  buttons. Added the `message.channels` event and Interactivity to the app
  config. Added `WIZARD_TEST_MODE` (executor) for a zero-cost send rehearsal.
- 2026-06-25: Added the Slack wizard (`slack_bot.py`, `slack_config.py`), the
  `launch.py` dispatcher, and the `slack_wiz` Railway service. Telegram behavior
  unchanged.
