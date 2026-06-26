#!/usr/bin/env python3
"""Per-reviewer persona + real-world OUTCOMES, for segmented cohort stats.

For each wear-test clip we pull the reviewer's skin profile and what actually
happened to their skin: did it stay matte, how many hours it lasted, did it break
them out, did it oxidize. Aggregating these over reviewers who match a shopper's
exact profile yields the numbers star ratings and ChatGPT cannot produce
("9 of 11 people with your skin were still matte at hour 8").

  set -a; . ../../credentials/.env; set +a
  python demo/extract_outcomes.py --db demo/foundation_wide.db
"""
import argparse
import json
import os
import sqlite3
import sys

from openai import OpenAI

MODEL = os.environ.get("OUTCOME_MODEL", "gpt-4.1-mini")
client = OpenAI()

SCHEMA = {
    "name": "wear_outcome",
    "schema": {
        "type": "object", "additionalProperties": False,
        "properties": {
            "product_reviewed": {"type": "string", "description": "the foundation actually worn in this video; '' if unclear"},
            "persona": {
                "type": "object", "additionalProperties": False,
                "properties": {
                    "skin_type": {"type": "string", "description": "oily | combination | dry | normal | sensitive (combine if stated), or unknown"},
                    "acne_prone": {"type": "string", "enum": ["yes", "no", "unknown"]},
                    "skin_tone_depth": {"type": "string", "enum": ["fair", "light", "medium", "tan", "deep", "unknown"]},
                    "undertone": {"type": "string", "enum": ["warm", "cool", "neutral", "olive", "unknown"]},
                    "shade_used": {"type": ["string", "null"]},
                },
                "required": ["skin_type", "acne_prone", "skin_tone_depth", "undertone", "shade_used"],
            },
            "outcomes": {
                "type": "object", "additionalProperties": False,
                "properties": {
                    "stayed_matte": {"type": "string", "enum": ["yes", "mostly", "no", "not_tested"], "description": "did it control oil / stay matte through the day"},
                    "wear_hours": {"type": ["number", "null"], "description": "hours it looked good before breaking down, if stated/tested"},
                    "broke_out": {"type": "string", "enum": ["yes", "no", "not_mentioned"]},
                    "oxidized": {"type": "string", "enum": ["yes", "no", "not_mentioned"], "description": "turned darker/orange after wear"},
                    "would_repurchase": {"type": "string", "enum": ["yes", "no", "not_mentioned"]},
                    "overall": {"type": "string", "enum": ["positive", "mixed", "negative"]},
                },
                "required": ["stayed_matte", "wear_hours", "broke_out", "oxidized", "would_repurchase", "overall"],
            },
            "is_sponsored": {"type": "boolean"},
            "key_quote": {"type": "string", "description": "one short verbatim quote capturing the wear outcome"},
        },
        "required": ["product_reviewed", "persona", "outcomes", "is_sponsored", "key_quote"],
    },
}

SYS = (
    "You read one YouTube foundation wear-test transcript and extract the reviewer's "
    "skin profile and the real outcome of wearing the foundation. Only use what the "
    "reviewer actually says or demonstrates; use 'not_tested'/'not_mentioned'/'unknown' "
    "when it isn't covered. 'stayed_matte' is about oil control over the day. 'oxidized' "
    "means the shade turned darker or orange. Flag sponsorship only with explicit "
    "evidence (gifted, #ad, paid). The key_quote must be the reviewer's real words."
)


def extract(title, channel, transcript):
    r = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "system", "content": SYS},
                  {"role": "user", "content": f"VIDEO: {title}\nCHANNEL: {channel}\n\nTRANSCRIPT:\n{transcript[:13000]}"}],
        response_format={"type": "json_schema", "json_schema": SCHEMA},
        max_completion_tokens=1200,
    )
    return json.loads(r.choices[0].message.content)


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--db", default="demo/foundation_wide.db")
    p.add_argument("--force", action="store_true")
    args = p.parse_args(argv)
    conn = sqlite3.connect(args.db)
    conn.execute("""CREATE TABLE IF NOT EXISTS clip_outcomes (
        url TEXT PRIMARY KEY, product TEXT, extracted TEXT, model TEXT, error TEXT, analyzed_at TEXT)""")
    conn.commit()
    rows = conn.execute("SELECT url, product, title, channel, transcript FROM clips").fetchall()
    done = {r[0] for r in conn.execute("SELECT url FROM clip_outcomes WHERE error IS NULL")}
    todo = [r for r in rows if args.force or r[0] not in done]
    print(f"{len(rows)} clips, {len(todo)} to analyze with {MODEL}", flush=True)
    ok = 0
    for url, product, title, channel, transcript in todo:
        if not transcript or len(transcript) < 400:
            continue
        try:
            rec = extract(title, channel, transcript)
            conn.execute("""INSERT INTO clip_outcomes (url,product,extracted,model,error,analyzed_at)
                VALUES (?,?,?,?,NULL,datetime('now'))
                ON CONFLICT(url) DO UPDATE SET extracted=excluded.extracted, error=NULL, analyzed_at=datetime('now')""",
                (url, product, json.dumps(rec), MODEL))
            conn.commit(); ok += 1
            if ok % 20 == 0:
                print(f"  {ok}/{len(todo)}", flush=True)
        except Exception as e:
            conn.execute("""INSERT INTO clip_outcomes (url,product,extracted,model,error,analyzed_at)
                VALUES (?,?,NULL,?,?,datetime('now')) ON CONFLICT(url) DO UPDATE SET error=excluded.error""",
                (url, product, MODEL, f"{type(e).__name__}: {str(e)[:120]}"))
            conn.commit()
            print(f"  FAIL {title[:40]}: {e}", file=sys.stderr)
    print(f"done: {ok} analyzed", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
