# autonomous-outreach

**Purpose:** send personalized cold emails at volume, autonomously, with the
no-double-contact guarantee enforced per send. The token-cheap companion to the
harness `clay-cold-email` skill — this is a standalone Python script (no LLM
in the orchestration loop except the one-sentence hook), so a long campaign
costs almost no Claude tokens.

## One command (the fast path — ≈3–5 min human time)

```bash
bash skills/autonomous-outreach/campaign.sh --from samarjit --dry   # enrich+filter, send nothing
bash skills/autonomous-outreach/campaign.sh --from samarjit          # send it
```

`campaign.sh` chains the whole pipeline with the 2026-06-10-proven defaults:
`findemail.find-exec` over `lead_bank.csv` (Hunter, conc 5, verified emails) →
`prep_queue.py` (drop invalid/generic/no-name) → `send_fast.py` (HTML,
co-founders CC'd, suppression-deduped, paced). Flags: `--from
samarjit|armaan|ethan|shamit`, `--domains <csv>`, `--min-score N`, `--pace S`,
`--dry`. Watch progress in the **Supabase ledger, not Gmail search** (it lags —
see `harness/learnings/03`). Dedup means re-running the same bank sends to
nobody new, so keep `lead_bank.csv` fed with fresh domains. Full reuse recipe +
lessons: `harness/learnings/`.

**Inputs:** a batch CSV with columns `brand,domain,email,first_name` (what
`prep_queue.py` produces), or just `brand,domain` for `campaign.sh` to enrich.
The committed `lead_bank.csv` (224 DTC domains) is the default universe; grow it
over time. Clay CSV exports also still work as input.

**Credentials:** gogcli (Dartmouth send account); Supabase keys from
`credentials/.env` for the suppression/ledger writes. The personalization hook
runs on headless Claude Code.

## Dedup: this sender records to `suppression`, NOT `contacted` (read this)

This script runs on the Supabase **service key**, which has no `auth.uid()`, so
it cannot write the `contacted` table (its `sent_by` requires a logged-in user).
Instead it uses the `suppression` table's primary key as its atomic dedup +
contact record. **Consequence: the people this sender has emailed live in
`suppression`, and `contacted` may be empty even after thousands of sends.**

So when you build or vet a list, **do not** dedup by querying `contacted` alone —
it will read as fresh when it isn't. Use one of:
- the `check_contact(channel, recipient)` RPC — it unions BOTH tables (returns
  `suppressed` / `contacted` / `new`) and the service key can call it; or
- query BOTH `contacted` AND `suppression`.

Dedup at **sourcing** time (before enrichment spend), not just at send time, and
treat any reused/pre-enriched lead file as already-contacted until checked — it
is usually a prior run's output. Full post-mortem:
`harness/learnings/07-ledger-split-contacted-vs-suppression.md`.

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

## Token strategy (what's expensive vs free)

Per Armaan's standing instruction (2026-06-10): make everything that *can* be
token-cheap, cheap.

- **Irreducible cost — Clay MCP enrichment.** Finding named contacts means
  calling the Clay connector, and every result (often 3–19 contacts ×
  many fields) lands in the model context. There is no headless path: the Clay
  connector only lives in an interactive session. To bound it: cap roles to the
  decision-makers you'll actually email, and do NOT re-poll `get-task` once the
  emails are `completed` — the poll re-returns the entire blob.
- **Free — everything downstream.** Sending, the suppression/ledger claim,
  logging, bounce handling, and reply triage all run in headless scripts
  (`send_fast.py`, `handle-replies/`) with zero model tokens. Send the proven
  template (no per-email LLM hook — that was slow and token-burning).
- **Rule of thumb:** the model context should only ever touch *new* enrichment
  data once. Bank it to `queue.csv` immediately; let the headless sender drain.

## send_fast.py vs send_batch.py

`send_fast.py` is the token-optimal sender: the proven "Stanford Student
Question" template with `{brand}`/`{first_name}` substitution, no per-email LLM
call, ~6s pacing with 403 rate-limit backoff. Use it for volume.
`send_batch.py` adds a per-email Claude hook (slower, nicer) — use only when a
small high-value batch warrants the personalization.

## Pairs with

- `clay-cold-email/` — the auditable harness version (full clarify→canary chain).
  Use that for accountable campaigns; use this for cheap autonomous volume.
- `handle-replies/` — triage + schedule calls from the replies this generates.

## Changelog

- 2026-06-10: created from the first autonomous run.
