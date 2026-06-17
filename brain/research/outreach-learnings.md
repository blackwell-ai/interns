# Outreach learnings

What has actually worked. The outreach agent reads and extends this file.

## Email-engine status (2026-06-17)

- Clay's email enrichment is still down, three days on. Re-probed June 17: 5 of
  5 known-good founders returned "None Found" (Graza CEO and COO, OLIPOP two
  co-founders plus a VP and CFO), including addresses already in our ledger. So
  this is a sustained provider outage on Clay's waterfall, not a transient blip
  or our setup. Clay's contact search is unaffected and stays free (no Email data
  point requested). Treat "pure Clay" cold email as unavailable until a probe on
  a known-good founder returns a real address. Full diagnosis:
  `brain/decisions/2026-06-16-prospeo-email-engine.md`.
- It is not only email: Clay's "Company Competitors" data point also returned
  state=error on June 17 across four seeds (Dieux, Taika, Gorgie, Obvi). Clay's
  whole enrichment side is degraded, while its contact search is fine. So
  competitor or lookalike discovery via Clay is not a usable way to refill the
  lead bank right now; refill from a curated external list until it recovers.
- Prospeo's free-tier block is a daily request cap, confirmed: the June 16 block
  cleared on its own by June 17, and a verified email came back on the first
  probe with credits intact. So pace Prospeo runs at 25s or more and a tripped
  block recovers next day, it is not a permanent ban.
- Dedup a brand by both its website TLD and its corporate mail TLD. June 17:
  greg@juneshine.co was already in the ledger and correctly skipped, even though
  juneshine.com (the website) read as a fresh domain. The verified mail domain
  can differ from the website, so company-level dedup on the website domain alone
  misses prior contacts. Prospeo returns the real verified domain, so check it
  against the ledger before constructing or extending pattern addresses on the
  website domain.

## Outreach approach update (2026-06-15, Armaan)

How we run cold outreach going forward. Mirrored to the Notion Tasks hub
(https://app.notion.com/p/380bea8c6fe781e6ab94dd6cbdf32c7f). Applies to whoever
runs the campaign; Armaan is running the current one.

- Source via Clay. Use Clay, the lead workbench, for sourcing and enrichment when
  running interactively, not the headless web-harvest plus Hunter path. Clay only
  runs in an interactive session (see
  `brain/decisions/2026-06-10-clay-is-the-lead-workbench.md`). The headless
  `autonomous-outreach` Hunter path stays as the fallback for cron or MCP-down runs.
- Multiple contacts per company. Pull several decision-makers per company, not just
  one: founder or CEO, head of ecommerce, head of operations, head of marketing.
  Different roles see different nodes of the value chain, which serves the
  exploration, and it raises reach per account. The ledger still dedupes per person.
- Broaden the ICP for the exploration phase. Do not restrict to DTC plus GEO. First
  cohort: DTC and physical-product brands, roughly $1M to $200M, Shopify and US,
  inventory-heavy categories (apparel, food and CPG, beauty, outdoor and home),
  founder reachable. Then widen across the value chain: small businesses, supply
  chain, manufacturers, and marketing orgs (the `brain/company/targets.md` secondary
  segments). See [[cpg-ecommerce-value-chain]] and [[gaps-from-laggards]] for the
  reasoning; the founder-led under-staffed band is the sharpest first cohort.
- Message discipline. Keep the proven "Stanford Student Question" discovery opener
  for the first broadened cohort, then test an inventory-and-ops-angle subject as a
  second variant against the same segment. Change one variable at a time.
- Format. Send every email as rich text/HTML with a plaintext fallback, not plain
  text only. send_fast.py already does this; the clay-cold-email path must send the
  HTML body.

## Giftly-era contacts are suppressed (2026-06-10)

All prior outreach was extracted from `~/Documents/Giftly` (send logs:
`outreach/outreach-log.csv` — the April Throne-merchant campaign, 1,693 sends
incl. 159 bounces, sent from the retired trygiftly account; and
`outreach-retailers/outreach-log.csv` — the May retailer campaign, 876 sends
incl. 120 bounces, from the Dartmouth account), deduped, and cross-checked
against 1,275 sent messages in the Dartmouth mailbox (sweep found **zero**
recipients missing from the logs — the logs are complete).

**2,561 unique addresses now sit in the Supabase `suppression` table**
(reason-tagged `giftly-era outreach (...)`), which `gmail.send` checks before
every send with no override — no one from the Giftly era can ever be
cold-emailed again by any harness flow. This includes current customer
contacts (e.g. nils@beautylish.com, the husqvarnagroup.com contacts): correct
for cold sends; replies and manual email are unaffected. To deliberately
re-approach someone suppressed, a human removes the row first.

## The cold email that landed the current customers (observed June 10, 2026)

Source: Armaan's Dartmouth sent mail. The same template opened the Beautylish/
Good Molecules, Public Goods, and Husqvarna threads in May 2026:

- **Subject:** "Stanford Student Question - thoughts on AI retail tools"
- **Body shape:** 3 short sentences — (1) "We're Stanford/Dartmouth students
  curious how {Company} is thinking about AI, given 50 million people now shop
  with ChatGPT daily." (2) ask for a quick 10-minute call; (3) fallback ask:
  "even a one-sentence response" with their thoughts
- Sent from armaan.priyadarshan.29@dartmouth.edu, co-founders CC'd
- Replies came fast (Nils Johnson replied same day, May 21) and threads
  converted to pitch calls within hours

Why it works (hypothesis): student framing + tiny fallback ask lowers the
reply bar; the .edu sender domain supports the framing and survives filters
(one Beautylish reply did get tagged "[ AREA1 SPAM ]" — watch deliverability).

Caveat: the team is now a YC company, not just students — this framing may age
out; revisit before reusing at scale.
