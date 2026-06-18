# campaign

**Purpose:** end-to-end cold outreach pipeline. Describe your ICP, find
decision-maker contacts via Hunter, compose personalised emails, send them,
track replies in Supabase, and sync reply counts to a shared Notion dashboard.
Supports A/B experiment mode and Clay/Origami CSV imports.

## Setup (one time per machine)

### 1. Gmail via gog

Install gog from https://gogcli.sh, then:

```bash
gog auth credentials ~/client_secret.json   # import your Google OAuth client
gog auth login you@gmail.com                # authorise Gmail access
```

gog stores credentials in its keyring. The campaign skill calls
`gog auth tokens export` at runtime to get a fresh access token — no Gmail
keys ever go in `.env`.

### 2. credentials/.env

Copy `credentials/.env.example` to `credentials/.env` and fill in:

```
TOOLBOX_TOKEN_HUNTER=<your hunter.io API key>   # get from hunter.io dashboard

# shared — get from a teammate out-of-band
SUPABASE_URL=https://lvzvmqeynkwywodcqxkv.supabase.co
SUPABASE_ANON_KEY=<shared anon key>
NOTION_TOKEN=<shared integration token>
```

No `GMAIL_*` keys needed.

### 3. Supabase login (one time)

```bash
toolbox auth login
```

### 4. Install the daily reply scan cron (optional)

```bash
skills/campaign/cron.sh --install
```

Runs at 23:00 daily — scans all logs in `~/.blackwell/campaigns/` and syncs
reply counts to Notion. Cron output logs to `runs/cron-campaign.log`.

## Quick start

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
| `template_a.md` | Default email template — frontmatter `subject:` + body with `{{slots}}` |

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
| Hunter | `--provider hunter` | Requires `TOOLBOX_TOKEN_HUNTER` |
| Apollo | `--provider apollo` | Requires paid Apollo plan |
| Clay | `--provider clay --leads export.csv` | Export from Clay UI first |
| Origami | `--provider origami --leads export.csv` | Same as Clay |

## A/B experiments

`--experiment` splits leads 50/50. Claude generates a variant B with a
different angle or structure. Reply rates per variant are tracked in
Supabase `replies.variant` and visible in `reply_report.py`.

## Scaling

Sends: 5 concurrent Gmail API calls — ~200 emails in ~40 seconds.
Inbox scan: batched `from:` queries (50 per query) so Gmail filters
server-side regardless of inbox size.
Daily limit: 500 sends/day on free Gmail, 2000/day on Google Workspace.

## Running tests

```bash
TOOLBOX_TOKEN_HUNTER=fake TOOLBOX_TOKEN_APOLLO=fake TOOLBOX_SESSION_TOKEN=fake \
  toolbox/.venv/bin/pytest skills/campaign/tests/ -v
```

All tests run without real API keys (HTTP calls mocked with respx).

## Changelog

- 2026-06-18: created. gog auth, Hunter/Apollo enrichment, Notion sync,
  A/B experiments, daily cron, concurrent send via Gmail REST API.
