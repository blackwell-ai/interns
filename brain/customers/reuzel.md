# Reuzel

reuzel.com, men's grooming and hair styling brand (pomades, tonics, shampoos,
beard care, tattoo aftercare), born out of the Schorem barbershop in Rotterdam.
Sold direct, through barbershops, and through retail (Amazon, Sally Beauty, Ulta,
and others). Shopify storefront (backing store `reuzelinc.myshopify.com`) behind
Cloudflare. Last updated June 17, 2026. Source: passive recon for the AI
visibility audit (see `agents/geo/reuzel/recon-2026-06-17.md`).

Engagement status: prospecting audit, not yet confirmed with Armaan. Same pattern
as Good Molecules and HUM Nutrition: the audit is a sales-and-credibility tool to
win an engagement, not a paid deliverable. No engagement letter. This file and the
recon were started June 17, 2026 at Armaan's request to audit reuzel.com.

## Audit status

Drafted, June 18, 2026. Composite 80/100 (Discoverability 80, Quotability 70,
Recommendability 80, Transactability 90, Reputation 78). Deck rendered (13 pages,
house format) and validated (pdfinfo 13 pages letter, zero em/en dashes,
rasterized visual check). Posted for human sign-off at
`inbox/queue/2026-06-18-review-reuzel-audit-deck.md`.

Engine battery run live June 18 (headed Chromium + stealth cleared the Cloudflare
walls; reused logged-in sessions). Category query "best men's pomade for strong
hold", web search on, across five engines. Reuzel's flagship Extreme Hold Matte is
the top or matte pick in ChatGPT (cited reuzel.com), Google AI Overview, and
Claude. Perplexity surfaced only the Liquid Death collab and cited a reseller;
Gemini omitted Reuzel entirely. Brand query "Reuzel Blue pomade price" returned
correct $19.95 and cited reuzel.com. Read: the brand is recommended well; the gap
is source authority (engines cite listicles, not reuzel.com) plus Gemini/Perplexity
under-representation, which the schema + rating fixes address. Recommendability
revised 76 -> 80 on this live evidence; composite 79 -> 80.

Two follow-ups left, both need a human-driven session: Microsoft Copilot was
CAPTCHA-blocked ("verify you are human"), and the search-off (parametric) pass per
engine was not run.

Working files under `agents/geo/reuzel/`:
- `reuzel-audit-2026-06-18.pdf` / `.html`, the deliverable
- `recon-2026-06-17.md`, full recon notes and evidence
- `engine-and-reputation-2026-06-18.md`, UCP probe, reputation corpus, engine
  status, scorecard basis
- `truth-table-raw.csv`, frozen catalog (89 products, 130 variants)
- `assets/pink-pdp-rating-rendered.png`, live 4.9-star / 168-review capture

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
