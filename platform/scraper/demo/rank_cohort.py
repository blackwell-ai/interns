#!/usr/bin/env python3
"""Rank foundations by the real outcomes of reviewers who match the shopper.

Cohort = reviewers with oily/combination + acne-prone skin (the shopper's profile).
We rank on her stated priorities from the cohort's actual outcomes, not stars.
"""
import json
import sqlite3
import sys
from collections import defaultdict

DB = sys.argv[1] if len(sys.argv) > 1 else "demo/foundation_wide.db"
MIN_COHORT = 3

c = sqlite3.connect(DB)
rows = c.execute("""SELECT co.product, co.extracted, cl.channel, cl.title, cl.url, cl.view_count
                    FROM clip_outcomes co JOIN clips cl ON co.url=cl.url
                    WHERE co.extracted IS NOT NULL""").fetchall()

def in_cohort(p):
    st = (p.get("skin_type") or "").lower()
    return ("oily" in st or "combination" in st) and p.get("acne_prone") in ("yes", "unknown")

prod = defaultdict(list)
for product, ex, channel, title, url, views in rows:
    d = json.loads(ex)
    if in_cohort(d["persona"]):
        prod[product].append({**d, "channel": channel, "title": title, "url": url, "views": views or 0})

def rate(reviews, key, vals):
    n = sum(1 for r in reviews if r["outcomes"].get(key) in vals or r["outcomes"].get(key) in vals)
    return n / len(reviews) if reviews else 0

def stats(reviews):
    n = len(reviews)
    matte = sum(1 for r in reviews if r["outcomes"]["stayed_matte"] in ("yes", "mostly")) / n
    broke = sum(1 for r in reviews if r["outcomes"]["broke_out"] == "yes") / n
    oxid = sum(1 for r in reviews if r["outcomes"]["oxidized"] == "yes") / n
    pos = sum(1 for r in reviews if r["outcomes"]["overall"] == "positive") / n
    hrs = [r["outcomes"]["wear_hours"] for r in reviews if isinstance(r["outcomes"].get("wear_hours"), (int, float))]
    avg_hrs = sum(hrs) / len(hrs) if hrs else None
    rep_yes = sum(1 for r in reviews if r["outcomes"]["would_repurchase"] == "yes")
    rep_no = sum(1 for r in reviews if r["outcomes"]["would_repurchase"] == "no")
    rep = rep_yes / (rep_yes + rep_no) if (rep_yes + rep_no) else None
    return {"n": n, "matte": matte, "broke": broke, "oxid": oxid, "pos": pos, "avg_hrs": avg_hrs, "rep": rep,
            "matte_n": sum(1 for r in reviews if r["outcomes"]["stayed_matte"] in ("yes", "mostly")),
            "broke_n": sum(1 for r in reviews if r["outcomes"]["broke_out"] == "yes"),
            "oxid_n": sum(1 for r in reviews if r["outcomes"]["oxidized"] == "yes")}

scored = []
for product, reviews in prod.items():
    if len(reviews) < MIN_COHORT:
        continue
    s = stats(reviews)
    fit = (1.5 * s["matte"] + 1.5 * (1 - s["broke"]) + 1.2 * (1 - s["oxid"]) + 1.0 * s["pos"] +
           1.2 * (min(s["avg_hrs"], 12) / 12 if s["avg_hrs"] else 0.5) + 1.0 * (s["rep"] if s["rep"] is not None else 0.5))
    scored.append((fit, product, s, reviews))

scored.sort(reverse=True)
print(f"{'PRODUCT':34} {'fit':>4} {'coh':>3} {'matte':>6} {'broke':>6} {'oxid':>6} {'hrs':>4} {'rep':>4}")
for fit, product, s, _ in scored:
    print(f"{product:34} {fit:4.2f} {s['n']:3d} {s['matte_n']}/{s['n']:<4} {s['broke_n']}/{s['n']:<4} {s['oxid_n']}/{s['n']:<4} "
          f"{(round(s['avg_hrs'],1) if s['avg_hrs'] else '-'):>4} {(round(s['rep'],2) if s['rep'] is not None else '-'):>4}")

print(f"\n=== cohort sizes (oily+acne) across ALL {len(prod)} products with any cohort ===")
for product in sorted(prod, key=lambda p: -len(prod[p])):
    print(f"  {len(prod[product]):2d}  {product}")
