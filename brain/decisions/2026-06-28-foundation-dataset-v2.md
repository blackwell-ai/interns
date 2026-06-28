# Foundation wear-test dataset v2: attribution audit and clean repackage

Decided 2026-06-28. Source: data-quality review of the v1 export in this thread,
plus founder direction from Armaan to ship a clean v2 now.

## Context

`platform/scraper/demo/export_dataset.py` packages the foundation corpus
(`demo/foundation_wide.db`: 246 YouTube wear-test videos, 28 foundations, each
transcribed and run through `gpt-4.1-mini` structured extraction in
`extract_outcomes.py`) into a sendable dataset, aimed at an AI-lab conversation.
A review of the v1 output found accuracy problems in exactly the artifact the
dataset sells, the per-cohort outcomes, plus packaging gaps a lab would flag.

## What the review found

- Attribution errors. About 15 records (6%) had structured outcomes describing a
  different foundation than the one they were filed under, because they were
  "vs" / dupe / "best of" roundup videos, out-of-catalog products, or not wear
  tests at all. The model's own `product_reviewed` disagreed with the filed
  `product`. These polluted the headline cohorts: the v1 README's "18 of 18
  Maybelline Super Stay positive" and the "20 of 20 NARS stayed matte" both
  included other brands and, for NARS, two non-wear-test tutorials.
- "0 broke out" overstated the evidence. `broke_out` is `not_mentioned` for 210
  of 246 records; the cohort reported the count with no denominator, so absence
  of data read as a clean result.
- Dropped provenance. The source DB already held `transcript_source`,
  `fetched_at`, `like_count`, `description`, and `transcript_segments`; the v1
  export discarded all of them. The extraction model was recorded in
  `clip_outcomes.model` but never carried out.
- Enum drift. Extraction used a JSON schema without `strict`, so the model
  emitted free text outside its own enums (undertone "yellow (warm)",
  `acne_prone` "not_mentioned", one comparison `oxidized` value).
- Packaging. One large JSON array, no canonical product id, non-ISO dates, no
  schema or data dictionary, no product-level rollup.

## Decision

Rewrite the exporter to produce a v2 dataset (231 records after exclusions):

- Drop 15 audited records to `excluded_records.jsonl`, each with a reason. The
  exclusion list is hardcoded by `video_id` in `EXCLUDE`. Re-attribution was
  rejected: these are comparisons and roundups whose outcomes are blended, so
  moving them into another bucket would carry the same contamination.
- Carry the dropped provenance, stamp every record with extraction model +
  schema version, add canonical `product_id` + `brand`, classify `video_type`
  (single_review / comparison / roundup) from the title, normalize dates to ISO
  8601 and persona/outcome values to the documented vocabulary while preserving
  every raw value under `analysis_provenance.normalized_from`.
- Emit JSONL as the primary file. Add `product_rollup.json` (per-foundation
  outcome distributions, multi-label skin-type slices), rebuild
  `cohort_analysis.json` with a denominator on every outcome and a precise
  cohort label, and ship `schema/foundation_record.schema.json` plus
  `DATA_DICTIONARY.md`.

## Deliberately not done

- No extraction-accuracy eval yet (founder chose to skip for now). This is the
  single biggest remaining gap before the `analysis` layer is decision-grade: a
  human-labeled sample compared against model output, reported as an accuracy
  number. Flagged in the README and data dictionary as the next step.
- Rights status is unresolved and left as a founder decision. The dataset is
  derived from publicly viewable YouTube videos; licensing and redistribution
  are not cleared. Documented honestly rather than silently.
- `skin_type` stays free text per record (the extractor models it that way);
  only the rollup adds normalized multi-label tags for clean slicing.
- SKU-level resolution within a brand (e.g. Fenty Pro Filt'r Soft Matte vs
  Hydrating vs Powder) is not attempted; attribution is resolved at brand level.

## Regeneration

`cd platform/scraper && python demo/export_dataset.py` rebuilds every output
from the DB. The video downloader is `demo/download_videos.py`.
