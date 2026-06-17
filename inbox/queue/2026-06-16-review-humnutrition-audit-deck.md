---
title: Review HUM Nutrition AI visibility audit deck before delivery
created: 2026-06-16
created_by: geo
assignee: armaan
priority: normal
claimed_by:
claimed_at:
---

## Task

The HUM Nutrition AI visibility audit is drafted and needs a human review before it
goes to the customer (charter guardrail: no GEO deliverable ships without sign-off).

Draft deck (12 pages, house format, WeasyPrint):
`agents/geo/humnutrition/humnutrition-audit-2026-06-16.pdf`
Source HTML: `agents/geo/humnutrition/humnutrition-audit-2026-06-16.html`

Supporting evidence and working files:
- `agents/geo/humnutrition/recon-2026-06-16.md` (crawler access, schema, agentic surfaces)
- `agents/geo/humnutrition/truth-table-raw.csv` (frozen catalog, 37 products)
- `agents/geo/humnutrition/engine-battery-2026-06-16.md` (live engine captures)
- Customer brain: `brain/customers/humnutrition.md`

Headline: HUM is readable but under-recommended. The site is open to AI crawlers and
serves clean server-side schema, so engines read humnutrition.com and get the facts right
when the brand is named. But "best collagen supplement" omits HUM on all five engines
tested (Perplexity, Google AI Overviews, Google AI Mode, ChatGPT, Copilot); the answers
come from third-party roundups. Composite 66/100. Recommendability is the gap (47);
quotability is the strength (85).

Update (June 16, later): all seven engines now measured (Perplexity, Google AI Overviews,
Google AI Mode, ChatGPT, Copilot, Claude, Gemini); only Amazon Rufus is unmeasured
(human-only). Agentic-commerce surfaces validated exhaustively by curl. Deck re-rendered
(13 pages) with the full engine table.

One thing to weigh before delivery:
1. Confirm engagement and pricing stage for HUM. The brain file has no engagement letter;
   confirm whether this is a paid pilot or a prospecting audit, which affects framing.

## Done when

Armaan has reviewed the deck, flagged any corrections, decided on the unmeasured engines,
and either approved it for the customer or sent edits back to the GEO agent.
