#!/usr/bin/env python3
"""
Product Quality API — Phase 2 processor (transcript -> structured quality data).

Turns the raw review transcripts collected in Phase 1 (`videos` table) into
structured, queryable product-quality records using an OpenAI model (e.g. gpt-5.5).

THE KEY IDEA — attributes are NOT decided in advance.
Instead of a fixed schema baked in by us, the quality *dimensions* are DISCOVERED
from the data, per product, because what matters for a water bottle (leak-proofing,
insulation, cleaning) is different from a hair tool (heat damage, curl longevity).
So the pipeline runs in two stages:

  Stage 1 — DISCOVER  (per product):
      Read all of a product's transcripts and ask the model to surface the
      recurring quality dimensions reviewers ACTUALLY talk about. Stored in
      `product_dimensions`.

  Stage 2 — EXTRACT  (per video):
      For each transcript, score the video against its product's discovered
      dimensions, plus a set of universal fields (verdict, pros/cons, sponsorship,
      evidence quotes, confidence). Stored in `video_analysis.extracted` (JSON).

The discovered dimensions are turned into a strict JSON Schema and handed to the
model as a structured-output contract, so the model is forced to score exactly the
dimensions that emerged from the data — emergent attributes, enforced mechanically.

Usage:
    export OPENAI_API_KEY=sk-...
    python processor.py                       # discover + extract for all products
    python processor.py --only "Oura Ring"    # one product
    python processor.py --limit 1             # first product only
    python processor.py --discover-only       # stage 1 only (preview the dimensions)
    python processor.py --force               # re-discover + re-extract everything
    python processor.py --dry-run             # assemble prompts/schema, no API calls
    python processor.py --model gpt-5.5       # pick the model
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sqlite3
import sys
import time
from datetime import datetime, timezone

# ===========================================================================
# CONFIG
# ===========================================================================

DB_PATH = "videos.db"

# Model. Override with --model or OPENAI_MODEL. "gpt-5.5" per the brief; set this to
# whatever OpenAI model your key can access.
DEFAULT_MODEL = os.environ.get("OPENAI_MODEL", "gpt-5.5")

# Discovery (stage 1)
MIN_TRANSCRIPTS_TO_DISCOVER = 3      # need a few reviews before patterns are meaningful
DISCOVER_TARGET_DIMENSIONS = "4 to 8"  # guidance to the model (not hard-enforced)
DISCOVER_CHARS_PER_TRANSCRIPT = 4500  # truncate each transcript in the discovery prompt

# Extraction (stage 2)
EXTRACT_MAX_TRANSCRIPT_CHARS = 14000  # truncate a single transcript for extraction

# OpenAI call robustness
MAX_API_RETRIES = 3
API_BACKOFF_SECONDS = 4.0
REQUEST_DELAY_SECONDS = 0.5           # small breather between calls

log = logging.getLogger("processor")


# ===========================================================================
# DATABASE
# ===========================================================================

DIMENSIONS_SCHEMA = """
CREATE TABLE IF NOT EXISTS product_dimensions (
    product       TEXT PRIMARY KEY,
    category      TEXT,
    dimensions    TEXT,          -- JSON: [{slug, name, definition, prevalence}]
    n_transcripts INTEGER,
    model         TEXT,
    discovered_at TEXT
);
"""

ANALYSIS_SCHEMA = """
CREATE TABLE IF NOT EXISTS video_analysis (
    video_id    TEXT PRIMARY KEY,   -- FK -> videos.video_id
    product     TEXT,
    status      TEXT,               -- pending | running | complete | error
    extracted   TEXT,               -- JSON: the validated quality record
    model       TEXT,
    error       TEXT,
    analyzed_at TEXT
);
"""


def connect_db(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute(DIMENSIONS_SCHEMA)
    conn.execute(ANALYSIS_SCHEMA)
    conn.commit()
    return conn


def load_products(conn: sqlite3.Connection) -> list[str]:
    return [r["product"] for r in conn.execute(
        "SELECT product, COUNT(*) n FROM videos GROUP BY product ORDER BY product")]


def load_transcripts(conn: sqlite3.Connection, product: str) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT video_id, title, channel, transcript FROM videos "
        "WHERE product = ? AND transcript IS NOT NULL AND transcript != '' "
        "ORDER BY view_count DESC",
        (product,),
    ).fetchall()


def get_saved_dimensions(conn: sqlite3.Connection, product: str) -> dict | None:
    row = conn.execute(
        "SELECT category, dimensions FROM product_dimensions WHERE product = ?",
        (product,)).fetchone()
    if not row:
        return None
    return {"category": row["category"], "dimensions": json.loads(row["dimensions"])}


def save_dimensions(conn, product, category, dimensions, n_transcripts, model) -> None:
    conn.execute(
        """
        INSERT INTO product_dimensions (product, category, dimensions, n_transcripts, model, discovered_at)
        VALUES (:product, :category, :dimensions, :n, :model, :ts)
        ON CONFLICT(product) DO UPDATE SET
            category=excluded.category, dimensions=excluded.dimensions,
            n_transcripts=excluded.n_transcripts, model=excluded.model,
            discovered_at=excluded.discovered_at
        """,
        {"product": product, "category": category,
         "dimensions": json.dumps(dimensions, ensure_ascii=False),
         "n": n_transcripts, "model": model,
         "ts": datetime.now(timezone.utc).isoformat()},
    )
    conn.commit()


def get_analysis_status(conn: sqlite3.Connection, video_id: str) -> str | None:
    row = conn.execute("SELECT status FROM video_analysis WHERE video_id = ?",
                       (video_id,)).fetchone()
    return row["status"] if row else None


def save_analysis(conn, video_id, product, status, extracted, model, error=None) -> None:
    conn.execute(
        """
        INSERT INTO video_analysis (video_id, product, status, extracted, model, error, analyzed_at)
        VALUES (:vid, :product, :status, :extracted, :model, :error, :ts)
        ON CONFLICT(video_id) DO UPDATE SET
            product=excluded.product, status=excluded.status, extracted=excluded.extracted,
            model=excluded.model, error=excluded.error, analyzed_at=excluded.analyzed_at
        """,
        {"vid": video_id, "product": product, "status": status,
         "extracted": json.dumps(extracted, ensure_ascii=False) if extracted is not None else None,
         "model": model, "error": error,
         "ts": datetime.now(timezone.utc).isoformat()},
    )
    conn.commit()


# ===========================================================================
# SCHEMA BUILDING (emergent dimensions -> strict JSON Schema)
# ===========================================================================

def slugify(name: str) -> str:
    """Turn a discovered dimension name into a safe snake_case JSON key."""
    s = re.sub(r"[^a-z0-9]+", "_", name.strip().lower()).strip("_")
    return s or "dimension"


def dedupe_slugs(dimensions: list[dict]) -> list[dict]:
    """Ensure every dimension has a unique slug key."""
    seen: dict[str, int] = {}
    out = []
    for d in dimensions:
        base = slugify(d.get("name", "dimension"))
        if base in seen:
            seen[base] += 1
            slug = f"{base}_{seen[base]}"
        else:
            seen[base] = 0
            slug = base
        out.append({**d, "slug": slug})
    return out


SENTIMENT_ENUM = ["positive", "mostly_positive", "mixed", "mostly_negative",
                  "negative", "not_discussed"]
YESNO_ENUM = ["yes", "no", "unclear"]


def build_extraction_schema(dimensions: list[dict]) -> dict:
    """Build a strict OpenAI JSON Schema whose `dimensions` keys ARE the discovered ones.

    Every discovered dimension becomes a required property scored with
    {score, sentiment, evidence}. This is how emergent attributes get enforced.
    """
    dim_props = {}
    for d in dimensions:
        dim_props[d["slug"]] = {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                # null when the video doesn't address this dimension
                "score": {"type": ["number", "null"],
                          "description": "-1.0 (very negative) .. 1.0 (very positive); null if not discussed"},
                "sentiment": {"type": "string", "enum": SENTIMENT_ENUM},
                "evidence": {"type": "string",
                             "description": "short quote/paraphrase from the transcript, or '' if not discussed"},
            },
            "required": ["score", "sentiment", "evidence"],
        }

    dimensions_obj = {
        "type": "object",
        "additionalProperties": False,
        "properties": dim_props,
        "required": list(dim_props.keys()),
    }

    schema = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "brand": {"type": "string"},
            "category": {"type": "string"},
            "overall_sentiment": {"type": "number",
                                  "description": "-1.0 .. 1.0 overall stance toward the product"},
            "verdict": {"type": "string", "description": "one-sentence bottom line"},
            "dimensions": dimensions_obj,
            "pros": {"type": "array", "items": {"type": "string"}},
            "cons": {"type": "array", "items": {"type": "string"}},
            "best_for": {"type": "array", "items": {"type": "string"}},
            "not_for": {"type": "array", "items": {"type": "string"}},
            "demonstrated_use_cases": {"type": "array", "items": {"type": "string"}},
            "would_keep_using": {"type": "string", "enum": YESNO_ENUM},
            "worth_the_price": {"type": "string", "enum": YESNO_ENUM},
            "is_sponsored": {"type": "boolean"},
            "sponsorship_evidence": {"type": "string"},
            "key_quotes": {"type": "array", "items": {"type": "string"}},
            "confidence": {"type": "number", "description": "0.0 .. 1.0 self-rated extraction confidence"},
        },
        "required": [
            "brand", "category", "overall_sentiment", "verdict", "dimensions",
            "pros", "cons", "best_for", "not_for", "demonstrated_use_cases",
            "would_keep_using", "worth_the_price", "is_sponsored",
            "sponsorship_evidence", "key_quotes", "confidence",
        ],
    }
    return schema


DISCOVERY_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "category": {"type": "string",
                     "description": "concise product category inferred from the reviews"},
        "dimensions": {
            "type": "array",
            "description": "the recurring quality dimensions reviewers actually evaluate",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "name": {"type": "string", "description": "short human label, e.g. 'Leak-proofing'"},
                    "definition": {"type": "string", "description": "what this dimension covers"},
                    "prevalence": {"type": "integer",
                                   "description": "how many of the provided reviews discuss it"},
                },
                "required": ["name", "definition", "prevalence"],
            },
        },
    },
    "required": ["category", "dimensions"],
}


# ===========================================================================
# PROMPTS
# ===========================================================================

def build_discovery_messages(product: str, transcripts: list[sqlite3.Row]) -> list[dict]:
    blocks = []
    for i, r in enumerate(transcripts, 1):
        text = (r["transcript"] or "")[:DISCOVER_CHARS_PER_TRANSCRIPT]
        blocks.append(f"--- REVIEW {i} (channel: {r['channel']}) ---\n{text}")
    corpus = "\n\n".join(blocks)
    system = (
        "You are a product-research analyst. You identify the quality dimensions that "
        "reviewers genuinely care about for a product, grounded ONLY in what they say. "
        "Do not impose a generic template; let the recurring themes emerge from the data."
    )
    user = (
        f"Product: {product}\n\n"
        f"Below are {len(transcripts)} YouTube review transcripts for this product.\n"
        f"Identify the {DISCOVER_TARGET_DIMENSIONS} quality dimensions that recur across "
        f"these reviews — the specific things reviewers repeatedly praise or criticize. "
        f"Prefer concrete, product-specific dimensions over vague ones. For each, give a "
        f"short name, a one-line definition, and how many of the reviews discuss it.\n\n"
        f"{corpus}"
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def build_extraction_messages(product: str, dimensions: list[dict], transcript: str) -> list[dict]:
    dim_lines = "\n".join(f"- {d['slug']}: {d['name']} — {d.get('definition','')}"
                          for d in dimensions)
    system = (
        "You extract structured product-quality data from a single review transcript. "
        "Base every field strictly on what the reviewer says — no outside knowledge. "
        "Score each dimension from the transcript; if a dimension is not discussed, set "
        "score=null, sentiment='not_discussed', evidence=''. Quote briefly as evidence."
    )
    user = (
        f"Product: {product}\n\n"
        f"Score these discovered quality dimensions (use the exact keys):\n{dim_lines}\n\n"
        f"Transcript:\n{transcript[:EXTRACT_MAX_TRANSCRIPT_CHARS]}"
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


# ===========================================================================
# OPENAI CALL
# ===========================================================================

def load_dotenv(path: str = ".env") -> None:
    """Minimal .env loader (no dependency). Real environment variables win."""
    if not os.path.exists(path):
        return
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                if line.startswith("export "):
                    line = line[len("export "):]
                key, _, val = line.partition("=")
                key = key.strip()
                val = val.strip().strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = val
    except OSError:
        pass


def make_client():
    """Create an OpenAI client. Imported lazily so the module loads without a key."""
    from openai import OpenAI
    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is not set. Add it to .env or `export OPENAI_API_KEY=sk-...`")
    return OpenAI()


def call_structured(client, model: str, messages: list[dict],
                    schema: dict, schema_name: str) -> dict:
    """One structured-output call returning a validated dict, with simple retries."""
    response_format = {
        "type": "json_schema",
        "json_schema": {"name": schema_name, "schema": schema, "strict": True},
    }
    last_err = None
    for attempt in range(1, MAX_API_RETRIES + 1):
        try:
            resp = client.chat.completions.create(
                model=model, messages=messages, response_format=response_format,
            )
            content = resp.choices[0].message.content
            return json.loads(content)
        except Exception as exc:  # noqa: BLE001 - retry transient API errors
            last_err = exc
            wait = API_BACKOFF_SECONDS * attempt
            log.warning("  API error (attempt %d/%d): %s; retrying in %.0fs",
                        attempt, MAX_API_RETRIES, str(exc)[:140], wait)
            time.sleep(wait)
    raise RuntimeError(f"OpenAI call failed after {MAX_API_RETRIES} attempts: {last_err}")


# ===========================================================================
# STAGES
# ===========================================================================

def discover_dimensions(client, model, product, transcripts) -> dict:
    """Stage 1: surface the recurring quality dimensions for one product."""
    messages = build_discovery_messages(product, transcripts)
    result = call_structured(client, model, messages, DISCOVERY_SCHEMA, "discovered_dimensions")
    dims = dedupe_slugs(result.get("dimensions", []))
    return {"category": result.get("category", ""), "dimensions": dims}


def extract_video(client, model, product, dimensions, transcript) -> dict:
    """Stage 2: extract one video's structured quality record."""
    schema = build_extraction_schema(dimensions)
    messages = build_extraction_messages(product, dimensions, transcript)
    return call_structured(client, model, messages, schema, "product_quality_record")


# ===========================================================================
# ORCHESTRATION
# ===========================================================================

def process_product(conn, client, model, product, *, force=False) -> dict:
    """Discover dimensions (if needed) then extract every transcript for a product."""
    log.info("=" * 70)
    log.info("PRODUCT: %s", product)
    transcripts = load_transcripts(conn, product)
    if len(transcripts) < MIN_TRANSCRIPTS_TO_DISCOVER:
        log.warning("  only %d transcripts (< %d) — skipping discovery for now",
                    len(transcripts), MIN_TRANSCRIPTS_TO_DISCOVER)
        return {"product": product, "extracted": 0, "skipped": len(transcripts), "errors": 0}

    # ---- Stage 1: dimensions ----
    saved = None if force else get_saved_dimensions(conn, product)
    if saved:
        dims = saved["dimensions"]
        log.info("  using %d saved dimensions: %s",
                 len(dims), ", ".join(d["name"] for d in dims))
    else:
        log.info("  discovering dimensions from %d transcripts...", len(transcripts))
        discovered = discover_dimensions(client, model, product, transcripts)
        dims = discovered["dimensions"]
        save_dimensions(conn, product, discovered["category"], dims, len(transcripts), model)
        log.info("  [%s] discovered %d dimensions: %s", discovered["category"],
                 len(dims), ", ".join(d["name"] for d in dims))
        time.sleep(REQUEST_DELAY_SECONDS)

    # ---- Stage 2: per-video extraction ----
    extracted = skipped = errors = 0
    for r in transcripts:
        vid = r["video_id"]
        if not force and get_analysis_status(conn, vid) == "complete":
            skipped += 1
            continue
        save_analysis(conn, vid, product, "running", None, model)
        try:
            record = extract_video(client, model, product, dims, r["transcript"])
            record["source_video_id"] = vid
            save_analysis(conn, vid, product, "complete", record, model)
            extracted += 1
            log.info("  extracted %s  verdict=%r sent=%.2f sponsored=%s",
                     vid, (record.get("verdict") or "")[:60],
                     record.get("overall_sentiment", 0.0), record.get("is_sponsored"))
        except Exception as exc:  # noqa: BLE001 - one bad video never stops the product
            errors += 1
            save_analysis(conn, vid, product, "error", None, model, error=str(exc)[:300])
            log.warning("  ERROR extracting %s: %s", vid, str(exc)[:140])
        time.sleep(REQUEST_DELAY_SECONDS)

    log.info("  -> %s: extracted %d, skipped %d, errors %d", product, extracted, skipped, errors)
    return {"product": product, "extracted": extracted, "skipped": skipped, "errors": errors}


def dry_run(conn, products) -> None:
    """Assemble and preview prompts/schema without any API calls."""
    log.info("DRY RUN — no API calls. Previewing prompts/schema.")
    for product in products:
        transcripts = load_transcripts(conn, product)
        log.info("=" * 70)
        log.info("PRODUCT: %s (%d transcripts)", product, len(transcripts))
        if not transcripts:
            log.info("  no transcripts — nothing to preview")
            continue
        msgs = build_discovery_messages(product, transcripts)
        log.info("  discovery: system=%d chars, user=%d chars",
                 len(msgs[0]["content"]), len(msgs[1]["content"]))
        # Show the extraction schema shape using placeholder dimensions.
        demo_dims = dedupe_slugs([{"name": "Example Dimension A", "definition": "x"},
                                  {"name": "Example Dimension B", "definition": "y"}])
        schema = build_extraction_schema(demo_dims)
        log.info("  extraction schema: %d top-level fields; dimension keys -> %s",
                 len(schema["properties"]),
                 list(schema["properties"]["dimensions"]["properties"].keys()))
    log.info("Dry run complete.")


# ===========================================================================
# MAIN
# ===========================================================================

def parse_args(argv=None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Phase 2: extract structured quality data from transcripts.")
    p.add_argument("--db", default=DB_PATH)
    p.add_argument("--model", default=None, help=f"OpenAI model (default {DEFAULT_MODEL})")
    p.add_argument("--only", default=None, help="single product by name")
    p.add_argument("--limit", type=int, default=None, help="first N products only")
    p.add_argument("--discover-only", action="store_true", help="stage 1 only")
    p.add_argument("--force", action="store_true", help="re-discover and re-extract everything")
    p.add_argument("--dry-run", action="store_true", help="assemble prompts/schema, no API calls")
    p.add_argument("-v", "--verbose", action="store_true")
    return p.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(message)s", datefmt="%H:%M:%S", stream=sys.stdout)

    load_dotenv()  # pick up OPENAI_API_KEY / OPENAI_MODEL from .env if present
    args.model = args.model or os.environ.get("OPENAI_MODEL") or "gpt-5.5"

    conn = connect_db(args.db)
    products = load_products(conn)
    if args.only:
        products = [p for p in products if p.lower() == args.only.lower()]
        if not products:
            log.error("no product named %r in the DB", args.only)
            return 2
    if args.limit:
        products = products[: args.limit]
    if not products:
        log.error("no products with transcripts found in %s — run the Phase 1 scraper first", args.db)
        return 2

    if args.dry_run:
        dry_run(conn, products)
        conn.close()
        return 0

    try:
        client = make_client()
    except RuntimeError as exc:
        log.error("%s", exc)
        conn.close()
        return 2

    log.info("Phase 2 processing %d product(s) with model=%s", len(products), args.model)
    results = []
    start = time.monotonic()
    try:
        for product in products:
            if args.discover_only:
                transcripts = load_transcripts(conn, product)
                if len(transcripts) < MIN_TRANSCRIPTS_TO_DISCOVER:
                    log.warning("PRODUCT %s: too few transcripts", product)
                    continue
                discovered = discover_dimensions(client, args.model, product, transcripts)
                save_dimensions(conn, product, discovered["category"],
                                discovered["dimensions"], len(transcripts), args.model)
                log.info("PRODUCT %s [%s]: %s", product, discovered["category"],
                         ", ".join(d["name"] for d in discovered["dimensions"]))
            else:
                results.append(process_product(conn, client, args.model, product, force=args.force))
    finally:
        conn.close()

    # ---- Run summary ----
    if not args.discover_only:
        elapsed = time.monotonic() - start
        total = sum(r["extracted"] for r in results)
        log.info("=" * 70)
        log.info("RUN SUMMARY  (%.0fs, %d newly extracted)", elapsed, total)
        for r in results:
            flag = "  <-- has errors" if r["errors"] else ""
            log.info("  %-32s extracted %2d  skipped %2d  errors %d%s",
                     r["product"], r["extracted"], r["skipped"], r["errors"], flag)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
