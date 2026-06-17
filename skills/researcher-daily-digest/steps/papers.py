#!/usr/bin/env python3
"""New-papers step for the daily digest: recent + trending AI papers.

Pulls from three key-free providers and folds them into one Papers section:

- arXiv (query-driven): the public Atom API, one row per query in
  papers-queries.csv. Keeps papers submitted within the last `--days`. This is
  the precision-targeted source: papers that match our own commerce/agent terms.
- Hugging Face Papers (huggingface.co/papers): the public daily_papers JSON API.
  The community-curated "trending today" set, broad AI. We walk back `--days`
  calendar days to cover the weekend gap, same as arXiv.
- alphaXiv (alphaxiv.org): the public v3 feed, sort=Hot over `--alphaxiv-interval`
  ("3 Days" | "7 Days" | "30 Days" | "90 Days" | "All time"). The community
  trending/discussion signal; includes native posts that are not on arXiv.

HF and alphaXiv are "what is hot right now" feeds, so they get NO publication-date
cutoff: a paper trending today may have been posted weeks ago, and dropping it on
age would defeat the point. Repetition day to day is prevented instead by the
shared dedup (below), not by a recency window.

Dedup is shared across all three providers and across days. A paper is keyed by
its bare arXiv id when it has one (so the same paper surfaced by arXiv, HF, and
alphaXiv appears once, and never repeats once it lands in a prior brain digest);
alphaXiv's native non-arXiv posts are keyed by their alphaXiv slug. Provider
priority on a tie is arXiv > HF > alphaXiv (our targeted queries win), and the
URL we render carries the id so tomorrow's run can see it.

Every record is appended to items.jsonl (cwd = the run dir) in the same item
shape as extract/discord/twitter, with kind "paper" so llm.digest routes it into
the Papers section. Each provider keeps its own source label ("arXiv",
"HF Papers", "alphaXiv") for attribution.

Best-effort, exactly like the X and Bookface steps: any provider can rate-limit
or time out, so every error is logged and skipped, and the step always exits 0.

Invoked by the flow as:
  {python: steps/papers.py, queries: "<path>", days: N, max: N,
   hf_max: N, alphaxiv_max: N, alphaxiv_interval: "7 Days",
   brain_digests: "<repo>/brain/research/digests"}
"""

import csv
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from xml.etree import ElementTree as ET

UA = "blackwell-researcher-digest/1.0"

ATOM = "{http://www.w3.org/2005/Atom}"
ARXIV_API = "http://export.arxiv.org/api/query"
HF_API = "https://huggingface.co/api/daily_papers"
ALPHAXIV_API = "https://api.alphaxiv.org/papers/v3/feed"

# A bare arXiv id is YYMM.NNNNN (4 digits, dot, 4-5 digits).
ARXIV_ID = re.compile(r"\b([0-9]{4}\.[0-9]{4,5})\b")
# Ids already surfaced in a prior digest: arXiv ids reachable via any of the
# three providers' canonical URLs, plus alphaXiv native slugs (2026.some-slug).
SEEN_ARXIV = re.compile(
    r"(?:arxiv\.org/abs/|huggingface\.co/papers/|alphaxiv\.org/abs/)([0-9]{4}\.[0-9]{4,5})",
    re.I,
)
SEEN_ALPHA_SLUG = re.compile(r"alphaxiv\.org/abs/([0-9]{4}\.[a-z][a-z0-9._-]*)", re.I)


def arg_value(name, default=None):
    a = sys.argv[1:]
    for i, x in enumerate(a):
        if x == name and i + 1 < len(a):
            return a[i + 1]
    return default


def get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def byline(authors):
    authors = [a for a in authors if a]
    if not authors:
        return ""
    return authors[0] + (" et al." if len(authors) > 1 else "")


def seen_keys(brain_dir):
    """Dedup keys already surfaced in any prior digest, so we never repeat one.

    Keys are bare arXiv ids (lowercased) and `alphaxiv:<slug>` for native posts,
    matching the keys the providers below produce.
    """
    keys = set()
    if not brain_dir or not os.path.isdir(brain_dir):
        return keys
    for fn in os.listdir(brain_dir):
        if not fn.endswith(".md"):
            continue
        try:
            text = open(os.path.join(brain_dir, fn), encoding="utf-8").read()
        except Exception:
            continue
        keys.update(m.lower() for m in SEEN_ARXIV.findall(text))
        keys.update("alphaxiv:" + m.lower() for m in SEEN_ALPHA_SLUG.findall(text))
    return keys


# --- arXiv (query-driven, recency-bounded) ----------------------------------

def fetch_arxiv_query(query, per_query):
    qs = urllib.parse.urlencode({
        "search_query": query,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
        "start": 0,
        "max_results": per_query,
    })
    req = urllib.request.Request(f"{ARXIV_API}?{qs}", headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return ET.fromstring(r.read())


def parse_arxiv(root):
    out = []
    for e in root.findall(f"{ATOM}entry"):
        raw_id = (e.findtext(f"{ATOM}id") or "").strip()
        m = ARXIV_ID.search(raw_id)
        if not m:
            continue
        aid = m.group(1).lower()
        title = " ".join((e.findtext(f"{ATOM}title") or "").split())
        summary = " ".join((e.findtext(f"{ATOM}summary") or "").split())
        published = (e.findtext(f"{ATOM}published") or "").strip()
        authors = [a.findtext(f"{ATOM}name") or "" for a in e.findall(f"{ATOM}author")]
        out.append({
            "key": aid, "source": "arXiv", "title": title, "summary": summary,
            "author": byline(authors), "url": f"https://arxiv.org/abs/{aid}",
            "published": published, "score": None,
        })
    return out


def arxiv_records(queries_path, days, cap, per_query, seen):
    if not queries_path or not os.path.exists(queries_path) or cap <= 0:
        return []
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    rows = list(csv.DictReader(open(queries_path, encoding="utf-8")))
    found = []
    for i, r in enumerate(rows):
        q = (r.get("query") or "").strip()
        if not q:
            continue
        if i:  # arXiv asks for <= 1 request / 3s
            time.sleep(3)
        try:
            entries = parse_arxiv(fetch_arxiv_query(q, per_query))
        except Exception as e:
            print(f"papers/arxiv: query {r.get('label') or q[:40]!r} failed: {str(e)[:80]}")
            continue
        for p in entries:
            if p["key"] in seen:
                continue
            try:
                pub = datetime.fromisoformat(p["published"].replace("Z", "+00:00"))
            except Exception:
                pub = None
            if pub and pub < cutoff:
                continue
            seen.add(p["key"])
            found.append(p)
    found.sort(key=lambda p: p.get("published", ""), reverse=True)
    return found[:cap]


# --- Hugging Face daily papers (trending, no recency cutoff) -----------------

def hf_records(days, cap, seen):
    if cap <= 0:
        return []
    today = datetime.now(timezone.utc).date()
    out = []
    for back in range(max(days, 1)):
        if len(out) >= cap:
            break
        date = (today - timedelta(days=back)).isoformat()
        url = f"{HF_API}?date={date}&limit=50"
        try:
            items = get_json(url)
        except Exception as e:
            print(f"papers/hf: {date} failed: {str(e)[:80]}")
            continue
        for it in items:
            if len(out) >= cap:
                break
            p = it.get("paper") or {}
            aid = (p.get("id") or "").strip().lower()
            if not ARXIV_ID.fullmatch(aid):
                continue
            if aid in seen:
                continue
            seen.add(aid)
            authors = [a.get("name", "") for a in p.get("authors") or []]
            out.append({
                "key": aid, "source": "HF Papers",
                "title": " ".join((p.get("title") or it.get("title") or "").split()),
                "summary": " ".join((p.get("summary") or it.get("summary") or "").split()),
                "author": byline(authors), "url": f"https://huggingface.co/papers/{aid}",
                "published": (p.get("publishedAt") or it.get("publishedAt") or ""),
                "score": p.get("upvotes"),
            })
    return out


# --- alphaXiv trending feed (Hot over an interval, no recency cutoff) --------

def alphaxiv_records(interval, cap, seen):
    if cap <= 0:
        return []
    qs = urllib.parse.urlencode({
        "pageNum": 0, "pageSize": max(cap * 3, 20), "sort": "Hot", "interval": interval,
    })
    try:
        data = get_json(f"{ALPHAXIV_API}?{qs}")
    except Exception as e:
        print(f"papers/alphaxiv: feed failed: {str(e)[:80]}")
        return []
    out = []
    for p in data.get("papers") or []:
        if len(out) >= cap:
            break
        upid = (p.get("universal_paper_id") or "").strip()
        if not upid:
            continue
        if ARXIV_ID.fullmatch(upid.lower()):
            key = upid.lower()
        else:  # native alphaXiv post (e.g. a blog/report slug), not on arXiv
            key = "alphaxiv:" + upid.lower()
        if key in seen:
            continue
        seen.add(key)
        ps = p.get("paper_summary") or {}
        summary = ps.get("summary") or p.get("abstract") or ""
        out.append({
            "key": key, "source": "alphaXiv",
            "title": " ".join((p.get("title") or "").split()),
            "summary": " ".join(summary.split()),
            "author": byline(p.get("authors") or []),
            "url": f"https://www.alphaxiv.org/abs/{upid}",
            "published": (p.get("first_publication_date") or ""),
            "score": None,
        })
    return out


def main():
    queries_path = arg_value("--queries")
    days = int(arg_value("--days", "4"))
    cap = int(arg_value("--max", "10"))
    per_query = int(arg_value("--per-query", "15"))
    hf_max = int(arg_value("--hf-max", "6"))
    alphaxiv_max = int(arg_value("--alphaxiv-max", "6"))
    alphaxiv_interval = arg_value("--alphaxiv-interval", "7 Days")
    brain_dir = arg_value("--brain-digests", "")

    seen = seen_keys(brain_dir)
    base = len(seen)

    # Order sets provider priority on a shared-id tie: arXiv > HF > alphaXiv.
    records = []
    records += arxiv_records(queries_path, days, cap, per_query, seen)
    records += hf_records(days, hf_max, seen)
    records += alphaxiv_records(alphaxiv_interval, alphaxiv_max, seen)

    with open("items.jsonl", "a", encoding="utf-8") as f:
        for p in records:
            f.write(json.dumps({
                "source": p["source"], "label": p["source"], "kind": "paper",
                "title": p["title"][:200], "url": p["url"], "link": "",
                "text": p["summary"][:4000], "author": p["author"],
                "score": p.get("score"), "comments": None, "ts": p["published"],
            }, ensure_ascii=False) + "\n")

    by_source = {}
    for p in records:
        by_source[p["source"]] = by_source.get(p["source"], 0) + 1
    breakdown = ", ".join(f"{k} {v}" for k, v in by_source.items()) or "none"
    print(f"papers: appended {len(records)} papers ({breakdown}); "
          f"{base} already seen in prior digests")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # never fail the digest run
        print(f"papers: unexpected error, skipping: {str(e)[:120]}")
