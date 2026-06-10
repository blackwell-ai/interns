# Decision: Clay is the lead workbench — Apollo and StoreLeads dropped entirely

**Date:** 2026-06-10 · **Source:** internal decision (Armaan, in session).

## What was decided

Lead sourcing and enrichment run through **Clay** (clay.com), full stop.
**Apollo and StoreLeads are not used at all** — not standalone, not as Clay
data providers. Remove them from charters, credentials, and the harness.

## Why

One workbench instead of three parallel tools: Clay covers sourcing,
multi-provider enrichment, and waterfall email lookups on its own, and the
team connected it via the claude.ai connector today.

## Implications

- `agents/outreach/AGENT.md` rewritten: Clay is the sole sourcing + enrichment
  layer in the operating loop.
- `brain/company/targets.md` lead-sources section updated (Apollo/StoreLeads
  removed).
- `credentials/.env`: `APOLLO_API_KEY` / `STORELEADS_API_KEY` slots removed
  (they were empty placeholders).
- **Harness impact (open):** the automation harness built earlier today
  (decision `2026-06-10-automation-harness-built.md`) has standalone
  `apollo`/`storeleads` primitives and an `apollo-cold-email` canonical skill.
  Per this decision they should be removed/reworked — see the task in
  `inbox/queue/`. Constraint to design around: Clay's claude.ai MCP connector
  is NOT available in headless/cron harness runs; a harness-side `clay`
  primitive needs Clay's HTTP API (API key) or Clay-exported CSVs as flow
  inputs.
