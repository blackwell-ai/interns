# Retro: the headless cold-email run (where 90 minutes actually went)

**Run:** 2026-06-10 evening. Goal: send 100+ cold emails from
`samarjit.deshmukh.29@dartmouth.edu`, sourcing the leads myself, headlessly.
**Outcome:** 166 verified DTC founders/decision-makers emailed, 0 failures, 0
double-contacts.

## Time breakdown (~90 min)

| Bucket | ~Time | Recurring? |
|---|---|---|
| **One-time discovery** — proving Clay can't be driven headlessly; reading Clay's API docs; testing that nested `claude -p` web-search is permission-blocked; confirming the main agent *can* web-search | ~25 min | **No** — answered forever |
| **One-time build** — writing + testing the `findemail` primitive (find / find-exec, two providers, smoke tests) | ~20 min | **No** — committed |
| **A detour I should have skipped** — building an "inferred `firstname@domain`" queue before realizing verified emails were both necessary and cheap via Hunter | ~10 min | **No** |
| **Tuning** — find-exec at concurrency 12 rate-limited (35% yield); diagnosing; re-running at concurrency 5 (80% yield) | ~10 min | **No** — default now baked in |
| **The misread** — killed a healthy send because Gmail *search* index lagged and made sends look failed; diagnosed via the ledger; relaunched | ~15 min | **No** — lesson encoded |
| **The actual recurring work** — harvest domains, filter the enriched list, add HTML, launch, monitor | ~10 min | **Yes** → now ~3 min via `campaign.sh` |

**The punchline:** ~70 of the 90 minutes was one-time work that never repeats.
The genuinely recurring part is ~10 minutes and is now ~3 via a wrapper. The
next run is a single command (file 04).

## What was actually produced (and is now reusable)

- `toolbox/src/toolbox/primitives/findemail/` — the headless enrichment
  primitive (domain → verified decision-maker email). Committed, tested.
- `credentials/.env` — Hunter + Supabase keys (gitignored, persist across runs).
  gog/Dartmouth accounts already authed. **Zero key setup next time.**
- `skills/autonomous-outreach/send_fast.py` — now HTML + any-account
  (`SEND_ACCOUNT`).
- `skills/autonomous-outreach/lead_bank.csv` — the 224-domain universe I
  harvested, checked in so sourcing isn't from scratch next time.
- These learnings + the `campaign.sh` wrapper.

## What I'd do differently

1. **Don't kill a run on a Gmail-search reading.** Watch the ledger count
   (`suppression`) — it's written synchronously per send; Gmail search lags
   minutes. (File 03.)
2. **Start enrichment at low concurrency** for rate-limited APIs. The "parallel
   by default" harness instinct backfired on Hunter. (File 03.)
3. **Go straight to the verification API.** Verified emails cost ~362 Hunter
   credits out of 2000 — trivial. The inferred-email detour was wasted effort.
   (File 02.)
