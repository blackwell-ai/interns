# autonomous-outreach

**Purpose:** send personalized cold emails at volume, autonomously, with the
no-double-contact guarantee enforced per send. The token-cheap companion to the
harness `clay-cold-email` skill — this is a standalone Python script (no LLM
in the orchestration loop except the one-sentence hook), so a long campaign
costs almost no Claude tokens.

**Inputs:** a batch CSV with columns `brand,domain,email,first_name`. Build it
from `~/Documents/Giftly` candidate lists (deduped against suppression) and/or
Clay-enriched named contacts.

**Credentials:** gogcli (Dartmouth send account); Supabase keys from
`credentials/.env` for the suppression/ledger writes. The personalization hook
runs on headless Claude Code.

## How it runs

    # env: SUPABASE_URL, SUPABASE_SECRET_KEY, GOG_KEYRING_PASSWORD
    python3 skills/autonomous-outreach/send_batch.py <batch.csv>

Per row:
1. **Claim** the recipient in Supabase `suppression` (insert; conflict → already
   contacted → skip). This is the hard no-double-contact gate.
2. **Hook** — one tailored sentence about how that brand likely appears to AI
   shopping assistants (headless Claude Code, haiku).
3. **Send** via gog from the Dartmouth account, co-founders CC'd, proven
   "Stanford Student Question" template.
4. **Record** — update the suppression reason with the message id; append to
   `/tmp/autonomous_send_log.csv`.
5. Paced at 25s/send (domain-reputation safety). On a Gmail hard-quota error it
   releases the claim and exits 9 (resume next day).

## Why a script, not an in-context loop

The user asked to minimize tokens. Orchestrating hundreds of sends turn-by-turn
in the model context is the expensive way; this script does the whole batch
headless and only reports a summary. Clay enrichment (finding named founders)
is the one step that must run in-session — do that in batches, append to the
CSV, then hand it to this script.

## Pairs with

- `clay-cold-email/` — the auditable harness version (full clarify→canary chain).
  Use that for accountable campaigns; use this for cheap autonomous volume.
- `handle-replies/` — triage + schedule calls from the replies this generates.

## Changelog

- 2026-06-10: created from the first autonomous run.
