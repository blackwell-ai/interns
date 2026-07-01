---
title: Build Slack `/respond` reply-review queue (Claude-drafted, human-edit-and-send, trained on past replies)
created: 2026-07-01
created_by: shamit
assignee:            # any engineering-capable agent
priority: normal
claimed_by: claude
claimed_at: 2026-07-01
---

## Task

Build a Slack flow that removes the friction of answering prospect replies. Today the
morning triage tells the founders which emails need a reply, but each founder still has
to leave Slack, find the thread in Gmail, and write the response by hand. This build
turns that into a guided review queue inside Slack: one command pulls up each
reply-worthy email in turn, pre-filled with a recommended Claude draft that is grounded
in how we have actually answered similar emails before, and the founder edits it and
sends it in-thread without leaving Slack.

Before writing code, read the campaign wizard architecture doc and the reply-triage and
reply-followup docs in the campaign skill to ground yourself in how the Slack wizard, the
triage pipeline, and Gmail fit together. Then critique this plan before you start (per the
repo harness rules). Paths and function names are intentionally left out of this doc
because they drift; find the current owners of each capability described below by reading
the campaign skill.

### Why this shape, and what it is deliberately NOT

We considered and rejected two adjacent ideas. Keep them out of scope so this stays small:

1. Blanket auto-reply to every inbound. Rejected. A generic auto-response to an
   open-ended or strategic question turns a prospect off, and an unsupervised send in a
   founder's name is a real commitment plus a deliverability risk. A human edits and
   sends every message in this build.
2. Whole-inbox triage. Out of scope for v1. The queue is fed by the existing
   ledger-scoped triage (replies from people we already contacted). Widening the net to
   the whole inbox is a separate, later task and must not be coupled to this one.

The one place auto-send already exists (time-due out-of-office bumps in the morning
follow-up job) stays as it is. This build adds no new autonomous send.

## Current state (what already exists, reuse it)

The capabilities below already live in the campaign skill and its Slack wizard. Find and
reuse them rather than rebuilding.

- Reply detection and triage. A probe polls each founder's Gmail on a schedule, scoped to
  replies from addresses in our Supabase `contacted` ledger, over a rolling window. An LLM
  classifier decides which replies need a response and assigns each a category. The results
  are deduped by thread and person and posted to Slack as an owner-grouped morning digest.
  Each surviving row carries the sender, a snippet, the Gmail thread id, and the message id.
  Detected replies are also persisted to a Supabase `replies` table (deduped on message id),
  with sentiment classified per reply. This triage output is the queue source for this build.
- A dismissal store. Humans can mark a reply "not relevant," and triage filters those out on
  the next run. Sending from the new queue should reuse this store so a handled email does
  not reappear.
- The Slack wizard. It holds the conversation state machine, Block Kit rendering, button and
  modal handlers, and the scheduled jobs, over Socket Mode on one channel. Its state is
  in-memory and resets on restart. There is an existing editable-draft UI (show a draft, let
  the human tweak it before it goes out) to model the new modal on.
- Drafting and sending. A follow-up module already constructs in-thread responses and stages
  them as Gmail drafts (draft-first, human-approve); it is the reference for how to build an
  in-thread reply. The live send path mints a per-founder Gmail token and hands off to the
  shared Gmail send primitive. Per-founder tokens are minted from refresh tokens on the
  server, and the sender roster (key, email, from-name, cc) is defined in the wizard. There is
  also a working thread-reader tool (used by the read-only Q&A loop) for pulling full thread
  context.
- Data store. Supabase (Postgres via the PostgREST REST API). Reads use the anon key; team-wide
  writes use the service key so row-level security does not hide inserts.

## The build

Four pieces. Three of them are mostly assembly of what already exists.

### 1. The review queue (state machine + modal)

- Add a `/respond` command (or a button on the morning triage digest) that starts a review
  session for the invoking founder.
- Queue source: the same "needs a response" rows the triage already produces for that founder,
  minus anything already dismissed or already replied to.
- For each email, open a Block Kit modal (model it on the existing editable-draft UI) showing:
  - the incoming email for context (quoted thread, truncated to Slack's text limit),
  - a multiline editable text input pre-filled with the recommended Claude draft,
  - buttons: Send, Skip, Regenerate.
- On Send: send the edited text in-thread (see piece 3), mark the email handled (see Gotchas),
  then advance to the next email by updating the modal view. On Skip: advance without sending.
  End when the queue is empty.
- Session state (queue list, current position) can live in memory like the rest of the wizard's
  state. A review session is short; just fail gracefully if the process restarts mid-session
  (tell the user to re-run `/respond`).

### 2. Draft generation, trained on our past replies

Do NOT fine-tune. Volume is too small and it cannot update quickly. Use retrieval-augmented
few-shot: put our real past replies into the prompt as worked examples.

Corpus build (new script):
- For each founder, walk the Gmail Sent folder using the existing per-founder token minting.
- For every sent message that is a reply, pair it with the inbound message it answered (same
  thread, the prior message). That yields `(incoming_email, reply_we_sent)` pairs.
- Tag each pair with a category using the existing triage/sentiment classifiers so retrieval can
  match by kind (pricing, capabilities, scheduling, objection, referral, and so on).
- Curate the seed corpus: bias toward threads that went well (positive/interested sentiment,
  already classified). Skip auto-replies and bounces. A bad exemplar produces a bad draft in
  our voice.
- Store pairs in a new Supabase table `reply_examples` (schema below), service-key writes.

Per-founder voice card (one-time, refreshable):
- Distill a short voice guide per founder from their sent mail (tone, sentence length, sign-off,
  how they hedge). Inject it into the draft prompt alongside the exemplars so novel questions
  still sound like the founder.

Draft-time generation (called lazily as the reviewer reaches each email):
- Pull the full thread with the existing thread reader and the original outreach for context.
- Classify the incoming email's category, retrieve the best matching `reply_examples` for that
  founder and category, and pass them plus the voice card as few-shot examples.
- Prompt instruction must be "match the voice and reasoning of these examples," not "reuse them,"
  or you get near-verbatim replies that misfit the new context.
- v1 retrieval by category-match is fine. Note a pgvector upgrade path for semantic similarity
  as a later improvement; do not build it now.

### 3. Send in-thread, as the right founder

- The reply must go out from the founder who owns that inbox (their roster entry and token),
  threaded to the original with the appropriate reply headers and the Gmail thread id the triage
  row already carries. A reply that is not threaded looks like a fresh cold email and reintroduces
  the slippage this whole effort is about.
- OPEN QUESTION for the implementer to resolve first: confirm whether the shared Gmail send
  primitive supports in-thread replies (thread id plus reply headers). If it does not, lift the
  in-thread mechanics from the follow-up module, which already constructs in-thread messages as
  Gmail drafts. Decide send-vs-draft-then-send based on what the primitive supports; the
  user-facing behavior is "one Send button sends the edited text into the thread."

### 4. The feedback loop (this is the compounding part)

- When a founder sends a reply from the queue, insert that `(incoming_email, sent_reply)` pair
  back into `reply_examples`, tagged and marked as a curated gold example (it is exactly what a
  founder chose to send after editing Claude's draft).
- Over time the drafts get more founder-shaped automatically. The review UI generates its own
  training data.

## Data model

New Supabase table `reply_examples` (add a migration following the campaign wizard's existing
migration pattern):

- `id` (pk)
- `founder` (which sender the example belongs to)
- `category` (pricing / capabilities / scheduling / objection / referral / other)
- `incoming_subject`, `incoming_body`
- `reply_body` (what we sent)
- `sentiment` (of the thread, for curation)
- `source` (`harvest` for backfilled Sent mail, `queue` for feedback-loop sends)
- `is_gold` (bool; true for `queue` sends and human-approved harvested pairs)
- `message_id` (dedupe key, unique)
- `created_at`

Reuse the existing dismissal store for "handled," do not duplicate it.

## Gotchas (these will bite if skipped)

1. Mark-as-handled on send. After a send, record the email as handled via the existing dismissal
   store so it does not reappear in tomorrow's digest and get answered twice. This is the most
   likely thing to be missed.
2. Correct sender and threading (piece 3). Wrong sender or an unthreaded reply defeats the purpose.
3. Slack text limits. Truncate the quoted incoming thread shown for context. Email replies fit the
   editable input; long quoted threads do not.
4. In-memory wizard state resets on restart. Keep sessions short and degrade gracefully.
5. Privacy. The harvest reads founders' real correspondence. Keep it server-side, write with the
   service key, and never log message bodies or PII (repo security rules).
6. Do not copy exemplars verbatim. Prompt for approach and voice, not reuse.
7. Queue stays ledger-scoped for v1. Do not widen to the whole inbox here.

## Suggested phasing

1. Corpus + generation offline first: build the harvest, populate `reply_examples`, and prove the
   draft generator produces good, in-voice drafts for a sample of real past emails, before any
   Slack UI. This de-risks the only genuinely new part.
2. Then the Slack review queue (piece 1) wired to send (piece 3) and mark-as-handled.
3. Then the feedback loop (piece 4).
4. Voice card can land alongside step 1 or just after.

## Testing

Per the harness rules, write tests for a complex feature in a separate folder (the campaign skill
already groups tests this way). Cover the awkward cases: empty queue, a thread with no prior inbound
to pair, a message with no matching category examples (must still produce a sane draft), a send that
fails partway (must not mark handled), a restart mid-session, and dedupe on re-harvest. Delete the
test folder after merge.

## Done when

- A founder can run `/respond` in Slack and walk their reply-worthy emails one by one.
- Each email shows an editable draft that visibly reflects our past replies and the founder's voice,
  not generic copy.
- Editing and pressing Send delivers the message in-thread from the correct founder, and that email
  does not reappear in the next triage digest.
- Skipped emails are left untouched and still appear next time.
- Every reply sent from the queue is written back into `reply_examples` as a gold example.
- The harvest has backfilled `reply_examples` from the three founders' Sent folders, curated to good
  threads.
- Tests for the cases above pass, in a separate folder, and are removed after merge.
- The campaign wizard architecture doc (and the reply-triage doc if relevant) is updated to describe
  the new command, the `reply_examples` table, and the feedback loop.

## Out of scope (do not build here)

- Whole-inbox triage / dropping the ledger filter on the triage query.
- Any unsupervised or auto-send reply beyond the existing out-of-office bump.
- pgvector semantic retrieval (note it as a follow-up; category-match is the v1).

## Result

Status: code-complete and unit-tested. Live rollout (migrations, Slack config,
harvest, deploy) is left as human steps below because each is outward-facing or
needs credentials I do not hold in-session. No real email was sent and the
harvest was not run against real Gmail.

### What was built

Phase 1 (offline corpus + generation, the genuinely new part):
- `wizard/migrations/2026-07-01_reply_examples.sql` and `_voice_cards.sql` (follow
  the triage_dismissed pattern: service-key, RLS-on/no-policies, applied by hand).
- `wizard/reply_examples.py` - corpus store + `classify_category` (new taxonomy:
  pricing/capabilities/scheduling/objection/referral/other) + retrieval + the
  `add_gold_example` feedback write.
- `wizard/voice_cards.py` - per-founder voice guide store + `distill_card`.
- `harvest_reply_examples.py` - CLI that walks a founder's Gmail Sent folder,
  pairs each reply with the inbound it answered, curates by sentiment, tags
  category, and upserts pairs + a voice card. Reuses the probe/gmail helpers.
- `wizard/reply_drafter.py` - `generate_draft`: reads the thread, classifies the
  incoming email, retrieves matching examples + voice card, prompts Claude to
  match the founder's voice and reasoning (not reuse), returns the draft + the
  threading anchors the send path needs.

Phase 2/3 (Slack queue + feedback loop):
- `wizard/triage.py` `needs_for_founder(email)` - exposes the structured `needs`
  rows per founder (run_triage only returned formatted Slack text).
- `wizard/respond.py` - per-Slack-user review sessions and the flow (build queue,
  draft, step, send in-thread via reply_followup's create_draft_api/send_draft_api
  with a per-founder token, write each sent reply back as a gold example).
- `wizard/blocks.py` - the picker/review/info modals (`_respond_*`).
- `wizard/slack_bot.py` - handlers: `/respond` command, `resp_pick` view,
  `resp_skip`/`resp_regen` actions, `resp_review` (Send) view. Modal stepping via
  views_update / response_action:"update".

Tests: `skills/campaign/tests_respond/` (14 pass). Covers the awkward cases from
the task: empty queue, a thread with no prior inbound to pair, a novel category
with no matching examples (falls back to any-category founder exemplars), a send
that fails partway (does NOT record gold or advance; keeps the edit for retry), a
restart mid-session, and dedupe on re-harvest. Per the repo rule this folder is
temporary; delete after merge. The existing wizard suite is unchanged (same
pre-existing env-only failures).

Docs updated: `wizard/ARCHITECTURE.md` (new modules, flow 6, the two tables, the
Slack-config dependency, where-to-change) and `REPLY_TRIAGE.md` (the `needs`
bucket feeds /respond; why handled-marking is not the dismiss store).

### Decisions (confirmed with the requester)

1. Entry point: `/respond` slash command (not the digest button).
2. Whose queue: a founder picker in the first modal every time (no Slack-user to
   founder map needed).
3. Mark-as-handled: OVERRODE the plan. The plan said reuse the dismissal store;
   that store is keyed on the prospect email permanently, so it would hide all
   future replies from a prospect once answered. Instead we rely on the existing
   triage behavior (our reply lands in-thread -> next triage sees us as last
   sender -> skip; a genuine new reply re-surfaces) plus session-local advance.
   More correct and less code. Documented in both docs.

### Human steps to go live (in order)

1. Apply the two migrations to prod Supabase (SQL editor or psql):
   `wizard/migrations/2026-07-01_reply_examples.sql` and `_voice_cards.sql`.
2. In the Slack app config: register the `/respond` slash command and enable
   Interactivity, both delivered over Socket Mode (no Request URL). Until this is
   done the `/respond` handlers are dead code.
3. Seed the corpus per founder (needs the wizard env + a gog/Gmail token for each
   account): `python3 skills/campaign/harvest_reply_examples.py --account <email>`
   for Armaan, Samarjit, Ethan. Run with `--dry-run` first to see counts. Until
   seeded, drafts still work but are plainer (no exemplars/voice yet).
4. Deploy the wizard (Railway `slack_wiz`) with the new code. Do this AFTER step 1
   or `/respond` will error on the missing tables. I did not deploy for that
   reason (and because the branch is unreviewed/uncommitted).

### Out of scope (as specified)

Whole-inbox triage, any new autonomous send, and pgvector semantic retrieval
(noted as a future upgrade; v1 is category-match) were left out.

### Durable knowledge

Architecture and rollout are in `wizard/ARCHITECTURE.md` (flow 6 + the migrations
+ the Slack-config note) and `REPLY_TRIAGE.md`, per the repo's docs-are-durable rule.
