# Harness learnings

Durable lessons pulled out of real automation runs, so the next run is faster
and the next agent doesn't relearn them. One file per theme. Newest themes
linked first.

- [01 — Retro: the headless cold-email run (where 90 minutes actually went)](01-retro-headless-cold-email.md)
- [02 — Lead enrichment: Clay isn't headless; Hunter is](02-enrichment-clay-vs-hunter.md)
- [03 — Operational: the ledger is truth, restart-safety, and rate limits](03-operational-ledger-restart-rate-limits.md)
- [04 — Make it 5 minutes: the reusable cold-email path](04-make-it-5-minutes.md)
- [05 — Hunter credit efficiency: why 362 for 169, and the fix](05-hunter-credit-efficiency.md)

## The one-paragraph version

The first headless cold-email campaign (166 verified DTC founders emailed from
the Dartmouth account) took ~90 minutes. Almost none of that was the actual
work — it was one-time discovery (Clay can't be driven headlessly → built the
`findemail` primitive), one tuning lesson (Hunter rate-limits at high
concurrency), and one self-inflicted detour (killed a healthy run because Gmail
*search* lags). All of that is now done, committed, and encoded. The recurring
work — source domains → enrich → send — is a single command
(`skills/autonomous-outreach/campaign.sh`) and ~3–5 minutes of human time. See
file 04 for the exact recipe.
