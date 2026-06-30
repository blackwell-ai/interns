# Campaign wizard architecture

A map of the Slack campaign bot as it actually runs, written so an agent landing
here cold can find the right file before changing anything. For one-time setup,
env vars, and the dated change history, see `README.md`; this file is the
structure, not the history.

## Keep this current

This doc is only useful if it matches the code. When you change the architecture
(add or remove a module, move a responsibility, change a data flow, add an
external dependency, change a stored table, or alter a core invariant), update
this file in the same change. Routine edits (copy tweaks, a bug fix inside an
existing function, a prompt wording change) do not need an entry here. If you are
a subagent sent to fix something, read this first, then confirm the file you are
about to touch still matches what is written below, and correct the doc if it
does not.

## What it is

The wizard is a Slack front end over the existing campaign pipeline. A teammate
mentions the bot in one channel with a plain-English request ("2000 to DTC
brands via Ethan"), the bot plans the send, shows a preview, and on confirmation
runs the same `run.py` campaign the CLI uses. The same service also runs reply
triage and morning follow-ups on a schedule. It is one long-lived process, one
Docker image, one Railway service (`slack_wiz`).

The planning and execution code is platform-agnostic; only `slack_bot.py` knows
about Slack. That split is deliberate, keep it.

## Process and transport

- Entry point: `launch.py` runs `slack_bot.main()`. The Dockerfile CMD is
  `python -m skills.campaign.server.launch`.
- Transport: Slack Socket Mode (`slack_bolt.AsyncApp` over a WebSocket, no public
  URL). Buttons and modals arrive on the same socket.
- Single instance only. Two processes on the same Slack app both receive every
  event and both reply. Never run a local instance against the prod app token.
- State lives in memory (`_state`, per-thread run records, the pester counters).
  A restart resets all of it. Nothing in the process is the source of truth;
  durable state is in Supabase and Gmail.

## Module map (`skills/campaign/server/`)

- `launch.py` - entry point, starts the bot.
- `slack_bot.py` - the only Slack-aware module. Holds the conversation state
  machine, the Block Kit rendering, the button/modal handlers, the scheduled
  jobs, and the live scoreboard. Key pieces: `on_message` (router entry),
  `_route` (intent dispatch), `_plan_and_present` / `_present_plan`,
  `_execute` (kicks off the run and the scoreboard), the `@app.action` /
  `@app.view` handlers (`on_send`, `on_cancel`, `on_edit`, `on_edit_submit`),
  and the scheduled jobs (`_remind_run`, `_pester_run`, `_daily_triage`,
  `_morning_followups`) wired up in `main()` via APScheduler.
- `agent.py` - planning and copy, no platform code. Claude turns a request into a
  structured plan (`plan`), `_divide` does sender and daily-cap arithmetic over
  `SENDERS`, and the template/draft helpers live here (`draft_csv_template`,
  `render_for_lead`, `editable_draft`, `refine_template`, `parse_contacts_csv`).
  `SENDERS` is the canonical list of sender accounts (key, email, from_name, cc).
- `executor.py` - runs each planned campaign as a `run.py` subprocess
  (`run_campaign`, `run_all`) and reports progress through two callbacks,
  `send_update` (async, posts text) and `set_progress`. `REPO_ROOT` and
  `_get_supabase_session_token` are here; other modules import them.
- `triage.py` - reply triage for Slack. Runs `reply_triage_probe.py --json` once
  per sender inbox (`_run_account`), merges across inboxes (`merge_results`),
  and renders the Slack messages (`format_messages`). Read only, sends nothing.
- `qa.py` - agentic project Q&A. Runs a Claude tool-use loop with a READ-ONLY
  toolset (`read_doc`, `search_inbox`, `read_email_thread`, `lookup_contact`,
  `campaign_stats`) to answer open-ended questions ("did X reply", "reply rate
  this week", "what can you do"). `answer(question, on_step)` is the loop;
  `classify_intent(text)` decides send vs question for a fresh mention. No send,
  draft, or delete tool exists here by design.
- `gmail_auth.py` - `get_access_token(email)` exchanges a per-sender refresh
  token (env `GMAIL_REFRESH_TOKEN_{KEY}`) for a Gmail access token. This is how
  the bot acts as each sender on Railway, where there is no `gog` keychain.
- `config.py` / `slack_config.py` - env-backed config. `slack_config` holds the
  Slack tokens, the channel id, the schedule toggle/timezone, the daily target,
  and the reminder user.
- `seed_tokens.py` / `setup_railway.py` - one-time provisioning helpers (seed the
  Gmail refresh tokens / Railway env). Not part of the request path.

## Shared pipeline modules (`skills/campaign/`, not platform-specific)

The bot reuses these; they also run from the CLI. Fix them here, not by forking.

- `run.py` - the campaign send pipeline: source/enrich leads, dedupe against the
  `contacted` ledger, send via `gmail_cli._send_all`, and finalize (write the
  `campaigns` row, append the JSONL log). The send is what writes a `contacted`
  row; anything emailed outside this path is invisible to the ledger.
- `reply_triage_probe.py` - the read-only triage engine `triage.py` shells out
  to. Scopes candidates to inbound from `contacted`-ledger addresses, fetches
  full threads, and classifies each with one Claude call (`_SYSTEM` prompt:
  reply / reroute / none, plus priority and a short `their_ask`).
- `reply_followup.py` - morning follow-up planning and drafting (OOO bumps,
  referral and ask emails for reroutes). `run_morning` is the entry the bot's
  `_morning_followups` job calls per account.
- `toolbox` `core/ledger.py` - the `contacted` ledger client (atomic claim,
  per-user rows under RLS). Read it with the service-role key to see the whole
  team (see invariants).

## External systems

- Supabase. Tables: `contacted` (who we have emailed, dedupe + triage scope),
  `campaigns` (one row per run), and the replies/contacts data the reports read.
  Auth is per-user; RLS scopes rows to the writer unless a service-role key is
  used.
- Gmail API. One refresh token per sender (Armaan, Samarjit, Ethan), minted to
  an access token by `gmail_auth`. Sends, thread reads, and drafts go through it.
- Anthropic API. Two uses: planning/copy in `agent.py`, and per-thread triage
  classification in `reply_triage_probe.py`.
- Hunter (and optionally Origami) for lead enrichment inside `run.py`.
- Slack. One channel (`SLACK_CHANNEL_ID`), Socket Mode.

## Core flows

### 1. Send a campaign

`on_message` -> `_route` detects a send request -> `_plan_and_present`
(`agent.plan` + `_divide`) -> preview with Send/Edit/Cancel. On Send,
`on_send` -> `_execute` -> `executor.run_all` spawns `run.py` per sender while
`_refresh_scoreboard` edits one status message in place. On finish, the
scoreboard shows sent count, Hunter spend, and elapsed time. A CSV/direct send
takes the same path but builds one audience-fit shared template first
(`_build_csv_template` / `agent.draft_csv_template`).

### 2. Reply triage

Triggered by a triage-intent message (`_is_triage` -> `_start_triage`) or the
daily job (`_daily_triage`). `triage.run_triage` mints a Gmail token per sender,
runs the probe per inbox concurrently, merges and dedupes (by thread, then by
person), and posts the report: awaiting-reply and worth-a-glance as owner-grouped
lists, reroute as a per-owner count (reroutes are pursued autonomously).

### 3. Answer a question (agentic Q&A)

A fresh @mention that is not triage and not a send request (decided by
`qa.classify_intent`), or an unmentioned message that reads as a question in any
other thread in the channel (`slack_bot._is_question`), routes to
`slack_bot._start_qa`. That posts a placeholder, then runs `qa.answer`, which
loops Claude over the read-only tools, editing the placeholder in place with
progress (`on_step`, throttled ~2s) and finally with the answer. Read only; it
can never send. Send requests still go through the gated preview flow.

### 4. Morning follow-ups

`_morning_followups` (9:00am job) calls `reply_followup.run_morning` per account
to auto-send due OOO bumps and stage the rest, then posts a report and runs the
triage broadcast after it.

### 5. Scheduled jobs

Registered in `slack_bot.main()` under APScheduler, gated by
`SLACK_SCHEDULES_ENABLED`, in `SLACK_SCHEDULE_TZ` (default Pacific): a 17:30
run-campaigns reminder (`_remind_run`) and the 09:00 morning job. The every-5-min
re-nudge (`_pester_run`) is currently commented out in `main()`.

## Invariants and gotchas

- One Socket Mode instance at a time (duplicate replies otherwise).
- One campaign at a time. A new mention while a thread is live gets a busy reply.
- The conversation is thread-based and scoped to one channel. Inside its active
  thread the bot reads every message with no further mention; elsewhere it is
  ignored.
- Triage and ledger coverage equals the `contacted` ledger. People emailed
  outside `run.py` (hand-sent, other tools) never get a `contacted` row, so
  triage never queries Gmail for them and they do not appear. Read the ledger
  with the service-role key (`TRIAGE_LEDGER_SERVICE_KEY`) so RLS does not hide
  other teammates' sends.
- Slack limits the bot renders around: a section block caps at 3000 chars and a
  message at 50 blocks, so long lists are chunked (see `triage.py`
  `_owner_sections` and `slack_bot._chunk_sections`).
- In-memory state resets on restart; per-thread Q&A records are bounded and
  ephemeral.
- The agentic Q&A (`qa.py`) is read-only by contract. It reads inboxes, the
  ledger, and docs and reasons over them, but has no tool that sends or mutates,
  so an instruction injected via an email it reads has nothing to act on. Sending
  stays solely on the gated preview path. Do not add a write tool to this loop.
- Gmail refresh tokens exist only on Railway, so a local run can plan and preview
  but cannot send. Local is a safe place to test the conversation.

## Where to change X

- Q&A behaviour, tools, or what it can read -> `qa.py` (`_TOOLS` + `_DISPATCH`,
  `_SYSTEM`). Keep it read-only: never add a send/draft/delete tool here.
- When the bot treats a message as a question vs a send -> `qa.classify_intent`
  and `slack_bot._is_question`, wired in `slack_bot.on_message`.
- Triage classification (what counts as needing a reply) -> `reply_triage_probe.py`
  `_SYSTEM`.
- Triage Slack layout (grouping, counts, dedupe) -> `triage.py` (`format_messages`,
  `merge_results`, `_owner_sections`).
- How a request is parsed into a plan -> `agent.py` `plan` / `_divide`.
- Sender accounts, names, CC -> `agent.py` `SENDERS`.
- Email copy / templates / draft editing -> `agent.py` (`draft_csv_template`,
  `render_for_lead`, `refine_template`).
- The send mechanics (sourcing, dedupe, actual send) -> `run.py` and the toolbox
  gmail primitive, not the server.
- Buttons, modal, scoreboard, routing -> `slack_bot.py`.
- Schedules (times, which jobs run) -> `slack_bot.main()` + `slack_config`.
- Follow-up drafting (OOO, referral, ask) -> `reply_followup.py`.
