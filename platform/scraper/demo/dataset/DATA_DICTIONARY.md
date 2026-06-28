# Data dictionary

One record describes one YouTube foundation wear-test video. Records are in
`foundation_dataset.jsonl`, one JSON object per line, validated against
`schema/foundation_record.schema.json`.

## Three layers, different reliability

A record holds three kinds of data, and they are not equally solid:

- `source`, `transcript`, `description`: facts pulled straight from YouTube.
- `analysis`: produced by a language model reading the transcript. Treat it as
  derived, not ground truth. The model and run are recorded in
  `analysis_provenance`. There is no human-verified accuracy number yet.
- `analysis_provenance.normalized_from`: the raw model values we changed to fit
  the documented vocabulary, so the original output is recoverable.

## Fields

### product
- `name`: catalog product name.
- `product_id`: canonical slug. Every review of the same foundation shares it.
  Not a GTIN/UPC; a real barcode identifier is future work.
- `brand`: display brand.

### source
- `platform`, `video_id`, `url`, `channel`, `title`.
- `published_at`: ISO 8601 date (YYYY-MM-DD).
- `duration_seconds`, `view_count`, `like_count`: integers. View and like counts
  are snapshots taken at `retrieved_at` and will drift.
- `retrieved_at`: ISO 8601 local timestamp, no timezone, when we fetched the video.
- `video_type`: `single_review`, `comparison`, or `roundup`, classified from the
  title. Comparison and roundup videos discuss more than one product, so their
  per-product outcome is less certain than a single review. Filter on this if you
  want only clean single-product evidence.

### transcript
- `text`: the transcript.
- `source`: `captions` (pulled from YouTube; creator-written and auto-generated
  are not distinguished) or `asr` (we transcribed the audio).
- `asr_model`: the model used when `source` is `asr`, else null.
- `segments_available`: whether timestamped segments exist in the source database.

### analysis
- `product_reviewed`: the foundation the model believes the video reviews.
- `persona.skin_type`: free text (e.g. `oily`, `combination oily`).
- `persona.acne_prone`: `yes` | `no` | `unknown`.
- `persona.skin_tone_depth`: `fair` | `light` | `medium` | `tan` | `deep` | `unknown`.
- `persona.undertone`: `warm` | `cool` | `neutral` | `olive` | `unknown`.
- `persona.shade_used`: free text, verbatim.
- `outcomes.stayed_matte`: `yes` | `mostly` | `no` | `not_tested`.
- `outcomes.wear_hours`: number of hours it looked good, or null.
- `outcomes.broke_out` / `oxidized` / `would_repurchase`: `yes` | `no` | `not_mentioned`.
- `outcomes.overall`: `positive` | `mixed` | `negative`.
- `is_sponsored`: boolean, flagged only on explicit evidence.
- `key_quote`: one verbatim reviewer quote, taken from the transcript, so it
  inherits any transcription error.

## Normalization rules

The extractor did not strictly enforce its enums, so some raw values were free
text. We normalized them and recorded each original under
`analysis_provenance.normalized_from`:

- `skin_tone_depth`: the first canonical depth term in the string; ranges like
  "light to medium" become `light`. Missing or "not_mentioned" become `unknown`.
- `undertone`: `olive` if present; otherwise the first of warm/cool/neutral, with
  yellow/golden/peach/red read as warm and pink as cool. Missing become `unknown`.
- `acne_prone`: "not_mentioned" and any free text collapse to `unknown`.
- outcome fields: kept if already valid, else the first valid token in the string,
  else the field's "not addressed" value.

## Known limitations

- The `analysis` layer has no measured accuracy. An eval (human-labeled sample vs
  model output) is the next step before this is decision-grade.
- `wear_hours` collapses multi-day or multi-checkpoint tests into one number.
- `video_type` is title-based, so a roundup with a single-product title can slip
  through as `single_review`.
- Rights status is unresolved (see README).
