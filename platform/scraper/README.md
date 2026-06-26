# Product Quality API — Phase 1 Scraper

A two-stage pipeline that builds a SQLite database of YouTube **review videos** for a
curated set of products and turns them into structured, queryable product-quality data:

- **Phase 1 — `scraper.py`**: discover review videos, fetch transcripts + metadata, store.
- **Phase 2 — `processor.py`**: read those transcripts with an LLM and extract structured
  quality records. Crucially, the quality *dimensions are discovered from the data per
  product* (not hardcoded) — see "Phase 2" below.

See `PLAN.md` for the Phase 1 design and `scraper_spec.md` (the original brief) for the spec.

## How it works

Discovery and transcript fetching require two different tools, because
`youtube-transcript-api` can only fetch a transcript **given a video ID** — it cannot
search. So:

| Job | Tool |
|---|---|
| Search YouTube + read video metadata (views, likes, date, duration) | `yt-dlp` |
| Fetch the spoken-word transcript for a video ID | `youtube-transcript-api` |
| Store everything | stdlib `sqlite3` (single file, zero setup) |

Per product, the scraper:
1. **Discovers** ~25 candidates with a fast flat search (`ytsearch25:"{query}"`).
2. **Filters** out Shorts (<60s), long videos (>30min), and livestreams.
3. For each candidate, **fetches the transcript first** (the most common failure
   point). Only when a transcript exists does it pay for full metadata extraction.
4. **Upserts** the row into SQLite, keyed on `video_id` (re-runs never duplicate).
5. Stops at **10 stored transcripts** per product or when candidates run out.

It is resilient (one bad video never crashes the run; every skip is logged with a
reason), polite (a small delay between requests), and resume-friendly (rows already
in the DB count toward the target on a re-run).

> **Run locally.** `youtube-transcript-api` is IP-blocked on datacenter IPs
> (AWS/GCP). On a laptop it works fine.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
python scraper.py                         # full run, all 10 products -> videos.db
python scraper.py --only "Owala FreeSip"  # a single product
python scraper.py --limit 1               # only the first product (smoke test)
python scraper.py --db scratch.db --target 3 --candidates 12   # quick test run
python scraper.py --help                  # all options
```

At the end it prints a per-product summary and flags any product that landed under 8.

## Database schema — table `videos`

One row per successfully-transcribed video.

| column | type | notes |
|---|---|---|
| `video_id` | TEXT PRIMARY KEY | YouTube video ID |
| `product` | TEXT | canonical seed product name |
| `title` | TEXT | |
| `channel` | TEXT | |
| `url` | TEXT | |
| `view_count` | INTEGER | nullable |
| `like_count` | INTEGER | nullable |
| `published_at` | TEXT | ISO date (`YYYY-MM-DD`), nullable |
| `duration_seconds` | INTEGER | |
| `language` | TEXT | transcript language code (e.g. `en`) |
| `is_generated` | INTEGER | 1 = auto-caption, 0 = manual |
| `transcript` | TEXT | full joined transcript text |
| `transcript_segments` | TEXT | JSON list of `{text, start, duration}` (Phase 2 timing) |
| `fetched_at` | TEXT | ISO timestamp (UTC) |

## Querying the data

It's a plain SQLite file — query it with the `sqlite3` CLI, any SQLite browser, or
Python:

```bash
# How many videos per product?
sqlite3 videos.db "SELECT product, COUNT(*) FROM videos GROUP BY product;"

# Most-viewed review per product
sqlite3 videos.db \
  "SELECT product, title, MAX(view_count) FROM videos GROUP BY product;"
```

```python
import sqlite3, json
conn = sqlite3.connect("videos.db")
conn.row_factory = sqlite3.Row
for r in conn.execute("SELECT * FROM videos WHERE product = ?", ("Oura Ring",)):
    segments = json.loads(r["transcript_segments"])   # [{text, start, duration}, ...]
    print(r["title"], "-", len(r["transcript"]), "chars,", len(segments), "segments")
```

The transcript text and timed segments are stored intact so the Phase 2 extraction
step has everything it needs.

## Phase 2 — Processor (transcript → structured quality data)

`processor.py` reads the transcripts collected by Phase 1 and produces a structured
quality record per video using an OpenAI model (default `gpt-5.5`).

**The attributes are not decided in advance.** Instead of a fixed schema, the pipeline
runs in two stages:

1. **Discover** (per product): read all of a product's transcripts and let the model
   surface the recurring quality dimensions reviewers actually evaluate — e.g. a water
   bottle yields *leak-proofing / insulation / cleaning*, a hair tool yields *heat
   damage / curl longevity*. Stored in the `product_dimensions` table.
2. **Extract** (per video): score each transcript against *its product's discovered
   dimensions* (turned into a strict JSON-Schema contract so the model must score exactly
   those), plus universal fields — verdict, overall sentiment, pros/cons, best-for /
   not-for, demonstrated use cases, would-keep-using, worth-the-price, sponsorship flag +
   evidence, key quotes, and a confidence score. Stored in `video_analysis.extracted` (JSON).

```bash
export OPENAI_API_KEY=sk-...          # required; never logged or stored
python processor.py --dry-run         # preview prompts/schema, no API calls
python processor.py --discover-only   # stage 1 only — preview the discovered dimensions
python processor.py                    # discover + extract for all products
python processor.py --only "Oura Ring" --model gpt-5.5
python processor.py --force            # re-discover + re-extract everything
```

It is idempotent (videos with `status='complete'` are skipped on re-run; per-video
status moves pending → running → complete/error) and one bad video never stops a product.

### Phase 2 tables

| table | key columns |
|---|---|
| `product_dimensions` | `product` (PK), `category`, `dimensions` (JSON: `[{slug,name,definition,prevalence}]`), `n_transcripts`, `model`, `discovered_at` |
| `video_analysis` | `video_id` (PK → `videos`), `product`, `status`, `extracted` (JSON record), `model`, `error`, `analyzed_at` |

> **Note on the original summary:** `video-extraction-summary.md` describes a *fixed* Zod
> schema plus video-frame/facial-cue signals. This build deliberately uses **emergent,
> data-driven dimensions** instead, and works from transcript text only (Phase 1 stores
> transcripts, not video frames).

## Dataset in this repo

The collected + processed data is committed so you don't have to re-scrape:

- **`videos.db`** — the SQLite database (raw transcripts/metadata + discovered dimensions
  + per-video preference records).
- **`data/preference_data.json`** — a browsable JSON snapshot (GitHub can't render the
  binary `.db`), grouped by product, with each product's dimensions and one structured
  record per video. Regenerate anytime with `export.py`:

  ```bash
  python export.py                          # -> data/preference_data.json
  python export.py --include-transcripts    # also embed transcript text
  python export.py --only "Oura Ring" --out oura.json
  ```

Current snapshot: **64 videos across 7 products, all with complete preference data**
(the remaining 3 products await a scrape from a non-throttled IP).

## Tests

Development used offline unit tests (mocked network + OpenAI) covering both phases —
filtering, upsert idempotency, IP-block handling, the emergent-dimension → strict-schema
machinery, extraction storage, and retry logic. Per project convention they're kept out
of the committed repo.

## Configuration

All knobs live in the `CONFIG` block at the top of `scraper.py`: the product list,
candidates-per-product (25), target-per-product (10), duration bounds, request delay,
and the database path.
