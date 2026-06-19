# campaign

**Purpose:** end-to-end cold outreach pipeline. Describe your ICP, find
decision-maker contacts via Hunter, compose personalised emails, send them,
track replies in Supabase, and sync reply counts to a shared Notion dashboard.
Supports A/B experiment mode and Clay/Origami CSV imports.

## Setup (one time per machine)

### 1. Gmail via gog

Install gog from https://gogcli.sh, then:

```bash
gog auth credentials ~/client_secret.json       # import your Google OAuth client
gog auth add you@gmail.com --services gmail    # authorise Gmail access
```

gog stores credentials in its keyring. The campaign skill calls
`gog auth tokens export` at runtime to get a fresh access token — no Gmail
keys ever go in `.env`.

### 2. credentials/.env

Copy `credentials/.env.example` to `credentials/.env` and fill in:

```
TOOLBOX_TOKEN_HUNTER=<your hunter.io API key>   # get from hunter.io dashboard

# Optional: use Apollo instead of Hunter to find and verify emails.
# Set this key, then pass apollo as the provider (see Providers and /campaign).
TOOLBOX_TOKEN_APOLLO=<your apollo.io API key>   # apollo.io > Settings > API

# shared — get from a teammate out-of-band
SUPABASE_URL=https://lvzvmqeynkwywodcqxkv.supabase.co
SUPABASE_ANON_KEY=<shared anon key>
NOTION_TOKEN=<shared integration token>
```

You only need the key for the provider you use: Hunter by default, Apollo if
you pass `apollo`. No `GMAIL_*` keys needed.

### 3. Supabase login (one time)

```bash
toolbox auth login
```

### 4. Install the daily reply scan cron

```bash
skills/campaign/cron.sh --install
```

Runs at 23:00 daily — scans all logs in `~/.blackwell/campaigns/` and syncs
reply counts to Notion. Cron output logs to `runs/cron-campaign.log`.

## Fastest path: the /campaign command

To send N emails across the full ICP mix with no questions asked, type:

```
/campaign 1000
```

That runs `skills/campaign/send.sh`, which distributes N across the segments in
`icp_mix.toml` (each with its own template), CCs the cofounders who are not the
sender (see `FOUNDERS.md`), and sends. Default sender is Samarjit; pass a sender
key to switch: `/campaign 1000 armaan`. The email provider defaults to Hunter;
add `apollo` to find and verify contacts through Apollo instead
(`/campaign 1000 armaan apollo`, or `/campaign 1000 apollo` to keep the default
sender). Apollo reads `TOOLBOX_TOKEN_APOLLO` from `credentials/.env`. The script
loads `credentials/.env` for you. You must be signed in first
(`toolbox auth login`); `run.py` preflight will say so if not.

Run the script directly with the same effect:

```bash
bash skills/campaign/send.sh 1000              # 1000 emails, Samarjit, Hunter, per icp_mix.toml
bash skills/campaign/send.sh 1000 ethan        # same, sent from Ethan
bash skills/campaign/send.sh 1000 ethan apollo # same, but find + verify via Apollo
```

## Quick start (single ICP or custom)

```bash
# Dry run first — see who would receive it
python3 skills/campaign/run.py \
  --icp "DTC home fitness brands" \
  --provider hunter \
  --from you@gmail.com \
  --from-name "Your Name" \
  --limit 5 \
  --dry-run

# Send for real
python3 skills/campaign/run.py \
  --icp "DTC home fitness brands" \
  --provider hunter \
  --from you@gmail.com \
  --from-name "Your Name" \
  --limit 5

# Scan for replies manually
python3 skills/campaign/reply_scan.py \
  --log ~/.blackwell/campaigns/campaign_<id>.jsonl

# See reply rates
python3 skills/campaign/reply_report.py \
  --log ~/.blackwell/campaigns/campaign_<id>.jsonl
```

## How it works

```
run.py
  1. Generate target domains from ICP description via Claude
  2. Enrich domains via Hunter or Apollo to find decision-maker contacts
     OR load a pre-exported Clay/Origami CSV with --leads
  3. Render template_a.md into per-contact emails
     (--experiment: Claude writes variant B; leads split 50/50)
  4. Check Supabase ledger — skip anyone already contacted
  5. Send via Gmail REST API using gog access token (5 concurrent)
  6. Write campaign row to Supabase `campaigns` table
  7. Create row in Notion Campaign Metrics database
  8. Write campaign log to ~/.blackwell/campaigns/campaign_<id>.jsonl

reply_scan.py
  1. Read campaign log — maps {email → run_id, variant}
  2. Get Gmail token from gog (one call)
  3. Search inbox with from:(contact1 OR contact2 ...) in batches of 50
     — Gmail filters server-side, no full inbox scan
  4. Classify reply sentiment via LLM (skip with --no-classify)
  5. Upsert to Supabase `replies` (UNIQUE on recipient + message_id)
  6. Query Supabase for cumulative reply count, update Notion row
```

## Files

| File | Purpose |
|------|---------|
| `run.py` | Main orchestrator |
| `reply_scan.py` | Gmail scanner, Supabase writer, Notion sync |
| `reply_report.py` | Reply rate table from Supabase |
| `gog_auth.py` | Gets Gmail access token from gog keyring |
| `notion_sync.py` | Creates/updates Notion Campaign Metrics rows |
| `cron.sh` | Daily reply scan cron |
| `send.sh` | Non-interactive entrypoint behind `/campaign N` — mix send, auto sender + CC |
| `template_a.md` | Default email template — frontmatter `subject:` + body with `{{slots}}` |
| `FOUNDERS.md` | Cofounder roster and the per-sender `--cc` convention |

Campaign logs live at `~/.blackwell/campaigns/campaign_<id>.jsonl` — one per
run, written by `run.py`, read by `reply_scan.py` and `reply_report.py`.

## Notion Campaign Metrics

Shared database all teammates write to:
https://app.notion.com/p/00b1d4354b7f475faeca57a13d426204

Columns: Campaign, Sender, Date, Provider, Template, ICP, Experiment, Sent,
Replied, Reply Rate (formula). Updated automatically on each run and scan.

## Providers

| Provider | Flag | Notes |
|----------|------|-------|
| Hunter | `--provider hunter` | Default. Requires `TOOLBOX_TOKEN_HUNTER` |
| Apollo | `--provider apollo` | Alternative email finder + verifier. Requires `TOOLBOX_TOKEN_APOLLO` (paid Apollo plan) |
| Clay | `--provider clay --leads export.csv` | Export from Clay UI first |
| Origami | `--provider origami --leads export.csv` | Same as Clay |

Hunter and Apollo both find the decision-maker email per domain and return a
verification status. `--min-score` (default 80) gates on it. For Apollo that
keeps only emails marked `verified` (score 95) and drops `likely` (70) and
`guessed` (40); for Hunter it keeps emails at or above 80 confidence. So passing
`apollo` gives you Apollo-verified-only sends without any extra flags.

## A/B experiments

`--experiment` splits leads 50/50. Claude generates a variant B with a
different angle or structure. Reply rates per variant are tracked in
Supabase `replies.variant` and visible in `reply_report.py`.

## Scaling and where the time goes

The send itself is fast and was never the bottleneck: Gmail sends run
concurrently (`--concurrency`, default 8, the `send.sh` path uses 12), so a
batch of contacts goes out in seconds. Inbox scan uses batched `from:` queries
(50 per query) so Gmail filters server-side regardless of inbox size.
Daily limit: 500 sends/day on free Gmail, 2000/day on Google Workspace.

The real cost is sourcing, in two parts:

- Domain generation (`claude -p`) is the single slowest step, ~15 to 30s per
  call, and it is a serialized resource. Measured: two concurrent `claude -p`
  calls took 35s versus 13s for one, because the Claude subscription throttles
  concurrent inference. So domain generation runs one call at a time
  (`_LLM_CONCURRENCY = 1`). Do not try to parallelize it; it gets slower.
- Hunter enrichment is real parallel HTTP and is genuinely concurrent, capped
  globally by `--concurrency` so several segments share one rate budget.

How the mix mode stays fast despite serial LLM calls: all segments run as one
job and overlap. While one segment's domains are being enriched over the network,
the next segment's `claude -p` call runs. So wall-clock is roughly the larger of
(total enrichment time) and (total LLM time), not their sum. Running six separate
`run.py` invocations instead, as an early version did, pays the preflight, auth,
and process-startup cost six times and serializes everything; that is what made
the first 60-email send take 10 to 15 minutes. Use `/campaign N` (one job) for
multi-ICP sends.

Hard ceiling for large N: Hunter credits and domain uniqueness. The LLM starts
repeating well-known brands past a few hundred domains per ICP, and every
enriched domain spends a Hunter credit. For N in the thousands, expect Hunter
credits, not send speed, to be the limit.

## Running tests

```bash
TOOLBOX_TOKEN_HUNTER=fake TOOLBOX_TOKEN_APOLLO=fake TOOLBOX_SESSION_TOKEN=fake \
  toolbox/.venv/bin/pytest skills/campaign/tests/ -v
```

All tests run without real API keys (HTTP calls mocked with respx).

## Changelog

- 2026-06-18: live visibility files. Generated domains stream to
  `enriched/domains_<id>.csv` (with timestamp + segment) as each `claude -p`
  call returns, and verified contacts stream to `enriched/enriched_<id>.csv` as
  they are enriched. Both also print to the terminal. Added `HOW_IT_WORKS.md`, a
  plain-language guide to the whole pipeline and the two known bugs.
- 2026-06-18: fixed Apollo enrichment after Apollo deprecated `mixed_people/search`
  (HTTP 422). `_apollo_domain` now uses `mixed_people/api_search` with the
  `q_organization_domains_list` filter (the old `organization_domains` is ignored
  and returns random people), then `people/match` to reveal + verify the email,
  keeping only on-domain results. Added a ledger token force-refresh + retry on
  401 so long runs survive a mid-run session expiry (unconfirmed root cause;
  logging added under `ledger.unauthorized`).
- 2026-06-18: created. gog auth, Hunter/Apollo enrichment, Notion sync,
  A/B experiments, daily cron, concurrent send via Gmail REST API.
- 2026-06-18: Apollo selectable as the email find + verification provider from
  the `/campaign` fast path (`send.sh <N> [sender] apollo`), not just
  `run.py --provider apollo`. Documented the `TOOLBOX_TOKEN_APOLLO` key in the
  setup section and `.env.example`.
- 2026-06-18: added `--cc` (cofounder CC convention), `--concurrency`, and the
  `/campaign N` command (`send.sh`) for non-interactive mix sends. Parallelized
  mix sourcing (segments concurrent, enrichment overlaps serial LLM domain
  generation) after measuring that concurrent `claude -p` throttles. Fixed
  `gog_auth` to read the client secret from `credentials.json` (the keychain
  copy was stale and caused `invalid_client`).
