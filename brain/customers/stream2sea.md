# Stream2Sea

Reef-safe mineral sunscreen and ocean-safe body care brand (stream2sea.com),
founded by cosmetic chemist Autumn Blum. Positioning: USDA BioBased, biodegradable,
tested to be safe for coral and marine life ("safe for you and our Blue Planet").
Core audience is divers, snorkelers, and ocean lovers. Shopify store, sold direct
and through Amazon and dive/snorkel retailers. Audited by the GEO agent starting
2026-06-29. As of 2026-06-30 no longer fully cold: reachable through an e-commerce
agency (contact Leandro) that manages Stream2Sea and asked us to pitch it. See
"Agency channel" below.

Last updated 2026-06-29. Sources: nine-phase AI visibility audit in progress
(`skills/ai-visibility-audit/`), artifacts under `agents/geo/stream2sea/` dated
2026-06-29. Recon (phase 1+2) frozen; engine battery and reputation in progress.

## Engagement framing

Cold prospect leave-behind to win the $1,000 two-phase pilot. Competitor set for
the scorecard and battery: Raw Elements, Badger, Thinksport (chosen with founder
2026-06-29 as the listicle-dominant reef-safe / mineral set closest to Stream2Sea's
clean-mineral positioning).

## Recon (phase 1+2, frozen 2026-06-29)

Source: `agents/geo/stream2sea/recon-2026-06-29.md`. Technically well-equipped,
unlike the weak cold-prospect audits. The likely deficits are Recommendability
(live engine inclusion) and off-site Reputation, not on-site plumbing.

- **Crawlability: clean.** All seven AI bot user-agents (GPTBot, OAI-SearchBot,
  ClaudeBot, PerplexityBot, Google-Extended, Amazonbot, Bingbot) return HTTP 200 on
  a product page. No walls.
- **Schema: present.** Homepage JSON-LD is `Organization` + `WebSite` +
  `SearchAction`. Product PDP (`swim-strong-travel-set`) serves `Product` + `Offer`
  + `Brand` + `Organization`. Decent depth; AggregateRating presence to be checked.
- **Agentic / UCP: live (Shopify-native).** `/agents.md`, `/llms.txt`,
  `/llms-full.txt` (text/markdown, ~4KB, Shopify default pointing agents to
  shop.app), `/.well-known/ucp` (real UCP JSON: cart/checkout/catalog/fulfillment/
  discount/order services, MCP transport, Google Pay + Shop Pay payment handlers,
  backend `f24312-2.myshopify.com`), and `sitemap_agentic_discovery.xml` all 200.
  The apex `/api/ucp/mcp` 404 is a red herring: the UCP doc points the live MCP
  endpoint to the myshopify backend, so Transactability is wired.
- **Catalog / content depth.** 82 products, 250+ collections, 195 blog articles.
  Meta description present and on-brand.
- **Caveat to verify in deck:** recon's title grep matched an inline SVG
  `<title>American Express</title>` (a payment-icon label), not necessarily the
  page `<title>`. Confirm the real homepage title before asserting any title
  finding.

## Scorecard: composite 69, grade C (verified 2026-06-29)

Discoverability 68, Quotability 70, Recommendability 56, Transactability 88,
Reputation 62. Competitive set (estimates from same-day public signals): Badger ~79,
Raw Elements ~77, Thinksport ~77; set averages ~78 (B). Stream2Sea trails by ~9
points, and the entire gap is Recommendability + Reputation, not on-site plumbing.

### Findings (verified 2026-06-29)

- **Recommendability 56 (the gap, flagship).** Memory/retrieval split. Named in both
  OFF passes (ChatGPT listed it for "diving/snorkeling"; Claude ranked it #3, "the
  standout if you actually snorkel or dive"), so the brand has real standing in
  training data. But in the live ON answers it mostly vanishes: named only by Claude
  and by ChatGPT in 1 of 2 renders; absent in Perplexity, Copilot, Gemini, and Google
  AI Overview. Live answers are dominated by Project Reef and Badger, which own the
  editorial citation graph (Treeline Review, NYT Wirecutter, Travel+Leisure, Good
  Housekeeping, Vogue). Evidence: `battery-log.md` + 9 captures. The lever is source
  authority in the guides engines retrieve, plus the HEL "Protect Land + Sea"
  certification competitors lead with.
- **Reputation 62.** Amazon is the only deep surface (flagship Water Sport SPF 30
  over 1,000 ratings at 4.0★; Every Day Active SPF 45 4.6★/203; catalog 4.0–4.6),
  positive but siloed. Trustpilot claimed but dormant (3.8, 2 reviews, "no
  history of asking for reviews"); no BBB or ConsumerAffairs profile; Reddit and
  YouTube thin and niche (positive r/scuba word-of-mouth, low-view clips). Homepage
  `Organization` entity has **no `sameAs`** and **no `AggregateRating`**, so none of
  it is connected to the machine-readable identity. See `reputation-2026-06-29.md`.
- **Transactability 88 (strength).** Full Shopify UCP agentic layer live: `/agents.md`,
  `/.well-known/ucp` (cart/checkout/catalog/fulfillment/discount/order, MCP transport,
  Google Pay + Shop Pay handlers), agentic-discovery sitemap. The apex `/api/ucp/mcp`
  404 is a red herring; the live MCP endpoint is on the myshopify backend.
- **Discoverability 68 / Quotability 70.** All seven AI bots return 200 (no walls);
  product PDPs carry Product + Offer + Brand. But the homepage entity is thin: no
  `sameAs`, no `AggregateRating`, and no server-rendered `<head>` `<title>` (only SVG
  payment-icon titles; title is JS-injected, og:title present). Raw Elements ships a
  richer homepage entity (AggregateRating + Brand) and is the competitor to beat on
  structured data.

### Competitive note

All four brands are on Shopify with the same native UCP layer and full crawlability,
so plumbing does not separate them. Project Reef (not in the chosen comp set) is the
brand that has captured the live reef-safe category answers through aggressive
content; Badger wins on the HEL certification. Stream2Sea's pitch is warm: the
engines already know and respect the brand from memory, so the work is getting that
reputation into the live citation graph and connecting it to the entity.

## Agency channel (2026-06-30)

Source: Granola meeting "E-commerce agency insights", 2026-06-30 10:00 PDT
(Granola auto-titled the brand "Stream to See"). Armaan met an e-commerce agency
that manages Stream2Sea plus two other brands (Guardian, WavMob). The agency
reviewer is Leandro, who verifies references by looking, not calling, and then
escalates to the brand founder.

- The agency praised the audit and the concept. Two pushbacks: the $1,000 fee
  reads as proof-of-concept (they asked where recurring revenue comes from), and
  they need defined before/after KPIs so the money-back guarantee is measurable.
- What they want per brand: a one-pager with 6 to 12 specific fixes, expected
  benefit, KPIs, and price, with the audit behind it as backup, plus two reference
  case studies. Target 2026-07-05.
- Timing risk: Stream2Sea just hired another SEO agency; confirm no overlap. The
  agency lead is satisfied GEO and SEO are complementary.
- Side opportunity: the agency lead has CEO-level relationships at Rip Curl,
  O'Neill, Hurley, Manera, and Decathlon via CircularFlow (neoprene recycling)
  and floated Blackwell becoming a reseller for European/UK brands.

Deliverable built 2026-06-30 (awaiting human sign-off before it goes to Leandro):
one-pager `agents/geo/stream2sea/stream2sea-one-pager.pdf` (framing, 8 fixes tied
to findings, 30-day money-back KPIs, $1,000 Phase 1 plus a Phase 2 retainer for
the recurring off-site work). Reference pack for Leandro:
`brain/customers/documents/blackwell-reference-pack.pdf` (Good Molecules and
Public Goods). Sibling audits: [[guardian]], [[wavmob]].

## Open items

- Human sign-off required before anything goes to the customer (charter guardrail).
- Armaan to set the Phase 2 retainer figure (the recurring-revenue answer Leandro
  asked for) before the one-pager ships.
- Confirm Armaan is fine naming Good Molecules and Public Goods to the agency
  (decided yes on 2026-06-30; overview.md's cite-with-care caution still applies).
- Live engine batteries now captured for all three: Stream2Sea (prior run),
  Guardian and WavMob run 2026-07-01 (ChatGPT, Perplexity, Gemini via /browse).
