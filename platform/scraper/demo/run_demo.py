#!/usr/bin/env python3
"""Freeze a real ChatGPT interaction: same OpenAI model, with and without Blackwell's corpus.

For each demo query we run gpt-5.5 twice:
  - baseline: no tools, answers from the model's own memory ("ChatGPT today")
  - grounded: given a query_blackwell_corpus function it can call, then answers
    citing real reviewers and disclosing sponsored reviews ("ChatGPT + Blackwell")

The only variable between the two runs is access to our verified, neutrality-scored
review corpus. Output is a single frozen.json the demo page renders verbatim.

Run:
  set -a; . ../../credentials/.env; set +a   # loads OPENAI_API_KEY
  python demo/run_demo.py
"""
import json
import os
import re
import sqlite3
import sys
from collections import defaultdict

from openai import OpenAI

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data", "preference_data.json")
DB = os.path.join(ROOT, "videos.db")
OUT = os.path.join(HERE, "frozen.json")
MODEL = os.environ.get("DEMO_MODEL", "gpt-5.5")

client = OpenAI()

# ---------------------------------------------------------------- load corpus
with open(DATA) as f:
    _raw = json.load(f)
PRODUCTS = {p["product"]: p for p in _raw["products"]}
PRODUCT_NAMES = list(PRODUCTS)


def _segments(video_id):
    try:
        conn = sqlite3.connect(DB)
        row = conn.execute(
            "SELECT transcript_segments FROM videos WHERE video_id=?", (video_id,)
        ).fetchone()
        conn.close()
        return json.loads(row[0]) if row and row[0] else []
    except Exception:
        return []


_WORD = re.compile(r"[a-z0-9]+")


def _words(s):
    return _WORD.findall((s or "").lower())


def _timestamp_for(quote, segs):
    """Best-effort: find the transcript segment that best overlaps a quote -> start sec."""
    qw = set(_words(quote))
    if len(qw) < 4 or not segs:
        return None
    best, best_score = None, 0.0
    for s in segs:
        sw = set(_words(s.get("text", "")))
        if not sw:
            continue
        score = len(qw & sw) / len(qw)
        if score > best_score:
            best, best_score = s, score
    # only trust a strong overlap so we never cite a wrong moment
    if best is not None and best_score >= 0.55:
        return int(best.get("start", 0))
    return None


def _yt(url, t):
    if t is None:
        return url
    sep = "&" if "?" in url else "?"
    return f"{url}{sep}t={t}s"


def _fmt_ts(t):
    if t is None:
        return None
    return f"{t // 60}:{t % 60:02d}"


def corpus_for(product):
    """Compact, structured intelligence for one product: what the grounded model sees."""
    p = PRODUCTS.get(product)
    if not p:
        return {"error": f"Unknown product. Available: {PRODUCT_NAMES}"}

    reviews, dim_scores = [], defaultdict(list)
    for v in p["videos"]:
        ex = v["extracted"]
        segs = _segments(v["video_id"])
        # attach approximate source timestamps to the quotes we cite
        quotes = []
        for q in (ex.get("key_quotes") or [])[:3]:
            t = _timestamp_for(q, segs)
            quotes.append({"text": q, "at": _fmt_ts(t), "url": _yt(v["url"], t)})
        for slug, dv in (ex.get("dimensions") or {}).items():
            if isinstance(dv, dict) and isinstance(dv.get("score"), (int, float)):
                dim_scores[slug].append(dv["score"])
        reviews.append({
            "channel": v["channel"],
            "url": v["url"],
            "views": v.get("view_count"),
            "published": v.get("published_at"),
            "verdict": ex.get("verdict"),
            "sentiment": ex.get("overall_sentiment"),
            "is_sponsored": bool(ex.get("is_sponsored")),
            "sponsorship_evidence": ex.get("sponsorship_evidence"),
            "pros": (ex.get("pros") or [])[:4],
            "cons": (ex.get("cons") or [])[:4],
            "worth_the_price": ex.get("worth_the_price"),
            "would_keep_using": ex.get("would_keep_using"),
            "confidence": ex.get("confidence"),
            "quotes": quotes,
        })

    dim_summary = {}
    for d in p.get("dimensions", []):
        slug = d["slug"]
        scores = dim_scores.get(slug, [])
        if scores:
            dim_summary[slug] = {
                "name": d["name"],
                "mean_score": round(sum(scores) / len(scores), 2),
                "n_reviews": len(scores),
            }
    n_spon = sum(1 for r in reviews if r["is_sponsored"])
    return {
        "product": p["product"],
        "category": p["category"],
        "reviews_analyzed": len(reviews),
        "sponsored_reviews": n_spon,
        "independent_reviews": len(reviews) - n_spon,
        "quality_dimensions": dim_summary,
        "reviews": reviews,
    }


# ---------------------------------------------------------------- the tool
TOOL = {
    "type": "function",
    "function": {
        "name": "query_blackwell_corpus",
        "description": (
            "Retrieve Blackwell's verified, neutrality-scored product-review "
            "intelligence for a consumer product. Returns quality dimensions "
            "discovered from real YouTube reviews (each with a mean score from -1 to "
            "1), every analyzed review's verdict and sentiment, and a sponsorship/"
            "independence flag with evidence. Call this for any question about a "
            "product's real-world quality, whether its reviews are trustworthy, "
            "whether it is worth the price, or to compare products. "
            f"Available products: {PRODUCT_NAMES}."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "product": {
                    "type": "string",
                    "enum": PRODUCT_NAMES,
                    "description": "Exact product name to look up.",
                }
            },
            "required": ["product"],
        },
    },
}

BASELINE_SYS = "You are a helpful shopping assistant. Answer the user's question."

GROUNDED_SYS = (
    "You are a shopping assistant with access to Blackwell's verified product-review "
    "corpus through the query_blackwell_corpus tool. For any product question, call "
    "the tool first and ground every specific claim in what it returns. Cite the "
    "reviewer channel for specific claims. When reviews are flagged sponsored, "
    "disclose that and weight the independent reviews more heavily. Be concrete and "
    "decisive. Do not invent specs or numbers the corpus does not support."
)


def baseline(prompt):
    r = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "system", "content": BASELINE_SYS},
                  {"role": "user", "content": prompt}],
        max_completion_tokens=4000,
    )
    return r.choices[0].message.content


def grounded(prompt):
    msgs = [{"role": "system", "content": GROUNDED_SYS},
            {"role": "user", "content": prompt}]
    used, sources = [], {}
    for _ in range(6):  # allow a few tool round-trips (e.g. comparisons)
        r = client.chat.completions.create(
            model=MODEL, messages=msgs, tools=[TOOL], max_completion_tokens=6000)
        m = r.choices[0].message
        if not m.tool_calls:
            return {"answer": m.content, "products_looked_up": used, "sources": sources}
        msgs.append(m.model_dump(exclude_none=True))
        for tc in m.tool_calls:
            args = json.loads(tc.function.arguments or "{}")
            prod = args.get("product")
            payload = corpus_for(prod)
            if prod and prod not in used and "error" not in payload:
                used.append(prod)
                sources[prod] = payload
            msgs.append({"role": "tool", "tool_call_id": tc.id,
                         "content": json.dumps(payload)})
    # safety net if the model never stops calling tools
    r = client.chat.completions.create(model=MODEL, messages=msgs, max_completion_tokens=4000)
    return {"answer": r.choices[0].message.content, "products_looked_up": used, "sources": sources}


# ---------------------------------------------------------------- demo queries
QUERIES = [
    {
        "id": "airpods_sponsorship",
        "title": "Can you trust the reviews?",
        "prompt": "I'm about to buy the Apple AirPods Pro. A lot of the YouTube "
                  "reviews feel like ads. Which reviews can I actually trust, and "
                  "what do the independent ones really say about the downsides?",
    },
    {
        "id": "owala_vs_stanley",
        "title": "Owala vs Stanley for the gym",
        "prompt": "Owala FreeSip vs Stanley Quencher 40oz for taking to the gym and "
                  "tossing in a bag. Which one should I buy and why?",
    },
    {
        "id": "dyson_worth_it",
        "title": "Is it worth the price?",
        "prompt": "Is the Dyson Airwrap actually worth $600+, or is it hype? What do "
                  "reviewers say goes wrong with it?",
    },
    {
        "id": "owala_retention",
        "title": "Does it hold temperature?",
        "prompt": "Does the Owala FreeSip really keep drinks cold all day like they "
                  "claim? Any catch?",
    },
]


def main():
    out = {"model": MODEL, "products_in_corpus": PRODUCT_NAMES,
           "totals": {"products": _raw["product_count"], "videos": _raw["video_count"]},
           "queries": []}
    for q in QUERIES:
        sys.stderr.write(f"[{q['id']}] baseline... ")
        sys.stderr.flush()
        b = baseline(q["prompt"])
        sys.stderr.write("grounded...\n")
        sys.stderr.flush()
        g = grounded(q["prompt"])
        out["queries"].append({**q, "baseline": b, "grounded": g})
    with open(OUT, "w") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print(f"wrote {OUT}: {len(out['queries'])} queries against {MODEL}")


if __name__ == "__main__":
    main()
