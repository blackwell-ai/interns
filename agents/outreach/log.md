# Outreach log

Dated run summaries (sourced / sent / replies / meetings), newest first.

## 2026-06-15 (Clay DTC campaign): 154 sends, zero failures

Broadened Clay DTC motion, run interactively by Armaan. Method: source DTC and
physical-product brands ($1M to $200M, inventory-heavy categories) via Clay
find-and-enrich-contacts-at-company, pull multiple decision-makers per company
(C-suite plus ecommerce, marketing, operations, digital), enrich emails,
MX-verify (wave 5 onward), dedup against the suppression ledger, and send the new
DTC opener (subject "Stanford Student Question About {brand}", $100M social proof
plus the 800M ChatGPT reach line) as HTML from the Dartmouth account, co-founders
CC'd.

- Sent: 154 total, zero failures. Breakdown: batch 1 (29, see entry below), wave 2
  (32), waves 3+4 (42), wave 5 (24, MX-verified), Armaan's manual adds (6, plus
  Leslie at Kettle & Fire), part 1 of the halted "100 push" (21, MX-verified).
  Every batch auto-skipped already-contacted people via the ledger.
- Brands reached (~55): Marine Layer, Faherty, Tracksmith, Mizzen+Main, Graza, Fly
  By Jing, Bachan's, Tower 28, Kosas, Bearaby, Brooklinen, Chubbies, True Classic,
  Summersalt, Thursday Boots, OLIPOP, Spindrift, Chamberlain Coffee, Parachute,
  Made In, Starface, Outdoor Voices, birddogs, Fair Harbor, Partake, immi, Coyuchi,
  Buffy, East Fork, MERIT, Saie, Crown Affair, Public Rec, Outerknown, Koio, Hero
  Cosmetics, OSEA, Ghia, GOODLES, BLK & Bold, Material, Wild One, Rhoback, UNTUCKit,
  Johnnie-O, State and Liberty, Birdwell, Atoms, Sarah Flint, Birdies, Westman
  Atelier, Topicals, Act+Acre, Live Tinted, Kettle & Fire, Oats Overnight,
  Splits59, Set Active, M.Gemi, Sanzo, Recess, Banza, Fishwife, Magic Mind, Cozy
  Earth, Varley, plus Who What Wear (manual).
- Data-quality lesson (from Armaan): Clay's company data lags (stale revenue bands,
  founders listed at their next venture, one closed company surfaced), made worse by
  sourcing brand names from memory and reaching for obscure ones. Fix going forward:
  source from curated lists, starting with the committed
  `skills/autonomous-outreach/lead_bank.csv` (224 vetted companies), pull fresh
  roles per company, dedup, keep MX verification. Do not free-recall brands.
- Replies and meetings: pending. Run `skills/handle-replies/` over the Dartmouth
  inbox. Watch bounces given the day's cold volume.

## 2026-06-15 (batch 3): Clay-sourced DTC, 29 sends

- First run of the broadened Clay motion (DTC, $1M to $200M, inventory-heavy
  categories, multiple decision-makers per company). Sourced via Clay
  find-and-enrich-contacts-at-company across 11 brands, emails enriched by Clay,
  deduped against the ledger. Copy: the new DTC discovery opener (subject "Stanford
  Student Question About {brand}", "AI tools for DTC brands", social proof Public
  Goods and Good Molecules), HTML with plaintext fallback, from Armaan's Dartmouth
  account, co-founders CC'd. This batch used the "hundred-million-dollar brands"
  wording; later batches switch to "$100M".
- Sent: 29, zero failures. Skipped 4 already-contacted founders (andrew@graza.co,
  jing@flybyjing.com, amy@tower28beauty.com, billy.may@brooklinen.com); the other
  roles at those same companies were fresh and sent, which validates
  multiple-contacts-per-company.
- Brands and roles reached: Marine Layer (CMO, COO), Faherty (CEO, CCO, Dir
  Ecommerce), Tracksmith (CEO, co-founder CEO, CFO, Head of Digital), Mizzen+Main
  (CEO, CFO, Dir Ecommerce, Dir Ops), Graza (COO, COO/CFO), Fly By Jing (COO, CFO,
  Head of Marketing), Bachan's (CEO, President), Tower 28 (CFO, Dir Ops), Kosas
  (Founder, CMO, VP Ecommerce), Bearaby (CEO), Brooklinen (CMO, VP Ecommerce, CFO).
- No email found: Bachan's COO, Kosas CFO. Tower 28 co-founder was still enriching
  at send time.
- Replies / meetings: pending. Run `skills/handle-replies/` over the Dartmouth inbox.
- Lead list: `skills/autonomous-outreach/clay_queue_2026-06-15.csv`.

## 2026-06-15 (batch 2): Worcester locals, 4 more sends

- Same hometown angle and template as batch 1, solo plain-text from the Dartmouth
  account, each claimed in the suppression ledger. Emails sourced and verified by
  a browse sweep (see
  `agents/outreach/playbooks/2026-06-15-worcester-local-outreach.md`).
- Sent: 4, zero failures. Worcester Wares (jessica@worcesterwares.com, msg
  19ecca8b623893bc); That's Entertainment (fitch@thatse.com, msg
  19ecca8ca58174b3); Acoustic Java (info@acousticjava.com, msg 19ecca8dfd7a830c);
  Crust Bakeshop (hello@crustbakeshop.com, msg 19ecca8f05dc9aa2).
- Replies / meetings: pending. Check the Dartmouth inbox or run
  `skills/handle-replies/`.
- Worcester total today: 7 locals contacted (3 in batch 1, 4 here). Tier 2
  (Wormtown, Redemption Rock, Birch Tree Bread, The Queen's Cups, and others) have
  no public email and are walk-in or DM targets for the in-person motion.

## 2026-06-15: Worcester local outreach (3 hometown sends)

- Approach: dropped the cold "Stanford Student / AI retail" framing for a hometown
  angle, per Armaan. Sent individually and solo (no co-founders CC'd), plain text,
  from the Dartmouth account, for a personal feel. New framing: CS students at
  Dartmouth who grew up in Worcester, helping small businesses bring in new
  customers and revenue online, including from people who now shop with AI tools
  like ChatGPT. Ask: a quick call or a one-sentence reply.
- Sent: 3, zero failures. Seed to Stem (seedtostem@gmail.com, msg
  19ecc908749f29eb); Crompton Collective (cromptoncollective@gmail.com, msg
  19ecc9098970da04); Worcester Public Market (info@worcesterpublicmarket.org, msg
  19ecc90aebdfc32a). Each claimed in the Supabase suppression ledger before send
  (reason tagged Worcester local outreach), so no flow can double-contact them.
- Replies / meetings: pending. Check the Dartmouth inbox or run
  `skills/handle-replies/`.
- Note: first relationship-style local send, testing the hometown,
  in-person-adjacent angle the June 10 advisor pushed (be local, be likable, talk
  to small businesses). A reply here is a signal to try more Worcester locals.

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
