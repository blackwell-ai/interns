# GEO agent log

## 2026-06-22: Reuzel audit finalized for delivery (Ethan's request)

Customer: Reuzel. Phase: prospecting audit, finalized. Closed the two open
follow-ups from the June 18 draft and rendered the canonical deliverable.
Deliverable: `brain/customers/documents/reuzel-audit.pdf` (13 pages, house format,
Chrome print-to-PDF). Working source: `agents/geo/reuzel/reuzel-ai-visibility-audit.html`.

Scorecard movement: composite 80 -> 79; Recommendability 80 -> 76; the other four
dimensions unchanged (Discoverability 80, Quotability 70, Transactability 90,
Reputation 78). The move is honest, not a position change: the sixth engine added
to the battery is a second clean category miss, so the dimension came down rather
than staying flat (refund-clause guardrail).

What got done this session:
- Microsoft Copilot captured (the named gap), via the Playwright browser in guest
  mode, web search on, no CAPTCHA this time. Query "best men's pomade for strong
  hold". Reuzel absent; Copilot returned an Amazon-sourced shopping carousel
  (Uppercut Deluxe top pick, then Brickell, Aveda, JVR, CrownNaturally). A second
  clean miss alongside Gemini, and consistent with the audit thesis: the engines
  that lean on third-party commerce data do not surface Reuzel, while the one that
  read reuzel.com (ChatGPT) ranked it first. Screenshot under `assets/`.
- Search-off (parametric) pass: attempted and left as a documented limitation.
  Logged-out ChatGPT refused a from-memory answer and force-grounded in live
  product data, so a clean parametric read needs logged-in sessions with the search
  tool off, or model API access. Captured the behavior (assets/) and wrote it into
  the deck's method section honestly rather than faking the pass.
- Deck updated (engine table now six rows, scorecard, narrative, method), rendered
  to the canonical path, and validated: zero em/en dashes in HTML and PDF text,
  13-page rasterized visual QA clean (cover date, scorecard, engine table, method
  all checked).
- Records: `brain/customers/reuzel.md` audit-status section rewritten;
  `inbox/queue/2026-06-18-review-reuzel-audit-deck.md` updated with the close-out.

Open: final human sign-off before this goes to the customer (the review task stays
in queue). At sign-off, confirm the engagement/pricing stage (still a prospecting
audit, no engagement letter) and the cover contact (currently Armaan's email).
Notion mirror pending (Notion MCP configured but not authenticated this session).
The June 18 draft (composite 80) is kept as history at
`agents/geo/reuzel/reuzel-audit-2026-06-18.*`.

## 2026-06-17 — Reuzel audit kickoff (recon + frozen truth table)

Customer: Reuzel (reuzel.com), men's grooming, Schorem barbershop heritage. Phase:
prospecting audit, phase 1. Deliverables: `agents/geo/reuzel/recon-2026-06-17.md`
and `truth-table-raw.csv` (89 products, 130 variants). New customer brain file
`brain/customers/reuzel.md`. Trigger: Armaan asked the GEO agent to audit
reuzel.com.

Headline: Reuzel is the inverse of Good Molecules and HUM on agentic readiness. On
Shopify, it ships the full native agentic stack live (/agents.md, /llms.txt, UCP
profile at /.well-known/ucp v2026-04-08, UCP MCP endpoint, agentic discovery
sitemap, /products.json) and lets every AI crawler in (all 200, Bing included).
Crawlability and Transactability are solved by the platform.

Findings sit on the dimensions Shopify does not auto-solve:
- Brand mislabeled: Product JSON-LD brand = "reuzelinc" (myshopify slug) vs
  Organization = "Reuzel". Entity-resolution risk (Discoverability/Recommendability).
- No aggregateRating in server-rendered schema despite four review apps (Okendo,
  Yotpo, Loox, Judge.me) loaded client-side — social proof invisible to non-JS
  crawlers. Central Quotability/Reputation finding, fixable.
- Review-app bloat (4 UGC apps on one PDP); catalog metadata gap (49/89 empty
  product_type); minor http (not https) @context and malformed sameAs.

Catalog healthy: 118/130 variants in stock, styling line $11–$23, flagship pomades
$19.95–$22.95.

Scorecard movement: n/a (no grading yet; truth table frozen for phase 2).

Open follow-ups (phase 2, needs /browse + human): two-pass engine battery across
six engines, reputation corpus (Reddit, YouTube, Amazon/retailer reviews,
Trustpilot), confirm canonical review app + real rating counts, grade five
dimensions, build deck. Confirm with Armaan whether to proceed.

## 2026-06-18 — Reuzel audit drafted (phases 2 onward, deck shipped to sign-off)

Customer: Reuzel. Phase: prospecting audit drafted. Deliverable:
`agents/geo/reuzel/reuzel-audit-2026-06-18.pdf` (12 pages, house format, Chromium
print-to-PDF; WeasyPrint not installed on this machine). Source HTML and evidence
files alongside. Posted for sign-off at
`inbox/queue/2026-06-18-review-reuzel-audit-deck.md`.

Composite 79/100: Discoverability 80, Quotability 70, Recommendability 76,
Transactability 90, Reputation 78. Reuzel is well ahead of HUM (66) and Good
Molecules because Shopify solved the hard infrastructure; the remaining points are
field-level content fixes.

Phase-2 work done this session:
- Exercised the UCP endpoint (/api/ucp/mcp) live. It enforces the agent-profile
  handshake before listing tools (correct, secure); read-only paths (/.well-known/ucp,
  /products.json) open and worked. Transactability is a platform strength.
- Live browser capture: Pink pomade PDP shows 4.9 stars / 168 reviews in the JS
  widget; the same page as ClaudeBot (raw HTML) has no aggregateRating. The central
  Quotability finding, made concrete (screenshot saved). Deck's "fix that moves the
  most" shows current vs proposed Product JSON-LD with these values.
- Reputation corpus: Ulta Blue 4.8/358, Ulta Red 4.9/182, Amazon Red ~4.6/5,000+,
  on-site 2,000+ 5-star, ReviewMeta 7,731/25 products; no claimed Trustpilot
  profile; Schorem entity story (founded 2013 by Bergman + van Dijk, shop opened
  2001). Strong reputation, under-surfaced in the brand's own schema.
- Recommendability grounded in organic search (engines retrieve from it): Reuzel
  named top in pomade roundups, own guides rank, competitive set is
  Suavecito/Layrite/Imperial/Uppercut.

Engine battery, run live same session (Armaan asked to run it): first headless
attempt was Cloudflare-blocked (Perplexity 403), so re-ran in headed Chromium with
stealth, which cleared the walls and reused the browser's logged-in sessions.
Category query "best men's pomade for strong hold", web search on, five engines:
- ChatGPT: Reuzel Extreme Hold Matte = top pick, cited reuzel.com (used the brand's
  own "10/10 hold" spec).
- Google AI Overview: Reuzel Extreme Hold Matte = category winner for thick/coarse.
- Claude: Reuzel Extreme Hold = matte pick, but cited listicles (magnussupply,
  hairfinest, thetrendspotter), not reuzel.com.
- Perplexity: weak; only the Liquid Death collab surfaced, cited to a reseller.
- Gemini: miss; Reuzel absent (named Suavecito, Layrite, Imperial, Baxter).
Brand query (Perplexity): "Reuzel Blue pomade price" returned correct $19.95, cited
reuzel.com. Read: Reuzel is recommended well (better than HUM, which was absent from
category answers); the gap is source authority (engines lean on listicles over
reuzel.com) plus Gemini/Perplexity under-representation. Revised Recommendability
76 -> 80, composite 79 -> 80; deck re-rendered to 13 pages with the live engine
table replacing the grounding-layer caveat. Screenshots saved under
agents/geo/reuzel/assets/. No engine output fabricated.

Roadblocks hit: Microsoft Copilot threw a "verify you are human" CAPTCHA before
answering (not captured); the search-off parametric pass per engine was not run.
Both need a human-driven session.

Durable updates: brain/customers/reuzel.md (audit status, scores, engine results),
agents/geo/reuzel/engine-and-reputation-2026-06-18.md (full battery table).

Open follow-ups: human sign-off on the deck; capture Copilot + the search-off pass
if wanted; confirm engagement/pricing stage; the audit flow has now run end-to-end
twice (HUM, Reuzel) and is ripe to codify as skills/ai-visibility-audit/ per the
charter.

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

## 2026-06-20 — Eclipse Sample Sales AI Visibility Audit (cold prospect)

Ran the full nine-phase audit on eclipsesamplesales.com (Shopify designer
sample sale brand, LA + NYC). Heavy house-format deck, 12 pages, Chrome
headless render. Scorecard: Discoverability 58, Quotability 68,
Recommendability 30, Transactability 72, Reputation 60. Composite 58, grade D
(competitive set 260 Sample Sale ~63, Rue La La ~77, Gilt ~76, averaging ~72).

The inverse of the Atlas case: Eclipse built genuinely good plumbing (full
homepage entity schema, full Product/Offer/Brand on PDPs, live UCP/MCP, real
agents.md) yet is still absent from AI category answers. 260 Sample Sale, the
peer AI names first, ships zero schema. So the gap is off-site authority and
linkage, not core schema. Flagship findings: not named in any genuine "best
online sample sale sites" query (only surfaces when the query echoes its own
tagline, citing the old shop.eclipse-official.com domain); brand split across
domains (eclipse-official.com 301s in, eclipsesamplesaleswear.shop is a
separate live lookalike); real reputation (96 Yelp reviews, repeated Time Out
LA coverage) stranded behind an empty `sameAs: [""]`; review apps (Okendo,
Loox, Yotpo) loaded but no AggregateRating in schema; llms.txt missing, h1
hidden, og:image over http; Meta Conversions API token empty.

Both dash gates clean (0 in HTML, 0 in PDF text); 12-page visual QA clean.
Deliverable: brain/customers/documents/eclipse-audit.pdf. Working source:
agents/geo/eclipse/eclipse-ai-visibility-audit.html. Findings: brain/customers/eclipse.md.
Cold prospect, no contact yet. Open items before sending: confirm the numeric
Yelp/Google star average, and verify whether eclipsesamplesaleswear.shop is a
sanctioned property or a third-party lookalike. Needs human review before it
goes to anyone.

## 2026-06-22 — GhostBed AI Visibility Audit (cold prospect)

Ran the full nine-phase audit on ghostbed.com (Shopify cooling-mattress brand,
owned by Nature's Sleep, Venus Williams signature line). Scorecard: Discoverability
64, Quotability 70, Recommendability 38, Transactability 84, Reputation 48.
Composite 61, grade C (competitive set estimates Saatva ~74, Purple ~70, Nectar ~64,
set average ~70).

Close to the inverse of Atlas and a sharper Reuzel/Eclipse: GhostBed runs the best
agent-commerce plumbing in its set and decent PDP schema, yet is the least
AI-visible brand in it. Flagship: asked for "best cooling mattress," "best online
mattress," and "best mattress 2026," web-search-backed AI named Helix, WinkBed,
Saatva, Nectar, Purple, Casper, DreamCloud and others; GhostBed appeared in none,
including the cooling query that is its own homepage tagline. It surfaces only when
the query already names it. Reputation is the second weakness: on-site first-party
4.8/10,223 diverges hard from the open web (Trustpilot 3.5 with 82% one-star, BBB
GhostBed 1.61 / 87 complaints, ConsumerAffairs 1.5), and the Organization entity
carries sameAs:none so nothing is linked. Homepage has zero JSON-LD and no server
h1; 36 vs-comparison pages and ~86 guides carry no Article/FAQPage schema and the
llms.txt only "mirrors" agents.md. Strength is Transactability: live UCP profile
(2026-04-08), MCP endpoint responding, agents.md/llms.txt/agentic-discovery sitemap,
none of which Saatva/Purple/Nectar expose.

Both dash gates clean (0 in HTML, 0 in PDF text); 13-page visual QA clean.
Deliverable: brain/customers/documents/ghostbed-audit.pdf. Working source:
agents/geo/ghostbed/ghostbed-ai-visibility-audit.html. Findings: brain/customers/ghostbed.md.
Cold prospect, no contact yet. Posted for human sign-off at
inbox/queue/2026-06-22-review-ghostbed-audit-deck.md per the charter guardrail.
Open before sending: re-verify Amazon per-model counts; decide whether to run the
full six-engine battery (browsing-off and browsing-on) before delivery; confirm
whether this stays a cold prospect or becomes a paid pilot.

---

## 2026-06-29 · Stream2Sea · full nine-phase audit

Customer: Stream2Sea (stream2sea.com), reef-safe mineral sunscreen and ocean-safe
body care, founder Autumn Blum. Cold prospect, requested by Armaan. Competitor set
chosen with founder: Raw Elements, Badger, Thinksport.

Scorecard composite 69 (C) against a set averaging 78 (Badger 79, Raw Elements 77,
Thinksport 77). Discoverability 68, Quotability 70, Recommendability 56,
Transactability 88, Reputation 62. The whole gap is Recommendability and Reputation,
not the plumbing.

Flagship finding is a memory/retrieval split surfaced by the full six-engine
two-pass battery (real /browse sessions, captured). From memory, ChatGPT and Claude
both name Stream2Sea and describe it accurately (Claude ranks it #3, "the standout
if you snorkel or dive"). In live retrieval it is named only by Claude and by
ChatGPT in 1 of 2 renders; absent in Perplexity, Copilot, Gemini, and the Google AI
Overview, where Project Reef and Badger dominate. The live answers draw on editorial
roundups (Treeline, NYT Wirecutter, Travel+Leisure, Good Housekeeping, Vogue,
Project Reef's blog) that under-feature Stream2Sea. Reputation is real but stranded:
Amazon flagship Water Sport SPF 30 over 1,000 ratings at 4.0 stars (Every Day Active
SPF 45 4.6/203), Trustpilot claimed but dormant (2 reviews), no BBB or
ConsumerAffairs, thin Reddit/YouTube, and homepage Organization entity has no
sameAs and no AggregateRating. Strength is Transactability: full Shopify UCP agent
layer live. Discoverability/Quotability are mid: all seven AI bots return 200,
product PDPs carry Product+Offer+Brand, but the homepage has no server-rendered
title (JS-injected; og:title present).

Battery note: ChatGPT initially stalled under anti-bot sentinel throttling on a slow
connection; resolved on retry once the connection recovered. Laptop died mid-run
after the ChatGPT on-pass; resumed, re-captured, finished all six engines.

Both dash gates clean (0 in HTML, 0 in PDF text); evidence gate PASS; 16-page visual
QA clean (one tight but non-overlapping line above the footer on page 14; fixed the
fixed-footer overlap that the template's bottom:0.34in caused on full content pages
by moving the footer to bottom:0.0in). Deliverable:
brain/customers/documents/stream2sea-audit.pdf. Working source:
agents/geo/stream2sea/stream2sea-ai-visibility-audit.html. Findings:
brain/customers/stream2sea.md. Posted for human sign-off at
inbox/queue/2026-06-29-review-stream2sea-audit-deck.md per the charter guardrail.
Open before sending: confirm cold prospect vs paid pilot, add a real contact.
