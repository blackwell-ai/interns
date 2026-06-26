# Phase 1 Scraper — Implementation Plan

Derived from `scraper_spec.md`. Phase 1 = **scrape + store only**. No transcript
processing/extraction (that's Phase 2). Goal: a local SQLite DB with ~100 review
videos (10 products × ~10 videos), each with full transcript + metadata.

## Architecture (the two-tool split)
- **Discovery + metadata** → `yt-dlp` (keyless, local). Search `"{query}"`, get
  candidate video IDs + basic stats.
- **Transcript text** → `youtube-transcript-api` (fetches by video ID only).
- **Storage** → stdlib `sqlite3`, single file `videos.db`, `video_id` PRIMARY KEY,
  upsert for idempotency.
- **Runs locally** (transcript API is IP-blocked on datacenter IPs).

## Per-product pipeline
1. **Discover** ~25 candidates via fast flat search (`ytsearch25:{query}`,
   `extract_flat`). Cheap: IDs + title/channel/duration/views.
2. **Filter** obvious non-reviews: drop < 60s (Shorts) and > 30min.
3. For each candidate, in order:
   a. **Try transcript first** (most likely failure point). Prefer English,
      fall back to any language, record the language code + generated flag.
   b. On success, **full-extract metadata** for that one video (likes, publish
      date) — only spend this cost on keepers.
   c. **Upsert** the row into SQLite.
   d. Stop at TARGET_PER_PRODUCT (10) successes, or when candidates run out.
4. **Politeness delay** between requests.

## Resilience
- One bad video never crashes the run; every skip logged with a reason.
- Light retry/backoff on transient transcript/extract errors.
- Resume-friendly: rows already in DB count toward the target on re-run.

## Storage schema — table `videos`
video_id (PK), product, title, channel, url, view_count, like_count,
published_at, duration_seconds, language, is_generated, transcript,
transcript_segments (JSON), fetched_at. Matches spec exactly.

## Config block (top of file)
PRODUCTS list, CANDIDATES_PER_PRODUCT=25, TARGET_PER_PRODUCT=10, MIN/MAX duration,
REQUEST_DELAY, DB_PATH.

## Run summary
Per-product stored counts; flag any product under 8.

## Test/verify
1. Smoke-test pipeline on ONE product first; adapt to the live API.
2. Run all 10.
3. Verify DB: row count ~100, no duplicates, all key fields populated,
   transcript + segments parse, sample query works.

## Known risks & mitigations
- transcript-api version drift → inspect installed API before coding.
- full-extracting all 250 candidates is slow → only extract keepers.
- YouTube throttling mid-run → retry/backoff + broad per-video catch.
