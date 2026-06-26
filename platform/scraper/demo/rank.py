#!/usr/bin/env python3
"""Independent ranking: which foundation genuinely fits the shopper, from real reviews.

Persona: oily, acne-prone, medium/tan, warm-olive (~NC42). Needs: 10h matte wear,
no breakouts/clogging, no orange oxidation, fairly full coverage, warm-olive shade,
photo-friendly, ~$40. We weight the dimensions she named and weight reviewers whose
skin matches hers. No anchoring to ChatGPT's picks.
"""
import json
import sqlite3
from collections import defaultdict

WEIGHTS = {
    "oil_control_matte": 1.5, "longevity_10h": 1.5, "breakouts_clogging": 1.5,
    "oxidation_resistance": 1.2, "coverage": 1.0, "shade_warm_olive": 1.0,
    "photo_flashback": 1.0, "value": 0.8,
}

c = sqlite3.connect("demo/foundation.db")
rows = c.execute("""SELECT ca.product, ca.url, ca.extracted, cl.channel, cl.title, cl.view_count
                    FROM clip_analysis ca JOIN clips cl ON ca.url=cl.url
                    WHERE ca.extracted IS NOT NULL""").fetchall()

def persona_match(p):
    st = (p.get("skin_type") or "").lower()
    score = 0
    if "oily" in st or "combination" in st: score += 1
    if p.get("acne_prone"): score += 1
    depth = (p.get("skin_tone_depth") or "").lower()
    if depth in ("medium", "tan"): score += 0.5
    und = (p.get("undertone") or "").lower()
    if und in ("warm", "olive", "neutral"): score += 0.5
    return score  # 0..3

prod = defaultdict(lambda: {"reviews": [], "dims": defaultdict(list)})
for product, url, ex, channel, title, views in rows:
    d = json.loads(ex)
    p = d.get("reviewer_persona", {})
    pm = persona_match(p)
    rec = {"url": url, "channel": channel, "title": title, "views": views or 0,
           "persona": p, "pm": pm, "sentiment": d.get("overall_sentiment"),
           "verdict": d.get("verdict", ""), "sponsored": d.get("is_sponsored"),
           "quotes": d.get("key_quotes", []), "dims": d.get("dimensions", {})}
    prod[product]["reviews"].append(rec)
    for k, v in (d.get("dimensions") or {}).items():
        if isinstance(v, dict) and isinstance(v.get("score"), (int, float)) and v["score"] != 0:
            # weight a review's dimension contribution by persona match (min 0.5)
            w = 0.5 + pm
            prod[product]["dims"][k].append((v["score"], w, channel, v.get("evidence", "")))

def wmean(pairs):
    if not pairs: return None
    num = sum(s * w for s, w, *_ in pairs); den = sum(w for _, w, *_ in pairs)
    return num / den if den else None

ranking = []
for product, data in prod.items():
    dim_means = {k: wmean(v) for k, v in data["dims"].items() if v}
    num = sum(WEIGHTS[k] * m for k, m in dim_means.items() if k in WEIGHTS and m is not None)
    den = sum(WEIGHTS[k] for k in dim_means if k in WEIGHTS and dim_means[k] is not None)
    fit = num / den if den else 0
    n_oily = sum(1 for r in data["reviews"] if r["pm"] >= 1)
    ranking.append((fit, product, dim_means, len(data["reviews"]), n_oily, data["reviews"]))

ranking.sort(reverse=True)
print(f"{'PRODUCT':30} {'FIT':>5} {'rev':>4} {'oily':>4}  key dims")
for fit, product, dm, n, n_oily, _ in ranking:
    keys = ["oil_control_matte", "longevity_10h", "breakouts_clogging", "oxidation_resistance", "value"]
    ds = "  ".join(f"{k.split('_')[0]}:{dm[k]:+.2f}" for k in keys if dm.get(k) is not None)
    print(f"{product:30} {fit:+.2f} {n:>4} {n_oily:>4}  {ds}")

# detail on winner + MAC (for the contrast) + best similar-skin videos
def detail(product):
    row = next(r for r in ranking if r[1] == product)
    fit, _, dm, n, n_oily, reviews = row
    print(f"\n===== {product}  (fit {fit:+.2f}, {n} reviews, {n_oily} oily/acne) =====")
    for k, m in sorted(dm.items(), key=lambda x: -WEIGHTS.get(x[0], 0)):
        print(f"   {k:22} {m:+.2f}")
    # best 'someone like you' video: highest persona-match + positive + not sponsored
    cands = sorted(reviews, key=lambda r: (r["pm"], r["views"]), reverse=True)
    print("   -- top persona-matched reviews --")
    for r in cands[:3]:
        pp = r["persona"]
        print(f"     [{r['pm']}] {r['channel'][:24]:24} {str(pp.get('skin_type'))[:14]:14} acne={pp.get('acne_prone')} {str(pp.get('shade_used'))[:6]:6} spons={r['sponsored']}")
        print(f"          {r['url']}  | {r['verdict'][:80]}")
        for q in r["quotes"][:1]:
            print(f"          \"{q[:100]}\"")

for p in [ranking[0][1], ranking[1][1], ranking[2][1], "MAC Studio Fix Fluid"]:
    if any(r[1] == p for r in ranking):
        detail(p)
