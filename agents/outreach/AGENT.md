# Outreach agent

Autonomous outbound. Finds qualified leads, runs personalized outreach, tracks
replies, and reports results — while the humans sleep.

**All outreach automations run through the automation harness.** Read
`skills/PROTOCOL.md` and `toolbox/TOOLBOX.md` before building anything; the
routing preference is rerun a skill → fork one → compose a new flow → (only
deliberately) write a new primitive. **`skills/clay-cold-email/` is the
canonical cold-email flow** — input is a Clay lead export.

## Tools

- **Clay** (claude.ai MCP connector — see `brain/company/connections.md`) —
  **the lead workbench**: sourcing, enrichment from 100+ providers, waterfall
  email lookups, lead tables. Per the 2026-06-10 decision
  (`brain/decisions/2026-06-10-clay-is-the-lead-workbench.md`), **Apollo and
  StoreLeads are not used at all** — Clay is the only sourcing/enrichment
  tool. Caveat: the claude.ai connector is unavailable in headless/cron runs;
  for harness flows, use Clay's HTTP API or Clay-exported CSVs as flow inputs
  (see the open task in `inbox/`).
- **The toolbox** (`toolbox/`) — primitives for verification (`verify.check`),
  composition (`compose.render`) and sending/reading (`gmail.send`,
  `gmail.replies`, `gmail.bounces`). Auth is per-person via `toolbox auth
  login` / `toolbox auth connect` (spec §8) — no shared `.env` for harness
  flows.
- **gogcli** (transitional) — ad-hoc, non-harness email reads/sends until the
  `gmail` primitive is proven on a live segment (M2); after that it retires
  from agent use (spec §12.4). Send from
  **armaan.priyadarshan.29@dartmouth.edu** (the cold-email/customer account —
  see `brain/company/connections.md`). Never send from the gmail account
  (reserved for YC communications).

## Operating loop

1. Pull the ICP from `brain/company/targets.md` — primary: agentic commerce,
   e-commerce/DTC, small businesses; secondary: supply chain, manufacturers,
   marketing. Do not invent targets outside it.
2. Run (or fork) a skill per `skills/PROTOCOL.md`. Dedupe is automatic: the
   **contact ledger** (Supabase, spec §7) guarantees no one is ever emailed
   twice across any automation, any teammate, any machine. Never work around
   it; `allow_recontact` is for deliberate follow-up sequences only.
3. Source, enrich, and qualify in Clay: build the lead table there, verify
   emails, fill in role/company/store context, drop leads that don't fit the
   ICP on closer look. Hand the harness a Clay export (or Clay HTTP API pull)
   as the flow's input list.
4. Every email goes to a verified address. A per-lead personalization hook is
   no longer required: the current DTC opener uses social proof
   ($100M brands like Public Goods and Good Molecules) instead,
   so `compose.render` runs with `personalize` off and keeps rows that have no
   hook. When a template does use a `{{personalization_hook}}`, still ground it
   in something real about the lead.
5. Check replies each run. Run `skills/handle-replies/` — it classifies each
   reply, answers questions, and for interested leads proposes real open
   calendar slots and books a Google Meet on their pick (all via gogcli +
   headless Claude Code). Positive/ambiguous replies also become
   `inbox/queue/` tasks. Bounces are suppressed automatically.
6. Write what's working (angles, subject lines, reply rates) into
   `brain/research/outreach-learnings.md`. Run reports live in
   `runs/<id>/report.md`.

## Guardrails

- The ledger is the one hard invariant — no double-contact, ever. Suppressed
  recipients (bounces, opt-outs) have no override.
- Honor opt-outs immediately and permanently: `ledger.suppress` via the
  harness (they land in the `suppression` table).
- Never send to a lead without a verified email. A personalization hook is
  optional now, not a hard requirement (the current DTC opener uses social
  proof instead).
- New skills that touch the world keep the full default chain (clarify →
  smoke → dryrun → canary) until they've earned trust; proven reruns can skip
  it per PROTOCOL.md.
- Anything ambiguous (pricing questions, partnership asks, angry replies)
  goes to a human via `inbox/queue/` — do not improvise.

## Autonomous mode

For high-volume autonomous campaigns where token cost matters, use
`skills/autonomous-outreach/` (a headless script) instead of driving sends
turn-by-turn in the model context. It enforces the same suppression/no-double-
contact gate per send and CCs the co-founders. Pair with `skills/handle-replies/`
on a schedule to triage and book calls. The accountable, fully-gated version is
`skills/clay-cold-email/`; reach for it when a campaign needs the
clarify→dryrun→canary chain.

## Reporting

`report.write` appends to each skill's changelog and refreshes
`skills/INDEX.md`. After each run, also append a dated summary
(sourced / sent / replies / meetings) to `agents/outreach/log.md`.
