---
title: Review GhostBed AI visibility audit deck before delivery
created: 2026-06-22
created_by: geo
assignee: armaan
priority: normal
claimed_by:
claimed_at:
---

## Task

The GhostBed (ghostbed.com) AI visibility audit is drafted and needs a human review
before it goes to the prospect (charter guardrail: no GEO deliverable ships without
sign-off). GhostBed is a cold prospect, no contact established yet.

Draft deck (13 pages, house format, Chromium print-to-PDF since WeasyPrint is not
installed on this machine):
`brain/customers/documents/ghostbed-audit.pdf`
Source HTML: `agents/geo/ghostbed/ghostbed-ai-visibility-audit.html`
Customer brain (full evidence, scorecard, competitor and reputation data):
`brain/customers/ghostbed.md`

Headline: close to the inverse of Atlas, and a sharper version of Reuzel/Eclipse.
GhostBed runs the best agent-commerce plumbing in its competitive set (live UCP
profile, MCP endpoint, agents.md, llms.txt, agentic-discovery sitemap, none of which
Saatva/Purple/Nectar expose) and ships decent PDP schema, yet it is the least
AI-visible brand in its set. Composite 61/100, grade C. Recommendability is the
failing dimension (38) and the flagship; Reputation (48) is the second.

The flagship is strong and reproducible: asked for "best cooling mattress," "best
online mattress," and "best mattress 2026," web-search-backed AI answers named
Helix, WinkBed, Saatva, Nectar, Purple, Casper, DreamCloud, and others. GhostBed
appeared in none of the three, including the cooling query, which is literally its
homepage title ("Luxury Cooling Mattresses"). It surfaces only when the query
already names it.

The reputation finding is nuanced and needs a careful read before sending. On-site
the PDP shows a first-party 4.8 from 10,223 reviews; the open web shows Trustpilot
3.5 (82% one-star all time), BBB GhostBed 1.61 (87 complaints in 3 yrs),
ConsumerAffairs 1.5, against editorial scores of 4.1 to 4.7. The deck frames the
divergence honestly and notes the negatives are about the company (returns, trial
mechanics, warranty/CS), not the bed. Confirm we are comfortable putting the low
external numbers in front of the prospect.

Three follow-ups, none blockers for review:

1. Re-verify the Amazon per-model star counts at delivery time. They were live DOM
   reads (Classic ~4.4/617, Ultimate ~4.2/157, Luxe ~3.9/38) and move; Amazon's
   /product-reviews/ pages now gate behind sign-in.
2. The AI battery was web-search-backed retrieval, not a six-engine browser run with
   browsing-off and browsing-on passes. Decide whether to run the full per-engine
   battery (ChatGPT, Perplexity, Gemini, Claude, Google AI Mode, Copilot) and drop a
   real engine table into the Recommendability section before delivery, as the
   Reuzel deck did.
3. No contact captured. Confirm whether this stays a cold prospecting audit or
   becomes a paid pilot, which affects the framing of the close.

## Done when

Armaan has reviewed the deck, flagged any corrections, decided on the reputation
framing and whether to run the human-assisted engine battery, and either approved it
for the prospect or sent edits back to the GEO agent.
