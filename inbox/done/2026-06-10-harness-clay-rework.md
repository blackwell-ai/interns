---
title: Build the Clay-fed cold-email skill (replaces removed apollo-cold-email)
created: 2026-06-10
created_by: claude (on Armaan's decision)
assignee:            # harness owner
priority: high
claimed_by: claude (session agent)
claimed_at: 2026-06-10
---

## Task

Armaan decided (2026-06-10, see
`brain/decisions/2026-06-10-clay-is-the-lead-workbench.md`): **Apollo and
StoreLeads are dropped entirely** — Clay (clay.com) is the only lead
sourcing/enrichment tool.

Already done (same day, in-session): `apollo`/`storeleads` primitives and
`skills/apollo-cold-email/` deleted; TOOLBOX.md, INDEX.md, charters, and
core docstrings scrubbed; smoke tests still green.

Remaining work — build the canonical **Clay-fed cold-email skill**:

- Input: a Clay lead list. Two viable paths — a `clay` primitive against
  Clay's HTTP API (`CLAY_API_KEY` slot exists in `credentials/.env`; migrate
  to Supabase auth per spec §8), or a Clay CSV export passed as a flow input.
  Note: Clay's claude.ai MCP connector is NOT available in headless/cron
  runs, so the harness cannot rely on it.
- Keep the rest of the chain intact (verify → compose → gmail send/replies,
  ledger invariant untouched).
- Register it in `skills/INDEX.md` with a SKILL.md per PROTOCOL.md.

## Done when

A Clay lead list goes end-to-end (smoke + dryrun green) through verify →
compose → send, and the skill is registered as the canonical cold-email flow.

## Result

Done 2026-06-10 (claude, in session). Built `skills/clay-cold-email/` —
flow.yaml (full default chain: clarify → verify → compose → smoke → dryrun →
canary → gmail.send → report), inputs.yaml, template.md (the proven "Stanford
Student Question" email with a personalization-hook slot), SKILL.md with
acceptance checks. Registered in skills/INDEX.md; outreach charter points to
it as canonical. Input path chosen: **Clay CSV export** passed as `leads_csv`
(a `clay` primitive against Clay's HTTP API remains future work if exports
get tedious). Offline tests green (39); smoke + dryrun of a live run still
pending the Google OAuth secrets (`supabase secrets set`) and `toolbox auth
connect gmail` — the harness's last setup gate.
