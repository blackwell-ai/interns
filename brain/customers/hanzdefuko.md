# Hanz de Fuko

Premium men's hair styling and grooming brand (hanzdefuko.com), known for Quicksand
(a matte molding paste) and Claymation (clay). Shopify store, sold direct and
through Amazon, Ulta, and Sephora. Cold prospect, audited by the GEO agent
2026-06-25. No engagement or contact established yet.

Last updated 2026-06-25. Sources: full nine-phase AI visibility audit
(`skills/ai-visibility-audit/`), all artifacts under `agents/geo/hanzdefuko/` and
dated 2026-06-25. Evidence gate PASS
(`./skills/ai-visibility-audit/verify-evidence.sh agents/geo/hanzdefuko`).

## Scorecard: composite 76, grade B

Discoverability 66, Quotability 74, Recommendability 78, Transactability 88,
Reputation 74. A strong brand whose one real deficit is the homepage entity.
Competitive set (estimates from same-day signals): Baxter ~74, American Crew ~78,
Reuzel 79 (from our full Reuzel audit). Hanz sits mid-pack in a strong set.

## Findings (verified 2026-06-25)

- **Discoverability 66 (the gap).** Homepage JSON-LD is only `WebSite` +
  `SearchAction`; no `Organization` or `Brand` entity, no `sameAs`. Engines name
  Hanz, but the brand has no machine-readable identity to resolve reputation to.
  All seven AI bots return 200. This is the flagship finding and the anchor for the
  rest.
- **Recommendability 78 (strength).** Verified live with the six-engine two-pass
  battery (`battery-log.md`). Claymation is named in five of six engines and is
  ChatGPT's outright top pick ("the best all-around men's hair clay"); Google AI
  Overview names "Hanz de Fuko Claymation for all-around versatility." The one clean
  miss is Perplexity in incognito (named Layrite, American Crew, Suavecito). The
  gap is source authority in the guides Perplexity cites.
- **Quotability 74.** The Quicksand PDP serves `Product` + `AggregateOffer` +
  `AggregateRating` in raw HTML, so the rating is machine-readable, a step ahead of
  Reuzel. But it is served twice (two `Product`, two `AggregateRating` blocks), the
  duplication that lowers an engine's confidence in the canonical record.
- **Reputation 74.** Amazon 4.3 to 4.6, active Reddit (Claymation how-to, "still
  worth?"), deep YouTube corpus. But Trustpilot is unclaimed (1 review), no BBB
  profile, and none of it is linked to a homepage entity.
- **Transactability 88 (strength).** Full Shopify agent stack live: `/.well-known/ucp`,
  `agents.md`, `llms-full.txt`, agentic-discovery sitemap, all 200.

## Deliverable

Deck: 14 pages, canonical house format (`template.html`), rendered via headless
Chromium; 0 em/en dashes in HTML and PDF; recommendability page carries the
six-engine table and the embedded Google AI Overview capture.

- Customer copy: `brain/customers/documents/hanzdefuko-audit.pdf`
- Working source: `agents/geo/hanzdefuko/hanzdefuko-ai-visibility-audit.html` (+ .pdf)

## Open items before it goes to anyone

- Human sign-off required (charter guardrail). Review task in `inbox/queue/`.
- Cold prospect, no contact captured. The pitch framing is "you are already
  recommended; let us make the brand the engines name machine-readable," which is a
  warmer open than the cold cosmetics audits.
- Gemini ran on the logged-in profile (no clean private mode), but hair clay is
  unrelated to prior audit searches so contamination risk is low; result consistent
  with the clean engines.
