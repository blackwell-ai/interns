# Reviewer / UGC creator panel (an audit service)

Filed 2026-06-25. Source: founder direction from Armaan (this thread), grounded in
the `platform/` social-proof pipeline and [[2026-06-24-social-proof-layer-thesis]].

## What it is

A vetted panel of independent reviewers and UGC creators, scored for neutrality,
that can seed genuine third-party reviews of a client's product across YouTube,
Reddit, and short-form video. It is sold as one of the ongoing Phase 2 services in
the AI visibility audit, not a one-time fix. The rationale is the same one the
audit already rests on: off-site mentions, YouTube especially, are the single
strongest correlate of AI visibility (r about 0.71 to 0.74, well ahead of
backlinks), and they are the part of reputation that on-site schema and `sameAs`
fixes cannot move. See [[answer-engine-citation-behavior]] and
[[audit-methodology]].

This is the rung-1 instrument from the social-proof thesis made into a named,
sellable service: every engagement that runs the panel deposits structured,
verified, neutrality-scored sentiment into the corpus we own.

## Honest current state (do not overstate to customers)

- The `platform/scrape/socialproof.py` pipeline ingests YouTube and Reddit reviews
  and classifies each source's independence (independent, incentivized free
  product, sponsored, affiliate, first-party, astroturf-suspected). A
  reviewer-level store (`platform/data/reviewers.json`) compounds those priors
  across products.
- As of this date the store holds a handful of scraped channels from the Helix
  mattress run only. That is a sourcing-and-scoring capability, not yet a managed
  network we commission to post.
- Customer-facing framing decided 2026-06-25: describe it as a panel we are
  **standing up** for Phase 2 design partners, scored for neutrality. Do not claim
  a guaranteed product send today, and do not print a specific headcount ("a
  couple hundred") in a customer deck until the panel actually backs it. Revisit
  this file and the audit copy when fulfillment is real.

## Where it lives in the deliverables

- `skills/ai-visibility-audit/SKILL.md`: standing instruction that every deck's
  Phase 2 section names the panel, with the honest-framing guardrail.
- `skills/ai-visibility-audit/template.html`: the Phase 2 / "The work" section
  carries the panel as a recurring service line.
