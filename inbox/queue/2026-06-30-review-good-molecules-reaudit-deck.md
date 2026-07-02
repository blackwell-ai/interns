---
title: Review Good Molecules AI visibility re-audit deck before delivery
created: 2026-06-30
created_by: geo
assignee: armaan
priority: normal
claimed_by:
claimed_at:
---

## Task

The Good Molecules (goodmolecules.com) AI visibility re-audit is drafted and needs a
human review before it goes to the client (charter guardrail: no GEO deliverable ships
without sign-off). Good Molecules is an existing engagement, not a cold prospect: this
is the after-benchmark against the June 1 audit (composite D/61), measuring what the
customer's WAF and structured-data remediation bought.

Draft deck (house format, Chrome print-to-PDF since WeasyPrint is not installed here):
`brain/customers/documents/good-molecules-reaudit.pdf`
Source HTML: `agents/geo/good-molecules-reaudit/good-molecules-reaudit.html`
Evidence (battery log, reputation notes, recon, all captures):
`agents/geo/good-molecules-reaudit/` (assets in `assets/`)
Durable findings: `brain/customers/good-molecules.md` (re-audit section, dated 2026-06-30)

Evidence gate: `./skills/ai-visibility-audit/verify-evidence.sh
agents/geo/good-molecules-reaudit` prints PASS (recon, all six reputation sources,
all six engines with ON captures).

Headline: this is a positive re-audit. Composite moved from D (61) to C (67), and both
June 1 Critical findings are closed, verified live:

1. Recommendability recovered. On "best affordable dark spot serum for 2026," the brand
   is named in six of nine engine passes, including the number-one pick on ChatGPT
   (from memory and live) and the top pick in Google's AI Overview, plus top-three on
   Gemini and Copilot. At the June 1 audit none of the standalone assistants named it.
2. Quotability fixed. The hero PDP now serves Product + Offer (price $12, USD, InStock)
   + AggregateRating (4.3 / 7,631), confirmed in the headed browser. The "Claude could
   not read the price, fell back to Amazon" centerpiece no longer reproduces.

Three open findings frame the Phase 2 work, all off-site or endpoint:

3. Claude and Perplexity still do not surface the brand in live retrieval; they answer
   from affiliate and derm roundups (Forbes, Yahoo, e.l.f., Goodal, Curology) that do
   not list Good Molecules. Off-site presence, not crawler access.
4. Reputation is strong but stranded: Amazon 4.4 across ~15.2K ratings and active
   Reddit and YouTube, but no sameAs linking the entity, and weak aggregators
   (Trustpilot 2.8 on 4 unclaimed, no BBB or ConsumerAffairs profile).
5. Agent-commerce layer half open: agents.md serves 200, but /.well-known/ucp,
   /api/ucp/mcp, and llms-full.txt return a 202 WAF challenge, not a confirmed handler.

Things to check before it ships to the client:

1. Cosmetic: every engine and reputation capture carries the Claude-in-Chrome
   extension's "Claude started debugging this browser" banner across the top. It is
   honest (the captures were browser-automation runs) but distracting for a client
   deliverable. Decide whether to re-capture the flagship shots (Google AI Overview,
   ChatGPT, Claude, Perplexity, Amazon) without the extension driving the tab, or to
   ship as is.
2. Scores are my calibration against the June 1 D/61 baseline. I did not have the June
   1 per-dimension breakdown (only the composite), so the deck shows composite movement
   (61 -> 67) and which dimensions moved, not a full per-dimension before/after. If the
   June 1 dimension scores exist in the original deck, confirm the movement narrative
   lines up.
3. Competitor scorecard uses only the two brands with same-day recon (The Ordinary,
   AXIS-Y). Confirm two competitor columns is enough, or ask for one or two more
   recon runs before delivery.
4. Gemini's ON read named the brand but the profile was logged in (contamination
   disclosed in the deck and battery log). It is used as a supporting "named" read, not
   a load-bearing one; confirm that framing is acceptable.

## Done when

Armaan has reviewed the deck, decided on the capture-banner question and the score
framing, flagged any corrections, and either approved it for the Good Molecules and
Beautylish contacts (Nils Johnson, Sameer Iyengar) or sent edits back to the GEO agent.
