#!/usr/bin/env python3
"""Trim frozen.json down to the three hero queries the demo page renders."""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
frozen = json.load(open(os.path.join(HERE, "frozen.json")))

# narrative order: trust -> decision -> value
ORDER = ["airpods_sponsorship", "owala_vs_stanley", "dyson_worth_it"]
by_id = {q["id"]: q for q in frozen["queries"]}

out = {"model": frozen["model"], "totals": frozen["totals"], "queries": []}
for qid in ORDER:
    q = by_id[qid]
    g = q["grounded"]
    sources = []
    for prod, payload in g["sources"].items():
        # show the best two and worst two dimensions, so the real cons (e.g.
        # Stanley's leak score, Dyson's value score) surface as red bars
        ranked = sorted(
            payload["quality_dimensions"].values(),
            key=lambda d: d["mean_score"], reverse=True)
        dims = ranked if len(ranked) <= 4 else ranked[:2] + ranked[-2:]
        reviews = [{
            "channel": r["channel"],
            "is_sponsored": r["is_sponsored"],
            "url": r["url"],
            "sentiment": r["sentiment"],
        } for r in payload["reviews"]]
        sources.append({
            "product": payload["product"],
            "category": payload["category"],
            "reviews_analyzed": payload["reviews_analyzed"],
            "independent": payload["independent_reviews"],
            "sponsored": payload["sponsored_reviews"],
            "dimensions": dims,
            "reviews": reviews,
        })
    out["queries"].append({
        "id": q["id"],
        "title": q["title"],
        "prompt": q["prompt"],
        "baseline": q["baseline"],
        "grounded": g["answer"],
        "sources": sources,
    })

dest = os.path.join(HERE, "demo-data.json")
with open(dest, "w") as f:
    json.dump(out, f, indent=2, ensure_ascii=False)
print("wrote", dest, "with", len(out["queries"]), "queries")
