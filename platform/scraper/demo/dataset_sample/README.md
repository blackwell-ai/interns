# Blackwell sample: structured product reviews

231 video reviews across 28 foundations, each structured into the reviewer's
profile and the real outcome of using the product, so an agent can surface the
most relevant reviews for a given shopper rather than leaning on one averaged
rating.

## What each record holds
- product: the product reviewed, with a stable id and brand.
- video: the reviewer, and the review's title, date, length, and view count.
- transcript: the full review transcript.
- reviewer_profile: the reviewer's skin type, tone, undertone, and whether they
  are acne-prone, plus the shade they used.
- outcomes: what actually happened over the day, whether it stayed matte, how
  many hours it lasted, whether it broke them out or oxidized, whether they would
  repurchase, and an overall read.
- is_sponsored: whether the review was sponsored (almost all are not).
- key_quote: one representative line from the reviewer.

## Files
- foundation_dataset.jsonl   one review per line.
- foundation_dataset.csv     flat summary of every reviewer and outcome.
- product_rollup.json        per-product outcome distributions, sliced by skin type.
- cohort_analysis.json       outcomes for a given reviewer profile, for example
  oily or combination skin, per product.
- schema/review.schema.json  machine-readable spec for one record.
- DATA_DICTIONARY.md         field definitions and allowed values.

## How an agent uses it
Match a shopper to reviewers with the same profile, then read the real outcomes
for that group instead of a single averaged score. cohort_analysis.json shows
this for oily and combination skin.
