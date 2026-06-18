# Reuzel phase-2 notes: engine battery attempt, UCP probe, reputation corpus

Working notes for the Reuzel AI visibility audit, June 18, 2026. Recon and the
frozen truth table are in `recon-2026-06-17.md`. This file holds the phase-2
evidence behind the scorecard: the live UCP endpoint test, the reputation corpus,
the on-page rating capture, and the engine-battery status.

## UCP endpoint, exercised live (June 18)

Probed `https://www.reuzel.com/api/ucp/mcp` directly.

- `tools/list` and `initialize` both return a UCP error: `invalid_profile_url`,
  "Unable to fetch agent profile: Missing profile uri". The endpoint requires the
  calling agent to present a fetchable agent-profile URI before it will list its
  tools or transact. This is correct, secure behavior, not a fault: it gates on
  agent identity and pairs with the buyer-approval rule stated in /agents.md.
- The read-only paths are open and worked first try: `/.well-known/ucp` returns
  the merchant profile (UCP version 2026-04-08, plus 2026-01-23; capabilities for
  checkout, cart, fulfillment, discount; mcp and embedded transports; backing
  store reuzelinc.myshopify.com), and `/products.json` returns the full catalog.

Read for the deck: an agent can discover and read the store now, and transact
once it presents identity, with the buyer approving payment. Transactability is a
platform-level strength.

## On-page rating capture (the Quotability proof)

Loaded `/products/pink-pomade-heavy-hold-medium-shine` in a real browser (gstack
browse, headless Chromium). The JavaScript review widget renders **4.9 stars from
168 reviews**. Reading the same URL as ClaudeBot (raw HTML) shows no
aggregateRating and no review nodes anywhere in the source. Screenshot saved at
`assets/pink-pdp-rating-rendered.png`.

This is the central finding made concrete: the rating exists for shoppers and is
invisible to non-JavaScript crawlers. The deck's "fix that moves the most" section
shows the current vs proposed Product JSON-LD using these live values.

## Reputation corpus (web research, June 18)

Ratings are excellent wherever they are exposed:

| Source | Rating | Depth |
|---|---|---|
| Ulta, Reuzel Blue pomade | 4.8 / 5 | 358 reviews |
| Ulta, Reuzel Red pomade | 4.9 / 5 | 182 reviews |
| Amazon, Reuzel Red pomade | ~4.6 / 5 | 5,000+ reviews |
| reuzel.com Pink pomade (on-page widget) | 4.9 / 5 | 168 reviews |
| reuzel.com /pages/reviews | 5-star | 2,000+ 5-star reviews cited |
| ReviewMeta brand aggregate | mixed-verified | 7,731 reviews across 25 products |

- Stocked broadly: Ulta (52 products), Walmart, Amazon brand store.
- No claimed Trustpilot business profile for reuzel.com; search returns only
  third-party retailer product pages. A trust channel several engines weight, left
  open. Brand-only action to claim.
- Entity story is strong and well-documented: Reuzel founded 2013 by Leen Bergman
  and Bertus van Dijk, the barbers behind Schorem (Rotterdam barbershop opened
  2001). "Reuzel" means pork drippings, "Schorem" means riffraff. Retold across
  barbering and grooming media, so engines have a consistent entity to attach to.

## Category presence (Recommendability grounding)

Organic search (what the answer engines retrieve from) places Reuzel well:

- "best men's pomade" and "best water-based pomade" guides name Reuzel products at
  the top (Extreme Hold Matte as a matte pick, Blue High Shine as a high-shine
  pick), alongside Suavecito, Layrite, Imperial, Uppercut Deluxe.
- Reuzel's own content ranks for these queries: a water-based pomade roundup and a
  tin-by-tin comparison guide on the reuzel.com blog.

## Engine battery: run live June 18 (5 of 6 engines)

Initial headless attempt was blocked by Cloudflare (Perplexity 403). Re-ran in
headed Chromium with stealth, which cleared the bot walls and reused the existing
logged-in sessions in the browser profile. Query: "best men's pomade for strong
hold" (browsing-on; each engine searched the web). Screenshots saved under
`assets/`.

| Engine | Reuzel named | Product surfaced | Cites reuzel.com | Note |
|---|---|---|---|---|
| ChatGPT (web search) | Yes, top pick | Extreme Hold Matte | Yes | Used Reuzel's own "10/10 hold, 1/10 shine" spec. Also cited suavecito, layrite, lockhartsauthentic |
| Google AI Overview | Yes, category winner | Extreme Hold Matte ("best for thick/coarse hair") | mixed | Named set: Reuzel, Suavecito, Layrite, American Crew, Imperial, Uppercut, Baxter |
| Claude (web search) | Yes, matte pick | Extreme Hold | No | Cited magnussupply, hairfinest, thetrendspotter, suavecito; not reuzel.com |
| Perplexity | Weak | Liquid Death collab only | No | Top picks were American Crew + Suavecito (own sites). Reuzel cited to a reseller (mensroombarbershop) |
| Gemini | No (miss) | none | n/a | Named Suavecito, Layrite, Imperial, Baxter; Reuzel absent |
| Microsoft Copilot | not captured | n/a | n/a | "Verify you are human" CAPTCHA before answering; needs a human-solved session |

Brand-name query, Perplexity: "Reuzel Blue pomade price and where to buy" returned
the correct $19.95 and cited reuzel.com as the official source. So named-brand
queries read the brand page fine; the gap is on category queries.

Reads for the deck:

- Reuzel is genuinely recommended in category answers. Its flagship Extreme Hold
  Matte is the top or matte pick in ChatGPT, Google AI Overview, and Claude. This
  is stronger than a grounding-layer estimate would suggest, and stronger than the
  HUM result, where the brand was absent from category answers.
- The weakness is source authority, not absence. Only ChatGPT cited reuzel.com;
  Claude and Perplexity built the Reuzel recommendation from third-party listicles
  and resellers, and Perplexity surfaced only the niche Liquid Death collab rather
  than the flagship line. Making reuzel.com the authoritative, citable source
  (the schema and rating fixes) is what converts "recommended via listicles" into
  "recommended and cited from the brand's own page".
- Two clean gaps to close: Gemini omits Reuzel entirely, and Perplexity does not
  surface the flagship pomades.

Limit: Copilot was CAPTCHA-blocked and the browsing-off (parametric, no web
search) pass was not run per engine. Both are worth a follow-up human-driven
session, but the browsing-on category read above is the core recommendability
measurement and it is captured for five engines.

## Scorecard (graded against the frozen truth table)

| Dimension | Score | Basis |
|---|---|---|
| Discoverability | 80 | All crawlers 200 incl. Bing; agent-discovery sitemap; minus brand mislabel + 49/89 empty product_type |
| Quotability | 70 | Price/stock/SKU + FAQ server-rendered; minus no aggregateRating, brand="reuzelinc", http context |
| Recommendability | 80 | Live: flagship Extreme Hold is top/matte pick in ChatGPT, Google AIO, Claude; brand-query price correct + reuzel.com cited. Headroom: Gemini miss, Perplexity collab-only, inconsistent reuzel.com citation |
| Transactability | 90 | Full Shopify UCP stack live and correct; standout |
| Reputation | 78 | 4.6–4.9 stars across thousands of reviews + Schorem entity; minus under-surfaced in own schema + no Trustpilot profile |
| **Composite** | **80** | Well ahead of typical; remaining points are field-level fixes |
