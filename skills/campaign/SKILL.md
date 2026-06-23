# campaign

End-to-end cold outreach pipeline. Describe your ICP, find decision-maker
contacts via Hunter or Apollo, compose personalised emails, send them, track
replies in Supabase, and sync reply counts to a shared Notion dashboard.

---

## Quickstart

### Interactive wizard (one-off or custom sends)

```bash
python3 skills/campaign/wizard.py
```

Walks you through sender, ICP description, template, count, and provider.
Shows a preview email, sends a test to your inbox, then asks for confirmation
before the real send. Best path when you want to try a new ICP or template.

### Batch send across the full ICP mix

```
/campaign 1000
```

or

```bash
bash skills/campaign/send.sh 1000              # 1000 emails, Samarjit, Hunter
bash skills/campaign/send.sh 1000 ethan        # sent from Ethan
bash skills/campaign/send.sh 1000 ethan apollo # find + verify via Apollo
```

Distributes N across the segments in `icp_mix.toml`, each with its own
template, and CCs the cofounders who are not the sender (see `FOUNDERS.md`).
Default sender is Samarjit.

### Direct CLI (scripting / dry runs)

```bash
# Dry run — compose without sending
python3 skills/campaign/run.py \
  --icp "DTC home fitness brands" \
  --provider hunter \
  --from you@gmail.com \
  --from-name "Your Name" \
  --limit 5 \
  --dry-run

# Live send
python3 skills/campaign/run.py \
  --icp "DTC home fitness brands" \
  --provider hunter \
  --from you@gmail.com \
  --from-name "Your Name" \
  --limit 5
```

---

## Setup (one time per machine)

### 1. Gmail via gog

Install gog from https://gogcli.sh, then:

```bash
gog auth credentials ~/client_secret.json       # import your Google OAuth client
gog auth add you@gmail.com --services gmail    # authorise Gmail access
```

Re-auth before any run where the account has not been used recently:

```bash
gog auth add you@gmail.com --services gmail
```

Check `gog auth list` to see the last auth timestamp — if it looks old, re-auth.

### 2. credentials/.env

Copy `credentials/.env.example` to `credentials/.env` and fill in:

```
TOOLBOX_TOKEN_HUNTER=<your hunter.io API key>
TOOLBOX_TOKEN_APOLLO=<your apollo.io API key>   # only if using Apollo

# shared — get from a teammate out-of-band
SUPABASE_URL=https://lvzvmqeynkwywodcqxkv.supabase.co
SUPABASE_ANON_KEY=<shared anon key>
NOTION_TOKEN=<shared integration token>
```

You only need the key for the provider you use. No `GMAIL_*` keys needed.

### 3. Supabase login

```bash
toolbox auth login
```

### 4. Daily reply scan cron

```bash
skills/campaign/cron.sh --install
```

Runs at 23:00 daily — scans all logs in `~/.blackwell/campaigns/` and syncs
reply counts to Notion. Output goes to `runs/cron-campaign.log`.

---

## Templates

Templates live in `skills/campaign/templates/`. Each is a markdown file with
frontmatter `subject:` and a body that uses `{{slots}}` for personalisation.
Available slots: `{{first_name}}`, `{{company}}`, `{{from_name}}`,
`{{segment_phrase}}`.

HTML templates are auto-detected: if the body starts with `<`, the email is
sent as multipart HTML. Use `<p>` tags for paragraphs. Do not add extra
frontmatter fields — `parse_template` only reads `subject:`.

The wizard lets you pick a template interactively. To use one directly:

```bash
python3 skills/campaign/run.py --template skills/campaign/templates/brands.md ...
```

Always pass `--template` explicitly when using `--leads` — the pipeline
defaults to `template_a.md` if you omit it.

---

## Providers

| Provider | Flag | Notes |
|----------|------|-------|
| Hunter | `--provider hunter` | Default. Requires `TOOLBOX_TOKEN_HUNTER` |
| Apollo | `--provider apollo` | Requires `TOOLBOX_TOKEN_APOLLO` (paid plan) |
| Clay | `--provider clay --leads export.csv` | Export from Clay UI first |
| Origami | `--provider origami --leads export.csv` | Same as Clay |

Hunter charges 1 credit per domain searched, regardless of how many emails
come back. A domain that yields 8 contacts costs the same as one that yields 1.
The free `/v2/email-count` pre-check filters out domains with 0 executive
emails before spending a credit. Cached enrichment CSVs (from previous runs)
skip the paid call entirely.

Apollo does two API calls per domain: one to list people, one to reveal and
verify the email. Only the single best contact per domain is revealed to keep
Apollo credits down. `--min-score` defaults to 80 (Hunter confidence) or
`verified` status (Apollo).

---

## A/B experiments

Pass `--experiment` to split leads 50/50. Claude writes a variant B with a
different angle or structure. Reply rates per variant are tracked in Supabase
`replies.variant` and visible in `reply_report.py`.

---

## Gotchas

**Gmail daily limit.** Free Gmail caps at 500 sends/day; Google Workspace at
2000. Sends past the cap log as `bounced_gmail_limit` and never deliver. If
this happens, delete the bounced rows from Supabase before retrying from
another account.

**gog token expired.** If a send fails with `unauthorized_client (401)`, the
stored OAuth token is stale. Run `gog auth add <email> --services gmail` to
re-auth.

**Hunter credits vs emails sent.** You asked for 20 emails, you used 21
credits. Credits are per domain searched, not per email sent. Domains that
pass the pre-check but return nothing (no_contact) still cost 1 credit.

**Company name from domain stem.** If Hunter's API does not return an
`organization` name, `{{company}}` falls back to the domain stem (e.g.
`ursamajorvt.com` → `Ursamajorvt`). Check the enriched CSV if the preview
looks wrong.

**Concurrent LLM calls are slower.** Domain generation uses one `claude -p`
call at a time (`_LLM_CONCURRENCY = 1`). Firing several in parallel throttles
the subscription and makes each one slower, not faster. Do not change this.

---

## How it works

```
run.py
  1. Generate target domains from ICP description via Claude
  2. Enrich domains via Hunter or Apollo to find decision-maker contacts
     (or load a pre-exported CSV with --leads)
  3. Render the template into per-contact emails
     (--experiment: Claude writes variant B; leads split 50/50)
  4. Check Supabase ledger — skip anyone already contacted
  5. Send via Gmail REST API (--concurrency, default 8)
  6. Write campaign row to Supabase `campaigns` table
  7. Create row in Notion Campaign Metrics database
  8. Write campaign log to ~/.blackwell/campaigns/campaign_<id>.jsonl

reply_scan.py
  1. Read campaign log — maps {email -> run_id, variant}
  2. Get Gmail token from gog
  3. Search inbox with from:(contact1 OR contact2 ...) in batches of 50
  4. Classify reply sentiment via LLM (skip with --no-classify)
  5. Upsert to Supabase `replies` (UNIQUE on recipient + message_id)
  6. Update Notion row with cumulative reply count
```

Scan replies manually:

```bash
python3 skills/campaign/reply_scan.py \
  --log ~/.blackwell/campaigns/campaign_<id>.jsonl
```

View reply rates:

```bash
python3 skills/campaign/reply_report.py \
  --log ~/.blackwell/campaigns/campaign_<id>.jsonl
```

---

## Files

| File | Purpose |
|------|---------|
| `run.py` | Main orchestrator |
| `wizard.py` | Interactive campaign wizard |
| `reply_scan.py` | Gmail scanner, Supabase writer, Notion sync |
| `reply_report.py` | Reply rate table from Supabase |
| `gog_auth.py` | Gets Gmail access token from gog keyring |
| `notion_sync.py` | Creates/updates Notion Campaign Metrics rows |
| `cron.sh` | Daily reply scan cron |
| `send.sh` | Non-interactive entrypoint behind `/campaign N` |
| `icp_mix.toml` | ICP segments and per-segment email counts |
| `templates/` | Email templates — one `.md` file per variant |
| `FOUNDERS.md` | Cofounder roster and per-sender `--cc` convention |
| `ERRORS_AND_LESSONS.md` | Known errors and their fixes |

Campaign logs: `~/.blackwell/campaigns/campaign_<id>.jsonl`
Live enrichment: `skills/campaign/enriched/enriched_<id>.csv`
Generated domains: `skills/campaign/enriched/domains_<id>.csv`

---

## Notion Campaign Metrics

Shared database all teammates write to:
https://app.notion.com/p/00b1d4354b7f475faeca57a13d426204

Columns: Campaign, Sender, Date, Provider, Template, ICP, Experiment, Sent,
Replied, Reply Rate (formula). Updated automatically on each run and scan.

---

## Running tests

```bash
TOOLBOX_TOKEN_HUNTER=fake TOOLBOX_TOKEN_APOLLO=fake TOOLBOX_SESSION_TOKEN=fake \
  toolbox/.venv/bin/pytest skills/campaign/tests/ -v
```

All tests run without real API keys (HTTP calls mocked with respx).

---

## Changelog

- 2026-06-22: fixed `{{company}}` slot falling back to domain stem (e.g.
  `Ursamajorvt`) — `_hunter_domain_all` now extracts `organization` from the
  Hunter API response and passes it through as `company`.
- 2026-06-22: converted templates to HTML (`<p>` tags) for correct Gmail
  rendering. Fixed a bug where extra frontmatter fields (e.g. `format: html`)
  broke `parse_template` and silently skipped the test email.
- 2026-06-19: added interactive wizard (`wizard.py`) — previews the email,
  sends a test, and confirms before the full send.
- 2026-06-18: live visibility: generated domains stream to
  `enriched/domains_<id>.csv` and verified contacts stream to
  `enriched/enriched_<id>.csv` as they are found.
- 2026-06-18: created. gog auth, Hunter/Apollo enrichment, Notion sync,
  A/B experiments, daily cron, concurrent send via Gmail REST API.
