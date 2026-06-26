#!/usr/bin/env python3
"""Build the 'people exactly like you' cohort demo data from the wide corpus."""
import json
import re
import sqlite3
import sys
from collections import defaultdict

DB = "demo/foundation_wide.db"
STATIC = "/home/armaan/Documents/interns/website/public/cgpt/static.html"
DEST = "/home/armaan/Documents/interns/website/app/demo/bw-cohort.json"
MIN_COHORT = 10   # only foundations with a real, convincing same-skin cohort
BUDGET = 45       # her stated ~$40, soft cap for the in-budget pick

# real retail prices + display brand/title (the search labels are messy)
META = {
 "Maybelline Super Stay Full Coverage": ("Maybelline", "Super Stay Full Coverage Foundation", 15, "super stay"),
 "NARS Soft Matte Complete":            ("NARS", "Soft Matte Complete Foundation", 52, None),
 "L'Oreal Infallible Fresh Wear":       ("L’Oréal Paris", "Infallible Fresh Wear 32HR Foundation", 16, "infallible"),
 "Revlon ColorStay":                    ("Revlon", "ColorStay Foundation for Combination/Oily", 15, "revlon"),
 "Fenty Pro Filtr Soft Matte":          ("Fenty Beauty", "Pro Filt’r Soft Matte Longwear Foundation", 41, "fenty"),
 "MAC Studio Fix Fluid":                ("M·A·C", "Studio Fix Fluid SPF 15 Foundation", 39, "mac studio fix"),
}

html = open(STATIC, encoding="utf-8", errors="ignore").read()
imgs = re.findall(r'alt="([^"]+)"\s+src="(real_files/[^"]+\.webp)"', html)
def image_for(key):
    if not key: return None
    for alt, src in imgs:
        if key in alt.lower(): return "/cgpt/" + src
    return None

c = sqlite3.connect(DB)
rows = c.execute("""SELECT co.product, co.extracted, cl.channel, cl.title, cl.url
                    FROM clip_outcomes co JOIN clips cl ON co.url=cl.url WHERE co.extracted IS NOT NULL""").fetchall()

def in_cohort(p):
    st = (p.get("skin_type") or "").lower()
    return ("oily" in st or "combination" in st) and p.get("acne_prone") in ("yes", "unknown")

def vidid(u):
    m = re.search(r"v=([\w\-]+)", u); return m.group(1) if m else None

prod = defaultdict(list)
for product, ex, channel, title, url in rows:
    d = json.loads(ex)
    if in_cohort(d["persona"]):
        prod[product].append({**d, "channel": channel, "title": title, "vid": vidid(url)})

def stats(rev):
    n = len(rev)
    o = lambda k, v: sum(1 for r in rev if r["outcomes"].get(k) in v)
    hrs = [r["outcomes"]["wear_hours"] for r in rev if isinstance(r["outcomes"].get("wear_hours"), (int, float))]
    rep_y = o("would_repurchase", ("yes",)); rep_n = o("would_repurchase", ("no",))
    matte = o("stayed_matte", ("yes", "mostly"))
    return {"n": n, "matte": matte, "broke": o("broke_out", ("yes",)), "oxid": o("oxidized", ("yes",)),
            "pos": o("overall", ("positive",)), "avg_hrs": round(sum(hrs)/len(hrs), 1) if hrs else None,
            "rep_yes": rep_y, "rep_n": rep_n,
            "matte_pct": round(100*matte/n), "rep_pct": round(100*rep_y/(rep_y+rep_n)) if (rep_y+rep_n) else None}

scored = []
for product, rev in prod.items():
    if len(rev) < MIN_COHORT: continue
    s = stats(rev)
    fit = (1.5*s["matte"]/s["n"] + 1.5*(1-s["broke"]/s["n"]) + 1.2*(1-s["oxid"]/s["n"]) + 1.0*s["pos"]/s["n"]
           + 1.2*(min(s["avg_hrs"],12)/12 if s["avg_hrs"] else .5) + 1.0*(s["rep_pct"]/100 if s["rep_pct"] is not None else .5))
    scored.append((fit, product, s, rev))
scored.sort(reverse=True)

def pack(product, s, rev, rank):
    brand, title, price, imgkey = META.get(product, (product, product, None, None))
    # cohort videos: prefer same-skin, positive, with quotes
    vids = []
    for r in sorted(rev, key=lambda r: (r["outcomes"]["overall"] == "positive", r["vid"] is not None), reverse=True):
        if not r["vid"]: continue
        vids.append({"vid": r["vid"], "channel": r["channel"],
                     "skin": (r["persona"].get("skin_type") or "oily").split(",")[0],
                     "acne": r["persona"].get("acne_prone") == "yes",
                     "matte": r["outcomes"]["stayed_matte"], "hrs": r["outcomes"].get("wear_hours"),
                     "quote": (r.get("key_quote") or "")[:140]})
    return {"product": product, "brand": brand, "title": title, "price": price,
            "image": image_for(imgkey or product.lower().split()[0]), "rank": rank,
            "cohort": s, "videos": vids[:14]}

# winner = best fit among large-cohort foundations that fit her budget;
# the over-budget top performer (e.g. NARS) becomes the "splurge" runner-up.
def price_of(p): return META.get(p, (0, 0, 999, 0))[2] or 999
in_budget = [x for x in scored if price_of(x[1]) <= BUDGET]
win_row = in_budget[0] if in_budget else scored[0]
winner = pack(win_row[1], win_row[2], win_row[3], 1)
rest = [x for x in scored if x[1] != win_row[1]][:3]
runner_ups = [pack(p, s, rev, i + 2) for i, (_, p, s, rev) in enumerate(rest)]

total_cohort = sum(len(v) for v in prod.values())
out = {
  "profile": {
    "summary": "Oily, acne-prone · warm-olive ~NC42 · wedding in 3 weeks",
    "attrs": ["Oily, acne-prone", "Warm-olive · ~NC42", "Combination (oily T-zone)",
              "Needs 10-hour wear", "Can’t oxidize orange", "Has to photograph well", "Budget ~$40"],
  },
  "corpus": {"videos": c.execute("SELECT COUNT(*) FROM clips").fetchone()[0],
             "products": c.execute("SELECT COUNT(DISTINCT product) FROM clips").fetchone()[0],
             "cohort_total": total_cohort,
             "sponsored_excluded": sum(1 for _,ex,*_ in rows if json.loads(ex).get("is_sponsored"))},
  "winner": winner, "runner_ups": runner_ups,
}
json.dump(out, open(DEST, "w"), indent=1, ensure_ascii=False)
print("WINNER:", winner["brand"], winner["title"], f"(cohort {winner['cohort']['n']})")
print("  matte", f"{winner['cohort']['matte']}/{winner['cohort']['n']} ({winner['cohort']['matte_pct']}%)",
      "| broke", winner['cohort']['broke'], "| oxid", winner['cohort']['oxid'],
      "| avg", winner['cohort']['avg_hrs'], "h | repurchase", winner['cohort']['rep_pct'], "%",
      "| image", bool(winner["image"]), "| videos", len(winner["videos"]))
print("RUNNER-UPS:", [(r["brand"], r["cohort"]["n"]) for r in runner_ups])
print("total same-skin cohort across corpus:", total_cohort)
print("wrote", DEST)
