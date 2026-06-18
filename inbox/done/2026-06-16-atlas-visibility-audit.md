---
title: Website visibility audit for Atlas Skateboarding
created: 2026-06-16
created_by: Ethan
assignee: Ethan
priority: normal
claimed_by: GEO agent
claimed_at: 2026-06-16
---

## Task

Run a website visibility audit on Atlas Skateboarding (atlasskateboarding.com),
the main shop run by the same owner as DLX, for whom Ethan prepared an audit on
June 9. Owner concerns are mainly traffic, with plans to run Meta ads later and a
wish for help beyond SEO and GEO. Benchmark against the skate shops doing well:
CCS (shop.ccs.com), Tactics (in financial trouble), and Labor
(laborskateshop.com). Deliver in the DLX house format, all the way to a
send-ready branded PDF, with a paid-readiness pillar and a DLX-mirrored close
scaled to Atlas.

## Done when

A branded PDF audit exists, every claim externally verifiable, no em or en
dashes, with the five-dimension scorecard, the three-competitor benchmark table,
the paid-readiness section, and the $1,000 Phase 1 close. Durable findings
recorded in `brain/`.

## Result

Delivered June 16, 2026 as the repo's heavy AI Visibility Audit (13 pages, the
Public Goods / Husqvarna house format), rendered with headless Chrome (WeasyPrint
would not import even after installing pango/cairo). Format iterated with Ethan: a
DLX-style light deck first (10 pages, then condensed to 4), then he asked for the
heavier repo format, which is the canonical deliverable.

- Deliverable: `brain/customers/documents/atlas-audit.pdf` (also
  `~/Downloads/Atlas Skateboarding - AI Visibility Audit.pdf`). Working source:
  `agents/geo/atlas/atlas-ai-visibility-audit.html`. Light variants stay at
  `agents/geo/atlas/atlas-audit.html` (4pp) and `-full.html` (10pp).
- Scorecard, five AI-behavior dimensions: Discoverability 50, Quotability 18,
  Recommendability 28, Transactability 60, Reputation 62. Composite 44, grade F
  (competitive set CCS/Tactics/Labor averages ~79, B range).
- Flagship finding: asked for the best Bay Area skate shops, AI answer engines
  named the sibling shop DLX, FTC, SF Skate Club, and others, but never Atlas, and
  Atlas is missing from the California.com listicle those engines cite. Reputation
  is real but stranded: 4.8 stars / 115 Birdeye reviews, 135 Yelp, official Nike
  SB and Vans dealer, with no entity schema linking any of it. Technical layer
  empty: zero schema across 4,528 products, one-word title, empty meta, generic
  llms.txt. Paid readiness: Google Ads and GA4 live, Meta pixel slot empty.
- Competitive table verified live for CCS, Tactics, and Labor; Atlas is the only
  one of the four empty on every machine-readable signal and absent from AI
  category answers.
- Durable knowledge: `brain/customers/atlas.md` (updated to the heavy audit),
  `brain/customers/overview.md` (prospect registered). Skill
  `skills/ai-visibility-audit/` aligned to the canonical heavy format (SKILL.md,
  recon.sh, template.html), registered in `skills/INDEX.md`.

Honest status: no contract yet. This is a prospecting and discovery artifact for
a warm relationship Ethan owns. There is still no DLX brain record; worth adding
when convenient.
