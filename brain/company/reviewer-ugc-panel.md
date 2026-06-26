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

- Pipeline swap 2026-06-25 (founder direction, Armaan): the old
  `platform/scrape/socialproof.py` scraper was replaced by the two-phase
  video-scraper now at `platform/scraper/`. Phase 1 (`scraper.py`) discovers
  YouTube review videos with yt-dlp, fetches each transcript, and stores it in
  `videos.db`. Phase 2 (`processor.py`) reads those transcripts with an LLM,
  discovers the quality dimensions reviewers actually evaluate per product, and
  writes a structured record per video (verdict, sentiment, pros/cons, best-for,
  use cases, worth-the-price, a per-video sponsorship flag with evidence, key
  quotes, confidence). `export.py` writes a browsable snapshot to
  `platform/scraper/data/preference_data.json`. See
  [[2026-06-25-video-scraper-supersedes-socialproof]].
- What the swap dropped: the cross-product reviewer-level neutrality store
  (`platform/data/reviewers.json`) and the GhostBed and Helix mattress runs were
  removed in the clean sweep. The new pipeline flags sponsorship per video but
  does not yet compound a neutrality prior per reviewer across products, and it
  reads YouTube transcripts only (no Reddit). Re-standing-up a reviewer-level
  neutrality store is open work if the panel needs it. Either way this is a
  sourcing-and-scoring capability, not yet a managed network we commission to post.
- Current dataset: 64 videos across 7 products, each with complete preference
  data; the remaining 3 products await a scrape from a non-throttled IP
  (`youtube-transcript-api` is blocked on datacenter IPs, so it runs locally).
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
