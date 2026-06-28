#!/usr/bin/env python3
"""Package the foundation corpus into a clean, sendable structured dataset (v2).

Changes from v1 (see brain/decisions/2026-06-28-foundation-dataset-v2.md):
  - Drops 15 records whose extraction is about a different / out-of-catalog
    product or that are not single-product wear tests (audited EXCLUDE list).
  - Carries the provenance the v1 export silently dropped: caption source,
    retrieval timestamp, like_count, description, transcript-segment availability.
  - Stamps every record with the extraction model + version (analysis_provenance).
  - Adds a canonical product_id + brand so reviews of one foundation join.
  - Normalizes published_at to ISO 8601 and persona/outcome values to the
    documented vocabulary, preserving each raw model value it had to change.
  - Classifies each video as single_review / comparison / roundup.
  - Emits JSONL (one record per line) instead of one large JSON array.

Outputs (under demo/dataset/):
  foundation_dataset.jsonl   one clean record per wear-test video
  foundation_dataset.csv     flat per-reviewer summary (normalized fields)
  videos.csv                 provenance index
  product_rollup.json        per-foundation outcome distributions, persona slices
  cohort_analysis.json       oily/combination cohort, with denominators
  excluded_records.jsonl     the 15 dropped records, each with a reason
  schema/foundation_record.schema.json   JSON Schema for one record
  DATA_DICTIONARY.md         field definitions, allowed values, normalization rules
  README.md
"""
import csv
import json
import os
import re
import sqlite3
import unicodedata
from collections import Counter, defaultdict

DB = "demo/foundation_wide.db"
OUT = "demo/dataset"
SCHEMA_VERSION = "2.0"
os.makedirs(f"{OUT}/schema", exist_ok=True)

# Records dropped after the 2026-06-28 attribution audit. Each is a comparison
# video, a "best of" roundup, an out-of-catalog product, or not a wear test, so
# its persona+outcome cannot be honestly attributed to the foundation it was
# filed under. Keyed by YouTube video_id.
EXCLUDE = {
    "SpBCiN4xKz8": "comparison (Estee Lauder Double Wear vs NARS); extraction is about Double Wear, filed under NARS Soft Matte Complete",
    "I_y7DU41-6E": "roundup of Double Wear alternatives; extraction is about Dior Forever, filed under Estee Lauder Double Wear",
    "W20nL_wRClk": "comparison (Estee Lauder Double Wear vs Clinique); extraction is about Double Wear, filed under Clinique Even Better",
    "UZapGAh5C_I": "out-of-catalog (Haus Labs Triclone); filed under Milk Makeup Future Fluid",
    "9BqlS8V_Mg0": "comparison (Estee Lauder Double Wear vs Lancome); extraction is about Double Wear, filed under Lancome Teint Idole",
    "SKBGrmzdVT0": "best/worst roundup; extraction is about Revlon ColorStay, filed under Maybelline Super Stay",
    "kq3QOLC0Nns": "multi-product; extraction is about L'Oreal Infallible Fresh Wear, filed under Maybelline Super Stay",
    "R513nmHy3V8": "out-of-catalog (L'Oreal True Matte); filed under Maybelline Super Stay",
    "BWSRFwVEA1Q": "drugstore roundup, out-of-catalog (CoverGirl Simply Ageless); filed under Maybelline Super Stay",
    "DC_sR1vrBcA": "not a wear test ('NO Foundation' tutorial); filed under NARS Soft Matte Complete",
    "WftrUdS8TBs": "makeup-artist roundup, out-of-catalog (Dior Backstage); filed under NARS Soft Matte Complete",
    "SjsiKJP5TCM": "generic tutorial, no single product reviewed; filed under NARS Soft Matte Complete",
    "kwlCEN0q330": "out-of-catalog (Bobbi Brown Skin Long Wear); filed under NARS Soft Matte Complete",
    "iAVHeckHtHg": "drugstore roundup, out-of-catalog (L'Oreal Infallible Pro Matte); filed under Revlon ColorStay",
    "aHOel2FccdI": "drugstore roundup (L'Oreal + Maybelline mix); filed under Revlon ColorStay",
}

# Display brand per catalog product. product_id is the slug of the product name.
BRAND = {
    "Catrice HD Liquid Coverage": "Catrice",
    "Charlotte Tilbury Airbrush Flawless": "Charlotte Tilbury",
    "Clinique Even Better": "Clinique",
    "CoverGirl Outlast": "CoverGirl",
    "Dior Forever": "Dior",
    "Estee Lauder Double Wear": "Estée Lauder",
    "Fenty Pro Filtr Soft Matte": "Fenty Beauty",
    "Giorgio Armani Luminous Silk": "Giorgio Armani",
    "Hourglass Vanish": "Hourglass",
    "Huda Beauty FauxFilter": "Huda Beauty",
    "IT Cosmetics CC Cream": "IT Cosmetics",
    "Kosas Revealer": "Kosas",
    "L'Oreal Infallible Fresh Wear": "L'Oréal",
    "Lancome Teint Idole Ultra Wear": "Lancôme",
    "MAC Studio Fix Fluid": "MAC",
    "Make Up For Ever HD Skin": "Make Up For Ever",
    "Maybelline Fit Me Matte Poreless": "Maybelline",
    "Maybelline Super Stay Full Coverage": "Maybelline",
    "Milk Makeup Future Fluid": "Milk Makeup",
    "NARS Sheer Glow": "NARS",
    "NARS Soft Matte Complete": "NARS",
    "NYX Cant Stop Wont Stop": "NYX",
    "Rare Beauty Liquid Touch": "Rare Beauty",
    "Revlon ColorStay": "Revlon",
    "Smashbox Studio Skin": "Smashbox",
    "Tarte Shape Tape": "Tarte",
    "Too Faced Born This Way": "Too Faced",
    "elf Flawless Satin": "e.l.f.",
}

VOCAB = {
    "skin_tone_depth": ["fair", "light", "medium", "tan", "deep", "unknown"],
    "undertone": ["warm", "cool", "neutral", "olive", "unknown"],
    "acne_prone": ["yes", "no", "unknown"],
    "stayed_matte": ["yes", "mostly", "no", "not_tested"],
    "broke_out": ["yes", "no", "not_mentioned"],
    "oxidized": ["yes", "no", "not_mentioned"],
    "would_repurchase": ["yes", "no", "not_mentioned"],
    "overall": ["positive", "mixed", "negative"],
}


def slug(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def iso_date(yyyymmdd):
    if yyyymmdd and re.fullmatch(r"\d{8}", yyyymmdd):
        return f"{yyyymmdd[:4]}-{yyyymmdd[4:6]}-{yyyymmdd[6:]}"
    return yyyymmdd or None


def iso_ts(s):
    # "2026-06-26 18:16:32" -> "2026-06-26T18:16:32" (naive, local; no tz asserted)
    return s.replace(" ", "T") if s else None


_RE_ROUNDUP = re.compile(r"\b(best|worst|top ?\d|drugstore foundations|foundations for|"
                         r"favorite foundations|favou?rite foundations|ranking|tier list)\b", re.I)
_RE_COMPARE = re.compile(r"(\bvs\.?\b|\bversus\b|\bbattle\b|\bcomparison\b|\bdupe\b|"
                         r"new vs old|old vs new|side by side)", re.I)


def video_type(title):
    t = title or ""
    if _RE_COMPARE.search(t):
        return "comparison"
    if _RE_ROUNDUP.search(t):
        return "roundup"
    return "single_review"


def _first_token(value, allowed):
    """Lowest-position canonical token found in a free-text value."""
    s = (value or "").lower()
    best, pos = None, len(s) + 1
    for tok in allowed:
        if tok == "unknown":
            continue
        i = s.find(tok)
        if 0 <= i < pos:
            best, pos = tok, i
    return best


def norm_tone(v):
    if not v or "not_mentioned" in v.lower():
        return "unknown"
    if v in VOCAB["skin_tone_depth"]:
        return v
    return _first_token(v, VOCAB["skin_tone_depth"]) or "unknown"


def norm_undertone(v):
    if not v or "not_mentioned" in v.lower():
        return "unknown"
    if v in VOCAB["undertone"]:
        return v
    s = v.lower()
    if "olive" in s:                       # distinct category, keep it when present
        return "olive"
    warm_kw = ("warm", "yellow", "golden", "gold", "peach", "red")
    cool_kw = ("cool", "pink")
    pos = {}
    for k in warm_kw:
        i = s.find(k)
        if i >= 0:
            pos["warm"] = min(pos.get("warm", 99), i)
    for k in cool_kw:
        i = s.find(k)
        if i >= 0:
            pos["cool"] = min(pos.get("cool", 99), i)
    if "neutral" in s:
        pos["neutral"] = s.find("neutral")
    if not pos:
        return "unknown"
    return min(pos, key=pos.get)


def norm_acne(v):
    if not v:
        return "unknown"
    if v in VOCAB["acne_prone"]:
        return v
    return "unknown"   # "not_mentioned" and any free text collapse to unknown


_SKIN_TAGS = ["oily", "combination", "dry", "normal", "sensitive"]


def skin_tags(v):
    """Multi-label tags from the free-text skin_type, for clean rollup slicing.
    The raw skin_type is kept verbatim on each record; this is derived for stats."""
    s = (v or "").lower()
    tags = [t for t in _SKIN_TAGS if t in s]
    return tags or ["unspecified"]


def norm_outcome(field, v):
    allowed = VOCAB[field]
    if v in allowed:
        return v
    tok = _first_token(v, allowed)
    if tok:
        return tok
    return "not_mentioned" if "not_mentioned" in allowed else ("not_tested" if "not_tested" in allowed else "mixed")


def normalize_analysis(a):
    """Return (normalized_analysis, changed_fields) where changed_fields maps a
    dotted field path to the original raw value, for every value we altered."""
    p = dict(a.get("persona") or {})
    o = dict(a.get("outcomes") or {})
    changed = {}

    def set_p(field, fn):
        raw = p.get(field)
        new = fn(raw)
        if new != raw:
            changed[f"persona.{field}"] = raw
        p[field] = new

    set_p("skin_tone_depth", norm_tone)
    set_p("undertone", norm_undertone)
    set_p("acne_prone", norm_acne)
    # skin_type stays free text; shade_used stays verbatim

    for field in ("stayed_matte", "broke_out", "oxidized", "would_repurchase", "overall"):
        raw = o.get(field)
        new = norm_outcome(field, raw)
        if new != raw:
            changed[f"outcomes.{field}"] = raw
        o[field] = new

    norm = {
        "product_reviewed": a.get("product_reviewed"),
        "persona": p,
        "outcomes": o,
        "is_sponsored": bool(a.get("is_sponsored")),
        "key_quote": a.get("key_quote"),
    }
    return norm, changed


def main():
    c = sqlite3.connect(DB)
    rows = c.execute("""
        SELECT cl.product, cl.id, cl.url, cl.channel, cl.title, cl.platform,
               cl.duration_seconds, cl.view_count, cl.like_count, cl.published_at,
               cl.transcript, cl.transcript_source, cl.transcript_segments,
               cl.description, cl.fetched_at,
               co.extracted, co.model, co.analyzed_at
        FROM clips cl LEFT JOIN clip_outcomes co ON cl.url = co.url
        ORDER BY cl.product, cl.published_at
    """).fetchall()

    records, excluded = [], []
    for (product, vid, url, channel, title, platform, dur, views, likes, pub,
         transcript, tsrc, tseg, desc, fetched, ex, model, analyzed) in rows:
        analysis = json.loads(ex) if ex else None
        norm, changed = normalize_analysis(analysis) if analysis else (None, {})
        is_asr = bool(tsrc and tsrc.startswith("audio:"))
        rec = {
            "schema_version": SCHEMA_VERSION,
            "product": {
                "name": product,
                "product_id": slug(product),
                "brand": BRAND.get(product),
            },
            "source": {
                "platform": (platform or "").lower() or "youtube",
                "video_id": vid,
                "url": url,
                "channel": channel,
                "title": title,
                "published_at": iso_date(pub),
                "duration_seconds": dur,
                "view_count": views,        # snapshot at retrieved_at
                "like_count": likes,        # snapshot at retrieved_at
                "retrieved_at": iso_ts(fetched),
                "video_type": video_type(title),
            },
            "transcript": {
                "text": transcript,
                "source": "asr" if is_asr else "captions",
                "asr_model": tsrc.split(":", 1)[1] if is_asr else None,
                "segments_available": bool(tseg),
            },
            "description": desc or None,
            "analysis": norm,
            "analysis_provenance": {
                "extraction_model": model,
                "analyzed_at": iso_ts(analyzed),
                "schema_version": SCHEMA_VERSION,
                # raw model values we normalized to the documented vocabulary
                "normalized_from": changed or None,
            },
        }
        if vid in EXCLUDE:
            excluded.append({"video_id": vid, "url": url, "filed_under": product,
                             "product_reviewed": (analysis or {}).get("product_reviewed"),
                             "title": title, "reason": EXCLUDE[vid]})
            continue
        records.append(rec)

    # ---- foundation_dataset.jsonl ----
    with open(f"{OUT}/foundation_dataset.jsonl", "w") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    # ---- excluded_records.jsonl ----
    with open(f"{OUT}/excluded_records.jsonl", "w") as f:
        for r in excluded:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    # ---- flat CSV summary (normalized fields) ----
    with open(f"{OUT}/foundation_dataset.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["product", "product_id", "brand", "channel", "url", "video_type",
                    "skin_type", "acne_prone", "tone", "undertone", "shade",
                    "stayed_matte", "wear_hours", "broke_out", "oxidized",
                    "would_repurchase", "overall", "is_sponsored", "key_quote"])
        for r in records:
            a = r["analysis"] or {}
            p = a.get("persona", {})
            o = a.get("outcomes", {})
            w.writerow([r["product"]["name"], r["product"]["product_id"], r["product"]["brand"],
                        r["source"]["channel"], r["source"]["url"], r["source"]["video_type"],
                        p.get("skin_type"), p.get("acne_prone"), p.get("skin_tone_depth"),
                        p.get("undertone"), p.get("shade_used"),
                        o.get("stayed_matte"), o.get("wear_hours"), o.get("broke_out"),
                        o.get("oxidized"), o.get("would_repurchase"), o.get("overall"),
                        a.get("is_sponsored"), a.get("key_quote")])

    # ---- videos.csv (provenance index) ----
    with open(f"{OUT}/videos.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["product", "product_id", "brand", "channel", "title", "url", "video_id",
                    "published_at", "retrieved_at", "video_type", "transcript_source"])
        for r in records:
            w.writerow([r["product"]["name"], r["product"]["product_id"], r["product"]["brand"],
                        r["source"]["channel"], r["source"]["title"], r["source"]["url"],
                        r["source"]["video_id"], r["source"]["published_at"],
                        r["source"]["retrieved_at"], r["source"]["video_type"],
                        r["transcript"]["source"]])

    # ---- product rollup ----
    by_product = defaultdict(list)
    for r in records:
        if r["analysis"]:
            by_product[r["product"]["name"]].append(r)

    def dist(recs, getter):
        return dict(Counter(getter(r) for r in recs))

    def tag_dist(recs):
        c = Counter()
        for r in recs:
            for t in skin_tags(r["analysis"]["persona"].get("skin_type")):
                c[t] += 1
        return dict(c)

    rollup = []
    for name, recs in sorted(by_product.items()):
        outs = [r["analysis"]["outcomes"] for r in recs]
        hrs = [o["wear_hours"] for o in outs if isinstance(o.get("wear_hours"), (int, float))]
        rollup.append({
            "product": name,
            "product_id": slug(name),
            "brand": BRAND.get(name),
            "n_reviews": len(recs),
            "video_type": dist(recs, lambda r: r["source"]["video_type"]),
            "skin_type_tags": tag_dist(recs),  # multi-label, counts can exceed n_reviews
            "outcomes": {
                "overall": dist(recs, lambda r: r["analysis"]["outcomes"]["overall"]),
                "stayed_matte": dist(recs, lambda r: r["analysis"]["outcomes"]["stayed_matte"]),
                "broke_out": dist(recs, lambda r: r["analysis"]["outcomes"]["broke_out"]),
                "oxidized": dist(recs, lambda r: r["analysis"]["outcomes"]["oxidized"]),
                "would_repurchase": dist(recs, lambda r: r["analysis"]["outcomes"]["would_repurchase"]),
            },
            "wear_hours": {"n_reported": len(hrs),
                           "avg": round(sum(hrs) / len(hrs), 1) if hrs else None},
        })
    rollup.sort(key=lambda x: -x["n_reviews"])
    json.dump({"n_products": len(rollup), "by_product": rollup},
              open(f"{OUT}/product_rollup.json", "w"), indent=1, ensure_ascii=False)

    # ---- cohort: oily/combination skin, acne-prone or unspecified ----
    def in_cohort(p):
        st = (p.get("skin_type") or "").lower()
        return ("oily" in st or "combination" in st) and p.get("acne_prone") in ("yes", "unknown")

    coh = defaultdict(list)
    for r in records:
        a = r["analysis"]
        if a and in_cohort(a["persona"]):
            coh[r["product"]["name"]].append(a)

    def mentioned(outs, field, yes="yes"):
        said = [o for o in outs if o[field] != "not_mentioned"]
        return sum(1 for o in said if o[field] == yes), len(said)

    cohort = []
    for name, items in sorted(coh.items(), key=lambda x: -len(x[1])):
        outs = [a["outcomes"] for a in items]
        hrs = [o["wear_hours"] for o in outs if isinstance(o.get("wear_hours"), (int, float))]
        bo_yes, bo_n = mentioned(outs, "broke_out")
        ox_yes, ox_n = mentioned(outs, "oxidized")
        rp_yes, rp_n = mentioned(outs, "would_repurchase")
        cohort.append({
            "product": name,
            "product_id": slug(name),
            "cohort_size": len(items),
            "acne_prone_yes": sum(1 for a in items if a["persona"]["acne_prone"] == "yes"),
            "acne_prone_unspecified": sum(1 for a in items if a["persona"]["acne_prone"] == "unknown"),
            "stayed_matte_yes_or_mostly": sum(1 for o in outs if o["stayed_matte"] in ("yes", "mostly")),
            "rated_positive": sum(1 for o in outs if o["overall"] == "positive"),
            "broke_out": f"{bo_yes} of {bo_n} who mentioned it",
            "oxidized": f"{ox_yes} of {ox_n} who mentioned it",
            "would_repurchase_yes": f"{rp_yes} of {rp_n} who mentioned it",
            "avg_wear_hours": round(sum(hrs) / len(hrs), 1) if hrs else None,
        })
    json.dump({
        "cohort": "reviewers with oily or combination skin who are acne-prone or did not state acne status",
        "note": "broke_out / oxidized / would_repurchase use a denominator of reviewers who addressed that outcome, "
                "since most wear-test reviewers do not mention it. A small denominator means low evidence, not a clean result.",
        "by_foundation": cohort,
    }, open(f"{OUT}/cohort_analysis.json", "w"), indent=1, ensure_ascii=False)

    write_schema()
    write_data_dictionary()
    write_readme(len(records), len(by_product), len(excluded))

    print(f"wrote {OUT}/ : {len(records)} records, {len(by_product)} foundations, "
          f"{len(excluded)} excluded")
    print("top cohorts:", [(x["product"], x["cohort_size"]) for x in cohort[:5]])


def write_schema():
    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Foundation wear-test record",
        "type": "object",
        "required": ["schema_version", "product", "source", "transcript", "analysis", "analysis_provenance"],
        "properties": {
            "schema_version": {"const": SCHEMA_VERSION},
            "product": {
                "type": "object",
                "required": ["name", "product_id", "brand"],
                "properties": {
                    "name": {"type": "string"},
                    "product_id": {"type": "string", "description": "canonical slug; reviews of one foundation share it"},
                    "brand": {"type": "string"},
                },
            },
            "source": {
                "type": "object",
                "required": ["platform", "video_id", "url", "video_type"],
                "properties": {
                    "platform": {"type": "string"},
                    "video_id": {"type": "string"},
                    "url": {"type": "string", "format": "uri"},
                    "channel": {"type": ["string", "null"]},
                    "title": {"type": ["string", "null"]},
                    "published_at": {"type": ["string", "null"], "description": "ISO 8601 date"},
                    "duration_seconds": {"type": ["integer", "null"]},
                    "view_count": {"type": ["integer", "null"], "description": "snapshot at retrieved_at"},
                    "like_count": {"type": ["integer", "null"], "description": "snapshot at retrieved_at"},
                    "retrieved_at": {"type": ["string", "null"], "description": "ISO 8601 local timestamp, no timezone"},
                    "video_type": {"enum": ["single_review", "comparison", "roundup"]},
                },
            },
            "transcript": {
                "type": "object",
                "required": ["text", "source"],
                "properties": {
                    "text": {"type": ["string", "null"]},
                    "source": {"enum": ["captions", "asr"],
                               "description": "captions = pulled from YouTube (creator or auto, not distinguished); asr = our own transcription of the audio"},
                    "asr_model": {"type": ["string", "null"]},
                    "segments_available": {"type": "boolean"},
                },
            },
            "description": {"type": ["string", "null"]},
            "analysis": {
                "type": "object",
                "required": ["product_reviewed", "persona", "outcomes", "is_sponsored", "key_quote"],
                "properties": {
                    "product_reviewed": {"type": ["string", "null"]},
                    "persona": {
                        "type": "object",
                        "properties": {
                            "skin_type": {"type": ["string", "null"], "description": "free text, e.g. 'oily', 'combination oily'"},
                            "acne_prone": {"enum": VOCAB["acne_prone"]},
                            "skin_tone_depth": {"enum": VOCAB["skin_tone_depth"]},
                            "undertone": {"enum": VOCAB["undertone"]},
                            "shade_used": {"type": ["string", "null"]},
                        },
                    },
                    "outcomes": {
                        "type": "object",
                        "properties": {
                            "stayed_matte": {"enum": VOCAB["stayed_matte"]},
                            "wear_hours": {"type": ["number", "null"]},
                            "broke_out": {"enum": VOCAB["broke_out"]},
                            "oxidized": {"enum": VOCAB["oxidized"]},
                            "would_repurchase": {"enum": VOCAB["would_repurchase"]},
                            "overall": {"enum": VOCAB["overall"]},
                        },
                    },
                    "is_sponsored": {"type": "boolean"},
                    "key_quote": {"type": ["string", "null"]},
                },
            },
            "analysis_provenance": {
                "type": "object",
                "required": ["extraction_model", "schema_version"],
                "properties": {
                    "extraction_model": {"type": ["string", "null"]},
                    "analyzed_at": {"type": ["string", "null"]},
                    "schema_version": {"type": "string"},
                    "normalized_from": {"type": ["object", "null"],
                                        "description": "dotted field path -> the raw model value before normalization"},
                },
            },
        },
    }
    json.dump(schema, open(f"{OUT}/schema/foundation_record.schema.json", "w"), indent=1)


def write_data_dictionary():
    doc = """# Data dictionary

One record describes one YouTube foundation wear-test video. Records are in
`foundation_dataset.jsonl`, one JSON object per line, validated against
`schema/foundation_record.schema.json`.

## Three layers, different reliability

A record holds three kinds of data, and they are not equally solid:

- `source`, `transcript`, `description`: facts pulled straight from YouTube.
- `analysis`: produced by a language model reading the transcript. Treat it as
  derived, not ground truth. The model and run are recorded in
  `analysis_provenance`. There is no human-verified accuracy number yet.
- `analysis_provenance.normalized_from`: the raw model values we changed to fit
  the documented vocabulary, so the original output is recoverable.

## Fields

### product
- `name`: catalog product name.
- `product_id`: canonical slug. Every review of the same foundation shares it.
  Not a GTIN/UPC; a real barcode identifier is future work.
- `brand`: display brand.

### source
- `platform`, `video_id`, `url`, `channel`, `title`.
- `published_at`: ISO 8601 date (YYYY-MM-DD).
- `duration_seconds`, `view_count`, `like_count`: integers. View and like counts
  are snapshots taken at `retrieved_at` and will drift.
- `retrieved_at`: ISO 8601 local timestamp, no timezone, when we fetched the video.
- `video_type`: `single_review`, `comparison`, or `roundup`, classified from the
  title. Comparison and roundup videos discuss more than one product, so their
  per-product outcome is less certain than a single review. Filter on this if you
  want only clean single-product evidence.

### transcript
- `text`: the transcript.
- `source`: `captions` (pulled from YouTube; creator-written and auto-generated
  are not distinguished) or `asr` (we transcribed the audio).
- `asr_model`: the model used when `source` is `asr`, else null.
- `segments_available`: whether timestamped segments exist in the source database.

### analysis
- `product_reviewed`: the foundation the model believes the video reviews.
- `persona.skin_type`: free text (e.g. `oily`, `combination oily`).
- `persona.acne_prone`: `yes` | `no` | `unknown`.
- `persona.skin_tone_depth`: `fair` | `light` | `medium` | `tan` | `deep` | `unknown`.
- `persona.undertone`: `warm` | `cool` | `neutral` | `olive` | `unknown`.
- `persona.shade_used`: free text, verbatim.
- `outcomes.stayed_matte`: `yes` | `mostly` | `no` | `not_tested`.
- `outcomes.wear_hours`: number of hours it looked good, or null.
- `outcomes.broke_out` / `oxidized` / `would_repurchase`: `yes` | `no` | `not_mentioned`.
- `outcomes.overall`: `positive` | `mixed` | `negative`.
- `is_sponsored`: boolean, flagged only on explicit evidence.
- `key_quote`: one verbatim reviewer quote, taken from the transcript, so it
  inherits any transcription error.

## Normalization rules

The extractor did not strictly enforce its enums, so some raw values were free
text. We normalized them and recorded each original under
`analysis_provenance.normalized_from`:

- `skin_tone_depth`: the first canonical depth term in the string; ranges like
  "light to medium" become `light`. Missing or "not_mentioned" become `unknown`.
- `undertone`: `olive` if present; otherwise the first of warm/cool/neutral, with
  yellow/golden/peach/red read as warm and pink as cool. Missing become `unknown`.
- `acne_prone`: "not_mentioned" and any free text collapse to `unknown`.
- outcome fields: kept if already valid, else the first valid token in the string,
  else the field's "not addressed" value.

## Known limitations

- The `analysis` layer has no measured accuracy. An eval (human-labeled sample vs
  model output) is the next step before this is decision-grade.
- `wear_hours` collapses multi-day or multi-checkpoint tests into one number.
- `video_type` is title-based, so a roundup with a single-product title can slip
  through as `single_review`.
- Rights status is unresolved (see README).
"""
    open(f"{OUT}/DATA_DICTIONARY.md", "w").write(doc)


def write_readme(n_records, n_products, n_excluded):
    readme = f"""# Blackwell foundation wear-test dataset (v2)

{n_records} YouTube foundation wear-test videos across {n_products} foundations,
each transcribed and turned into structured, per-reviewer data: the reviewer's
skin profile (type, acne-prone, tone, undertone, shade) and the real outcome of
wearing the product (stayed matte, hours of wear, broke out, oxidized, would
repurchase). The structured layer is model-generated and marked as derived, not
ground truth.

Built by Blackwell's pipeline: discover, transcribe (YouTube captions or our own
audio ASR), then language-model structured extraction. The value is the layer on
top of the transcript: cleaned, product-resolved, per-persona outcomes, the thing
a scraper or a single star rating does not give you.

## Files
- `foundation_dataset.jsonl`   one record per video (source + transcript +
  analysis + provenance), one JSON object per line.
- `foundation_dataset.csv`     flat per-reviewer summary of normalized fields.
- `product_rollup.json`        per-foundation review counts and outcome
  distributions, sliced by skin type. A purchase decision needs a distribution,
  not one anecdote.
- `cohort_analysis.json`        outcomes for oily / combination reviewers, with a
  denominator on every outcome.
- `videos.csv`                 provenance index (product, channel, url, dates).
- `excluded_records.jsonl`     {n_excluded} records removed in the 2026-06-28
  attribution audit, each with a reason.
- `schema/foundation_record.schema.json`  JSON Schema for one record.
- `DATA_DICTIONARY.md`         field definitions, allowed values, normalization rules.

## What changed from v1
- Removed {n_excluded} records whose extraction was about a different product, an
  out-of-catalog product, or that were not single-product wear tests. They had
  inflated the v1 cohort headlines.
- Carried provenance the v1 export dropped: caption source, retrieval timestamp,
  like count, video description.
- Stamped every record with the extraction model and a schema version.
- Normalized dates and the persona/outcome vocabulary, preserving raw values.
- Switched the primary file to JSONL.

## Extraction model
The `analysis` block was produced by `gpt-4.1-mini` (recorded per record in
`analysis_provenance`). Extraction accuracy has not been measured against human
labels yet; that eval is the next step before treating these fields as
decision-grade.

## Provenance and rights
Every record carries its source URL and retrieval timestamp. Transcripts are
derived from publicly viewable YouTube videos. Licensing and redistribution
rights are not yet cleared, so the rights status of this dataset is unresolved.
Resolve that before sharing the data outside the company.
"""
    open(f"{OUT}/README.md", "w").write(readme)


if __name__ == "__main__":
    main()
