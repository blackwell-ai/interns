# Decision: the automation harness is built and is how automations run

**Date:** 2026-06-10 · **Source:** internal decision (spec v0.2 + build plan, both in
`harness/outreach_automation_docs/`), implemented same day.

## What was decided

1. Repeatable automations are **flows**: declarative step lists
   (`skills/<name>/flow.yaml`) executed by `toolbox/` — the only maintained
   code. Process steps (clarify, smoke, dryrun, canary) are removable lines;
   the ledger check is not removable (it lives in the send primitives + a
   Postgres UNIQUE constraint).
2. **No volume caps, no warmup, no throttles** in any default (spec §9). The
   outreach charter's 25/day guardrail was deleted. The only provider-facing
   behavior is reactive: transient errors back off; hard quota errors fail the
   step cleanly for a later resume.
3. **Per-person auth on Supabase** replaces `credentials/.env` for harness
   flows (`toolbox auth login` / `connect`). Sign-in and Gmail-send are two
   separate OAuth consents; provider client-secrets live only in edge
   functions. `.env` survives transitionally for gogcli until the M4 rotation.
4. **The no-double-contact invariant is database-enforced**:
   `UNIQUE (channel, recipient)` + SECURITY DEFINER claim RPC. Proven by
   integration tests: 20-way claim race → exactly one winner; two people,
   overlapping lists, concurrent runs → zero duplicates; crash mid-send →
   resume → zero duplicates.

## Why (deviations from the spec worth remembering)

- The spec's "release claims older than 1h" was replaced with a
  heartbeat-based reaper (`runs` table): a *paused* run (canary gate) keeps
  its claims for hours legitimately; only dead/failed runs release them.
- Resume trusts the runner's `step.completed` events plus the per-run
  `ledger.jsonl` mirror (appended the instant the provider returns a message
  id) — artifact existence alone is never trusted.
- gogcli is NOT retired yet: the Dartmouth send account must first be
  connected through `oauth-connect` and proven on a live segment (M2), per
  `brain/company/connections.md`.

## Status at decision time

Built and tested offline + against a local Supabase stack (52 tests green).
Human-gated remainder: hosted Supabase project + Google OAuth app secrets,
`ANTHROPIC_API_KEY` (the `credentials/.env` slot is empty), first live send,
then credential rotation + `credentials/` deletion (M4).
