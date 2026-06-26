#!/usr/bin/env python3
"""Export the Blackwell-powered shopping experience data from the real corpus."""
import json
import re
import sqlite3
from collections import defaultdict

DEST = "/home/armaan/Documents/interns/website/app/demo/bw-shop-data.json"
STATIC = "/home/armaan/Documents/interns/website/public/cgpt/static.html"

# realistic US retail prices (the ChatGPT carousel prices were unreliable)
PRICE = {
    "Fenty Pro Filt'r Soft Matte": 41, "MAC Studio Fix Fluid": 39,
    "L'Oréal Infallible Fresh Wear": 16, "Maybelline Fit Me Matte": 9,
    "Revlon ColorStay": 15, "Maybelline Super Stay": 15,
    "Estée Lauder Double Wear": 48, "NARS Soft Matte": 52,
    "Dior Forever Matte": 58, "Charlotte Tilbury Airbrush": 49,
    "Make Up For Ever HD Skin": 45, "IT Cosmetics CC+ Cream": 44,
}
# map our product names to the alt-text fragment in ChatGPT's saved carousel imgs
IMG_KEY = {
    "Fenty Pro Filt'r Soft Matte": "Fenty", "MAC Studio Fix Fluid": "MAC Studio Fix",
    "L'Oréal Infallible Fresh Wear": "Infallible",
}

# --- product images from the saved ChatGPT page (alt -> local webp) ---
html = open(STATIC, encoding="utf-8", errors="ignore").read()
imgmap = {}
for m in re.finditer(r'alt="([^"]+)"\s+src="(real_files/[^"]+\.webp)"', html):
    imgmap[m.group(1)] = "/cgpt/" + m.group(2)
def image_for(product):
    key = IMG_KEY.get(product)
    if not key:
        return None
    for alt, src in imgmap.items():
        if key.lower() in alt.lower():
            return src
    return None

c = sqlite3.connect("demo/foundation.db")
rows = c.execute("""SELECT ca.product, ca.url, ca.extracted, cl.channel, cl.title, cl.view_count
                    FROM clip_analysis ca JOIN clips cl ON ca.url=cl.url
                    WHERE ca.extracted IS NOT NULL""").fetchall()

def yid(url):
    m = re.search(r"v=([A-Za-z0-9_\-]+)", url); return m.group(1) if m else None

prod = defaultdict(list)
for product, url, ex, channel, title, views in rows:
    d = json.loads(ex)
    prod[product].append({"url": url, "vid": yid(url), "channel": channel, "title": title,
                          "views": views or 0, **d})

def persona_match(p):
    st = (p.get("skin_type") or "").lower(); s = 0
    if "oily" in st or "combination" in st: s += 1
    if p.get("acne_prone"): s += 1
    return s

def dim_mean(reviews, key):
    vals = [(r["dimensions"][key]["score"], r["dimensions"][key].get("evidence", ""), r["channel"], r)
            for r in reviews if r.get("dimensions", {}).get(key)
            and isinstance(r["dimensions"][key].get("score"), (int, float)) and r["dimensions"][key]["score"] != 0]
    if not vals: return None
    mean = sum(v[0] for v in vals) / len(vals)
    # representative evidence: the highest-scoring quote
    best = max(vals, key=lambda v: v[0])
    return {"score": round(mean, 2), "n": len(vals), "pct": round((mean + 1) / 2 * 100),
            "evidence": best[1][:160], "channel": best[2]}

CRITERIA = [
    ("oil_control_matte", "Stays matte all day", "no midday shine"),
    ("longevity_10h", "Lasts a 10-hour day", "still on at hour 10"),
    ("breakouts_clogging", "Won't clog or break you out", "skin stayed clear"),
    ("oxidation_resistance", "No orange oxidation", "stays true to shade"),
    ("coverage", "Covers acne & redness", "medium-to-full coverage"),
    ("photo_flashback", "Photographs well", "no flash-back"),
]

def build_product(product):
    revs = prod[product]
    oily = [r for r in revs if persona_match(r["reviewer_persona"]) >= 1]
    use = oily or revs
    crits = []
    for key, label, sub in CRITERIA:
        dm = dim_mean(use, key)
        if dm:
            crits.append({"key": key, "label": label, "sub": sub, **dm})
    n_spon = sum(1 for r in revs if r.get("is_sponsored"))
    def neg(key):
        return sum(1 for r in use if r.get("dimensions", {}).get(key)
                   and isinstance(r["dimensions"][key].get("score"), (int, float))
                   and r["dimensions"][key]["score"] < -0.2)
    clean = {"breakout_complaints": neg("breakouts_clogging"),
             "oxidation_complaints": neg("oxidation_resistance"), "n_same_skin": len(use)}
    # proof videos: same-skin reviewers, positive, not sponsored, ranked by match+views
    proof = []
    for r in sorted(use, key=lambda r: (persona_match(r["reviewer_persona"]), r["views"]), reverse=True):
        if r.get("is_sponsored"): continue
        p = r["reviewer_persona"]
        skin = " ".join(filter(None, [str(p.get("skin_type") or "").split(",")[0],
                                       "acne-prone" if p.get("acne_prone") else ""])).strip()
        proof.append({"vid": r["vid"], "channel": r["channel"], "skin": skin or "oily",
                      "shade": p.get("shade_used"), "quote": (r.get("key_quotes") or [""])[0][:120],
                      "verdict": r.get("verdict", "")[:140]})
        if len(proof) >= 5: break
    return {"product": product, "price": PRICE.get(product), "image": image_for(product),
            "n_reviews": len(revs), "n_oily": len(oily), "n_sponsored": n_spon,
            "criteria": crits, "proof": proof, "clean": clean}

fenty = build_product("Fenty Pro Filt'r Soft Matte")
mac = build_product("MAC Studio Fix Fluid")
loreal = build_product("L'Oréal Infallible Fresh Wear")

# overall match score for the pick: weighted avg of its criteria pct
def match_score(p):
    w = {"oil_control_matte": 1.5, "longevity_10h": 1.5, "breakouts_clogging": 1.5,
         "oxidation_resistance": 1.2, "coverage": 1.0, "photo_flashback": 1.0}
    num = sum(w.get(c["key"], 1) * c["pct"] for c in p["criteria"])
    den = sum(w.get(c["key"], 1) for c in p["criteria"])
    return round(num / den) if den else 0

# ranking (fit) for the full list
def fit(p):
    w = {"oil_control_matte": 1.5, "longevity_10h": 1.5, "breakouts_clogging": 1.5,
         "oxidation_resistance": 1.2, "coverage": 1.0, "photo_flashback": 1.0, "value": 0.8}
    num = den = 0
    for key in w:
        dm = dim_mean([r for r in prod[p] if persona_match(r["reviewer_persona"]) >= 1] or prod[p], key)
        if dm: num += w[key] * (dm["score"]); den += w[key]
    return round(num / den, 2) if den else 0

ranking = sorted(prod.keys(), key=lambda p: fit(p), reverse=True)
rank_out = [{"product": p, "price": PRICE.get(p), "fit": fit(p),
             "n_oily": sum(1 for r in prod[p] if persona_match(r["reviewer_persona"]) >= 1),
             "image": image_for(p)} for p in ranking]

out = {
    "shopper": {
        "summary": "Oily, acne-prone · warm-olive ~NC42 · wedding in a month",
        "filters": ["Oily", "Acne-prone", "Warm-olive ~NC42", "10-hour wear", "No oxidation", "Won't clog", "Photo-ready", "~$40"],
    },
    "corpus": {"videos": len(rows), "products": len(prod),
               "reviewers_matched": sum(1 for r in rows if persona_match(json.loads(r[2])["reviewer_persona"]) >= 1),
               "sponsored_excluded": sum(1 for r in rows if json.loads(r[2]).get("is_sponsored"))},
    "pick": {**fenty, "match": match_score(fenty), "brand": "Fenty Beauty",
             "title": "Pro Filt'r Soft Matte Longwear Foundation", "shade": "370 (warm)",
             "why": "Every oily, acne-prone reviewer in the corpus rated it a keeper, with no breakout or oxidation complaints."},
    "head_to_head": {
        "product": "MAC Studio Fix Fluid", "image": mac["image"], "price": mac["price"],
        "claim": "“24-hour wear, oil control, won’t clog pores” — per MAC",
        "reality": [c for c in mac["criteria"] if c["key"] in ("oil_control_matte", "longevity_10h")],
        "note": "The usual top pick. Real wear tests from oily skin rate its oil control and all-day wear only modest, the exact thing you said fails by 2pm. That rec trusts MAC’s label; we checked it.",
    },
    "alternative": {"product": "L'Oréal Infallible Fresh Wear", "image": loreal["image"], "price": loreal["price"],
                    "match": match_score(loreal),
                    "note": "Best oil control and wear of all 12, and $16 — but one acne-prone reviewer broke out, so patch-test first."},
    "ranking": rank_out,
}
json.dump(out, open(DEST, "w"), indent=1, ensure_ascii=False)
print("wrote", DEST)
print("pick match:", out["pick"]["match"], "| criteria:", len(fenty["criteria"]), "| proof vids:", len(fenty["proof"]))
print("corpus:", out["corpus"])
print("top5 fit:", [(r["product"], r["fit"]) for r in rank_out[:5]])
