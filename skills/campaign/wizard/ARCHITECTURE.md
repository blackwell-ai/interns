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
  `python -m skills.campaign.wizard.launch`.
- Transport: Slack Socket Mode (`slack_bolt.AsyncApp` over a WebSocket, no public
  URL). Buttons and modals arrive on the same socket.
- Single instance only. Two processes on the same Slack app both receive every
  event and both reply. Never run a local instance against the prod app token.
- State lives in memory (`_state`, per-thread run records, the pester counters).
  A restart resets all of it. Nothing in the process is the source of truth;
  durable state is in Supabase and Gmail.

## Module map (`skills/campaign/wizard/`)

The Slack front end was split out of one 1300-line `slack_bot.py` into four
modules (`slack_bot`, `session`, `blocks`, `schedules`), and the planning/copy
`agent.py` into two (`planner`, `drafting`). `agent.py` and `slack_bot.py` remain
as import surfaces (see "Compatibility facades" below), so callers and tests that
use `agent.<name>` / `slack_bot.<name>` are unchanged. Change code in the focused
module, not the facade.

- `launch.py` - entry point, starts the bot (`slack_bot.main()`).
- `slack_bot.py` - the Bolt-facing module: the `@app.event` / `@app.action` /
  `@app.view` handlers (`on_message` router, `on_send`, `on_cancel`, `on_edit`,
  `on_edit_submit`), the run-campaigns nudge jobs (`_remind_run`, `_pester_run`,
  `_run_reminder_text` - here rather than in `schedules` because their tests
  patch `slack_bot._post_channel`), `_bot_user_id`, and `main()`, which wires the
  schedules via APScheduler. Re-exports the session/blocks/schedules names that
  tests reach for as `slack_bot.<name>`.
- `session.py` - the conversation core: the shared `_state` machine (`_route`,
  `_present_plan`, `_plan_and_present`, `_present_csv_leads`), `_execute` (kicks
  off the run and the live scoreboard), the reply/triage/Q&A glue (`_reply_to`,
  `_post_channel`, `_start_triage`, `_handle_triage_edit`, `_start_qa`), the draft
  override helpers, and the shared pester counter (`_pester`,
  `record_campaign_sent`). Owns the Bolt `app` object and all in-memory state.
- `blocks.py` - pure Block Kit builders (no state, no `app`): `_preview_blocks`,
  `_sample_blocks`, `_niche_blocks`, `_progress_blocks`, `_edit_modal`, and the
  morning report (`_morning_report_blocks`, `_chunk_sections`).
- `schedules.py` - the 9am morning jobs: `_morning_followups` (auto-send OOO
  bumps, stage the rest) and `_daily_triage` (the inbox-triage broadcast).
- `planner.py` - planning, no platform code. Claude turns a request into a
  structured plan (`plan`), `_divide` does sender and daily-cap arithmetic over
  `SENDERS` (the canonical sender list), `preview_niches` surfaces the target
  niches, and `answer_about_campaign` answers grounded questions about a run.
- `drafting.py` - email copy: template rendering (`render_sample`,
  `render_for_lead`, `editable_draft`), CSV parsing (`parse_contacts_csv`), and
  the Claude copy prompts (`draft_csv_template`, `refine_template`).
- `agent.py` - compatibility facade re-exporting `planner` + `drafting`.
- `respond.py` - the `/respond` reply-review queue: per-Slack-user review sessions
  (`_review_sessions`) and the flow that pulls a founder's awaiting-reply queue,
  drafts each reply, steps through them, sends in-thread, and writes each sent
  reply back to the corpus. Handlers are in `slack_bot.py`; modal layouts in
  `blocks.py`.
- `reply_drafter.py` - `generate_draft(founder_key, founder_email, thread_id)`:
  reads the thread, classifies the incoming email, retrieves the founder's
  matching `reply_examples` plus their voice card, and prompts Claude to MATCH the
  voice and reasoning of those examples (not reuse them). Returns the draft plus
  the threading anchors the send path needs.
- `reply_examples.py` - the `reply_examples` corpus: `classify_category`,
  `upsert_examples`, `retrieve`/`retrieve_any`, and `add_gold_example` (the
  feedback-loop write). Service-key Supabase access.
- `voice_cards.py` - per-founder voice guide store: `distill_card`, `get_card`,
  `upsert_card`.
- `executor.py` - runs each planned campaign as a `run.py` subprocess
  (`run_campaign`, `run_all`) and reports progress through two callbacks,
  `send_update` (async, posts text) and `set_progress`. `REPO_ROOT` and
  `_get_supabase_session_token` are here; other modules import them.
- `triage.py` - reply triage for Slack. Runs `reply_triage_probe.py --json` once
  per sender inbox (`_run_account`), merges across inboxes (`merge_results`),
  and renders the Slack messages (`format_messages`). Read only, sends nothing.
- `qa.py` - agentic project Q&A. Runs a Claude tool-use loop with a READ-ONLY
  toolset (`read_doc`, `search_inbox`, `read_email_thread`, `lookup_contact`,
  `campaign_stats`, `sent_today`, `list_replies`) to answer open-ended questions
  ("did X reply", "reply rate this week", "what are the aerospace folks saying",
  "what can you do"). `list_replies` scopes replies to a group by matching the
  campaign ICP, so group questions get real answers instead of a generic triage.
  `answer(question, on_step)` is the loop; `classify_intent(text)` is the 3-way
  router (send / triage / question) for a fresh mention. No send, draft, or
  delete tool exists here by design.
- `gmail_auth.py` - `get_access_token(email)` exchanges a per-sender refresh
  token (env `GMAIL_REFRESH_TOKEN_{KEY}`) for a Gmail access token. This is how
  the bot acts as each sender on Railway, where there is no `gog` keychain.
- `config.py` / `slack_config.py` - env-backed config. `slack_config` holds the
  Slack tokens, the channel id, the schedule toggle/timezone, the daily target,
  and the reminder user.
- `seed_tokens.py` / `setup_railway.py` - one-time provisioning helpers (seed the
  Gmail refresh tokens / Railway env). Not part of the request path.

### Compatibility facades

`agent.py` and `slack_bot.py` are import surfaces, not where the logic lives.
`agent.py` re-exports every public name from `planner` and `drafting` (plus the
few private helpers the tests use, like `_divide`, `_allocate`); `slack_bot.py`
re-exports the `session` / `blocks` / `schedules` names that tests and callers
reach for as `slack_bot.<name>`. This keeps `from ... import agent`,
`agent.plan`, `slack_bot._state`, etc. working after the split. Rule of thumb:
read and change the focused module (`planner`, `drafting`, `session`, `blocks`,
`schedules`); touch the facade only to add or rename an exported name. The one
deliberate exception is the run-nudge trio, which lives in `slack_bot.py` (not
`schedules.py`) so its tests can patch `slack_bot._post_channel`.

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
  `_morning_followups` job calls per account. Also the ONLY place with working
  in-thread reply construction: `create_draft_api(token, spec)` (sets the Gmail
  `threadId` and `In-Reply-To`/`References`) + `send_draft_api(token, draft_id)`.
  The `/respond` send path reuses these with a per-founder token.
- `harvest_reply_examples.py` - offline CLI (`--account`) that backfills the
  `reply_examples` corpus and `voice_cards` from a founder's Gmail Sent folder:
  pairs each reply they sent with the inbound it answered, curates by sentiment,
  tags category, and upserts. Run once per founder at rollout, or to refresh.
- `toolbox` `core/ledger.py` - the `contacted` ledger client (atomic claim,
  per-user rows under RLS). Read it with the service-role key to see the whole
  team (see invariants).

## External systems

- Supabase. Tables: `contacted` (who we have emailed, dedupe + triage scope),
  `campaigns` (one row per run), `replies` (detected inbound replies + sentiment),
  `triage_dismissed` (people hidden from triage), `reply_examples` ((incoming,
  reply) exemplars for the /respond drafter, source harvest|queue), and
  `voice_cards` (per-founder voice guide). The last two are created by the
  migrations dated 2026-07-01 under `migrations/`, applied by hand.
  Auth is per-user; RLS scopes rows to the writer unless a service-role key is
  used.
- Gmail API. One refresh token per sender (Armaan, Samarjit, Ethan), minted to
  an access token by `gmail_auth`. Sends, thread reads, and drafts go through it.
- Anthropic API. Two uses: planning in `planner.py` and email copy in
  `drafting.py`, and per-thread triage classification in `reply_triage_probe.py`.
- Hunter (and optionally Origami) for lead enrichment inside `run.py`.
- Slack. One channel (`SLACK_CHANNEL_ID`), Socket Mode.

## Core flows

### 1. Send a campaign

`slack_bot.on_message` -> `session._route` detects a send request ->
`session._plan_and_present` (`planner.plan` + `_divide`) -> `session._present_plan`
also calls `planner.preview_niches` so the confirm preview lists the target
niches and a few sample domains per ICP. That is the human catch for sourcing
intent drift (e.g. an "affiliate marketing" ask returning Robinhood) before
anything sends, and it populates the same `SubcategoryCache` (keyed on the ICP
string) that the run.py subprocess reads, so the niches shown are the niches
used. Then preview (`blocks._preview_blocks`) with Send/Edit/Cancel. On Send,
`slack_bot.on_send` -> `session._execute` -> `executor.run_all` spawns `run.py`
per sender while `_refresh_scoreboard` edits one status message in place. On
finish, the scoreboard shows sent count, Hunter spend, and elapsed time. A
CSV/direct send takes the same path but builds one audience-fit shared template
first (`session._build_csv_template` / `drafting.draft_csv_template`).

### 2. Reply triage

Triggered by a triage-intent message (`_is_triage` -> `_start_triage`) or the
daily job (`_daily_triage`). `triage.run_triage` mints a Gmail token per sender,
runs the probe per inbox concurrently, merges and dedupes (by thread, then by
person), and posts the report: awaiting-reply and worth-a-glance as owner-grouped
lists, reroute as a per-owner count (reroutes are pursued autonomously).

### 3. Answer a question (agentic Q&A)

A fresh @mention is routed by `qa.classify_intent`, a 3-way classifier (send /
triage / question) that runs before any keyword gate. This is deliberate: a
question that merely contains "replies" or "responses" ("what did the aerospace
folks say") must reach the Q&A loop, not be swallowed by a keyword-matched
full-inbox triage. An unmentioned message that reads as a question in any other
thread in the channel (`slack_bot._is_question`) also routes to
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

### 6. Respond to a reply (the /respond review queue)

A founder runs `/respond` (`slack_bot.on_respond_command`) and picks whose inbox
to work (`blocks._respond_picker_modal`; a founder picker every time, so no
Slack-user-to-founder map is needed). On submit, `respond.build_first` pulls that
founder's awaiting-reply rows via `triage.needs_for_founder` (the same probe
`run_triage` uses, scoped to one inbox, dismiss-list applied), then steps through
them one modal at a time. For each, `reply_drafter.generate_draft` reads the
thread, classifies the incoming email, retrieves the founder's matching
`reply_examples` plus their voice card, and drafts a reply that matches their
voice. The founder edits it and hits Send (`respond.on_send`), which sends
in-thread as that founder via `reply_followup.create_draft_api` +
`send_draft_api`, then writes the sent reply back to `reply_examples` as a gold
example (`reply_examples.add_gold_example`) so the corpus compounds. Skip and
Regenerate are in-modal buttons. Sessions are per-Slack-user and in memory
(`respond._review_sessions`); a restart just means re-running `/respond`.

Handled-marking is deliberately NOT persisted. A sent reply lands in-thread, so
the next triage sees us as last sender and drops that thread (`skip` bucket),
while a genuine new reply from the same prospect correctly re-surfaces. The
dismiss store is not used for "handled" (it is keyed on the prospect email
forever and would silence future replies). Within a session, a handled email is
just advanced past.

This flow needs one-time Slack app config: register the `/respond` slash command
and enable Interactivity, both over Socket Mode (no Request URL). Without it the
handlers are dead code. The modal stepping uses `views_update` /
`response_action:"update"` (the only view-stepping in the wizard).

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
  `_owner_sections` and `blocks._chunk_sections`).
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
- When the bot treats a message as send vs triage vs question -> the 3-way
  `qa.classify_intent` (and `_CLASSIFY_SYSTEM`) plus `slack_bot._is_question`,
  wired in `slack_bot.on_message`. Do not reinstate a keyword triage gate ahead
  of the classifier: it is what made "what did X reply" trigger a full scan.
- Group reply questions ("what are the aerospace folks saying") -> `qa.py`
  `list_replies` (joins campaigns ICP -> contacted -> replies).
- Triage classification (what counts as needing a reply) -> `reply_triage_probe.py`
  `_SYSTEM`.
- Triage Slack layout (grouping, counts, dedupe) -> `triage.py` (`format_messages`,
  `merge_results`, `_owner_sections`).
- How a request is parsed into a plan -> `planner.py` `plan` / `_divide`.
- Sourcing intent drift (a niche wandering off the target market) -> `run.py`
  `generate_subcategories` prompt and `_critique_subcategories` (the audit pass).
  The niche preview that surfaces it to a human -> `planner.preview_niches` +
  `blocks._niche_blocks`.
- Sender accounts, names, CC -> `planner.py` `SENDERS`.
- Email copy / templates / draft editing -> `drafting.py` (`draft_csv_template`,
  `render_for_lead`, `refine_template`).
- The conversation flow, buttons, modal, scoreboard -> `session.py`; the Bolt
  handlers and startup -> `slack_bot.py`; the Block Kit layout -> `blocks.py`.
- The send mechanics (sourcing, dedupe, actual send) -> `run.py` and the toolbox
  gmail primitive, not the wizard package.
- The /respond queue flow (build queue, step, send, feedback) -> `respond.py`; its
  handlers -> `slack_bot.py` (`on_respond_command`, `on_respond_pick`,
  `on_respond_skip`, `on_respond_regen`, `on_respond_send`); its modals ->
  `blocks.py` (`_respond_*`). The queue source -> `triage.needs_for_founder`.
- How a reply draft is written (prompt, retrieval, voice) -> `reply_drafter.py`
  (`_SYSTEM`) + `reply_examples.retrieve` + `voice_cards`. The category taxonomy
  -> `reply_examples.CATEGORIES` / `classify_category`.
- The reply-example corpus (backfill) -> `harvest_reply_examples.py`; the schema
  -> `migrations/2026-07-01_reply_examples.sql` (and `_voice_cards.sql`).
- Buttons, modal, scoreboard, routing -> `slack_bot.py`.
- Schedules (times, which jobs run) -> `slack_bot.main()` + `slack_config`.
- Follow-up drafting (OOO, referral, ask) -> `reply_followup.py`.
