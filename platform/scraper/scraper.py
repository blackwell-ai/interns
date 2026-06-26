#!/usr/bin/env python3
"""
Product Quality API — Phase 1 scraper (scrape + store only).

For each seed product, this script:
  1. Discovers ~25 candidate YouTube review videos with yt-dlp (fast flat search).
  2. Fetches each candidate's transcript with youtube-transcript-api.
  3. Pulls full metadata (likes, publish date) for videos that DO have a transcript.
  4. Stores one row per transcribed video in a local SQLite database (idempotent upsert).

It keeps going per product until TARGET_PER_PRODUCT transcripts are stored or the
candidate list is exhausted. Phase 2 (LLM extraction of structured quality data)
is intentionally NOT built here — we only collect and store, keeping transcripts +
metadata fully intact so Phase 2 can plug in cleanly.

Run LOCALLY. youtube-transcript-api gets IP-blocked on datacenter IPs (AWS/GCP).

Usage:
    python scraper.py                 # full run, all products -> videos.db
    python scraper.py --limit 1       # only the first product (smoke test)
    python scraper.py --db scratch.db # use a different database file
    python scraper.py --only "Owala FreeSip"   # run a single product by name
"""

from __future__ import annotations

import argparse
import json
import logging
import sqlite3
import sys
import time
from datetime import datetime, timezone

from yt_dlp import YoutubeDL
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api import (
    AgeRestricted,
    InvalidVideoId,
    IpBlocked,
    NoTranscriptFound,
    NotTranslatable,
    PoTokenRequired,
    RequestBlocked,
    TranscriptsDisabled,
    VideoUnavailable,
    VideoUnplayable,
    YouTubeRequestFailed,
)

# ===========================================================================
# CONFIG
# ===========================================================================

# (canonical name stored in `product` column, YouTube search query)
PRODUCTS: list[tuple[str, str]] = [
    ("Dyson Airwrap",                 "Dyson Airwrap review"),
    ("Stanley Quencher 40oz",         "Stanley Quencher 40oz review"),
    ("Owala FreeSip",                 "Owala FreeSip bottle review"),
    ("Ninja Creami",                  "Ninja Creami review"),
    ("Apple AirPods Pro",             "Apple AirPods Pro review"),
    ("Oura Ring",                     "Oura Ring review"),
    ("Rare Beauty Soft Pinch Blush",  "Rare Beauty Soft Pinch liquid blush review"),
    ("Sol de Janeiro Bum Bum Cream",  "Sol de Janeiro Bum Bum Cream review"),
    ("Lululemon Align Leggings",      "Lululemon Align leggings review"),
    ("Therabody Theragun",            "Therabody Theragun review"),
]

CANDIDATES_PER_PRODUCT = 25      # over-fetch: buffer for videos with no transcript
TARGET_PER_PRODUCT = 10          # stored transcripts we want per product
UNDER_TARGET_FLAG = 8            # warn if a product lands below this

MIN_DURATION_SECONDS = 60        # drop Shorts / clips
MAX_DURATION_SECONDS = 30 * 60   # drop very long videos (livestreams, compilations)

PREFERRED_LANGUAGES = ["en", "en-US", "en-GB"]  # try these first; fall back to any

REQUEST_DELAY_SECONDS = 2.0      # be polite between transcript requests
INTER_PRODUCT_DELAY = 2.0        # extra breather between products
MAX_TRANSCRIPT_RETRIES = 1       # quick retries for *network* transcript errors only
RETRY_BACKOFF_SECONDS = 3.0      # base backoff, multiplied by attempt number

# IP-block handling. youtube-transcript-api gets the whole IP soft-blocked when it
# fetches too fast. That block is systemic (not per-video), so retrying a single
# video is pointless — instead we count consecutive blocks across the run, attempt
# ONE long cool-down, and if the block persists we stop gracefully (the DB is
# resume-friendly, so a later re-run picks up exactly where we left off).
MAX_CONSECUTIVE_BLOCKS = 3       # this many blocks in a row => sustained block
BLOCK_COOLDOWN_SECONDS = 5       # brief pause; in practice the IP's window outlasts
                                 # any short in-run wait, so we abort fast and the
                                 # operator rotates IP / waits before re-running.

DB_PATH = "videos.db"

# Transcript errors that are PERMANENT for a given video -> skip, never retry.
PERMANENT_TRANSCRIPT_ERRORS = (
    TranscriptsDisabled,
    NoTranscriptFound,
    VideoUnavailable,
    VideoUnplayable,
    InvalidVideoId,
    NotTranslatable,
    AgeRestricted,
    PoTokenRequired,
)
# Errors that mean "the IP is (soft) blocked" — systemic, handled at the run level.
BLOCK_TRANSCRIPT_ERRORS = (
    IpBlocked,
    RequestBlocked,
)
# Errors that may be a transient network blip for THIS video -> one quick retry.
NETWORK_TRANSCRIPT_ERRORS = (
    YouTubeRequestFailed,
)

# Outcomes of a single transcript attempt.
TRANSCRIPT_OK = "ok"          # got a transcript (data = transcript dict)
TRANSCRIPT_SKIP = "skip"      # no transcript for this video (endpoint responded fine)
TRANSCRIPT_BLOCKED = "blocked"  # IP soft-blocked — back off at the run level


class RunAborted(Exception):
    """Raised to stop the whole run early but cleanly (e.g. persistent IP block)."""


log = logging.getLogger("scraper")


# ===========================================================================
# DATABASE
# ===========================================================================

SCHEMA = """
CREATE TABLE IF NOT EXISTS videos (
    video_id            TEXT PRIMARY KEY,
    product             TEXT NOT NULL,
    title               TEXT,
    channel             TEXT,
    url                 TEXT,
    view_count          INTEGER,
    like_count          INTEGER,
    published_at        TEXT,
    duration_seconds    INTEGER,
    language            TEXT,
    is_generated        INTEGER,
    transcript          TEXT,
    transcript_segments TEXT,
    fetched_at          TEXT
);
"""


def connect_db(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute(SCHEMA)
    conn.commit()
    return conn


def existing_video_ids(conn: sqlite3.Connection) -> set[str]:
    """All video IDs already stored — used to skip work on re-runs."""
    return {row["video_id"] for row in conn.execute("SELECT video_id FROM videos")}


def count_for_product(conn: sqlite3.Connection, product: str) -> int:
    cur = conn.execute("SELECT COUNT(*) AS n FROM videos WHERE product = ?", (product,))
    return cur.fetchone()["n"]


def upsert_video(conn: sqlite3.Connection, row: dict) -> None:
    """Insert a video, or update it in place if the video_id already exists.

    Keyed on video_id (PRIMARY KEY) so re-running never creates duplicates.
    """
    conn.execute(
        """
        INSERT INTO videos (
            video_id, product, title, channel, url, view_count, like_count,
            published_at, duration_seconds, language, is_generated,
            transcript, transcript_segments, fetched_at
        ) VALUES (
            :video_id, :product, :title, :channel, :url, :view_count, :like_count,
            :published_at, :duration_seconds, :language, :is_generated,
            :transcript, :transcript_segments, :fetched_at
        )
        ON CONFLICT(video_id) DO UPDATE SET
            product             = excluded.product,
            title               = excluded.title,
            channel             = excluded.channel,
            url                 = excluded.url,
            view_count          = excluded.view_count,
            like_count          = excluded.like_count,
            published_at        = excluded.published_at,
            duration_seconds    = excluded.duration_seconds,
            language            = excluded.language,
            is_generated        = excluded.is_generated,
            transcript          = excluded.transcript,
            transcript_segments = excluded.transcript_segments,
            fetched_at          = excluded.fetched_at
        """,
        row,
    )
    conn.commit()


# ===========================================================================
# DISCOVERY (yt-dlp)
# ===========================================================================

# Shared yt-dlp options. quiet + no_warnings silences the JS-runtime / ffmpeg
# noise (we only ever read metadata, never download video).
_YDL_BASE_OPTS = {
    "quiet": True,
    "no_warnings": True,
    "skip_download": True,
    "noplaylist": True,
    "ignoreerrors": True,
}


def search_candidates(query: str, n: int) -> list[dict]:
    """Flat YouTube search -> lightweight candidate dicts.

    `extract_flat` returns IDs + basic metadata in a single fast call (no per-video
    page loads). We filter out non-video entries, livestreams, and durations outside
    the review window here so we don't waste transcript calls on them.
    """
    opts = {**_YDL_BASE_OPTS, "extract_flat": True}
    search_url = f"ytsearch{n}:{query}"
    try:
        with YoutubeDL(opts) as ydl:
            info = ydl.extract_info(search_url, download=False)
    except Exception as exc:  # noqa: BLE001 - discovery must never crash the run
        log.error("discovery failed for query %r: %s", query, exc)
        return []

    candidates: list[dict] = []
    for entry in (info or {}).get("entries", []) or []:
        if not entry:
            continue
        vid = entry.get("id")
        if not vid:
            continue

        # Skip live / upcoming streams.
        if entry.get("live_status") in ("is_live", "is_upcoming", "post_live"):
            log.info("  skip %s: live_status=%s", vid, entry.get("live_status"))
            continue

        # Duration filter (drop Shorts and very long videos). Unknown duration is
        # kept — flat search occasionally omits it; we'll learn the real length on
        # full extraction.
        duration = entry.get("duration")
        if duration is not None:
            if duration < MIN_DURATION_SECONDS:
                log.info("  skip %s: too short (%ss)", vid, int(duration))
                continue
            if duration > MAX_DURATION_SECONDS:
                log.info("  skip %s: too long (%ss)", vid, int(duration))
                continue

        candidates.append(
            {
                "video_id": vid,
                "title": entry.get("title"),
                "channel": entry.get("channel") or entry.get("uploader"),
                "url": entry.get("url") or f"https://www.youtube.com/watch?v={vid}",
                "view_count": entry.get("view_count"),
                "duration": int(duration) if duration is not None else None,
                "timestamp": entry.get("timestamp"),  # epoch upload time, if present
            }
        )
    return candidates


def fetch_full_metadata(video_id: str) -> dict:
    """Full per-video extraction for the fields flat search omits (likes, publish date).

    Only called for videos we are actually going to store, to keep it cheap.
    Returns {} on failure — the caller falls back to the flat-search metadata.
    """
    url = f"https://www.youtube.com/watch?v={video_id}"
    for attempt in range(1, 3):
        try:
            with YoutubeDL(_YDL_BASE_OPTS) as ydl:
                info = ydl.extract_info(url, download=False)
            if not info:
                return {}
            return {
                "title": info.get("title"),
                "channel": info.get("channel") or info.get("uploader"),
                "view_count": info.get("view_count"),
                "like_count": info.get("like_count"),
                "duration": info.get("duration"),
                "published_at": _to_iso_date(info.get("upload_date"), info.get("timestamp")),
            }
        except Exception as exc:  # noqa: BLE001
            log.warning("  metadata extract failed for %s (attempt %d): %s",
                        video_id, attempt, exc)
            time.sleep(RETRY_BACKOFF_SECONDS * attempt)
    return {}


def _to_iso_date(upload_date, timestamp) -> str | None:
    """Convert yt-dlp's 'YYYYMMDD' (or epoch fallback) to an ISO 'YYYY-MM-DD' date."""
    if upload_date and len(str(upload_date)) == 8:
        s = str(upload_date)
        return f"{s[0:4]}-{s[4:6]}-{s[6:8]}"
    if timestamp:
        try:
            return datetime.fromtimestamp(int(timestamp), tz=timezone.utc).date().isoformat()
        except (ValueError, OverflowError, OSError):
            return None
    return None


# ===========================================================================
# TRANSCRIPTS (youtube-transcript-api)
# ===========================================================================


def _select_transcript(transcript_list):
    """Pick the best transcript: prefer English, else fall back to the first available.

    `find_transcript` honours the language priority list and returns either a manual
    or generated track. If no English exists, we take whatever the video does have
    and record its language code.
    """
    try:
        return transcript_list.find_transcript(PREFERRED_LANGUAGES)
    except NoTranscriptFound:
        for transcript in transcript_list:  # TranscriptList is iterable
            return transcript
    return None


def fetch_transcript(api: YouTubeTranscriptApi, video_id: str) -> dict | None:
    """Fetch one video's transcript. Returns a dict or None.

    Return value:
        {language, is_generated, transcript (joined text), segments (raw list)}  on success
        None                                                                      on permanent failure

    Raises only for *transient* errors (so the caller can retry).
    """
    transcript_list = api.list(video_id)
    transcript = _select_transcript(transcript_list)
    if transcript is None:
        return None

    fetched = transcript.fetch()
    segments = fetched.to_raw_data()  # [{text, start, duration}, ...]
    full_text = " ".join(seg["text"] for seg in segments).strip()
    if not full_text:
        return None

    return {
        "language": transcript.language_code,
        "is_generated": 1 if transcript.is_generated else 0,
        "transcript": full_text,
        "segments": segments,
    }


def attempt_transcript(api: YouTubeTranscriptApi, video_id: str) -> tuple[str, dict | None]:
    """Try to fetch one transcript and classify the outcome.

    Returns one of:
        (TRANSCRIPT_OK, {language, is_generated, transcript, segments})
        (TRANSCRIPT_SKIP, None)     -- no transcript / permanent issue for this video
        (TRANSCRIPT_BLOCKED, None)  -- IP soft-blocked; run-level cooldown applies

    Network blips for a single video get one quick retry; IP-block errors do NOT get
    per-video retries (futile against a systemic block) — they bubble up as BLOCKED.
    """
    for attempt in range(1, MAX_TRANSCRIPT_RETRIES + 2):
        try:
            result = fetch_transcript(api, video_id)
            if result is None:
                log.info("  skip %s: no usable transcript", video_id)
                return TRANSCRIPT_SKIP, None
            return TRANSCRIPT_OK, result
        except BLOCK_TRANSCRIPT_ERRORS as exc:
            log.warning("  blocked %s: %s", video_id, type(exc).__name__)
            return TRANSCRIPT_BLOCKED, None
        except PERMANENT_TRANSCRIPT_ERRORS as exc:
            log.info("  skip %s: %s", video_id, type(exc).__name__)
            return TRANSCRIPT_SKIP, None
        except NETWORK_TRANSCRIPT_ERRORS as exc:
            if attempt <= MAX_TRANSCRIPT_RETRIES:
                wait = RETRY_BACKOFF_SECONDS * attempt
                log.warning("  network %s on %s; retry %d/%d in %.0fs",
                            type(exc).__name__, video_id, attempt,
                            MAX_TRANSCRIPT_RETRIES, wait)
                time.sleep(wait)
                continue
            log.warning("  skip %s: %s persisted", video_id, type(exc).__name__)
            return TRANSCRIPT_SKIP, None
        except Exception as exc:  # noqa: BLE001 - unknown error must not crash the run
            log.warning("  skip %s: unexpected %s: %s",
                        video_id, type(exc).__name__, str(exc)[:120])
            return TRANSCRIPT_SKIP, None
    return TRANSCRIPT_SKIP, None


def handle_block(run_state: dict) -> None:
    """Run-level reaction to a sustained IP block: one cooldown, then abort.

    `run_state` carries {consecutive_blocks, cooled_down} across products.
    """
    if run_state["consecutive_blocks"] < MAX_CONSECUTIVE_BLOCKS:
        return
    if not run_state["cooled_down"]:
        log.warning("Sustained IP block (%d in a row). One-time cooldown: %ds...",
                    run_state["consecutive_blocks"], BLOCK_COOLDOWN_SECONDS)
        time.sleep(BLOCK_COOLDOWN_SECONDS)
        run_state["cooled_down"] = True
        run_state["consecutive_blocks"] = 0
        log.warning("Cooldown done — resuming.")
    else:
        log.error("IP block persists after cooldown. Stopping run; re-run later to "
                  "resume from the database.")
        raise RunAborted()


# ===========================================================================
# PER-PRODUCT PIPELINE
# ===========================================================================


def build_row(product: str, candidate: dict, transcript: dict, metadata: dict) -> dict:
    """Merge flat-search candidate + full metadata + transcript into a DB row.

    Full metadata wins where present; we fall back to the flat-search values so a
    failed metadata extract never blanks out fields we already had.
    """
    return {
        "video_id": candidate["video_id"],
        "product": product,
        "title": metadata.get("title") or candidate.get("title"),
        "channel": metadata.get("channel") or candidate.get("channel"),
        "url": candidate.get("url"),
        "view_count": metadata.get("view_count") if metadata.get("view_count") is not None
        else candidate.get("view_count"),
        "like_count": metadata.get("like_count"),
        "published_at": metadata.get("published_at")
        or _to_iso_date(None, candidate.get("timestamp")),
        "duration_seconds": metadata.get("duration") or candidate.get("duration"),
        "language": transcript["language"],
        "is_generated": transcript["is_generated"],
        "transcript": transcript["transcript"],
        "transcript_segments": json.dumps(transcript["segments"], ensure_ascii=False),
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }


def process_product(
    conn: sqlite3.Connection,
    api: YouTubeTranscriptApi,
    product: str,
    query: str,
    already_stored_ids: set[str],
    run_state: dict,
) -> int:
    """Discover, transcribe, and store videos for one product. Returns stored count.

    May raise RunAborted if an IP block persists past the one-time cooldown.
    """
    log.info("=" * 70)
    log.info("PRODUCT: %s   (query: %r)", product, query)

    stored = count_for_product(conn, product)
    if stored >= TARGET_PER_PRODUCT:
        log.info("  already have %d/%d stored — skipping discovery", stored, TARGET_PER_PRODUCT)
        return stored

    candidates = search_candidates(query, CANDIDATES_PER_PRODUCT)
    log.info("  %d candidates after filtering (need %d more transcripts)",
             len(candidates), TARGET_PER_PRODUCT - stored)

    attempts = 0
    for candidate in candidates:
        if stored >= TARGET_PER_PRODUCT:
            break
        vid = candidate["video_id"]

        # Resume / dedupe: already in the DB (this run or a previous one) — count and skip.
        if vid in already_stored_ids:
            log.info("  have %s already — skipping", vid)
            continue

        attempts += 1
        status, transcript = attempt_transcript(api, vid)
        time.sleep(REQUEST_DELAY_SECONDS)  # politeness

        if status == TRANSCRIPT_BLOCKED:
            run_state["consecutive_blocks"] += 1
            handle_block(run_state)  # may cooldown, or raise RunAborted
            continue

        # A clean response (success or "no transcript") means the IP is healthy.
        run_state["consecutive_blocks"] = 0
        if status == TRANSCRIPT_SKIP:
            continue

        # status == TRANSCRIPT_OK: only now (transcript exists) pay for full metadata.
        metadata = fetch_full_metadata(vid)
        row = build_row(product, candidate, transcript, metadata)
        upsert_video(conn, row)
        already_stored_ids.add(vid)
        stored += 1
        log.info("  stored %d/%d  %s  [lang=%s gen=%s] %s",
                 stored, TARGET_PER_PRODUCT, vid, row["language"],
                 row["is_generated"], (row["title"] or "")[:50])

    log.info("  -> %s: stored %d (tried %d candidates)", product, stored, attempts)
    return stored


# ===========================================================================
# MAIN
# ===========================================================================


def parse_args(argv=None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Phase 1 YouTube review-video scraper.")
    p.add_argument("--db", default=DB_PATH, help=f"SQLite path (default: {DB_PATH})")
    p.add_argument("--limit", type=int, default=None,
                   help="only process the first N products (smoke testing)")
    p.add_argument("--only", default=None,
                   help="process a single product by canonical name")
    p.add_argument("--candidates", type=int, default=CANDIDATES_PER_PRODUCT,
                   help="candidates to fetch per product")
    p.add_argument("--target", type=int, default=TARGET_PER_PRODUCT,
                   help="transcripts to store per product")
    p.add_argument("-v", "--verbose", action="store_true", help="debug logging")
    return p.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)

    # Allow CLI overrides of the per-run knobs (handy for testing).
    global CANDIDATES_PER_PRODUCT, TARGET_PER_PRODUCT
    CANDIDATES_PER_PRODUCT = args.candidates
    TARGET_PER_PRODUCT = args.target

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(message)s",
        datefmt="%H:%M:%S",
        stream=sys.stdout,
    )

    products = PRODUCTS
    if args.only:
        products = [p for p in PRODUCTS if p[0].lower() == args.only.lower()]
        if not products:
            log.error("no product named %r; valid: %s",
                      args.only, ", ".join(name for name, _ in PRODUCTS))
            return 2
    if args.limit:
        products = products[: args.limit]

    log.info("Scraping %d product(s) -> %s (candidates=%d, target=%d)",
             len(products), args.db, CANDIDATES_PER_PRODUCT, TARGET_PER_PRODUCT)

    conn = connect_db(args.db)
    seen_ids = existing_video_ids(conn)

    api = YouTubeTranscriptApi()
    results: dict[str, int] = {name: count_for_product(conn, name) for name, _ in products}
    run_state = {"consecutive_blocks": 0, "cooled_down": False}
    aborted = False
    start = time.monotonic()
    try:
        for i, (name, query) in enumerate(products):
            results[name] = process_product(conn, api, name, query, seen_ids, run_state)
            if i < len(products) - 1:
                time.sleep(INTER_PRODUCT_DELAY)
    except RunAborted:
        aborted = True
        # Refresh counts from the DB so the summary reflects what actually landed.
        for name, _ in products:
            results[name] = count_for_product(conn, name)
    finally:
        conn.close()

    # ---- Run summary ----
    elapsed = time.monotonic() - start
    total = sum(results.values())
    log.info("=" * 70)
    if aborted:
        log.warning("RUN ABORTED EARLY (IP block). Re-run later to resume from the DB.")
    log.info("RUN SUMMARY  (%.0fs, %d total stored)", elapsed, total)
    flagged = []
    for name, _ in products:
        count = results.get(name, 0)
        flag = ""
        if count < UNDER_TARGET_FLAG:
            flag = f"  <-- UNDER {UNDER_TARGET_FLAG}"
            flagged.append(name)
        log.info("  %-32s %2d / %d%s", name, count, TARGET_PER_PRODUCT, flag)
    if flagged:
        log.warning("Products under %d: %s", UNDER_TARGET_FLAG, ", ".join(flagged))
    else:
        log.info("All products met the >= %d threshold.", UNDER_TARGET_FLAG)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
