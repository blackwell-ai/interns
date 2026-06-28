# Blackwell foundation wear-test dataset

246 YouTube foundation wear-test videos across 28 foundations,
transcribed and turned into structured, per-reviewer data: each reviewer's skin
profile (type, acne-prone, tone, undertone, shade) and the real outcome of
wearing the product (did it stay matte, hours of wear, did it break them out, did
it oxidize, would they repurchase). 246 of 246 are fully
analyzed.

Built by Blackwell's pipeline: discover -> transcribe (audio -> ASR) -> LLM
structured extraction. This is the layer ChatGPT and star ratings lack: outcomes
segmented by the shopper's exact skin, not a single averaged star.

## Files
- foundation_dataset.json  one record per video: source metadata + full
  transcript + structured analysis.
- foundation_dataset.csv   flat summary of every reviewer's skin + outcome.
- cohort_analysis.json      per-foundation outcomes for oily / acne-prone
  reviewers (e.g. 18 of 18 rated Maybelline Super Stay positively, 0 broke out).
- videos.csv                video index (product, channel, url) for provenance.

## Provenance
Every record links to its source video URL. {VIDEO_NOTE}
