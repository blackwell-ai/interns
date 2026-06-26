#!/usr/bin/env python3
"""Extract reviewer persona + foundation verdict from each collected clip.

Reads clips from foundation.db, runs gpt-5.5 once per clip, writes a structured
record to the clip_analysis table. Dimensions are FIXED to the shopper's stated
needs so every foundation is scored on the same axes (and we can surface a wear
test from a reviewer whose skin matches hers).

  cd platform/scraper && source .venv/bin/activate
  set -a; . ../../credentials/.env; set +a
  python demo/extract_foundation.py --db demo/foundation.db
"""
import argparse
import json
import os
import sqlite3
import sys

from openai import OpenAI

MODEL = os.environ.get("EXTRACT_MODEL", "gpt-5.5")
client = OpenAI()

DIMENSIONS = [
    ("oil_control_matte",   "Stays matte / controls oil and shine over the day"),
    ("longevity_10h",       "Lasts a full ~10 hour day without breaking down/fading"),
    ("breakouts_clogging",  "Does NOT clog pores or cause breakouts (positive = skin stayed clear)"),
    ("oxidation_resistance","Does NOT oxidize darker/orange after application (positive = true to shade)"),
    ("coverage",            "Coverage strength and how well it hides acne/redness/texture"),
    ("shade_warm_olive",    "Has a true warm/olive shade match (positive = matched, no grey/peach pull)"),
    ("photo_flashback",     "Photographs well with flash, no white flashback (positive = photo-safe)"),
    ("value",               "Worth the price for the result"),
]

SCHEMA = {
    "name": "foundation_review",
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "reviewer_persona": {
                "type": "object", "additionalProperties": False,
                "properties": {
                    "skin_type": {"type": "string", "description": "oily | combination | dry | normal | sensitive; combine if stated"},
                    "acne_prone": {"type": ["boolean", "null"]},
                    "skin_tone_depth": {"type": "string", "description": "fair | light | medium | tan | deep | unknown"},
                    "undertone": {"type": "string", "description": "warm | cool | neutral | olive | unknown"},
                    "shade_used": {"type": ["string", "null"], "description": "exact shade named, e.g. NC42, 480"},
                    "age_range": {"type": ["string", "null"]},
                },
                "required": ["skin_type", "acne_prone", "skin_tone_depth", "undertone", "shade_used", "age_range"],
            },
            "verdict": {"type": "string", "description": "one or two sentence overall take"},
            "overall_sentiment": {"type": "string", "enum": ["positive", "mixed", "negative"]},
            "recommends": {"type": ["boolean", "null"]},
            "would_repurchase": {"type": ["boolean", "null"]},
            "dimensions": {
                "type": "object", "additionalProperties": False,
                "properties": {
                    k: {
                        "type": ["object", "null"], "additionalProperties": False,
                        "properties": {
                            "score": {"type": "number", "description": "-1 worst to 1 best, on the meaning given"},
                            "evidence": {"type": "string", "description": "a near-verbatim quote from the reviewer"},
                        },
                        "required": ["score", "evidence"],
                    } for k, _ in DIMENSIONS
                },
                "required": [k for k, _ in DIMENSIONS],
            },
            "is_sponsored": {"type": "boolean"},
            "sponsorship_evidence": {"type": ["string", "null"]},
            "key_quotes": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["reviewer_persona", "verdict", "overall_sentiment", "recommends",
                     "would_repurchase", "dimensions", "is_sponsored", "sponsorship_evidence", "key_quotes"],
    },
}

SYS = (
    "You analyze a single YouTube foundation review transcript and extract a strict "
    "structured record. Score ONLY from what the reviewer actually says or demonstrates; "
    "if a dimension is not addressed, set its score to 0 and evidence to 'not discussed'. "
    "For breakouts_clogging and oxidation_resistance, a POSITIVE score means the GOOD "
    "outcome (skin stayed clear / shade stayed true). Capture the reviewer's own skin "
    "type, tone, undertone and shade so we can match them to a shopper. Flag sponsorship "
    "only with explicit evidence (gifted, #ad, paid, brand sent it). Quotes must be the "
    "reviewer's real words.\n\n"
    "Dimension meanings:\n" + "\n".join(f"- {k}: {d}" for k, d in DIMENSIONS)
)


def extract_one(product, title, channel, transcript):
    user = (f"PRODUCT: {product}\nVIDEO: {title}\nCHANNEL: {channel}\n\nTRANSCRIPT:\n{transcript[:14000]}")
    r = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "system", "content": SYS}, {"role": "user", "content": user}],
        response_format={"type": "json_schema", "json_schema": SCHEMA},
        max_completion_tokens=4000,
    )
    return json.loads(r.choices[0].message.content)


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--db", default="demo/foundation.db")
    p.add_argument("--force", action="store_true", help="re-extract clips already done")
    args = p.parse_args(argv)

    conn = sqlite3.connect(args.db)
    conn.execute("""CREATE TABLE IF NOT EXISTS clip_analysis (
        url TEXT PRIMARY KEY, product TEXT, extracted TEXT, model TEXT,
        error TEXT, analyzed_at TEXT)""")
    conn.commit()

    rows = conn.execute("SELECT url, product, title, channel, transcript FROM clips").fetchall()
    done = {r[0] for r in conn.execute("SELECT url FROM clip_analysis WHERE error IS NULL").fetchall()}
    todo = [r for r in rows if args.force or r[0] not in done]
    print(f"{len(rows)} clips, {len(todo)} to analyze with {MODEL}")

    for url, product, title, channel, transcript in todo:
        if not transcript or len(transcript) < 400:
            print(f"  skip (thin transcript): {title[:50]}")
            continue
        try:
            rec = extract_one(product, title, channel, transcript)
            persona = rec["reviewer_persona"]
            conn.execute(
                """INSERT INTO clip_analysis (url,product,extracted,model,error,analyzed_at)
                   VALUES (?,?,?,?,NULL,datetime('now'))
                   ON CONFLICT(url) DO UPDATE SET extracted=excluded.extracted,
                     model=excluded.model, error=NULL, analyzed_at=datetime('now')""",
                (url, product, json.dumps(rec), MODEL))
            conn.commit()
            print(f"  ok [{persona['skin_type']:18} {persona['skin_tone_depth']:6} {str(persona['undertone'])[:6]:6} {str(persona['shade_used'])[:6]:6}] {title[:42]}")
        except Exception as e:
            conn.execute(
                """INSERT INTO clip_analysis (url,product,extracted,model,error,analyzed_at)
                   VALUES (?,?,NULL,?,?,datetime('now'))
                   ON CONFLICT(url) DO UPDATE SET error=excluded.error""",
                (url, product, MODEL, f"{type(e).__name__}: {str(e)[:120]}"))
            conn.commit()
            print(f"  FAIL {title[:42]}: {type(e).__name__}: {str(e)[:100]}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
