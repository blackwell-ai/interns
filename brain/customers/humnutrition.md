# HUM Nutrition

humnutrition.com, DTC beauty-from-within supplements (skin, hair, body, mood),
sold direct, on Sephora, and on Amazon. Custom Astro storefront behind Cloudflare.
Last updated June 16, 2026. Source: passive recon for the AI visibility audit
(see `agents/geo/humnutrition/recon-2026-06-16.md`).

Engagement status: prospecting audit (confirmed by Armaan, June 16, 2026). This is a
sales-and-credibility tool to win an engagement, not a paid deliverable, the same way the
Good Molecules audit was used. No engagement letter yet; terms would go in a separate
letter if HUM converts.

## Documents

- Draft audit deck (12 pages, house format): `agents/geo/humnutrition/humnutrition-audit-2026-06-16.pdf`
  (source HTML alongside it). Posted for sign-off at
  `inbox/queue/2026-06-16-review-humnutrition-audit-deck.md`.

## Audit status

Phases 1 and 2 done and the deck is drafted. Recon and truth table frozen first (before
any engine query, per the charter); live engine battery run across five engines; five
dimensions graded; deck rendered and validated (12 pages, zero em/en dashes, pypdf +
pdftoppm checked). Composite 66/100.

Working files under `agents/geo/humnutrition/`:
- `humnutrition-audit-2026-06-16.pdf` / `.html`, the deliverable
- `recon-2026-06-16.md`, full recon notes and evidence
- `truth-table-raw.csv`, frozen catalog (37 products, price/availability/rating/reviews)
- `engine-battery-2026-06-16.md`, live engine captures

Final scorecard: Discoverability 75, Quotability 85, Recommendability 47, Transactability
55, Reputation 68, composite 66. Seven engines measured (all but Amazon Rufus, human-only);
they agree, so the shape is solid. Agentic-commerce surfaces validated exhaustively by curl
(36 candidate paths, all genuine 404s; apex 301-redirects to www).

## What recon found (this is the inverse of Good Molecules)

- **AI crawlers are allowed; Bingbot is blocked.** GPTBot, OAI-SearchBot, ChatGPT-User,
  ClaudeBot, Claude-User, PerplexityBot, Perplexity-User, Amazonbot, Applebot all get
  200 with the full page. Bingbot gets a deterministic 403 at the Cloudflare edge, on
  every path and on apex plus www. The one closed channel is Bing, which feeds Microsoft
  Copilot and parts of Bing's answer surface.
- **Schema is a strength.** PDPs are server-rendered (Astro) and carry well-formed
  Product, Offer (price, currency, priceValidUntil, InStock, return policy),
  AggregateRating, FAQPage, and BreadcrumbList in raw HTML, with canonical
  `https://schema.org` context and correct `Product` casing. This is exactly what Good
  Molecules got wrong, done right here. Plus OpenGraph product meta in source.
- **Agentic-commerce surfaces are all absent.** No llms.txt, agents.md, or any
  `/.well-known/*` (ucp, agent.json, ai-plugin.json, mcp.json). No agent can discover or
  buy on-site. Milder than the usual version of this finding because the product data an
  agent needs is already clean.
- **Strong, deep review corpus.** Ratings 4.2 to 4.75 across the catalog; several
  products over 1,000 reviews (Flatter Me 2,869, Daily Cleanse 2,493). Material for
  Reputation and Recommendability.

## Phase 2 live testing, open engines (June 16, 2026)

Ran headed (Cloudflare blocks headless on Perplexity and Google). Captures in
`agents/geo/humnutrition/engine-battery-2026-06-16.md`. Engines: Perplexity, Google AI
Overviews, Google AI Mode. The thesis held: HUM is readable but under-recommended.

- Quotability confirmed strong. Direct brand queries on all three engines read
  humnutrition.com, cite it, and get price and ingredients right (Collagen Love $40,
  ~$34 Amazon/subscription, grass-fed beef collagen + vitamin C + hyaluronic acid).
- Recommendability is the gap. "Best collagen supplement" and "best hair supplement"
  omit HUM on every engine and return Vital Proteins, California Gold Nutrition,
  Transparent Labs, Ancient Nutrition, Nutrafol, Viviscal, drawn from Rolling Stone, GNC,
  iHerb, Health.com roundups. Google AI Overview also repeats a "capsules underdose vs
  powder" frame that works against HUM's collagen specifically.
- Reputation is mixed and the engines reflect it. Trustpilot 1.8/5 over 72 reviews
  (claimed), BBB A- not accredited, against strong on-site reviews (4.2 to 4.75, thousands).
  Engines synthesize "legit yes, essential no": well-tested and clean-label, but pricey
  with subscription and service complaints.

Provisional scorecard (open-engine pass only, NOT final): Discoverability ~74,
Quotability ~85, Recommendability ~48, Transactability ~55, Reputation ~68, composite
about 66. Same ballpark as Good Molecules, opposite shape.

Operator engines captured June 16 in the headed browser (Armaan signed in): ChatGPT,
Copilot, Claude, Gemini. All seven measured engines confirm the split. Two nuances:
Claude got the facts right but cited retailers (Grove, Amazon, Fortune), not HUM's own
page, despite ClaudeBot being allowed to crawl the site; Gemini refused the category
question on safety grounds, so it is not a supplement-recommendation surface at all.
Copilot reached HUM despite the Bingbot block, so that finding is milder than recon
implied. Only Amazon Rufus remains unmeasured (human-only, Amazon blocks crawlers).

## Provisional audit thesis (confirmed in open-engine testing)

Fundamentals are good: open to AI assistants' crawlers, clean server-side schema, deep
real reviews. The story is "readable but under-recommended," not "invisible." The repairs
are concrete: reopen Bingbot at the Cloudflare WAF, get HUM into the third-party category
roundups the engines cite, add agentic-commerce surfaces. Score honestly; the refund
clause makes an inflated number a liability.
