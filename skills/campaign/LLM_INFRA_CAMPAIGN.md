# LLM + AI infra campaign — continuation guide

Campaign targeting local/on-device LLM companies and data center/AI infra companies.
Template B only. Run from: samarjit.deshmukh.29@dartmouth.edu (June 2026, partial run).

## Current state (as of 2026-06-21)

| | Count |
|---|---|
| Enriched contacts (Hunter) | 732 unique |
| Delivered | 315 |
| Bounced — Gmail daily limit | 122 |
| Never attempted | 295 |
| **Remaining to send** | **417** |

All 417 remaining contacts are in:
`skills/campaign/enriched/remaining_to_send.csv`

The `status` column is either `never_attempted` or `bounced_gmail_limit`.

## Sending the remaining 417

### Step 1 — check auth (do this once per session)

```bash
# Supabase
toolbox/.venv/bin/toolbox auth status

# If not logged in:
toolbox/.venv/bin/toolbox auth login

# gog Gmail (confirm the sender account is still authorized)
gog auth list
```

### Step 2 — run from a different sender account

The 122 bounced contacts are recorded in Supabase as "sent" (even though they weren't delivered).
The `--leads` dedup check skips anyone already in the ledger, so Samarjit's account would skip them.

Use Armaan, Ethan, or Shamit as the sender. The ledger does not track per-sender, so anyone
not yet contacted by *any* account will still go through; the bounced 122 will be re-reached
because the dedup records them under Samarjit's run — a different sender account is a clean slate
only for the 295 never-attempted, not the 122 bounced.

To also reach the 122 bounced from a new account, delete their Supabase rows first (or accept
that they'll be skipped and handle them manually later).

Run command — replace `armaan` with your chosen sender:

```bash
toolbox/.venv/bin/python -u skills/campaign/run.py \
  --config skills/campaign/icp_mix_llm_infra.toml \
  --leads skills/campaign/enriched/remaining_to_send.csv \
  --segment-phrase "running AI models locally or on-device" \
  --from armaan.priyadarshan.29@dartmouth.edu \
  --from-name "Armaan Priyadarshan" \
  --cc samarjit.deshmukh.29@dartmouth.edu,ethanpzhou@berkeley.edu,shamitd@stanford.edu \
  --concurrency 8 \
  --provider hunter \
  > /tmp/campaign_remaining.log 2>&1
```

Run it in the background so Claude's Monitor tool doesn't kill it:

```bash
# In Claude Code, use run_in_background: true and tail separately:
tail -f /tmp/campaign_remaining.log
```

Cap at ~400 emails per sender per day to stay under Gmail's limit.

### Step 3 — monitor progress

The run prints a `run_id` at startup. Use it to check Supabase:

```sql
SELECT COUNT(*), MAX(created_at) FROM contacted WHERE run_id = '<your-run-id>';
```

## Auth troubleshooting

| Error | Fix |
|---|---|
| `command not found: toolbox` | Use `toolbox/.venv/bin/toolbox`, not the system path |
| `Supabase session invalid (400)` | Run `toolbox/.venv/bin/toolbox auth login` |
| `invalid_client (401)` on Gmail | Already fixed: `client_secret` is in `~/Library/Application Support/gogcli/credentials.json`. If it recurs, re-run `gog auth credentials ~/client_secret_*.json` |
| `ModuleNotFoundError: typer` | Wrong Python. Always use `toolbox/.venv/bin/python` |
| Monitor kills the run mid-send | Run Python with `run_in_background: true` and tail the log file separately |

## Config files

| File | Purpose |
|---|---|
| `skills/campaign/icp_mix_llm_infra.toml` | ICP segments for this campaign (local LLM + data center, 50/50, template B only) |
| `skills/campaign/enriched/enriched_eb13c9b9.csv` | Original 732 enriched contacts (Hunter, June 2026) |
| `skills/campaign/enriched/remaining_to_send.csv` | 417 contacts not yet delivered |
| `skills/campaign/enriched/unsent_gmail_limit.csv` | 122 bounced contacts (Gmail limit) — subset of above |
| `skills/campaign/templates/template_b.md` | The email template used for all sends |

## Hunter credits

Starter plan, resets 2026-07-19. As of 2026-06-21: 525 used, 1475 remaining.
The remaining 417 contacts are already enriched — no additional Hunter credits needed to resend them.
