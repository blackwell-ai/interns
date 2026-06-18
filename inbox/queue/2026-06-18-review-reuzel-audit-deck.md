---
title: Review Reuzel AI visibility audit deck before delivery
created: 2026-06-18
created_by: geo
assignee: armaan
priority: normal
claimed_by:
claimed_at:
---

## Task

The Reuzel (reuzel.com) AI visibility audit is drafted and needs a human review
before it goes to the customer (charter guardrail: no GEO deliverable ships
without sign-off).

Draft deck (12 pages, house format, Chromium print-to-PDF since WeasyPrint is not
installed on this machine):
`agents/geo/reuzel/reuzel-audit-2026-06-18.pdf`
Source HTML: `agents/geo/reuzel/reuzel-audit-2026-06-18.html`

Supporting evidence and working files:
- `agents/geo/reuzel/recon-2026-06-17.md` (crawler access, schema, agentic stack)
- `agents/geo/reuzel/truth-table-raw.csv` (frozen catalog, 89 products / 130 variants)
- `agents/geo/reuzel/engine-and-reputation-2026-06-18.md` (UCP probe, reputation corpus, engine-battery status, scorecard basis)
- `agents/geo/reuzel/assets/pink-pdp-rating-rendered.png` (live capture: 4.9 stars / 168 reviews, invisible to crawlers)
- Customer brain: `brain/customers/reuzel.md`

Headline: Reuzel is the inverse of the prior two audits on agentic readiness. On
Shopify, it ships the full agent-commerce stack live (agents.md, llms.txt, UCP
profile and a working UCP endpoint) and every AI crawler reaches the site (Bing
included). The hard half is solved by the platform. The gaps are content-level and
fixable: the Product schema labels the brand "reuzelinc" not "Reuzel", and it
carries no rating, so a shopper sees 4.9 stars / 168 reviews on the Pink pomade
while a crawler reading the raw HTML sees none of it. Composite 80/100.
Transactability is the strength (90); Quotability is the soft spot (70).

Engine battery is done (live, June 18, web search on, five engines). Reuzel's
Extreme Hold Matte is the top or matte pick in ChatGPT (cited reuzel.com), Google
AI Overview, and Claude; Perplexity surfaced only the Liquid Death collab; Gemini
missed Reuzel entirely. The deck's Recommendability section carries the real engine
table. Screenshots under `agents/geo/reuzel/assets/`.

Two follow-ups left, both need a human-driven session (not blockers for delivery):

1. Microsoft Copilot was CAPTCHA-blocked ("verify you are human"), so it is not in
   the engine table. The search-off (from-memory) pass per engine was also not run.
   Decide whether to capture these before delivery or ship with the five-engine,
   search-on read.
2. Confirm engagement and pricing stage for Reuzel. The brain file has no
   engagement letter; confirm whether this is a paid pilot or a prospecting audit,
   which affects framing.

## Done when

Armaan has reviewed the deck, flagged any corrections, decided whether to run the
human-assisted engine battery, and either approved it for the customer or sent
edits back to the GEO agent.
