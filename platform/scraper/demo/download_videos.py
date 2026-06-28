#!/usr/bin/env python3
"""Download every corpus video as an mp4, organized by foundation, for the
sendable dataset package. Resumable (download archive), continues past failures.

  cd platform/scraper && source .venv/bin/activate
  python demo/download_videos.py
"""
import os
import re
import sqlite3
import sys

import yt_dlp

BASE = "/home/armaan/Downloads/blackwell-foundation-dataset"
VIDEOS = os.path.join(BASE, "videos")
os.makedirs(VIDEOS, exist_ok=True)


def slug(s):
    return re.sub(r"[^A-Za-z0-9]+", "-", s).strip("-")


db = sqlite3.connect("demo/foundation_wide.db")
rows = db.execute("SELECT product, url, id FROM clips ORDER BY product").fetchall()
print(f"{len(rows)} videos to fetch -> {VIDEOS}", flush=True)

archive = os.path.join(BASE, "download-archive.txt")
ok = fail = 0
fails = []
for i, (product, url, vid) in enumerate(rows, 1):
    folder = os.path.join(VIDEOS, slug(product))
    os.makedirs(folder, exist_ok=True)
    opts = {
        "format": "best[height<=480][ext=mp4]/best[height<=480]/best",
        "outtmpl": os.path.join(folder, "%(id)s.%(ext)s"),
        "noplaylist": True, "quiet": True, "no_warnings": True,
        "download_archive": archive, "ignoreerrors": True, "retries": 2,
    }
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            rc = ydl.download([url])
        # consider it ok if a file for this id now exists
        exists = any(f.startswith(vid + ".") for f in os.listdir(folder))
        if exists:
            ok += 1
        else:
            fail += 1; fails.append((product, url))
    except Exception as e:
        fail += 1; fails.append((product, url))
        print(f"  FAIL {vid}: {type(e).__name__}: {str(e)[:90]}", file=sys.stderr, flush=True)
    if i % 15 == 0:
        print(f"  {i}/{len(rows)} (ok {ok}, fail {fail})", flush=True)

print(f"done: {ok} downloaded, {fail} failed", flush=True)
if fails:
    open(os.path.join(BASE, "failed.txt"), "w").write("\n".join(f"{p}\t{u}" for p, u in fails))
# size report
total = sum(os.path.getsize(os.path.join(dp, f)) for dp, _, fs in os.walk(VIDEOS) for f in fs)
print(f"videos total: {total/1e9:.2f} GB", flush=True)
