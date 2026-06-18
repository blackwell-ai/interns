# Atlas Skateboarding

San Mateo, CA skate shop and art gallery, open since May 2007. Shopify store
at atlasskateboarding.com. Sibling shop to DLX (same owner). Warm prospect
sourced by Ethan.

Last updated June 16, 2026. Sources: live site recon by GEO agent (curl, sitemap
and products.json reads, view-source) on June 16, 2026; AI-category and reputation
web searches (Yelp, Birdeye, Nike SB and Vans locators, the California.com
listicle); the DLX audit of June 9, 2026; web search on Tactics' ownership and
store closures; founder context from Ethan on the owner conversation.

## Relationship

Ethan met the owner (who runs both DLX and Atlas) the week of June 8, 2026 and
prepared a DLX website visibility audit (June 9, the lighter surface-level house
format, not the heavy 9-phase deck). In that conversation the owner asked Ethan
to look at Atlas, described as the main shop, and said the concerns are mainly
traffic, with plans to run Meta ads later and a wish for help beyond SEO and GEO.
The owner named the skate shops doing well as benchmarks: CCS (shop.ccs.com),
Tactics (in financial trouble), and Labor (laborskateshop.com).

Engagement letter drafted June 17, 2026: Atlas only, $1,000 paid upfront and
refunded if benchmarks are not met, scope is the audit's Phase 1. Not yet sent or
signed. DLX would get its own letter later (Ethan chose Atlas-only for now). The
audit was the prospecting artifact; this is the close. Verify status before
citing externally.

## Contacts

- Owner of DLX and Atlas (name not yet on record). Single decision maker across
  both shops. Ethan owns the relationship; the DLX and Atlas audits both list
  ethanpzhou@berkeley.edu as contact.

## Documents

- Engagement letter (Atlas only, $1,000, drafted June 17, 2026, not yet signed):
  [documents/atlas-engagement-letter.pdf](documents/atlas-engagement-letter.pdf).
  Working source: `agents/geo/atlas/atlas-engagement-letter.html`. One page,
  modeled on the Public Goods June 2 letter; scope is the audit's Phase 1, terms
  are the standard refundable pilot. Blackwell signatory is Ethan Zhou (Founder),
  with ethanpzhou@berkeley.edu as the contact since Ethan owns this relationship
  (a departure from the usual Armaan/Dartmouth address on letters); customer
  signature block left blank for the owner.
- Atlas audit deck (canonical): [documents/atlas-audit.pdf](documents/atlas-audit.pdf),
  the repo's heavy AI Visibility Audit format (13 pages, five AI-behavior
  dimensions, sans-serif house style like Public Goods and Husqvarna). Working
  source: `agents/geo/atlas/atlas-ai-visibility-audit.html` (Chrome headless render).
- Superseded: a lighter DLX-style version was built first
  (`agents/geo/atlas/atlas-audit.html`, 4 pages; `-full.html`, 10 pages). Ethan
  asked for the heavier repo format instead, so the light PDFs were pulled from
  distribution. The HTML sources stay for reference.
- DLX audit (sibling, June 9): delivered as `~/Downloads/DLX Skate Shop ... .pdf`,
  not yet in the repo. No DLX brain file exists yet.

## Audit findings (verified June 16, 2026)

Atlas is the DLX pattern at nearly double the scale. Every signal below is
externally reproducible.

- **Homepage invisible**: `<title>Atlas</title>` (one word), empty meta
  description, zero `<h1>`, `og:image` declared over insecure `http://` (resolves
  200 on https). Zero homepage JSON-LD, so no Organization or LocalBusiness entity.
- **Catalog with no structured data**: 4,528 products (2,500 + 2,028 across two
  product sitemaps) and 106 collections, zero JSON-LD on product pages. No
  Product, Offer, or AggregateRating schema anywhere. Data exists in Shopify, just
  unexposed.
- **No machine-readable identity**: the about page tells the story (San Mateo,
  CA 94401, retail store and art gallery since 2007, "driven by passion over
  profit") but none of it is in schema. The name "Atlas" is highly ambiguous.
- **AI-commerce layer provisioned but empty**: generic Shopify boilerplate
  llms.txt (4.4 KB) and agents.md, plus a working `.well-known/ucp` endpoint and
  an agentic-discovery sitemap. Transaction layer works; identity and content
  layer is blank.
- **Under-leveraged assets**: three blogs (news, projects, videos) with roughly
  990 article URLs in the sitemap, carrying no Article schema and not wired into
  SEO. Real collab and artist content (Alien Workshop, Lakai, Stussy, Antihero).
- **Paid readiness (the Meta-ads ask)**: Google Ads (AW-841187191) and GA4
  (G-3PF1CHM497) are live, plus Klaviyo and Attentive. But no Meta pixel fires on
  the storefront; Shopify customer-events shows the Meta app slot present with an
  empty system-user token, so neither the browser pixel nor the Conversions API
  is sending events. Advantage+ and dynamic product ads need the clean product
  feed that the schema fix produces.

- **Recommendability (AI category answers)**: asked for the best Bay Area skate
  shops, AI answer engines returned DLX, FTC, SF Skate Club, 510, and Circle-A;
  Atlas was not named once. Atlas is also absent from the California.com "13 best
  Bay Area skate shops" listicle (which lists Skateworks in Los Altos and Circle-A
  in San Jose on the Peninsula). Competitors appear; Atlas does not. This is the
  flagship finding of the heavy deck.
- **Reputation (strong but stranded)**: 4.8 stars across 115 Birdeye reviews and
  135 on Yelp, an official Nike SB and Vans dealer, called "the best skate
  boutique along the peninsula." Address 209 2nd Ave, San Mateo CA 94401, open 11
  to 7 daily. But no Organization/LocalBusiness schema and no sameAs links, so the
  reputation is not connected to the entity and AI cannot attribute it. Atlas's
  best dimension, doing no work.

Scorecard, repo heavy format (five AI-behavior dimensions, like Public Goods):
Discoverability 50, Quotability 18, Recommendability 28, Transactability 60,
Reputation 62. Composite 44, grade F (competitive set CCS/Tactics/Labor averages
~79, B range). Note this is higher than the 29 the lighter DLX-style rubric gave,
because the heavy rubric credits Atlas's real reputation and working Shopify
transaction rails; the failing dimensions are quotability and recommendability,
both downstream of zero schema.

## Competitive set (verified June 16, 2026)

- **CCS** (shop.ccs.com, Shopify): descriptive title, Organization + WebSite +
  SearchAction entity schema, full Product + Offer schema on PDPs, meta present.
- **Tactics** (tactics.com, custom platform): the most complete. Organization +
  WebSite + SearchAction + ContactPoint entity schema, full Product + Offer +
  AggregateRating + Brand on PDPs, a live Meta pixel, Google Ads. Acquired out of
  Japanese ownership (TSI) by Lakai's owner in 2025, closed its Ballard, Seattle
  store February 2026, CFO departed. Plumbing stays intact under financial strain.
- **Labor** (laborskateshop.com, Shopify): descriptive title ("Labor Skateboard
  Shop | New York, NY"), entity schema, full Product + Offer + Brand on PDPs.

Atlas is the only one of the four empty on every machine-readable signal.

## Engagement framing

Two phases, matching the repo's heavy decks. Phase 1 is a 30-day stabilization
sprint at $1,000 upfront, refunded if benchmarks are not met (the standard pilot
price, see [[overview]] in `brain/company/`): title/meta/h1 templates, Product +
Offer schema across 4,528 products, Organization + LocalBusiness + sameAs linking
the entity to the 4.8-star reputation, llms.txt/agents.md content map with
agent-readable pricing, Article schema on the blog archive, and the Meta
pixel/Conversions API plus catalog feed for Advantage+. Phase 2 is ongoing AI
visibility work (monitoring, entity establishment, category-source placement),
scoped after Phase 1 benchmarks land.
