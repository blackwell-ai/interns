# Hunter credit efficiency: why 362 for 169, and the fix

The first run spent **362 Hunter credits to deliver ~169 emails** — ~2.1
credits each. That's wasteful. Here's exactly why, measured (not guessed), and
the fixes (now implemented in `findemail`).

## How Hunter actually charges (probed against the live API)

| Call | Cost |
|---|---|
| Domain Search, `limit=25` | **3 credits** |
| Domain Search, `limit=10` | **1 credit** |
| Domain Search, `limit=1` | **1 credit** |
| **Repeat** of a domain already searched | **0 credits** (Hunter caches it) |

So Hunter bills **≈ ceil(emails_returned / 10) credits per domain search** — it
charges for the *results returned*, not per call. (Email Verifier and Email
Finder are billed separately; we used neither — `find-exec` reads the
`verification.status` that comes free inside domain-search.)

## Why 362 / 169 ≈ 2.1 each

Two contributors, in order of size:

1. **`find-exec` was hardcoded to `limit=25`.** It fetched up to 25 emails per
   domain, then kept exactly one (the decision-maker) and threw away the other
   24 — while paying 2–3 credits for the bigger brands (those with 11–25
   personal emails). Small brands (<10 emails) already cost 1, so the overage
   came from the larger DTC brands in the list.
2. **NOT the debug re-runs.** I re-ran enrichment over overlapping domain sets
   (136 → 160 → 224) while tuning concurrency, but **Hunter caches repeated
   searches for free**, so those re-queries cost ~0. (Verified: a repeat
   domain-search returned 0 credits.) The instinct to blame the re-runs was
   wrong; the measurement corrected it.

## The fixes (implemented)

1. **Efficient default: `limit=10` + `seniority=executive` → 1 credit/domain.**
   Cuts cost ~3×. The returned set is execs only, so the decision-maker is
   still picked well. **Tradeoff, measured:** Hunter sorts results by
   *confidence*, not seniority, so for some larger brands the actual FOUNDER
   ranks below a VP/Director by confidence and gets cut from the top 10 — you
   get "VP of Operations" instead of "Co-Founder." Still a valid senior
   contact, but not founder-to-founder.
2. **`--thorough` (limit=25, no seniority filter) → 3 credits/domain** for when
   founder precision matters more than credits. Explicit lever, not a hidden
   default.
3. **Persistent cache (`--cache file.jsonl`) → every domain billed once, ever.**
   `find-exec` skips Hunter for any domain already in the cache (hits *and*
   misses are cached, so known-empty domains aren't re-paid either).
   `campaign.sh` points it at `enrichment_cache.jsonl`, so a growing lead bank
   and any re-run are free. Verified live: 2nd run over the same domains = 0
   credits.

## What a clean run costs now

- Default, fresh bank of 224 domains: **~224 credits** (1 each), vs the original
  362 — and **0 on every subsequent run** (cache). Net: the recurring cost of a
  campaign drops toward **the number of NEW domains since last time**, not the
  queue size.
- Two more levers (documented, not yet automated):
  - **Pre-filter domains against the suppression ledger** before enriching —
    don't spend a credit finding the email of a brand already contacted (the
    send would skip it anyway). Worth adding to `campaign.sh`.
  - **`--min-score`/`--per-domain`** tune the precision/coverage/cost balance.

## Rule of thumb

Enrichment credits are cheap (2,000/mo on Starter; a full campaign is now
~100–250) — but don't fetch data you discard. Fetch one decision-maker per
domain, cache forever, and only pay `--thorough` when the founder specifically
matters.
