# Make it 5 minutes: the reusable cold-email path

The 90-minute first run produced everything needed to make the *next* run a
single command. Nothing below has to be rebuilt or rediscovered.

## What's already done (so it never costs time again)

| Asset | Where | Saves |
|---|---|---|
| Headless enrichment | `findemail` primitive (`find-exec`: domain → verified decision-maker) | the entire "find emails" problem |
| API keys | `credentials/.env` (Hunter + Supabase), gog authed | **all key/auth setup** |
| Proven defaults | concurrency 5, min-score 72, HTML template, CC co-founders, suppression dedup | tuning + template work |
| Lead universe | `skills/autonomous-outreach/lead_bank.csv` (224 DTC domains) | cold-start sourcing |
| One-command wrapper | `skills/autonomous-outreach/campaign.sh` | the orchestration |
| The lessons | `harness/learnings/` (don't kill on Gmail search; low concurrency; ledger=truth) | repeating the mistakes |

## The next run (≈3–5 min of human time)

```bash
# dry run first — enrich + build the queue, see the count, send nothing:
bash skills/autonomous-outreach/campaign.sh --from samarjit --dry

# looks good? send it:
bash skills/autonomous-outreach/campaign.sh --from samarjit
```

That's it. `campaign.sh` does: `find-exec` over the lead bank (Hunter, conc 5)
→ filter out invalid/generic/no-name (`prep_queue.py`) → send from the chosen
co-founder account (HTML, co-founders CC'd, paced, **suppression-deduped so
nobody is contacted twice**). Watch progress in the ledger, not Gmail search
(file 03). The send paces itself and self-stops at Gmail's daily cap; re-running
later resumes safely (already-sent rows skip).

Switch sender with `--from armaan|ethan|shamit`. Point at a different list with
`--domains path.csv` (any CSV with a `domain` column).

## The only recurring input: fresh leads

Dedup means re-running over the **same** bank sends to nobody new — every run
needs **un-contacted** domains. Two ways to keep the bank fed:

1. **Grow the bank.** When an agent harvests new DTC brands (a few `WebFetch`es
   over "fastest-growing DTC brands" listicles → `brand,domain` rows), append
   them to `lead_bank.csv`. It's checked in (domains are public; no PII), so the
   universe compounds over time and cold-start sourcing disappears.
2. **New segment on demand.** Ask the agent for a segment ("DTC pet brands");
   it harvests ~150 domains in ~2 minutes and passes them via `--domains`.

Either way the human cost is a single command plus, at most, naming a segment.

## Two follow-ups worth doing once (not blocking)

- **Reconcile the two ledgers** (`suppression` vs `contacted`) so a future
  harness-native `clay-cold-email`/`gmail.send` flow dedups against the same
  history — see file 03 §4. Until then, use `campaign.sh` (suppression path).
- **Reply/bounce loop:** a few days after a send, run
  `gmail.replies --file-inbox-tasks` and `gmail.bounces` to triage responses and
  auto-suppress bounces. Worth turning into a scheduled step.

## Honest scope of "5 minutes"

Human-attended time is ≈3–5 min: type the command, eyeball the dry-run count,
fire it. The **sends themselves** still pace out over ~20–30 min in the
background (deliverability protection) and the account's daily cap is the real
ceiling on volume — neither is human time, and both are features, not delays.
