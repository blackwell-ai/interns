# Blackwell foundation wear-test dataset (v2)

231 YouTube foundation wear-test videos across 28 foundations,
each transcribed and turned into structured, per-reviewer data: the reviewer's
skin profile (type, acne-prone, tone, undertone, shade) and the real outcome of
wearing the product (stayed matte, hours of wear, broke out, oxidized, would
repurchase). The structured layer is model-generated and marked as derived, not
ground truth.

Built by Blackwell's pipeline: discover, transcribe (YouTube captions or our own
audio ASR), then language-model structured extraction. The value is the layer on
top of the transcript: cleaned, product-resolved, per-persona outcomes, the thing
a scraper or a single star rating does not give you.

## Files
- `foundation_dataset.jsonl`   one record per video (source + transcript +
  analysis + provenance), one JSON object per line.
- `foundation_dataset.csv`     flat per-reviewer summary of normalized fields.
- `product_rollup.json`        per-foundation review counts and outcome
  distributions, sliced by skin type. A purchase decision needs a distribution,
  not one anecdote.
- `cohort_analysis.json`        outcomes for oily / combination reviewers, with a
  denominator on every outcome.
- `videos.csv`                 provenance index (product, channel, url, dates).
- `excluded_records.jsonl`     15 records removed in the 2026-06-28
  attribution audit, each with a reason.
- `schema/foundation_record.schema.json`  JSON Schema for one record.
- `DATA_DICTIONARY.md`         field definitions, allowed values, normalization rules.

## What changed from v1
- Removed 15 records whose extraction was about a different product, an
  out-of-catalog product, or that were not single-product wear tests. They had
  inflated the v1 cohort headlines.
- Carried provenance the v1 export dropped: caption source, retrieval timestamp,
  like count, video description.
- Stamped every record with the extraction model and a schema version.
- Normalized dates and the persona/outcome vocabulary, preserving raw values.
- Switched the primary file to JSONL.

## Extraction model
The `analysis` block was produced by `gpt-4.1-mini` (recorded per record in
`analysis_provenance`). Extraction accuracy has not been measured against human
labels yet; that eval is the next step before treating these fields as
decision-grade.

## Provenance and rights
Every record carries its source URL and retrieval timestamp. Transcripts are
derived from publicly viewable YouTube videos. Licensing and redistribution
rights are not yet cleared, so the rights status of this dataset is unresolved.
Resolve that before sharing the data outside the company.
