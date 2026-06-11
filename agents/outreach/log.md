# Outreach log

Dated run summaries (sourced / sent / replies / meetings), newest first.

## 2026-06-10 (evening) — fully-headless sourcing + 166-send run from Samarjit

- **Approach (zero manual lead work):** built the `findemail` harness primitive
  (Clay can't be driven headlessly — see
  `brain/decisions/2026-06-10-clay-not-headless-findemail-primitive.md`). Pipeline:
  web-search harvested ~224 DTC brand domains → `findemail.find-exec` (Hunter
  Domain Search) → 180 verified named decision-makers (median deliverability
  score 98; 362/2000 Hunter credits used) → filtered out invalid/generic/no-name
  → 169-lead queue.
- **Sent: 166** verified founders/decision-makers (CEO/founder/CMO/head of
  ecommerce) from **samarjit.deshmukh.29@dartmouth.edu**, co-founders CC'd,
  **HTML/rich-text** version of the proven "Stanford Student Question" template
  (plaintext fallback included), paced ~8s with rate-limit backoff. **0 failures,
  0 double-contacts** (every recipient claimed in the Supabase suppression ledger
  before send; UNIQUE constraint held — 242 unique blackwell-volume rows, 0 dups).
- **Skipped: 3** (Cuts Clothing, Grove, Buck Mason) — already in suppression from
  a prior session; correctly not re-contacted.
- **Brands include:** Caraway, Cuts, Halfdays, Blueland, Pepper, Cometeer, Knix,
  Phlur, Glamnetic, Magic Spoon, Our Place, Lovevery, The Ridge, MUD\WTR,
  Dr. Squatch, Mack Weldon, Jones Road, Brightland, Four Sigmatic, Rhone,
  Madhappy, TRUFF, Tushy, Tatcha, Bombas, and ~140 more.
- **Replies/meetings:** — (check the Dartmouth inbox; run `gmail.replies
  --file-inbox-tasks` and `gmail.bounces` over the next days).
- **Note:** one mid-run stop/restart happened because Gmail's *search* index
  lagged and made healthy sends look like failures; the ledger proved all sends
  succeeded, and the claim-dedup made the restart safe (already-sent rows
  skipped). Lesson: trust the ledger, not Gmail search, for live send progress.

## 2026-06-10 — first Blackwell-era cold send (manual, pre-harness)

- **Sourced:** 705 never-contacted brands recovered from the Giftly batch
  lists (after seeding suppression with all 2,562 previously-contacted
  addresses). Top pick enriched in Clay: 100% PURE (Purity Cosmetics,
  San Jose, $25–75M, founder-led clean beauty, multichannel).
- **Sent: 1** — Richard Kostick, Founder & CEO, richard@puritycosmetics.com
  (gmail message 19eb2703d6c7a791). From the Dartmouth account, co-founders
  CC'd, proven "Stanford Student Question" template + multichannel-pricing
  hook. Sent via gogcli (harness gmail not yet authed); recipient recorded in
  Supabase suppression so no flow can ever double-contact him.
- **Replies:** — (check the Dartmouth inbox / thread 19eb2703d6c7a791)
- **Meetings:** —
- Backup contact if no reply: Kelly McElwain, Marketing Manager,
  kelly.mccreery@100percentpure.com (verified, uncontacted).

## 2026-06-10 (later) — autonomous volume attempt; blocked at mass-send

- **Approach:** Clay-enriched verified named contacts (no generic inboxes, no
  guessed emails), proven "Stanford Student Question" template, co-founders CC'd,
  Supabase suppression-claim per send. Headless `send_fast.py`; token-optimized
  (no per-email LLM, enrichment is the only model-context cost).
- **Enriched (Clay):** Lo & Sons, NAKEDCASHMERE, Elevated Craft, Lola Blankets,
  Roxanne Assoulin, Ice Shaker, BASMA, Plank+Beam, 100% PURE (~34 verified
  contacts queued). Skipped bad list matches (smartwings=airline, wolfbox=dashcam mfr).
- **Sent this session:** ~18 (verified named contacts) + the earlier 4
  (Richard/Plank+Beam founder + 3 generic before the no-generics rule).
- **Blocked:** Claude Code auto-mode classifier refused the unattended
  mass-send daemon (human-gating required). Not worked around. Resume path +
  queue saved — see inbox task 2026-06-10-resume-autonomous-send.

## 2026-06-10 (resumed) — unblocked + autonomous send running

- Armaan added the Bash allow-rule (`.claude/settings.local.json`) for
  `run_sender.sh`, which clears the gate the human way. Sender relaunched as a
  daemon over `last_queue.csv`; it re-reads the file each scan, so new
  Clay-enriched contacts appended via the Edit tool get picked up and sent.
- **Sent: 53 today** (and climbing) — verified named decision-makers
  (CEO/founder/CMO/head of ecommerce/marketing) across ~25 brands: Lo & Sons,
  NAKEDCASHMERE, Elevated Craft, Lola Blankets, Roxanne Assoulin, Ice Shaker,
  BASMA, Plank+Beam, 100% PURE, HydroJug, OOLY, Fin Fun, PDPAOLA, Keyport,
  Bad Birdie, Little Sleepies, Lulu & Georgia. All Dartmouth account,
  co-founders CC'd, suppression-claimed (zero double-contact), proven template.
- **Queue:** ~69 verified contacts; daemon paces ~6s/send with rate-limit
  backoff, self-stops on Gmail's daily cap (the real ceiling) and resumes.
- **Token note:** the SEND loop is free (headless daemon); the ENRICH loop
  (Clay MCP, finding named contacts) is the only model-token cost and is the
  practical limit on how fast the queue grows in one session.
