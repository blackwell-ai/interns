#!/usr/bin/env python3
"""Social proof scraper: pull product reviews across sources and score neutrality.

Each review becomes one record with a verdict and a neutrality assessment. The
neutrality field is the whole point: every source is classified as independent,
incentivized, sponsored, affiliate, first-party, or astroturf-suspected, so the
aggregate can weight for a clean, unbiased stream.

Usage:
  set -a; . credentials/.env; set +a
  python3 platform/scrape/socialproof.py youtube ghostbed 4
"""
import glob
import json
import os
import re
import subprocess
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRODUCTS = json.load(open(os.path.join(BASE, "products.json")))
DATA = os.path.join(BASE, "data")

OPENAI_MODELS = ["gpt-4o-mini", "gpt-4.1-mini", "gpt-4o"]

INDEPENDENCE = [
    "independent",            # unpaid, no free product, genuine
    "incentivized_free_product",  # got the product free / gifted for review
    "sponsored_paid",         # paid placement, #ad, paid partnership
    "affiliate_only",         # monetized via affiliate links / discount codes
    "first_party",            # the brand's own site / channel
    "astroturf_suspected",    # looks fake or planted
]

# rule-based pre-flags, fed to the model as hints and kept on the record
COMP_PATTERNS = {
    "free_product": r"\b(free|gifted|sent (me|us)|provided by|for review|complimentary)\b",
    "sponsored": r"\b(sponsor|sponsored|paid partnership|#ad|paid promotion)\b",
    "affiliate": r"\b(affiliate|commission|use code|discount code|promo code|links below)\b",
}


def rule_flags(text):
    t = (text or "").lower()
    return {k: bool(re.search(p, t)) for k, p in COMP_PATTERNS.items()}


def llm_json(system, user, max_tokens=900):
    import requests
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("OPENAI_API_KEY not in env. Run: set -a; . credentials/.env; set +a")
    last = None
    for model in OPENAI_MODELS:
        try:
            r = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    "response_format": {"type": "json_object"},
                    "temperature": 0,
                    "max_tokens": max_tokens,
                },
                timeout=120,
            )
            data = r.json()
            if "error" in data:
                last = data["error"].get("message", "")
                if "model" in last.lower() or "does not exist" in last.lower():
                    continue
                raise RuntimeError(last)
            return json.loads(data["choices"][0]["message"]["content"]), model
        except requests.RequestException as e:
            last = str(e)
            continue
    raise RuntimeError(f"all models failed: {last}")


def parse_vtt(path):
    lines = []
    for raw in open(path, encoding="utf-8", errors="ignore"):
        s = raw.strip()
        if not s or s.startswith(("WEBVTT", "Kind:", "Language:")):
            continue
        if "-->" in s or re.match(r"^\d{2}:\d{2}:\d{2}", s):
            continue
        s = re.sub(r"<[^>]+>", "", s)
        if s and (not lines or lines[-1] != s):
            lines.append(s)
    return " ".join(lines)


INTENT_QUERIES = ["review", "honest review", "problems", "long term review",
                  "worth it", "complaints"]


def discover_youtube(product, per_query=2):
    """Discovery adapter: deduped [(url, title)] across intent queries."""
    name = PRODUCTS[product]["name"]
    seen, hits = set(), []
    for intent in INTENT_QUERIES:
        out = subprocess.run(
            ["yt-dlp", "-J", "--flat-playlist", "--no-warnings",
             f"ytsearch{per_query}:{name} {intent}"],
            capture_output=True, text=True, timeout=180,
        )
        try:
            data = json.loads(out.stdout or "{}")
        except json.JSONDecodeError:
            continue
        for e in data.get("entries", []):
            vid = e.get("id")
            if vid and vid not in seen:
                seen.add(vid)
                hits.append((f"https://www.youtube.com/watch?v={vid}", e.get("title", "")))
    return hits


def get_captions(url, workdir, vid):
    subprocess.run(
        ["yt-dlp", "--skip-download", "--write-auto-subs", "--sub-langs", "en.*",
         "--sub-format", "vtt", "-o", os.path.join(workdir, vid), "--no-warnings", url],
        capture_output=True, text=True, timeout=180,
    )
    vtts = sorted(glob.glob(os.path.join(workdir, f"{vid}*.vtt")))
    return parse_vtt(vtts[0]) if vtts else ""


def whisper_transcribe(url, workdir, vid):
    """Universal fallback for platforms without captions (TikTok, IG, etc.)."""
    import requests
    audio = os.path.join(workdir, f"{vid}.mp3")
    subprocess.run(
        ["yt-dlp", "-q", "--no-warnings", "-f", "bestaudio", "-x", "--audio-format", "mp3",
         "-o", os.path.join(workdir, f"{vid}.%(ext)s"), url],
        capture_output=True, text=True, timeout=300,
    )
    if not os.path.exists(audio):
        return ""
    clip = os.path.join(workdir, f"{vid}_clip.mp3")
    subprocess.run(
        ["ffmpeg", "-nostdin", "-loglevel", "error", "-t", "720", "-i", audio,
         "-ac", "1", "-ar", "16000", clip, "-y"],
        capture_output=True, text=True, timeout=180,
    )
    src = clip if os.path.exists(clip) else audio
    with open(src, "rb") as fh:
        r = requests.post(
            "https://api.openai.com/v1/audio/transcriptions",
            headers={"Authorization": f"Bearer {os.environ.get('OPENAI_API_KEY')}"},
            files={"file": fh}, data={"model": "whisper-1", "response_format": "text"},
            timeout=300,
        )
    return r.text if r.status_code == 200 else ""


VERDICT_SYS = (
    "You analyze one product-review video and return strict JSON. First decide whether "
    "the video is actually a review of THE GIVEN PRODUCT (is_about_product, "
    "relevance_confidence), since search is broad. Then judge it. Be skeptical about "
    "neutrality. independence must be one of: " + ", ".join(INDEPENDENCE) + ". Treat a "
    "free or gifted product as incentivized_free_product even when the reviewer claims "
    "honesty; treat affiliate links, discount codes, or TikTok Shop tags as affiliate_only; "
    "use first_party only if the channel is the brand itself. Return JSON keys: "
    "is_about_product (bool), relevance_confidence (number 0-1), recommended (bool), "
    "score_0_10 (number), summary (<=240 chars), pros (array), cons (array), key_quote "
    "(string), neutrality (object: independence, disclosed (bool), evidence (string), "
    "confidence_0_1 (number))."
)


def ingest_video(product, url, title_hint=""):
    """Ingestion core: any video URL -> record with verdict + neutrality."""
    workdir = os.path.join(DATA, product, "_media")
    os.makedirs(workdir, exist_ok=True)
    meta = json.loads(subprocess.run(
        ["yt-dlp", "-J", "--no-warnings", url],
        capture_output=True, text=True, timeout=240,
    ).stdout or "{}")
    vid = meta.get("id") or re.sub(r"\W+", "", url)[-16:]
    platform = (meta.get("extractor_key") or meta.get("extractor") or "unknown").lower()

    transcript, tsource = get_captions(url, workdir, vid), "captions"
    if not transcript:
        transcript, tsource = whisper_transcribe(url, workdir, vid), "whisper"
    if not transcript:
        return None

    desc = (meta.get("description") or "")[:1500]
    flags = rule_flags(transcript + " " + desc)
    channel = meta.get("channel") or meta.get("uploader") or meta.get("uploader_id") or ""
    user = json.dumps({
        "product": PRODUCTS[product]["name"],
        "brand": PRODUCTS[product]["brand"],
        "video_title": meta.get("title", title_hint),
        "channel": channel,
        "platform": platform,
        "description_excerpt": desc,
        "rule_based_flags": flags,
        "transcript_excerpt": transcript[:6000],
    })
    verdict, model = llm_json(VERDICT_SYS, user)
    return {
        "source_type": "video",
        "platform": platform,
        "product": product,
        "video_id": vid,
        "url": meta.get("webpage_url", url),
        "title": meta.get("title", title_hint),
        "channel": channel,
        "view_count": meta.get("view_count"),
        "like_count": meta.get("like_count"),
        "upload_date": meta.get("upload_date"),
        "duration_s": meta.get("duration"),
        "transcript_source": tsource,
        "rule_flags": flags,
        "verdict": verdict,
        "model": model,
    }


def update_reviewers(records):
    """Reviewer-level neutrality store. Priors compound across products."""
    path = os.path.join(DATA, "reviewers.json")
    store = json.load(open(path)) if os.path.exists(path) else {}
    for r in records:
        key = f"{r['platform']}:{r['channel']}".lower()
        ind = r["verdict"].get("neutrality", {}).get("independence", "unknown")
        ent = store.setdefault(key, {"platform": r["platform"], "channel": r["channel"],
                                     "videos": 0, "independence_counts": {}, "products": []})
        ent["videos"] += 1
        ent["independence_counts"][ind] = ent["independence_counts"].get(ind, 0) + 1
        if r["product"] not in ent["products"]:
            ent["products"].append(r["product"])
    json.dump(store, open(path, "w"), indent=2)
    return store


def run_youtube(product, n=2, max_videos=8):
    hits = discover_youtube(product, per_query=n)[:max_videos]
    print(f"  discovered {len(hits)} candidate videos", file=sys.stderr)
    records = []
    for url, title in hits:
        try:
            rec = ingest_video(product, url, title)
            if not rec:
                print(f"  skip (no transcript): {title[:50]}", file=sys.stderr)
                continue
            v = rec["verdict"]
            if not v.get("is_about_product", True):
                print(f"  drop (off-topic): {title[:50]}", file=sys.stderr)
                continue
            ind = v.get("neutrality", {}).get("independence", "?")
            print(f"  ok [{rec['platform']}/{rec['transcript_source']}][{ind}] {title[:42]}",
                  file=sys.stderr)
            records.append(rec)
        except Exception as e:
            print(f"  err {url}: {e}", file=sys.stderr)
    out = os.path.join(DATA, product, "video.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    json.dump(records, open(out, "w"), indent=2)
    update_reviewers(records)
    print(f"wrote {len(records)} video records -> {out}", file=sys.stderr)
    return records


# ---------------------------------------------------------------- reddit -----
REDDIT_UA = "blackwell-socialproof/0.1 (research)"

REDDIT_SYS = (
    "You analyze one Reddit thread discussing a product and return strict JSON about "
    "what the thread's participants actually think of it. independence must be one of: "
    + ", ".join(INDEPENDENCE) + ". Reddit is usually independent user discussion, so "
    "default to independent and mark incentivized_free_product, sponsored_paid, "
    "affiliate_only, or astroturf_suspected only on clear signals like referral codes, "
    "self-identified brand reps, or suspiciously promotional identical posts. Return JSON "
    "keys: recommended (bool or null if the thread is mixed), score_0_10 (number), "
    "summary (<=240 chars), pros (array), cons (array), key_quote (string), neutrality "
    "(object: independence, disclosed (bool), evidence (string), confidence_0_1 (number))."
)


def reddit_token():
    import requests
    cid, sec = os.environ.get("REDDIT_CLIENT_ID"), os.environ.get("REDDIT_CLIENT_SECRET")
    if not (cid and sec):
        raise RuntimeError("REDDIT_CLIENT_ID/SECRET not in env")
    r = requests.post(
        "https://www.reddit.com/api/v1/access_token",
        auth=(cid, sec), data={"grant_type": "client_credentials"},
        headers={"User-Agent": REDDIT_UA}, timeout=30,
    )
    return r.json()["access_token"]


def reddit_search(token, query, n):
    import requests
    r = requests.get(
        "https://oauth.reddit.com/search",
        headers={"Authorization": f"bearer {token}", "User-Agent": REDDIT_UA},
        params={"q": query, "limit": n, "sort": "relevance", "type": "link", "t": "all"},
        timeout=30,
    )
    out = []
    for c in r.json().get("data", {}).get("children", []):
        d = c["data"]
        out.append({
            "id": d["id"], "title": d.get("title", ""), "selftext": d.get("selftext", "") or "",
            "subreddit": d.get("subreddit", ""), "score": d.get("score"),
            "num_comments": d.get("num_comments"), "author": d.get("author", ""),
            "permalink": "https://reddit.com" + d.get("permalink", ""),
        })
    return out


def reddit_comments(token, sub_id, k=6):
    import requests
    r = requests.get(
        f"https://oauth.reddit.com/comments/{sub_id}",
        headers={"Authorization": f"bearer {token}", "User-Agent": REDDIT_UA},
        params={"limit": k, "sort": "top", "depth": 1}, timeout=30,
    )
    data = r.json()
    comments = []
    try:
        for c in data[1]["data"]["children"]:
            if c.get("kind") != "t1":
                continue
            body = c["data"].get("body", "")
            if body and body not in ("[deleted]", "[removed]"):
                comments.append({"author": c["data"].get("author", ""),
                                 "score": c["data"].get("score"), "body": body})
            if len(comments) >= k:
                break
    except Exception:
        pass
    return comments


def extract_reddit(product, thread, comments):
    text = thread["title"] + "\n" + thread["selftext"] + "\n\n" + "\n".join(
        f"- ({c['score']}) {c['body']}" for c in comments)
    flags = rule_flags(text)
    user = json.dumps({
        "product": PRODUCTS[product]["name"],
        "brand": PRODUCTS[product]["brand"],
        "subreddit": thread["subreddit"],
        "thread_title": thread["title"],
        "rule_based_flags": flags,
        "content_excerpt": text[:6000],
    })
    verdict, model = llm_json(REDDIT_SYS, user)
    return {
        "source_type": "reddit",
        "product": product,
        "thread_id": thread["id"],
        "url": thread["permalink"],
        "subreddit": thread["subreddit"],
        "score": thread["score"],
        "num_comments": thread["num_comments"],
        "n_comments_read": len(comments),
        "rule_flags": flags,
        "verdict": verdict,
        "model": model,
    }


def run_reddit(product, n):
    p = PRODUCTS[product]
    token = reddit_token()
    threads = reddit_search(token, p["reddit_query"], n)
    records = []
    for t in threads:
        try:
            comments = reddit_comments(token, t["id"])
            rec = extract_reddit(product, t, comments)
            ind = rec["verdict"].get("neutrality", {}).get("independence", "?")
            print(f"  ok r/{t['subreddit']} [{ind}] {t['title'][:50]}", file=sys.stderr)
            records.append(rec)
        except Exception as e:
            print(f"  err {t['id']}: {e}", file=sys.stderr)
    out = os.path.join(DATA, product, "reddit.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    json.dump(records, open(out, "w"), indent=2)
    print(f"wrote {len(records)} reddit records -> {out}", file=sys.stderr)
    return records


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    product = sys.argv[2] if len(sys.argv) > 2 else ""
    n = int(sys.argv[3]) if len(sys.argv) > 3 and sys.argv[3].isdigit() else 2
    if product not in PRODUCTS:
        print(f"usage: socialproof.py <youtube|ingest|reddit|all> <{ '|'.join(PRODUCTS) }> [n|url]", file=sys.stderr)
        sys.exit(2)
    if cmd == "youtube":
        run_youtube(product, n)
    elif cmd == "ingest":
        print(json.dumps(ingest_video(product, sys.argv[3]), indent=2))
    elif cmd == "reddit":
        run_reddit(product, n)
    elif cmd == "all":
        run_youtube(product, n)
        run_reddit(product, n)
    else:
        print(f"usage: socialproof.py <youtube|ingest|reddit|all> <{ '|'.join(PRODUCTS) }> [n|url]", file=sys.stderr)
        sys.exit(2)
