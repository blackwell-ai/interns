#!/usr/bin/env python3
"""New-papers step for the daily digest: recent, relevant arXiv papers.

Queries the public arXiv Atom API (no auth) for each row in papers-queries.csv,
keeps papers submitted within the last `--days`, drops any arXiv id that already
appeared in a prior brain digest (so the same paper never repeats day to day),
and appends the survivors to items.jsonl (cwd = the run dir) in the same item
shape as extract/discord/twitter. Each record carries source "arXiv" and
kind "paper" so llm.digest can route it into the Papers section.

Best-effort, exactly like the X and Bookface steps: arXiv can rate-limit or
time out, so every error is logged and skipped, and the step always exits 0.

Invoked by the flow as:
  {python: steps/papers.py, queries: "<path>", days: N, max: N,
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

ATOM = "{http://www.w3.org/2005/Atom}"
API = "http://export.arxiv.org/api/query"
ABS_ID = re.compile(r"arxiv\.org/abs/([0-9]+\.[0-9]+)", re.I)


def arg_value(name, default=None):
    a = sys.argv[1:]
    for i, x in enumerate(a):
        if x == name and i + 1 < len(a):
            return a[i + 1]
    return default


def seen_ids(brain_dir):
    """arXiv ids already surfaced in any prior digest, so we never repeat one."""
    ids = set()
    if not brain_dir or not os.path.isdir(brain_dir):
        return ids
    for fn in os.listdir(brain_dir):
        if not fn.endswith(".md"):
            continue
        try:
            text = open(os.path.join(brain_dir, fn), encoding="utf-8").read()
        except Exception:
            continue
        ids.update(m.lower() for m in ABS_ID.findall(text))
    return ids


def fetch_query(query, per_query):
    qs = urllib.parse.urlencode({
        "search_query": query,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
        "start": 0,
        "max_results": per_query,
    })
    req = urllib.request.Request(f"{API}?{qs}", headers={"User-Agent": "blackwell-researcher-digest/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return ET.fromstring(r.read())


def parse_entries(root):
    out = []
    for e in root.findall(f"{ATOM}entry"):
        raw_id = (e.findtext(f"{ATOM}id") or "").strip()
        m = ABS_ID.search(raw_id)
        if not m:
            continue
        aid = m.group(1).lower()
        title = " ".join((e.findtext(f"{ATOM}title") or "").split())
        summary = " ".join((e.findtext(f"{ATOM}summary") or "").split())
        published = (e.findtext(f"{ATOM}published") or "").strip()
        authors = [a.findtext(f"{ATOM}name") or "" for a in e.findall(f"{ATOM}author")]
        authors = [a for a in authors if a]
        byline = authors[0] + (" et al." if len(authors) > 1 else "") if authors else ""
        out.append({
            "id": aid, "title": title, "summary": summary,
            "published": published, "author": byline,
            "url": f"https://arxiv.org/abs/{aid}",
        })
    return out


def main():
    queries_path = arg_value("--queries")
    if not queries_path or not os.path.exists(queries_path):
        print("papers: no queries file; skipping")
        return
    days = int(arg_value("--days", "4"))
    cap = int(arg_value("--max", "12"))
    per_query = int(arg_value("--per-query", "15"))
    brain_dir = arg_value("--brain-digests", "")

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    already = seen_ids(brain_dir)
    rows = list(csv.DictReader(open(queries_path, encoding="utf-8")))

    found = {}  # arxiv id -> record, dedup across queries
    for i, r in enumerate(rows):
        q = (r.get("query") or "").strip()
        if not q:
            continue
        if i:  # arXiv asks for <= 1 request / 3s
            time.sleep(3)
        try:
            entries = parse_entries(fetch_query(q, per_query))
        except Exception as e:
            print(f"papers: query {r.get('label') or q[:40]!r} failed: {str(e)[:80]}")
            continue
        for p in entries:
            if p["id"] in already or p["id"] in found:
                continue
            try:
                pub = datetime.fromisoformat(p["published"].replace("Z", "+00:00"))
            except Exception:
                pub = None
            if pub and pub < cutoff:
                continue
            found[p["id"]] = p

    # newest first, capped
    papers = sorted(found.values(), key=lambda p: p.get("published", ""), reverse=True)[:cap]

    with open("items.jsonl", "a", encoding="utf-8") as f:
        for p in papers:
            f.write(json.dumps({
                "source": "arXiv", "label": "arXiv", "kind": "paper",
                "title": p["title"][:200], "url": p["url"], "link": "",
                "text": p["summary"][:4000], "author": p["author"],
                "score": None, "comments": None, "ts": p["published"],
            }, ensure_ascii=False) + "\n")
    print(f"papers: appended {len(papers)} papers from {len(rows)} queries "
          f"(window {days}d, {len(already)} already seen)")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # never fail the digest run
        print(f"papers: unexpected error, skipping: {str(e)[:120]}")
