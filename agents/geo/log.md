# GEO agent log

## 2026-06-17 — Good Molecules before-benchmark recon (first weekly check-in)

Customer: Good Molecules. Phase: implementation engagement, baseline re-check ahead
of the first weekly call. Deliverable:
`agents/geo/good-molecules/before-benchmark-recon-2026-06-17.md`. Customer brain
updated with a dated recon section.

Trigger: customer reported two changes since the June 1 audit (initial WAF rule
edits, server-side structured data) "for a more useful before benchmark." Ran
passive recon (curl with each crawler's published UA) to verify.

Findings:
- WAF Critical finding remediated for the major assistants: GPTBot, OAI-SearchBot,
  ChatGPT-User, ClaudeBot, Claude-User, PerplexityBot all 200 (blocked at audit).
  Open: Perplexity-User still 405; spoofed Googlebot/Bingbot 405 (flag to confirm
  verified search crawlers still pass, since search-index surfaces were the working
  channel at audit).
- Structured-data Critical finding (02) remediated: PDPs serve server-side JSON-LD
  Product/Brand/Offer (price, USD, InStock)/AggregateRating. Canonical PDP resolves
  to size-specific URL, addressing the 12ml/30ml price-confusion finding too.
- Bonus: rich llms.txt now live (absent at audit).
- Still 404: llms-full.txt, agents.md, /.well-known/ endpoints, sitemap.xml.

Framing for the engagement: customer pre-remediated the two heaviest findings
before a clean baseline, so re-baseline the "before" on today's live state and
measure remaining work against it. The real before benchmark is the live engine
battery (headed, by hand) against the frozen truth table, next step, not yet run.

Follow-up same day (kickoff prep, per Armaan): full server-side structured-data
teardown across 10 PDPs + homepage + category page, since the June 1 audit's
"missing structured data" picture is now outdated. Schema is real and
server-rendered but minimum-viable and uniform catalog-wide. Live: Product
(name/image/description/brand), Offer (price/currency/availability/condition),
AggregateRating, OnlineStore node. Gaps, ranked: no product identifiers
(sku/gtin/mpn, the retailer-reconciliation join key, root of the price-substitution
finding); no ProductGroup/variant size modeling; Offer missing shipping/return/
priceValidUntil/url; no Review objects; thin homepage entity schema (no sameAs);
no breadcrumbs/ItemList/OG-product meta; sitemap.xml 404 and llms-full/agents.md/
.well-known still 404; no FAQPage. Deliverable: kickoff brief with a worked
before/after Product JSON-LD example and a week-one plan (we draft schema templates,
customer supplies GTINs/return text and deploys). File:
`agents/geo/good-molecules/kickoff-week1-2026-06-17.md`. No engine battery run, per
Armaan.

## 2026-06-16 — HUM Nutrition audit, phases 1 and 2 (open engines)

Customer: HUM Nutrition (humnutrition.com), new. Phase: recon, truth-table freeze, and
the open-engine live battery. Working files under `agents/geo/humnutrition/`
(`recon-2026-06-16.md`, `truth-table-raw.csv`, `engine-battery-2026-06-16.md`); customer
brain at `brain/customers/humnutrition.md`.

Work done:
- Passive recon. HUM is the inverse of Good Molecules: AI crawlers all allowed (GPTBot,
  OAI-SearchBot, ClaudeBot, PerplexityBot, etc. all 200), Bingbot blocked with a
  deterministic 403 at the Cloudflare edge. Schema is a strength: server-rendered Astro
  with canonical, well-formed Product/Offer/AggregateRating/FAQPage/MerchantReturnPolicy
  and OpenGraph product meta in raw source. Agentic-commerce surfaces all absent (no
  llms.txt, agents.md, or /.well-known/*).
- Truth table frozen before any engine query: 37 PDPs, prices $12 to $60, on-site ratings
  4.2 to 4.75, several products over 1,000 reviews.
- Open-engine battery (headed, Cloudflare blocks headless): Perplexity, Google AI
  Overviews, Google AI Mode. Quotability strong (engines read humnutrition.com, cite it,
  facts right). Recommendability is the gap (HUM absent from collagen/hair/skin category
  answers, which return Vital Proteins, California Gold, Nutrafol, etc. from third-party
  roundups). Reputation mixed (Trustpilot 1.8/72, BBB A- not accredited, vs strong on-site).
- Provisional scorecard (NOT final): Disc ~74, Quot ~85, Rec ~48, Trans ~55, Rep ~68,
  composite about 66. Score honestly per the refund clause.

Operator engines (run same day in the headed browser, Armaan signed in): all of ChatGPT,
Copilot, Claude, and Gemini captured. ChatGPT/Copilot/Gemini read humnutrition.com and got
facts right; Claude got facts right but cited retailers (Grove, Amazon, Fortune) not the
brand's own page; Gemini refused the category question on safety grounds. Every engine that
recommends omits HUM from the collagen category. Copilot reached the brand despite the
Bingbot block, so that finding is milder than recon implied. Seven engines measured and
consistent; only Amazon Rufus unmeasured (human-only).

Agentic-commerce files validated exhaustively by curl per Armaan: 36 candidate paths
(llms, agents, all /.well-known variants, ucp/acp/ap2/mcp), every one a genuine 404; apex
301-redirects to www; positive surfaces (server-rendered Product/Offer/AggregateRating/
FAQPage, OG meta, AI-crawler 200s, Bingbot 403) reconfirmed.

Deck built and validated the same day: `agents/geo/humnutrition/humnutrition-audit-2026-06-16.pdf`
(12 pages, house WeasyPrint format, zero em/en dashes, pypdf + pdftoppm checked). Final
scorecard Disc 75 / Quot 85 / Rec 47 / Trans 55 / Rep 68, composite 66. Posted for human
sign-off at `inbox/queue/2026-06-16-review-humnutrition-audit-deck.md` per the charter
guardrail.

Open follow-ups: Armaan reviews the deck; decide whether to re-run Claude/Gemini/Rufus
manually before delivery; confirm HUM engagement and pricing stage. If HUM closes a Phase 1,
this is the second audit run end-to-end under the charter, so codify the flow as
`skills/ai-visibility-audit/` per the charter's "Codify the flow."

## 2026-06-11 — Husqvarna follow-up meeting prep

Customer: Husqvarna. Phase: post-audit follow-up (converting engineer
critiques into Phase 1). Deliverable:
`agents/geo/husqvarna/husqvarna-followup-2026-06-11.md`.

Work done:
- Designed 12-prompt Amazon Rufus battery; analyzed Armaan's manual run of
  prompts 1–4 (Amazon blocks crawlers — human-only surface).
- Deep PDP review of 410/420/440 iQ (curl + JSON-LD extraction): schema gaps
  reproduce, price absent from rendered text, no checkout, under-trees
  objection unanswered on-page; NEW FAQPage schema found.
- Re-verified agent endpoints (403), bot parity (clean), old-model pages
  (430X support page still serves Product schema; 450X/450XH live).
- Corrected BBB pull for the entity registered to husqvarna.com/us: A+ /
  1.03/5 (58 reviews) / 204 complaints 3yr. Engineers' critique absorbed;
  finding stands.
- Live Trustpilot read via /browse headed mode (Cloudflare bypassed): 1.4/872,
  81% one-star, still unclaimed.
- Background research: answer-engine citation behavior briefing (saved to
  brain/research/answer-engine-citation-behavior.md) and a named
  correction-target list (18 listicles, comparison cluster, Reddit, YouTube).
- Scorecard movement: n/a (no re-benchmark this session).

Durable updates: brain/customers/husqvarna.md (June 11 re-verification
section), brain/research/answer-engine-citation-behavior.md, charter guardrail
on capability-honest scope tiers.

Open follow-ups: Rufus prompts 5–12 (Armaan, manual); seller-of-record
capture on Amazon listings; if Phase 1 closes, codify the audit flow as
skills/ai-visibility-audit/ per the charter.

## 2026-06-11 — Follow-up meeting held (Armaan)

Positive reception of the audit. Asks captured and shipped same day in the
revised brief: Amazon testing detail, content-first proposals (worked
trees-FAQ + description drafts), per-page PDP updates from public data,
engagement terms. Husqvarna is sending a product feed with detailed PDPs
across the catalog — next session should ingest it, run the page checks
feed-wide, and extend the proposals. Rufus prompts 5-12 still open.

## 2026-06-12 — Product feed received; Husqvarna files reorganized

The catalog feed arrived: 1,254 products with full PDP fields (title,
description, URL, category, price, and per-star review counts). Filed at
`agents/geo/husqvarna/husqvarna-product-feed-2026-06-11.csv`. Consolidated all
Husqvarna GEO working files under `agents/geo/husqvarna/` (followup deck set,
FAQ screenshots, and the feed); `AGENT.md` and this log stay at the geo root.
Next session ingests the feed, runs the page checks feed-wide, and extends the
PDP proposals across the catalog.
