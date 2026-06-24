# Reuzel

reuzel.com, men's grooming and hair styling brand (pomades, tonics, shampoos,
beard care, tattoo aftercare), born out of the Schorem barbershop in Rotterdam.
Sold direct, through barbershops, and through retail (Amazon, Sally Beauty, Ulta,
and others). Shopify storefront (backing store `reuzelinc.myshopify.com`) behind
Cloudflare. Last updated June 22, 2026. Source: passive recon and the AI
visibility audit (see `agents/geo/reuzel/recon-2026-06-17.md` and the finalized
deck).

Engagement status: prospecting audit, not yet confirmed with Armaan. Same pattern
as Good Molecules and HUM Nutrition: the audit is a sales-and-credibility tool to
win an engagement, not a paid deliverable. No engagement letter. This file and the
recon were started June 17, 2026 at Armaan's request to audit reuzel.com.

## Audit status

Finalized for delivery, June 22, 2026. Composite 79/100 (Discoverability 80,
Quotability 70, Recommendability 76, Transactability 90, Reputation 78). Canonical
deliverable: `brain/customers/documents/reuzel-audit.pdf` (13 pages, house format,
Chrome print-to-PDF; zero em/en dashes in HTML and PDF text; 13-page rasterized
visual check clean). Working source: `agents/geo/reuzel/reuzel-ai-visibility-audit.html`.
This supersedes the June 18 draft (composite 80) at
`agents/geo/reuzel/reuzel-audit-2026-06-18.html` / `.pdf`. One gate remains before
it goes to the customer: final human approval (charter guardrail), tracked at
`inbox/queue/2026-06-18-review-reuzel-audit-deck.md`.

Engine battery: six engines captured, category query "best men's pomade for strong
hold", web search on. Five run June 18 (headed Chromium + stealth cleared the
Cloudflare walls, reused logged-in sessions); Microsoft Copilot added June 22
(guest mode, no login or CAPTCHA this time). Reuzel's flagship Extreme Hold Matte
is the top or matte pick in ChatGPT (cited reuzel.com), Google AI Overview, and
Claude. Perplexity surfaced only the Liquid Death collab; Gemini and Copilot
omitted Reuzel entirely (Copilot returned an Amazon-sourced shopping carousel
naming Uppercut, Brickell, Aveda). Brand query "Reuzel Blue pomade price" returned
correct $19.95 and cited reuzel.com. Read: recommended well in half the engines,
under-surfaced in the three that lean on third-party commerce and listicle data
(Gemini, Copilot, Perplexity); the schema and rating fixes address it. The June 18
draft revised Recommendability up to 80 on the five-engine read; the sixth engine
(a second clean miss) brought it back to 76 and the composite to 79. Honest move,
not a regression in the brand's actual position.

Search-off (from-memory / parametric) pass: attempted June 22 and left as a
documented limitation. Asked to answer from its own knowledge with web search off,
logged-out ChatGPT declined and grounded in live product data anyway. A clean
parametric read now needs logged-in sessions with the search tool toggled off, or
direct model API access. Not a blocker for delivery.

**Clean re-run, 2026-06-22 (resolves the contamination question).** The full
six-engine two-pass battery was re-run with in-app incognito/temporary/guest
sessions and passes the evidence gate
(`./skills/ai-visibility-audit/verify-evidence.sh agents/geo/reuzel` = PASS; see
`agents/geo/reuzel/battery-log.md`, captures dated 2026-06-22). Reuzel's
recommendability is genuine, not a logged-in artifact: ChatGPT in a Temporary Chat
makes Reuzel Extreme Hold Matte its outright top pick on the ON pass; Perplexity in
Incognito (no memory) names Reuzel's strong-hold pomade as a best pick and cites
reuzel.com (better than the earlier "only the Liquid Death collab" read); Copilot
as guest names it. The deck's Claude claim holds for the browsing-ON pass (web
retrieval surfaces Reuzel, cites reuzel.com) though Claude's parametric pass does
not name it. Two corrections for the deck: Google AI Overview is non-deterministic
for this query (Reuzel was absent from the AIO in one same-evening render and
present in another, so say "in some renders," not "the AIO pick"); and Gemini could
not be run clean (logged-in Rishi profile carries prior Reuzel searches), so its
mentions are discounted. Net: composite 79 / Recommendability 76 is justified, and
the gap is schema/aggregateRating, not basic recommendability.

Working files under `agents/geo/reuzel/`:
- `reuzel-ai-visibility-audit.html`, the finalized deck source (canonical PDF at
  `brain/customers/documents/reuzel-audit.pdf`)
- `reuzel-audit-2026-06-18.pdf` / `.html`, the superseded June 18 draft
- `recon-2026-06-17.md`, full recon notes and evidence
- `engine-and-reputation-2026-06-18.md`, UCP probe, reputation corpus, engine
  status, scorecard basis
- `truth-table-raw.csv`, frozen catalog (89 products, 130 variants)
- `assets/`, live captures: `pink-pdp-rating-rendered.png` (4.9-star / 168-review),
  six engine screenshots including `copilot-best-pomade-2026-06-22.png` and
  `chatgpt-loggedout-parametric-2026-06-22.png`

## What recon found (June 17, 2026)

Reuzel is the inverse of the prior two audits on agentic readiness. It runs on
Shopify and ships the full native agentic-commerce stack: `/agents.md`,
`/llms.txt`, `/llms-full.txt`, a UCP merchant profile at `/.well-known/ucp`
(version 2026-04-08), a UCP MCP endpoint, an agentic discovery sitemap, and
`/products.json`. Every AI crawler gets 200, Bing included. Crawlability and
Transactability are effectively solved by the platform.

The findings are on the dimensions Shopify does not auto-solve:

1. Brand mislabeled in schema. The Product JSON-LD `brand` is "reuzelinc" (the
   myshopify slug), while the Organization blocks correctly say "Reuzel". The page
   contradicts itself on the brand entity, an entity-resolution risk.
2. No aggregateRating in the server-rendered schema, despite four review apps
   (Okendo, Yotpo, Loox, Judge.me) loaded client-side. The social proof is
   invisible to non-JavaScript crawlers. This is the central Quotability and
   Reputation finding, and it is fixable.
3. Review-app bloat: four UGC apps on one PDP; only one is plausibly canonical.
4. Catalog metadata gap: 49 of 89 products have an empty product_type.
5. Minor: Product schema uses http (not https) @context; duplicated/malformed
   sameAs in the two Organization blocks.

Catalog is healthy: 118 of 130 variants in stock, retail styling line $11 to $23,
flagship pomades (Pink, Blue, Red, Green grease/water-based, plus matte clays) all
$19.95 to $22.95.

## Entity context (for the reputation phase)

Schorem (the Rotterdam barbershop) heritage is a real entity-strength asset; the
brand and shop have a large YouTube and social following. Confirm in phase 2 that
the engines associate Reuzel with that heritage and recommend it in men's-pomade
category queries against Suavecito, Layrite, Baxter of California, American Crew,
and Imperial.

## Related

Methodology: `brain/company/audit-methodology.md`. Sibling DTC audits with the
opposite agentic-readiness profile: [[good-molecules]] (WAF-blocked, broken
schema), [[humnutrition]] (clean schema, no agentic surfaces). ICP fit:
[[targets.md]] segment 2 (DTC brands on Shopify).
