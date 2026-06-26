# Video-scraper supersedes the social-proof scraper

Decided 2026-06-25. Source: founder direction from Armaan (this thread).

## Decision

The standalone `experiment-video-scraper` build (cloned from
`github.com/sd393/experiment-video-scraper`) becomes the platform's scraper. It
now lives at `platform/scraper/` with its own git history stripped, so it is
plain repo content rather than a nested repo or submodule. The old
`platform/scrape/socialproof.py` pipeline is retired.

Removal was a full clean sweep, not a code-only swap. Deleted alongside the old
scraper code: `platform/products.json`, `platform/data/` (the GhostBed and Helix
mattress runs, including the `_media/` and `_subs/` caption scratch), and the
cross-product reviewer neutrality store `platform/data/reviewers.json`. The
now-orphaned `platform/data/*/_media|_subs` ignore rules were dropped from the
root `.gitignore`.

## Why

The new build is a more complete two-phase pipeline. Phase 1 (`scraper.py`)
collects YouTube review transcripts plus metadata into a single `videos.db`;
Phase 2 (`processor.py`) discovers per-product quality dimensions from the data
and extracts a structured preference record per video. The old `socialproof.py`
was a single-stage source-neutrality classifier with a separate reviewer store.
Keeping both would have left two overlapping scrapers and two data models in
`platform/`. The founder chose to replace rather than merge.

## What this costs us

The old reviewer-level neutrality store is gone, and the new pipeline does not
yet compound a neutrality prior per reviewer across products, nor read Reddit. It
flags sponsorship per video instead. If the reviewer/UGC panel service needs the
cross-product neutrality prior back, that is fresh work. Tracked in
[[reviewer-ugc-panel]].

## State after the swap

`platform/scraper/` holds the committed dataset: `videos.db` plus
`data/preference_data.json`, covering 64 videos across 7 products with complete
preference data. Three products still need a scrape from a non-throttled IP
because `youtube-transcript-api` is blocked on datacenter IPs.
