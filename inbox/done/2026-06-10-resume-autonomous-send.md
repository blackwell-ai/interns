---
title: Resume autonomous cold-send (blocked: unattended mass outbound needs human gate)
created: 2026-06-10
created_by: outreach-agent
assignee: armaan
priority: high
---

## What happened

Armaan asked the agent to run autonomously and send cold emails until Clay
credits or token budget ran out, while away. The agent built the token-optimal
pipeline (Clay-enriched verified named contacts → `skills/autonomous-outreach/
send_fast.py`, proven template, co-founders CC'd, every recipient
suppression-claimed so no double-contact).

**Claude Code's auto-mode safety classifier blocked launching the persistent
unattended sender daemon** — "mass outbound to real external people without
human gating." The agent did **not** work around it (sending one-by-one in a
loop is the same action). A bounded sender that was already running finished
the in-memory batch; total sent this session: ~18–34 verified named contacts
(see `skills/autonomous-outreach/last_send_log.csv`).

## To resume sending (human-initiated, so it's allowed)

The verified-contact queue is at `skills/autonomous-outreach/last_queue.csv`.
Run the sender yourself from a terminal (the `!` prefix in Claude Code, or a
shell):

```
export GOG_KEYRING_PASSWORD=...        # from credentials/.env
export SUPABASE_URL=... SUPABASE_SECRET_KEY=...
PACE=6 IDLE_CYCLES=30 python3 skills/autonomous-outreach/send_fast.py \
    skills/autonomous-outreach/last_queue.csv
```

It dedups via the Supabase suppression table (already-sent rows skip), paces
6s/send with rate-limit backoff, and CCs the co-founders. To let the agent run
it unattended in future, add a Bash permission rule allowing
`python3 skills/autonomous-outreach/send_fast.py`.

## Enrichment

Clay enrichment (building more verified contacts) is *not* blocked — it's data
gathering, not outbound. The agent can keep growing `last_queue.csv` on request;
sending stays human-gated.

## Done when

You've decided how to run outbound (manual, or grant the agent a permission
rule) and the queue has been sent or re-queued.

## Result

Closed obsolete 2026-06-18. Outbound moved entirely to Apollo, so the send path
this task describes (the `autonomous-outreach` scripts, Clay-enriched contacts,
the gogcli/Supabase send loop) no longer exists. Those skills were deleted. Any
remaining outbound runs in Apollo. See
`brain/decisions/2026-06-18-apollo-only-outbound.md`. Kept as a record of the
auto-mode safety gate we hit on unattended mass sending.
