# Automation Harness — Spec v0.2

**Repo:** `blackwell-ai/interns` · **Date:** 2026-06-10 · **Status:** draft for team review
**Supersedes v0.1.** What changed: flows are now declarative compositions of primitives (nothing hardcoded, including the build loop itself); process steps like planning, clarification, tests, and canaries are removable primitives; auth moves from `credentials/.env` to per-person Supabase OAuth; ledgers move to Supabase and enforce the no-double-contact rule across all people and all automations; all volume caps, throttles, and warmup machinery are deleted — the harness optimizes for speed.

---

## 0. Where this sits in the brain

The **company brain** is the whole system: this repo, the agent fleet, and the Supabase backbone described below. Per the founding notes, the brain's capabilities span retrieving and manipulating everything the company knows, running arbitrary automations while we sleep, business research and ideation, and end-to-end company creation.

This spec covers **one organ of the brain: the automation harness** — the machinery that turns a natural-language request into running, remembered, forkable automations. In particular, this spec applies the infrastructure below to automations dealing with outreach. The repo as a whole will include other agents - a researcher agent, a future company-creator agent, something that doesn't exist yet. 

---

## 1. The capability

Anyone on the team tells an agent a flow in plain English — *"fetch 1,000 domains related to X, find their emails on Apollo, fill a template, send"* — and the agent:

1. composes the flow from existing **primitives** (small, tested building blocks),
2. includes whatever **process steps** the request calls for — planning, one-pass clarification, tests, a canary — all of which are themselves primitives and all of which can be left out,
3. runs it fast: parallel where possible, no artificial pacing,
4. never contacts the same person twice across any automation, any teammate, any machine — the one hard invariant,
5. saves it as a **skill** that can be rerun, or forked in seconds with steps added or removed.

---

## 2. Why `email_automation_pipeline` broke

The email_automation_pipeline (an old version of this particular organ of the company brain) can be found at the following url: https://github.com/sd393/email_automation_pipeline ; Here are the problems with it - 

**Flexibility lived at the wrong layer.** `brief.yaml` let you change *values* (segment, roles), but the pipeline's *shape* — five fixed stages in fixed order — was frozen into ~2,200 lines of stage scripts. Any structurally different flow meant engineering, not a request.

**Each new flow shape cost a waterfall.** The repo's `planning/` folder shows a 12-section build plan for a single pipeline. That cost can't be paid per flow.

**Stages were monoliths.** `send_emails.py` alone is 493 lines mixing orchestration, Gmail mechanics, locking, and phase logic. Nothing was independently callable, so nothing recombined.

**No memory.** Campaigns were disposable; the only reusable unit was the entire engine.

**What we still port:** `gmail.py` (MIME construction + send, with auth swapped out), `csv_schema.py`, `observability.py`, `template_render.py`, `first_name.py`, `llm.py` (provider swapped to Anthropic). **What we now drop from the port list:** `rate_limit.py` and the Phase A ramp machinery (see §8 — speed posture), and `dedup.py`'s file-locking design (the *idea* survives as the Supabase ledger, §6).

---

## 3. Design principles

1. **Everything is a primitive; flows are compositions.** Work steps (search Apollo, send mail) and process steps (write a plan, ask clarifying questions, smoke-test, dry-run, canary) are the same kind of thing: removable, reorderable lines in a flow. No step is sacred. The default chains in §7 are defaults, not law.
2. **Fork first.** The threshold for forking is near zero. Routing preference, in order: rerun an existing skill → fork one → compose a new flow from existing primitives → write a new primitive (the only deliberate, justified act).
3. **Nothing hardcoded in flows.** A flow is a declarative step list — *declarative* meaning it states *what* runs in *what* order, not how — executed by a generic runner. Removing the smoke test from a fork is deleting one line.
4. **Files are the interface.** Each step reads files from the run folder and writes files back. Generated glue stays tiny, every intermediate state is inspectable, and resume-after-crash is free.
5. **One invariant, enforced below the flow layer: the contact ledger.** Flows can drop any step they like; they cannot compose away the ledger check, because it lives inside the send-class primitives and in a database constraint, not in the flow.
6. **Speed is the optimization target.** No proactive throttling, no caps, no warmup. Parallel by default. The only nod to providers is that a refused request retries with backoff instead of killing the run — a dead run is the slowest possible run.
7. **Identity through Supabase.** Every person authenticates once; every integration hangs off their account; every irreversible action is attributable to a person. No secrets in the repo, ever.
8. **Documents are the durable asset** (per `/CLAUDE.md`). A *registered* skill has a `SKILL.md` that its flow is regenerable from. One-off "just run it now" flows can skip the ceremony and live unregistered in `runs/`.

---

## 4. Architecture

```
                        ┌─────────────────────────────────────┐
                        │  Supabase backbone                   │
                        │   auth (per-person OAuth)            │
                        │   connections (per-person tokens)    │
                        │   ledgers (contacted / suppression)  │
                        └──────────────▲──────────────────────┘
                                       │ core/auth.py · core/ledger.py
repo:                                  │
  brain/       what the company knows  │                      (exists, unchanged)
  agents/      the fleet — outreach, researcher, …            (charters get edits)
  inbox/       task queue                                     (exists, unchanged)
  toolbox/     primitives + the runner — the only maintained code   (NEW)
  skills/      remembered flows: SKILL.md + flow.yaml + inputs.yaml (upgraded)
  runs/        one folder per execution: artifacts, events, report  (NEW, gitignored)
  supabase/    migrations + edge functions for the backbone        (NEW)
```

Deleted relative to today's repo: `credentials/` (replaced by §7 auth) and the planned `data/` ledger files from v0.1 (replaced by Supabase tables, §6).

Vocabulary: a **primitive** is a small tested program doing one job. A **flow** is a declarative step list combining primitives, executed by the runner. A **skill** is a remembered flow. A **run** is one execution with its own folder. The **ledger** is the database record of irreversible actions.

---

## 5. Primitives (`toolbox/`)

The only maintained code. Two kinds, same contract:

**Work primitives** — touch the world or transform data:

```
gmail/        send mail, read replies/bounces        (port of gmail.py, auth swapped)
apollo/       people/company search + enrichment     (new)
storeleads/   e-commerce store search                (new)
domains/      web-search domain sourcing             (port of source_domains internals)
verify/       MX/DNS + mailbox checks                (port of verifiers/)
compose/      template render + LLM personalization  (port of template_render, first_name)
```

**Process primitives** — the steps that used to be a hardcoded "build loop," now optional lines in a flow:

```
plan.write     draft/refresh SKILL.md from the request and brain context   (build-time)
clarify.ask    fill inputs.yaml with defaults, present ONE review pass     (build- or run-time)
test.smoke     run the offline smoke tests of every primitive the flow uses
test.dryrun    execute send-class steps with --dry-run on a sample, grade
               the output against SKILL.md → Acceptance checks
canary.run     small live batch (default 10, incl. seed inboxes) then a
               human go/no-go gate
report.write   write runs/<id>/report.md, append to skill changelog, update INDEX.md
```

Want an automation with no smoke test, no questions, no canary? Those lines simply aren't in its flow. The agent includes them by default when building something *new* (§6) and drops any of them the moment you say so.

**Shared plumbing** (`toolbox/core/`): `runner.py` (executes flows), `auth.py` (§7), `ledger.py` (§6), `events.py`, `io.py`, `llm.py`.

### The primitive contract (`TOOLBOX.md`)

1. **File in, file out.** Invoked as a CLI with `--in/--out` paths inside the run folder. Primitives never import or call each other; only the runner sequences them.
2. **`--dry-run` on anything irreversible.** Dry run does everything except the irreversible part and writes what *would* have happened to `runs/<id>/dryrun/`. (The flag exists on the primitive; whether a flow ever exercises it via `test.dryrun` is the flow's choice.)
3. **Ledger check on anything irreversible — the one non-removable behavior.** Send-class primitives claim the recipient in the ledger before acting (§6). This lives inside the primitive and in a database constraint precisely so that no generated flow, however minimal, can skip it.
4. **Concurrency built in.** Every network primitive takes `--concurrency N` and defaults to parallel. No internal throttles, no daily caps. Transient provider errors retry with exponential backoff (wait, retry, wait longer — so a blip doesn't kill an hours-long run); nothing slows down proactively.
5. **Structured events** to the run's `events.jsonl` via `core/events.py`.
6. **Auth via `core/auth.py` only** (§7). No env files, no secrets in argv, nothing echoed or logged.
7. **`TOOL.md` per primitive**: purpose, subcommands, file schemas, connection needed, dry-run behavior, failure modes. The agent composes flows by reading `TOOL.md`s, never `tool.py`.
8. **An offline smoke test per primitive**, runnable by `test.smoke` when a flow includes it.

New-primitive bar: writing one requires a sentence of justification in the calling skill's `SKILL.md` ("no existing primitive can X"). This keeps the toolbox small and reuse high.

---

## 6. Flows, skills, and forking (`skills/`)

A flow is data, not code:

```yaml
# skills/apollo-cold-email/flow.yaml
steps:
  - clarify.ask:    {form: inputs.yaml}
  - domains.source: {query: "{{segment}}", count: "{{target_count}}", out: domains.csv}
  - apollo.enrich:  {in: domains.csv, roles: "{{contact_roles}}", out: contacts.csv, concurrency: 20}
  - verify.check:   {in: contacts.csv, out: verified.csv, concurrency: 20}
  - compose.render: {in: verified.csv, template: "{{template}}", out: outbox.csv}
  - test.dryrun:    {of: gmail.send, sample: 10, checks: "SKILL.md#acceptance-checks"}
  - canary.run:     {of: gmail.send, count: 10, seeds: ["<our inboxes>"]}
  - gmail.send:     {in: outbox.csv, from: "{{from_account}}", concurrency: 8}
  - report.write:   {}
```

`core/runner.py` executes the list top to bottom: resolve `{{inputs}}`, invoke each primitive, pause where a step pauses (clarify, canary), resume from artifacts + ledger after any interruption. For genuinely custom logic a step may be `python: steps/transform.py` — a tiny adjacent script — but if one grows past trivial, that's the signal to promote it into a primitive.

A skill folder:

```
skills/apollo-cold-email/
  SKILL.md      # canonical: purpose, inputs, the step list explained, acceptance checks, changelog
  flow.yaml     # the executable composition above
  inputs.yaml   # parameters with defaults — the one-pass clarification form
skills/INDEX.md # registry: one line per skill (name · purpose · primitives used · last run)
skills/PROTOCOL.md  # this section + §5, written for agents
```

### Default chains (defaults, not law)

When composing, the agent proposes a step list based on what's being made — and strips any step the human waves off ("no questions, no canary, just send it"):

- **New skill, irreversible actions:** full chain — `plan.write → clarify.ask → test.smoke → test.dryrun → canary.run → <work steps> → report.write`.
- **Rerun of a proven skill:** `<work steps> → report.write`. No interview, no canary — it already earned trust.
- **Fork:** `test.dryrun → <work steps> → report.write` — one cheap sanity pass on the changed parts, nothing else.
- **One-off, "just run it":** `<work steps>` alone, unregistered, living only in `runs/`.

### Forking — the default reflex

The bar for forking is deliberately on the floor. "Same outreach, but yoga studios, and skip the canary":

1. `cp -r skills/apollo-cold-email skills/apollo-cold-email-yoga`
2. Edit `inputs.yaml` defaults (segment, template angle).
3. Delete the `canary.run` line from `flow.yaml`.
4. Run.

Seconds, not minutes; zero new code. `SKILL.md` gets a one-line "forked from X, differs by Y" note so the registry stays honest. Pure-parameter variations shouldn't even fork — rerun the original with different inputs.

---

## 7. The ledger (Supabase)

The scenario this must make impossible: person A's automation B emails person C on Monday; person X's unrelated automation Y, built independently, tries to email C on Wednesday. Y must skip C — automatically, with no coordination between A and X.

That guarantee cannot live in flows (flows are minimal and editable) or in per-machine files (A and X are on different laptops). It lives in one shared database with a uniqueness rule:

```sql
contacted (
  channel      text,        -- 'email' | 'discord' | 'linkedin' | …
  recipient    text,        -- canonicalized: lowercased, trimmed
  status       text,        -- 'claimed' | 'sent' | 'failed'
  sent_by      uuid,        -- which person's auth performed it
  skill        text,
  run_id       text,
  message_hash text,
  created_at   timestamptz,
  UNIQUE (channel, recipient)   -- the invariant, enforced by the database itself
)

suppression (channel, recipient, reason, created_at)   -- bounces and opt-outs; permanent
```

A *unique constraint* means the database physically refuses a second row for the same `(channel, recipient)` — so the rule holds even against buggy generated code or two runs firing at the same instant.

**The claim pattern** (inside every send-class primitive, via `core/ledger.py`):

1. `INSERT … status='claimed' ON CONFLICT DO NOTHING`. Zero rows inserted → someone, somewhere, already has this recipient → skip, log, move on.
2. Send.
3. Success → update the row to `sent` (+ `message_hash`). Permanent failure (dead address) → `failed`, and the row stays so nobody wastes a send on it again.
4. Crashed runs leave `claimed` rows; the runner releases claims older than an hour on startup, so a crash never permanently blocks a recipient.

Per-run resume still uses a local `runs/<id>/ledger.jsonl` mirror — but Supabase is the only source of truth for "have we ever contacted this person."

**Override exists, default off.** `allow_recontact: false` in every `inputs.yaml`; setting it true (deliberate follow-up sequences) is logged loudly and recorded in the row. Suppressed recipients have no override.

---

## 8. Auth: per-person OAuth on Supabase

`credentials/.env` is deleted. The model from the founding notes — *everyone has their own account, and that one account connects every piece of context* — implemented:

1. **Sign in once.** Each person authenticates to the Supabase project with Google OAuth. Agents act *as a person*: `toolbox auth login` opens the browser, completes OAuth, and stores the session token in the OS keychain — never in the repo.
2. **Connect integrations from there.** A `connections` table holds each person's provider credentials — Gmail OAuth refresh tokens, Apollo key, StoreLeads key, later Slack/GitHub/Discord — written via a small connect flow, encrypted at rest. *Row-level security* (RLS — database rules that filter rows by who's asking) ensures a person's session can only read their own connections; org-shared keys (e.g., a team Apollo account) are org-scoped rows visible to all members.
3. **Primitives fetch tokens at runtime.** `core/auth.py → get_token("gmail")` exchanges the person's session for a fresh provider token. Refresh happens in a Supabase *edge function* (a small server-side function) so provider client-secrets never reach laptops at all.
4. **Attribution falls out for free.** Every ledger row's `sent_by` is the authenticated person — which is also what makes the §7 cross-person guarantee meaningful.

Migration: delete `credentials/`, rotate every secret that ever lived in git history (deleting the file doesn't un-leak it from history), update `/CLAUDE.md` and the charters to point at `toolbox auth login`.

---

## 9. Speed posture

Empirical reality, stated by the team: months of multi-thousand-per-day sending from the existing account with zero repercussions. The harness is built for that reality:

- **No daily caps, no warmup schedules, no throttles, no circuit breakers — anywhere, in any default.** The 25/day guardrail in `agents/outreach/AGENT.md` is wrong and gets deleted in M1; `contacted.md` is replaced by the §7 ledger.
- **Parallel by default.** Enrichment, verification, and composition fan out with `--concurrency`; sends batch as fast as the API accepts them. Target: a 1,000-contact flow completes the same day it's requested, end to end.
- **The only provider-facing behavior is reactive:** a refused or transient-erroring request retries with backoff rather than crashing. This is a speed feature — it keeps long runs alive — not pacing.
- A `throttle` primitive exists in the toolbox for the rare flow that *wants* pacing. It appears in no default chain.

---

## 10. Worked example

> "Fetch 1,000 domain names related to X, find their emails on Apollo, fill out a template and send those emails."

**Build (new skill, default chain):** the agent finds no `INDEX.md` match, drafts `SKILL.md` and the `flow.yaml` shown in §6, and presents one clarification form — every field pre-filled, including a template it drafted itself; the human edits two values and says go. Smoke tests pass; dry run renders 10 messages, the agent catches two empty `{{personalization_hook}}`s against the acceptance checks, fixes the compose fallback, reruns green. Canary sends 10 (two to our own inboxes), human approves. Full send fans out at `concurrency: 8` — 1,000 sends complete within the day. `report.write` registers the skill.

**The same afternoon, a teammate:** "do that for yoga studios — and skip the questions and canary, I trust it." Fork: copy folder, edit `inputs.yaml` segment + template angle, delete the `clarify.ask` and `canary.run` lines. Under a minute of human time, zero new code. The ledger silently skips the 14 yoga-adjacent contacts the first run already touched — neither person had to know about the other's run.

---

## 11. Milestones

**M0 — Supabase backbone.** Project setup; auth with Google OAuth; `connections`, `contacted`, `suppression` tables with RLS + the unique constraint; token-refresh edge function; `toolbox auth login`; `core/auth.py`, `core/ledger.py`.
*Done when:* two different people's sessions can each fetch a Gmail token for their own account and a claim-insert race (two simultaneous claims on one recipient) admits exactly one winner.

**M1 — Toolbox + runner + protocol.** Port the §2 keep-list into primitives; write the new ones (`apollo`, `storeleads`); implement `core/runner.py` and the process primitives; write `TOOLBOX.md`, `skills/PROTOCOL.md`, `INDEX.md`; update `/CLAUDE.md` and `agents/outreach/AGENT.md` (route automation requests through the protocol; delete the volume guardrails and `contacted.md`).
*Done when:* all smoke tests pass offline, and a fresh Claude Code session scaffolds a toy skill as a `flow.yaml` composition unprompted.

**M2 — First skill end to end.** `apollo-cold-email` (§10) on a real segment.
*Done when:* ≤1 clarification round; 1,000-contact flow completes same-day; **kill the run mid-send, rerun, zero duplicates**; **two overlapping runs by two people produce zero duplicates** (the §7 scenario, tested live); skill registered with report.

**M3 — Fork proof (hours).** New segment, steps removed on request.
*Done when:* fork ships in under a minute of human time with zero toolbox edits, and the removed steps demonstrably didn't run.

**M4 — Brain-breadth proof + cleanup (2–3 days).** A *non-outreach* agent composes the same harness — e.g., the researcher's watchlist sweep as a flow (`fetch sources → llm filter → file inbox tasks`) — proving this is brain infrastructure, not an outreach feature. Delete `credentials/`, rotate everything in git history, finish reply-detection (`gmail` primitive's read side) feeding positive replies into `inbox/queue/` per the charter.

---

## 12. Open questions

1. **Recipient identity across channels.** The ledger keys on `(channel, recipient)`. Is `ceo@x.com` emailed and `@ceo_x` DM'd on Discord the same person? v1 says channels are independent; cross-channel identity resolution is a later brain capability.
2. **Recontact policy shape.** Default is *never twice, ever*. When deliberate follow-up sequences arrive, do they ride `allow_recontact: true`, or does the ledger grow a `sequence_step` concept? Decide when sequences are actually built.
3. **Supabase hosting.** Hosted project vs. self-hosted; and which org-level provider secrets live only in edge functions. Hosted is the fast default.
4. **gogcli.** The charter names it for email today; the Supabase token model wants the Gmail API client directly. Proposal: the `gmail` primitive is the API client, gogcli retires from agent use.
5. **Runner ergonomics.** Pure-YAML steps plus a `python:` escape hatch is the proposal; if escape-hatch scripts proliferate, that's evidence some primitive is missing — revisit then.
