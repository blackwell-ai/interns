# Guardian Water Sports

Snorkeling, swimming, and diving gear brand (guardianwatersports.com), US, DTC on
Shopify plus wide big-box retail (Dick's, West Marine, Big 5, Amazon). Value and
mid-tier snorkel masks, full-face masks (OMNi), fins, and combos, roughly $20 to
$50. Referred by the e-commerce agency (Leandro) on 2026-06-30 alongside
[[stream2sea]] and [[wavmob]]. Lighter audit pass (methodology run, no full deck)
to support a one-pager. No direct contact yet; reached through the agency.

Last updated 2026-06-30. Sources: recon `agents/geo/guardian/recon-2026-06-30.md`
(recon.sh), plus editorial-roundup and reputation checks the same day. The live
engine battery was run 2026-07-01 across all six major engines (ChatGPT, Perplexity,
Gemini, Claude, Google AI Overview, Copilot) via `/browse`, logins and Google captcha
cleared by Armaan; see `battery-log.md`. All six omit Guardian and converge on Ocean
Reef, Cressi, Seaview/WildHorn, SEAC, Decathlon Subea, and Khroom.

## Findings (2026-06-30)

- **Plumbing is strong, not the problem.** Shopify. All seven AI bot user-agents
  return 200 on a product page (clean crawl). Full agentic stack live: `/agents.md`,
  `/llms-full.txt`, `/.well-known/ucp`, `sitemap_agentic_discovery.xml` all 200.
  Homepage and PDP JSON-LD carry Product, Offer, Brand, Organization, plus
  AggregateRating, sameAs, and gtin/sku on the product page. Better structured-data
  coverage than Stream2Sea at audit.
- **Recommendability is the gap (flagship).** Absent from every "best snorkel mask
  / full-face snorkel set" roundup checked (DiveIn, Snorkel Pursuits, Tropical
  Snorkeling, The Outdoor Champ, khroom-sport). Those guides, which the engines
  retrieve, are owned by Ocean Reef Aria, Cressi, Khroom/Seaview, and WildHorn.
  Guardian shows up only on its own site and big-box retailer pages.
- **Full-face safety certification is the specific lever.** Every full-face roundup
  now gates recommendations on independent CO2-safety testing (TUV, DEKRA, SGS).
  No visible certification for Guardian's full-face masks, so it is filtered out
  before consideration. Certification is a manufacturer step we would guide, not
  assert.
- **Reputation is retailer-siloed.** Sells and is reviewed mostly inside Amazon
  and Dick's; no independent aggregator (Trustpilot) surfaced. The "No.1 snorkel
  brand" self-claim on the About page is unsupported.
- **Title finding.** Homepage `<title>` grep matched an inline SVG payment-icon
  title (`American Express`), i.e. no server-rendered page title; JS-injected, same
  pattern as Stream2Sea. Confirm the real head title before asserting in anything
  customer-facing.

## Deliverable

One-pager built 2026-06-30, awaiting human sign-off:
`agents/geo/guardian/guardian-one-pager.pdf` (6 fixes tied to findings, 30-day
money-back KPIs, $1,000 Phase 1 plus Phase 2 retainer). Agency target 2026-07-05.

## Open items

- Battery done 2026-07-01: Guardian absent in all six engines (ChatGPT, Perplexity,
  Gemini, Claude, Google AI Overview, Copilot). Unanimous.
- Verify whether Guardian holds any CO2-safety certification before leaning on that
  finding externally.
