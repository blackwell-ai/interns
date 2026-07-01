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

### Always-on chat wizards (Telegram and Slack)

A hosted wizard runs the same pipeline from chat: describe the send in plain
English, it plans and previews, you confirm, it sends. The Telegram bot and the
Slack bot (mention `@email_wizard` in the configured channel) share one codebase
under `server/`. Setup, deployment, and the Railway services are documented in
`server/README.md`.

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
TOOLBOX_TOKEN_APOLLO=<your apollo.io API key>      # only if using Apollo
TOOLBOX_TOKEN_STORELEADS=<your storeleads.app key> # optional, see below

# shared — get from a teammate out-of-band
SUPABASE_URL=https://lvzvmqeynkwywodcqxkv.supabase.co
SUPABASE_ANON_KEY=<shared anon key>
NOTION_TOKEN=<shared integration token>
```

You only need the key for the provider you use. No `GMAIL_*` keys needed.

`TOOLBOX_TOKEN_STORELEADS` is optional and improves domain *sourcing* (it is not
a contact provider — Hunter/Apollo still find the emails). When set, each niche's
target domains come from real, live stores in the StoreLeads database instead of
Claude guessing company names. See "Domain sourcing" below.

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
`{{segment_phrase}}`, `{{personal_line}}` (per-brand line; see AI-visibility
mode below). Every slot a template uses must be non-empty for every row or that
row fails compose.

HTML templates are auto-detected: if the body starts with `<`, the email is
sent as multipart HTML. Use `<p>` tags for paragraphs. Do not add extra
frontmatter fields — `parse_template` only reads `subject:`.

The wizard lets you pick a template interactively. To use one directly:

```bash
python3 skills/campaign/run.py --template skills/campaign/templates/brands.md ...
```

Always pass `--template` explicitly when using `--leads` — the pipeline
defaults to `template_a.md` if you omit it.

### AI-visibility (GEO) mode

`--personalize-visibility` fills a `{{personal_line}}` slot per brand from a
live check: it asks an AI which brands it names for the buyer's niche and
whether this brand is one of them, then opens the email with what it found
(brand absent -> names real competitors; present -> softer line; check failed
-> a safe generic line that claims nothing unverified). The line is never
empty, so it never breaks compose. Off by default; one extra LLM call per
contact, so only GEO runs pay for it. Template: `templates/ai_visibility.md`.

Through the Slack/Telegram wizard this turns on automatically: frame the ask
around AI visibility ("40 emails to DTC apparel brands about how they show up
in ChatGPT") and the planner sets `geo: true`, which routes to the GEO template
and passes `--personalize-visibility`. The claim-making logic lives in one
tested module, `visibility.py`.

**Preview the real line before sending — `geo test`.** The wizard's normal
preview runs before any brand is sourced, so it shows `{{personal_line}}`
unfilled; the real line is generated per brand at send time. To see it, ask the
Slack wizard:

```
@wizard geo test women's lingerie          # sources 2 live brands for the niche
@wizard geo test orange-lingerie.com       # tests one exact brand (most reliable)
```

It sources live brands (StoreLeads), runs the real check, and posts the
finished email. Read-only, sends nothing. Use the domain form when you want a
trustworthy preview: the niche form adds sourcing + niche-inference noise (a
loosely matched store or a wrong niche guess can slip in), which is exactly what
this command lets you catch. Handler: `server/geo_test.py`.

Direct CLI:

```bash
python3 skills/campaign/run.py --icp "DTC apparel brands" \
  --template skills/campaign/templates/ai_visibility.md \
  --personalize-visibility --limit 20 --dry-run ...
```

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

## Domain sourcing

Before any contact provider runs, the pipeline needs a list of target domains for
the ICP. There are two ways it gets them, and StoreLeads is preferred when
available.

**StoreLeads (preferred).** With `TOOLBOX_TOKEN_STORELEADS` set, each niche is
translated into StoreLeads search filters by one cheap structured LLM call
(`subcat_to_filters`), then `storeleads.search_domains` returns real, live
e-commerce stores ranked by estimated sales. This beats LLM guessing on every
axis: domains are confirmed live (so no Hunter credit is spent enriching a dead
or hallucinated domain), the result set is real and far larger than the ~20 names
Claude can recall before it starts inventing, and the strongest stores enrich
first. Get a key from storeleads.app (Account -> API). It uses the same API the
StoreLeads MCP wraps, called directly over HTTP so the headless pipeline needs no
MCP.

**LLM generation (fallback).** When no StoreLeads key is set, or a niche is not
consumer e-commerce (B2B services, 3PL/logistics, software, manufacturing — none
of which StoreLeads indexes), or a StoreLeads query errors or returns nothing,
sourcing falls back to `generate_domains_for_subcat` (Claude lists real company
domains for the niche). Nothing breaks without the key; you just lose the quality
and volume StoreLeads adds for the DTC segments.

The seam is `source_domains_for_subcat` in `run.py`; everything downstream
(enrichment, dedup, the Supabase ledger) is unchanged and only consumes a list of
domain strings. The LLM-chosen `category` is best-effort — if it names a path that
does not exist in StoreLeads' taxonomy the query returns nothing, so sourcing
retries once on the keyword alone before dropping to LLM generation.

**Test it without burning credits.** Domain sourcing never calls Hunter, so you
can verify StoreLeads end-to-end for free:

```bash
# zero Claude tokens, zero Hunter — pure StoreLeads with explicit filters
python3 skills/campaign/storeleads_probe.py --no-llm --q "maternity clothing" --category "/Apparel"

# the real production seam (1 small Claude call to translate the niche), no Hunter
python3 skills/campaign/storeleads_probe.py --subcat "DTC pet supplements"
```

The mocked unit tests cost nothing at all:

```bash
PYTHONPATH="$PWD:$PWD/toolbox/src" toolbox/.venv/bin/pytest \
  skills/campaign/tests_sourcing/test_storeleads_sourcing.py -v
```

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
  1. Source target domains per niche — StoreLeads (real stores) when
     TOOLBOX_TOKEN_STORELEADS is set, else Claude generation (see Domain sourcing)
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
| `storeleads.py` | StoreLeads REST client — real store domains for a niche |
| `storeleads_probe.py` | Verify StoreLeads sourcing without spending Hunter credits |
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

- 2026-06-29: StoreLeads-primary domain sourcing. With `TOOLBOX_TOKEN_STORELEADS`
  set, each niche's domains come from real, live stores in the StoreLeads database
  (`storeleads.py` + `subcat_to_filters`/`source_domains_for_subcat` in `run.py`)
  instead of Claude guessing names — confirmed-live domains (no Hunter credit on
  dead/hallucinated ones), 50 real stores per niche vs the ~20 Claude could recall,
  ranked by estimated sales. Falls back to LLM generation when the key is absent,
  the niche is not consumer e-commerce, or a query errors/returns nothing, so
  nothing breaks without the key. The LLM-chosen category is best-effort: a
  hallucinated category path zeros the query, so the search retries once on the
  keyword alone before falling back. Only the per-niche domain source changed; all
  downstream enrichment/dedup/ledger logic is untouched. Verify for free with
  `storeleads_probe.py` (never calls Hunter) or the mocked
  `tests_sourcing/test_storeleads_sourcing.py` (delete after the next large run
  confirms StoreLeads sourcing in production). Known follow-up: cross-run cursor
  paging to page *deeper* into a niche on repeat runs (the API returns
  `next_cursor`; we store it but do not yet resume from it).
- 2026-06-29: lifted the ~1000-contacts-per-run sourcing ceiling. The flat
  `_MAX_SOURCING_NICHES = 60` cap (60 niches x 20 domains ~= 1200 domains, ~1000
  new contacts after dedup) meant a 2000 ask could never fill — the loop hit 60
  niches and quit. `_niche_cap(limit)` now scales the per-run niche budget with
  the ask (~1 niche per 8 wanted contacts, floor 60); the enrichment-error
  circuit breaker still bounds credit burn. Also: the sub-category cache key is
  now `md5(_normalize_icp(icp))`, so casing/whitespace/trailing-punctuation
  variants of one ICP share a single niche + exclusion memory instead of
  fragmenting (we had 4 separate caches for "DTC brands" spellings). Note: the
  re-find waste from re-suggesting already-contacted domains is bounded by
  `--max-domain-count` (default 3) filtering pre-Hunter — left at 3 on purpose so
  a 2nd/3rd exec at the same company is still reachable. Tests in
  `tests_sourcing/` (delete after the next large run confirms it fills).
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
