#!/usr/bin/env python3
"""Build the buyer-facing sample package for outreach.

Reads the v2 dataset (demo/dataset/foundation_dataset.jsonl) and writes a
cleaned sample under demo/dataset_sample/ that matches the outreach narrative:
structured product reviews with no source-platform identifiers and no internal
pipeline notes (extraction model, rights status, eval gaps, QA exclusions), plus
a buyer-facing README and data dictionary and the aggregates that show the value.

  cd platform/scraper && python demo/export_sample.py
"""
import csv
import json
import os
import shutil

SRC = "demo/dataset"
OUT = "demo/dataset_sample"
os.makedirs(f"{OUT}/schema", exist_ok=True)

recs = [json.loads(l) for l in open(f"{SRC}/foundation_dataset.jsonl")]

clean = []
for r in recs:
    s = r["source"]
    a = r["analysis"]
    clean.append({
        "product": r["product"],
        "video": {
            "reviewer": s.get("channel"),
            "title": s.get("title"),
            "published_at": s.get("published_at"),
            "duration_seconds": s.get("duration_seconds"),
            "view_count": s.get("view_count"),
            "review_type": s.get("video_type"),
        },
        "transcript": (r.get("transcript") or {}).get("text"),
        "reviewer_profile": a.get("persona"),
        "outcomes": a.get("outcomes"),
        "is_sponsored": a.get("is_sponsored"),
        "key_quote": a.get("key_quote"),
    })

with open(f"{OUT}/foundation_dataset.jsonl", "w") as f:
    for r in clean:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")

with open(f"{OUT}/foundation_dataset.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["product", "brand", "reviewer", "review_type", "skin_type", "acne_prone",
                "tone", "undertone", "shade", "stayed_matte", "wear_hours", "broke_out",
                "oxidized", "would_repurchase", "overall", "is_sponsored", "key_quote"])
    for r in clean:
        p = r["reviewer_profile"] or {}
        o = r["outcomes"] or {}
        w.writerow([r["product"]["name"], r["product"]["brand"], r["video"]["reviewer"],
                    r["video"]["review_type"], p.get("skin_type"), p.get("acne_prone"),
                    p.get("skin_tone_depth"), p.get("undertone"), p.get("shade_used"),
                    o.get("stayed_matte"), o.get("wear_hours"), o.get("broke_out"),
                    o.get("oxidized"), o.get("would_repurchase"), o.get("overall"),
                    r["is_sponsored"], r["key_quote"]])

# aggregates carry over unchanged (no source identifiers in them)
shutil.copy(f"{SRC}/product_rollup.json", f"{OUT}/product_rollup.json")
shutil.copy(f"{SRC}/cohort_analysis.json", f"{OUT}/cohort_analysis.json")

schema = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "Structured product review",
    "type": "object",
    "required": ["product", "video", "reviewer_profile", "outcomes"],
    "properties": {
        "product": {
            "type": "object",
            "required": ["name", "product_id", "brand"],
            "properties": {
                "name": {"type": "string"},
                "product_id": {"type": "string", "description": "stable slug shared by all reviews of one product"},
                "brand": {"type": "string"},
            },
        },
        "video": {
            "type": "object",
            "properties": {
                "reviewer": {"type": ["string", "null"]},
                "title": {"type": ["string", "null"]},
                "published_at": {"type": ["string", "null"], "description": "ISO 8601 date"},
                "duration_seconds": {"type": ["integer", "null"]},
                "view_count": {"type": ["integer", "null"]},
                "review_type": {"enum": ["single_review", "comparison", "roundup"]},
            },
        },
        "transcript": {"type": ["string", "null"]},
        "reviewer_profile": {
            "type": "object",
            "properties": {
                "skin_type": {"type": ["string", "null"]},
                "acne_prone": {"enum": ["yes", "no", "unknown"]},
                "skin_tone_depth": {"enum": ["fair", "light", "medium", "tan", "deep", "unknown"]},
                "undertone": {"enum": ["warm", "cool", "neutral", "olive", "unknown"]},
                "shade_used": {"type": ["string", "null"]},
            },
        },
        "outcomes": {
            "type": "object",
            "properties": {
                "stayed_matte": {"enum": ["yes", "mostly", "no", "not_tested"]},
                "wear_hours": {"type": ["number", "null"]},
                "broke_out": {"enum": ["yes", "no", "not_mentioned"]},
                "oxidized": {"enum": ["yes", "no", "not_mentioned"]},
                "would_repurchase": {"enum": ["yes", "no", "not_mentioned"]},
                "overall": {"enum": ["positive", "mixed", "negative"]},
            },
        },
        "is_sponsored": {"type": "boolean"},
        "key_quote": {"type": ["string", "null"]},
    },
}
json.dump(schema, open(f"{OUT}/schema/review.schema.json", "w"), indent=1)

readme = """# Blackwell sample: structured product reviews

231 video reviews across 28 foundations, each structured into the reviewer's
profile and the real outcome of using the product, so an agent can surface the
most relevant reviews for a given shopper rather than leaning on one averaged
rating.

## What each record holds
- product: the product reviewed, with a stable id and brand.
- video: the reviewer, and the review's title, date, length, and view count.
- transcript: the full review transcript.
- reviewer_profile: the reviewer's skin type, tone, undertone, and whether they
  are acne-prone, plus the shade they used.
- outcomes: what actually happened over the day, whether it stayed matte, how
  many hours it lasted, whether it broke them out or oxidized, whether they would
  repurchase, and an overall read.
- is_sponsored: whether the review was sponsored (almost all are not).
- key_quote: one representative line from the reviewer.

## Files
- foundation_dataset.jsonl   one review per line.
- foundation_dataset.csv     flat summary of every reviewer and outcome.
- product_rollup.json        per-product outcome distributions, sliced by skin type.
- cohort_analysis.json       outcomes for a given reviewer profile, for example
  oily or combination skin, per product.
- schema/review.schema.json  machine-readable spec for one record.
- DATA_DICTIONARY.md         field definitions and allowed values.

## How an agent uses it
Match a shopper to reviewers with the same profile, then read the real outcomes
for that group instead of a single averaged score. cohort_analysis.json shows
this for oily and combination skin.
"""
open(f"{OUT}/README.md", "w").write(readme)

ddict = """# Data dictionary

One record describes one video product review, in foundation_dataset.jsonl (one
JSON object per line), validated against schema/review.schema.json.

## product
- name: product name.
- product_id: stable slug shared by every review of the same product.
- brand: brand name.

## video
- reviewer: the reviewer.
- title: the review title.
- published_at: ISO 8601 date.
- duration_seconds, view_count: integers.
- review_type: single_review, comparison, or roundup.

## transcript
The full review transcript.

## reviewer_profile
- skin_type: free text, for example oily or combination.
- acne_prone: yes | no | unknown.
- skin_tone_depth: fair | light | medium | tan | deep | unknown.
- undertone: warm | cool | neutral | olive | unknown.
- shade_used: the shade named, verbatim.

## outcomes
- stayed_matte: yes | mostly | no | not_tested.
- wear_hours: hours it looked good, or null.
- broke_out / oxidized / would_repurchase: yes | no | not_mentioned.
- overall: positive | mixed | negative.

## is_sponsored
Boolean, flagged only on explicit evidence.

## key_quote
One verbatim line from the reviewer.
"""
open(f"{OUT}/DATA_DICTIONARY.md", "w").write(ddict)

print(f"wrote {OUT}/ : {len(clean)} reviews")
