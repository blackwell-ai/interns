# GhostBed

Direct-to-consumer cooling mattress brand, owned by Nature's Sleep LLC (Plantation,
FL), founded by Marc Werner. Sells mattresses, adjustable bases, and bedding on a
Shopify store at ghostbed.com, plus Costco and Amazon channels. Cold prospect,
audited by the GEO agent June 22, 2026. No engagement or contact established yet.

Last updated June 22, 2026. Sources: live site recon by the GEO agent (recon.sh,
curl, products.json and sitemap reads, view-source of the homepage and a product
page, direct probes of agents.md, llms.txt, /.well-known/ucp and the /api/ucp/mcp
endpoint) on June 22, 2026; AI-category and brand web searches the same day;
reputation corpus from Trustpilot, BBB, ConsumerAffairs, Amazon, Reddit, and the
major mattress-review publishers; competitor recon on saatva.com, purple.com, and
nectarsleep.com the same day.

## What GhostBed is

Cooling-first mattress brand, roughly a decade in market, homepage title "Shop
GhostBed: Luxury Cooling Mattresses & Bedding." Lineup is three tiers (Luxe,
Signature, Comfort), each in hybrid and memory-foam builds, plus RV, Massage, and a
Venus Williams Legend signature line. Catalog is about 40 products (39 in the
product sitemap, 44 on products.json page one), 429 /pages, 11 collections.
Distribution includes its own Shopify store, Costco, and Amazon. Pricing observed
on the Luxe Hybrid PDP ran $1,849 to $3,798 across variants.

## Audit findings (verified June 22, 2026)

This is close to the inverse of the Atlas case, and a sharper version of the
Reuzel/Eclipse pattern: GhostBed has strong commerce plumbing and decent product
schema, yet it is the least AI-visible brand in its competitive set. Every signal
below is externally reproducible.

- **Recommendability is the failing dimension (flagship), score 38.** Asked for the
  "best cooling mattress for hot sleepers 2026," "best online mattress brands 2026,"
  and "best mattress 2026," web-search-backed AI answers named Helix, Brooklyn
  Bedding, WinkBed, DreamCloud, Bear, Saatva, Nectar, Casper, Leesa, Purple,
  Amerisleep, Tempur-Pedic, and more. GhostBed appeared in none of the three,
  including the cooling query, which is its own homepage tagline. It surfaces only
  when the query already names it ("GhostBed vs Purple/Saatva"), where engines pull
  GhostBed's own comparison pages and Tom's Guide. That is brand defense, not
  discovery. Named competitors Saatva and Nectar are both in the open answers.

- **Reputation is weak and unlinked, score 48.** GhostBed's Luxe Hybrid PDP carries
  a first-party `AggregateRating` of 4.8 over 10,223 reviews. The open-web corpus is
  very different: Trustpilot 3.5/5 (172 reviews, 82% one-star all time; profile
  claimed Sept 2025, paid, responds, uses invitations), BBB GhostBed profile B+ /
  customer reviews 1.61/5 (36) / 87 complaints in 3 years, ConsumerAffairs 1.5/5
  (120, unclaimed), Sitejabber 1.0/5 (3). Editorial reviewers score the mattress
  well (Sleepopolis 4.6, Mattress Nerd 4.7, Mattress Clarity 4.1, NapLab 8.82/10);
  Amazon per-model 3.9 to 4.4. The `Organization` entity in GhostBed's own schema
  carries `sameAs: none`, so nothing links the brand to any of this or separates the
  GhostBed BBB entity (B+) from the parent Nature's Sleep LLC entity (A+). Sentiment
  split: negatives cluster on returns, restocking fees, 101-night-trial mechanics,
  and warranty/CS responsiveness, not the bed; Costco-channel buyers skew positive.
  No verifiable Google rating widget was found; the "13,000+ reviews / 86% five-star"
  figure that circulates traces to GhostBed marketing, not an independent Google
  score, so do not cite it as Google.

- **Homepage is strong for humans, blank for machines, Discoverability 64.** Title,
  meta description, and OG/Twitter cards are present and descriptive. But the
  homepage renders zero JSON-LD (no `Organization`, `WebSite`, `SearchAction`, or
  `Brand`), has no server-rendered `h1`, and the body is JavaScript-required (the raw
  HTML carries a "requires JavaScript" notice and a near-empty shell). All major AI
  crawlers reach the site cleanly: GPTBot, ClaudeBot, PerplexityBot, OAI-SearchBot,
  Google-Extended, and Amazonbot each returned 200 on a product page
  (meta-externalagent returned a transient 429). Purple, by contrast, ships
  `Organization` + `Brand` + `WebPage` + `ItemList` + `ContactPoint` on its homepage.

- **Content exists but is hidden from engines, Discoverability/Quotability.** 429
  /pages including 36 head-to-head "vs" comparison pages (ghostbed-vs-saatva,
  -casper, -helix, -brooklyn-bedding, both /pages/ghostbed-vs-saatva-mattress-review
  and the Purple equivalent resolve 200) and roughly 86 buying-guide pages. None
  carry `Article` or `FAQPage` schema; the blog sitemap has 1 article; and the
  llms.txt, by its own text, only "mirrors" agents.md (the agent transaction file)
  rather than mapping the content.

- **Product schema is strong; the surrounding entity/policy schema is missing,
  Quotability 70.** Luxe Hybrid PDP renders `Product`, seven `Offer` blocks with
  price and `InStock` availability, plus `AggregateRating`, `Review`, and `Rating`,
  all server-side. Missing: `WebSite`/`SearchAction`, `BreadcrumbList`, `FAQPage` on
  PDPs and policy pages. So an engine can read a GhostBed price but has no structured
  answer for the trial, warranty, or shipping terms.

- **Agent-commerce layer is the strength and ahead of the category, Transactability
  84.** Live UCP profile at /.well-known/ucp (version 2026-04-08; checkout,
  fulfillment, discount capabilities; canonical ghostbed.myshopify.com); /api/ucp/mcp
  responds over MCP/JSON-RPC (a bare tools/list is rejected pending the agent-profile
  handshake, which is by design); branded agents.md and llms.txt (HTTP 200);
  sitemap_agentic_discovery.xml present; Shop Pay buyer-approved checkout; Offer
  pricing machine-readable. Saatva, Purple, and Nectar expose none of this (no ucp,
  no agents.md, no llms.txt). Honest caveat: this is Shopify-platform-provided, not a
  GhostBed build, but it is live and correct, which is rare in the set.

## Scorecard

Discoverability 64, Quotability 70, Recommendability 38, Transactability 84,
Reputation 48. Composite 61, grade C. Competitive set estimates from same-day public
signals: Saatva ~74 (C), Purple ~70 (C), Nectar ~64 (C); set average ~70, so
GhostBed trails by about 9 points. GhostBed leads the entire set on Transactability
(84 vs ~46) and trails most on Recommendability (38 vs 76 to 90) and Reputation
(48 vs 68 to 84).

## Competitor recon (June 22, 2026)

- **Purple** (purple.com, Drupal, not Shopify): descriptive title, h1 1, strong
  homepage JSON-LD (`Brand`, `ContactPoint`, `ImageObject`, `ItemList`,
  `Organization`, `WebPage`). No agentic layer (no ucp/agents.md/llms.txt). Named in
  cooling and best-mattress answers.
- **Saatva** (saatva.com, not Shopify): thin homepage JSON-LD (Offer only; curl
  caught an "Instagram" title artifact, likely a social embed), h1 1. No agentic
  layer. Named as the top luxury/online pick across answers.
- **Nectar** (nectarsleep.com, Resident, not Shopify): descriptive title, h1 2, no
  homepage JSON-LD (shares GhostBed's gap). No agentic layer. Named as a best-online
  pick. Shows that category presence plus reputation can carry the AI recommendation
  even without homepage schema, which GhostBed lacks on both counts.

## Deliverable

Deck: 13 pages, house WeasyPrint format rendered via headless Chrome (WeasyPrint not
installed on this machine). Both dash gates clean (0 em/en dashes in HTML and in
extracted PDF text); 13-page visual QA clean.

- Customer copy: `brain/customers/documents/ghostbed-audit.pdf`
- Working source: `agents/geo/ghostbed/ghostbed-ai-visibility-audit.html` (+ .pdf)

## Open items before it goes to anyone

- Human sign-off required (charter guardrail). Review task posted at
  `inbox/queue/2026-06-22-review-ghostbed-audit-deck.md`.
- Re-verify the Amazon per-model star counts at delivery time (they were live DOM
  reads and move; Amazon's /product-reviews/ pages now gate behind sign-in).
- The live AI battery was run via web-search-backed retrieval, not a six-engine
  browser run with browsing-off and browsing-on passes. If this converts toward a
  pilot, run the full per-engine battery (ChatGPT, Perplexity, Gemini, Claude,
  Google AI Mode, Copilot) to put a real engine table in the Recommendability
  section, as the Reuzel deck did.
- No contact captured yet. Confirm whether this stays a cold prospecting audit or
  becomes a paid pilot, which changes the framing of the close.
