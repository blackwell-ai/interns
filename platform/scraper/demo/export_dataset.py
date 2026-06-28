#!/usr/bin/env python3
"""Package the foundation corpus into a clean, sendable structured dataset.

Outputs (under demo/dataset/):
  - foundation_dataset.json : one record per wear-test video (source metadata +
    transcript + structured analysis: reviewer skin profile + real outcomes).
  - foundation_dataset.csv  : flat summary (no transcript) for quick scanning.
  - cohort_analysis.json    : per-foundation aggregates for oily/acne-prone
    reviewers (the segmented outcomes star ratings can't produce).
  - videos.csv              : video index (product, channel, url) for provenance.
  - README.md
"""
import csv
import json
import os
import re
import sqlite3
from collections import defaultdict

DB = "demo/foundation_wide.db"
OUT = "demo/dataset"
os.makedirs(OUT, exist_ok=True)

c = sqlite3.connect(DB)
rows = c.execute("""SELECT cl.product, cl.id, cl.url, cl.channel, cl.title, cl.platform,
                           cl.duration_seconds, cl.view_count, cl.published_at, cl.transcript,
                           co.extracted
                    FROM clips cl LEFT JOIN clip_outcomes co ON cl.url=co.url
                    ORDER BY cl.product""").fetchall()

records = []
for product, vid, url, channel, title, platform, dur, views, pub, transcript, ex in rows:
    analysis = json.loads(ex) if ex else None
    records.append({
        "product": product,
        "source": {"video_id": vid, "url": url, "platform": platform, "channel": channel,
                   "title": title, "duration_seconds": dur, "view_count": views, "published_at": pub},
        "transcript": transcript,
        "analysis": analysis,  # {product_reviewed, persona, outcomes, is_sponsored, key_quote}
    })

json.dump(records, open(f"{OUT}/foundation_dataset.json", "w"), indent=1, ensure_ascii=False)

# flat CSV summary
with open(f"{OUT}/foundation_dataset.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["product", "channel", "url", "skin_type", "acne_prone", "tone", "undertone", "shade",
                "stayed_matte", "wear_hours", "broke_out", "oxidized", "would_repurchase", "overall",
                "is_sponsored", "key_quote"])
    for r in records:
        a = r["analysis"] or {}
        p = a.get("persona", {}); o = a.get("outcomes", {})
        w.writerow([r["product"], r["source"]["channel"], r["source"]["url"],
                    p.get("skin_type"), p.get("acne_prone"), p.get("skin_tone_depth"), p.get("undertone"), p.get("shade_used"),
                    o.get("stayed_matte"), o.get("wear_hours"), o.get("broke_out"), o.get("oxidized"),
                    o.get("would_repurchase"), o.get("overall"), a.get("is_sponsored"), a.get("key_quote")])

with open(f"{OUT}/videos.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["product", "channel", "title", "url", "video_id"])
    for r in records:
        w.writerow([r["product"], r["source"]["channel"], r["source"]["title"], r["source"]["url"], r["source"]["video_id"]])

# cohort analysis: oily + acne-prone reviewers, per foundation
def in_cohort(p):
    st = (p.get("skin_type") or "").lower()
    return ("oily" in st or "combination" in st) and p.get("acne_prone") in ("yes", "unknown")

coh = defaultdict(list)
for r in records:
    a = r["analysis"]
    if a and in_cohort(a.get("persona", {})):
        coh[r["product"]].append(a["outcomes"])

cohort_analysis = []
for product, outs in sorted(coh.items(), key=lambda x: -len(x[1])):
    n = len(outs)
    hrs = [o["wear_hours"] for o in outs if isinstance(o.get("wear_hours"), (int, float))]
    cohort_analysis.append({
        "product": product, "cohort_size": n,
        "stayed_matte": sum(1 for o in outs if o["stayed_matte"] in ("yes", "mostly")),
        "broke_out": sum(1 for o in outs if o["broke_out"] == "yes"),
        "oxidized": sum(1 for o in outs if o["oxidized"] == "yes"),
        "rated_positive": sum(1 for o in outs if o["overall"] == "positive"),
        "avg_wear_hours": round(sum(hrs)/len(hrs), 1) if hrs else None,
        "would_repurchase_yes": sum(1 for o in outs if o["would_repurchase"] == "yes"),
    })
json.dump({"cohort": "oily / acne-prone reviewers", "by_foundation": cohort_analysis},
          open(f"{OUT}/cohort_analysis.json", "w"), indent=1, ensure_ascii=False)

n_products = len(set(r["product"] for r in records))
n_analyzed = sum(1 for r in records if r["analysis"])
readme = f"""# Blackwell foundation wear-test dataset

{len(records)} YouTube foundation wear-test videos across {n_products} foundations,
transcribed and turned into structured, per-reviewer data: each reviewer's skin
profile (type, acne-prone, tone, undertone, shade) and the real outcome of
wearing the product (did it stay matte, hours of wear, did it break them out, did
it oxidize, would they repurchase). {n_analyzed} of {len(records)} are fully
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
Every record links to its source video URL. {{VIDEO_NOTE}}
"""
open(f"{OUT}/README.md", "w").write(readme)

print(f"wrote {OUT}/ : {len(records)} records, {n_products} foundations, {n_analyzed} analyzed")
print("cohort sizes:", [(x["product"], x["cohort_size"]) for x in cohort_analysis[:6]])
