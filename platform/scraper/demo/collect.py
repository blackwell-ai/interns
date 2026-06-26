#!/usr/bin/env python3
"""Robust, multi-platform clip acquisition for the foundation demo.

Replaces the blockable youtube-transcript-api with a two-path transcript layer:

  1. caption-first  — yt-dlp writes existing auto/manual captions (fast, free,
     uses yt-dlp's player extraction, not the soft-blocked transcript endpoint).
  2. audio fallback — yt-dlp pulls bestaudio, OpenAI gpt-4o-transcribe turns it
     into text. Works for anything yt-dlp supports (TikTok, Instagram, X, ...)
     and for YouTube clips that ship no captions.

One downloader (yt-dlp) spans every platform; transcription runs on our own
OpenAI key. Curated URLs in, structured records out.

  cd platform/scraper && source .venv/bin/activate
  set -a; . ../../credentials/.env; set +a
  python demo/collect.py "https://www.youtube.com/watch?v=..."        # one url
  python demo/collect.py --force-audio "https://..."                  # test the whisper path
  python demo/collect.py --urls demo/urls.txt --db demo/foundation.db # batch -> sqlite
"""
import argparse
import glob
import json
import os
import re
import sqlite3
import sys
import tempfile

import yt_dlp
from openai import OpenAI

TRANSCRIBE_MODEL = os.environ.get("TRANSCRIBE_MODEL", "gpt-4o-transcribe")
PREFERRED_LANGS = ["en", "en-US", "en-GB", "en-orig"]
_client = None


def client():
    global _client
    if _client is None:
        _client = OpenAI()
    return _client


# ---------------------------------------------------------------- metadata
def metadata(url):
    opts = {"quiet": True, "skip_download": True, "noplaylist": True}
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)
    return {
        "id": info.get("id"),
        "platform": info.get("extractor_key"),
        "title": info.get("title"),
        "channel": info.get("uploader") or info.get("channel") or info.get("uploader_id"),
        "url": info.get("webpage_url") or url,
        "duration_seconds": info.get("duration"),
        "view_count": info.get("view_count"),
        "like_count": info.get("like_count"),
        "published_at": info.get("upload_date"),  # YYYYMMDD
        "description": (info.get("description") or "")[:2000],
    }


# ---------------------------------------------------------------- captions
def _parse_json3(path):
    data = json.load(open(path))
    segs = []
    for ev in data.get("events", []):
        if "segs" not in ev:
            continue
        text = "".join(s.get("utf8", "") for s in ev["segs"]).strip()
        if not text:
            continue
        start = ev.get("tStartMs", 0) / 1000.0
        dur = ev.get("dDurationMs", 0) / 1000.0
        segs.append({"text": text, "start": round(start, 2), "duration": round(dur, 2)})
    return segs


def _parse_vtt(path):
    segs = []
    cur_start = None
    buf = []
    ts = re.compile(r"(\d+):(\d+):(\d+)[.,](\d+)\s*-->\s*(\d+):(\d+):(\d+)")
    for line in open(path, encoding="utf-8"):
        m = ts.search(line)
        if m:
            if cur_start is not None and buf:
                segs.append({"text": " ".join(buf).strip(), "start": cur_start, "duration": 0})
            h, mi, s, ms = m.group(1, 2, 3, 4)
            cur_start = int(h) * 3600 + int(mi) * 60 + int(s) + int(ms) / 1000.0
            buf = []
        elif line.strip() and not line.strip().isdigit() and "WEBVTT" not in line:
            txt = re.sub(r"<[^>]+>", "", line).strip()
            if txt:
                buf.append(txt)
    if cur_start is not None and buf:
        segs.append({"text": " ".join(buf).strip(), "start": round(cur_start, 2), "duration": 0})
    # dedupe consecutive identical lines (YouTube auto-caption rolling artifact)
    out = []
    for s in segs:
        if not out or out[-1]["text"] != s["text"]:
            out.append(s)
    return out


def captions(url, tmp):
    out_tmpl = os.path.join(tmp, "%(id)s.%(ext)s")
    opts = {
        "quiet": True, "skip_download": True, "noplaylist": True,
        "writeautomaticsub": True, "writesubtitles": True,
        "subtitleslangs": PREFERRED_LANGS, "subtitlesformat": "json3/vtt/best",
        "outtmpl": out_tmpl,
    }
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])
    except Exception:
        return None
    for ext, parse in (("json3", _parse_json3), ("vtt", _parse_vtt)):
        files = sorted(glob.glob(os.path.join(tmp, f"*.{ext}")))
        if files:
            try:
                segs = parse(files[0])
                if segs:
                    return segs
            except Exception:
                continue
    return None


# ---------------------------------------------------------------- audio -> AI
def audio_transcript(url, tmp):
    out_tmpl = os.path.join(tmp, "%(id)s.%(ext)s")
    opts = {
        "quiet": True, "noplaylist": True, "format": "bestaudio/best",
        "outtmpl": out_tmpl,
        "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3",
                            "preferredquality": "64"}],
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([url])
    mp3s = sorted(glob.glob(os.path.join(tmp, "*.mp3")))
    if not mp3s:
        raise RuntimeError("audio extraction produced no mp3")
    path = mp3s[0]
    size_mb = os.path.getsize(path) / 1e6
    if size_mb > 24:
        raise RuntimeError(f"audio {size_mb:.0f}MB exceeds 25MB OpenAI limit (re-encode lower)")
    try:
        with open(path, "rb") as f:
            text = client().audio.transcriptions.create(
                model=TRANSCRIBE_MODEL, file=f, response_format="text")
    except Exception as e:
        # gpt-4o-transcribe caps audio at 1400s; whisper-1 has no such cap
        if "longer than" in str(e) or "duration" in str(e):
            with open(path, "rb") as f:
                text = client().audio.transcriptions.create(
                    model="whisper-1", file=f, response_format="text")
        else:
            raise
    return str(text).strip()


# ---------------------------------------------------------------- collect one
def collect(url, force_audio=False):
    meta = metadata(url)
    with tempfile.TemporaryDirectory() as tmp:
        segs = None if force_audio else captions(url, tmp)
        if segs:
            transcript = " ".join(s["text"] for s in segs)
            source = "captions"
        else:
            transcript = audio_transcript(url, tmp)
            segs = []
            source = f"audio:{TRANSCRIBE_MODEL}"
    meta["transcript"] = transcript
    meta["transcript_segments"] = segs
    meta["transcript_source"] = source
    meta["transcript_chars"] = len(transcript)
    return meta


# ---------------------------------------------------------------- storage
def ensure_db(path):
    conn = sqlite3.connect(path)
    conn.execute("""CREATE TABLE IF NOT EXISTS clips (
        id TEXT, platform TEXT, url TEXT PRIMARY KEY, title TEXT, channel TEXT,
        product TEXT, duration_seconds INTEGER, view_count INTEGER, like_count INTEGER,
        published_at TEXT, transcript TEXT, transcript_segments TEXT,
        transcript_source TEXT, description TEXT, fetched_at TEXT)""")
    conn.commit()
    return conn


def save(conn, rec, product=None):
    conn.execute(
        """INSERT INTO clips (id,platform,url,title,channel,product,duration_seconds,
            view_count,like_count,published_at,transcript,transcript_segments,
            transcript_source,description,fetched_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,datetime('now'))
           ON CONFLICT(url) DO UPDATE SET transcript=excluded.transcript,
            transcript_segments=excluded.transcript_segments,
            transcript_source=excluded.transcript_source, fetched_at=datetime('now')""",
        (rec["id"], rec["platform"], rec["url"], rec["title"], rec["channel"], product,
         rec["duration_seconds"], rec["view_count"], rec["like_count"], rec["published_at"],
         rec["transcript"], json.dumps(rec["transcript_segments"]), rec["transcript_source"],
         rec["description"]))
    conn.commit()


def main(argv=None):
    p = argparse.ArgumentParser(description="Robust multi-platform clip collector.")
    p.add_argument("url", nargs="?", help="single video URL")
    p.add_argument("--urls", help="file of 'product<TAB>url' or just 'url' per line")
    p.add_argument("--db", help="sqlite path to store into")
    p.add_argument("--force-audio", action="store_true", help="skip captions, test the AI path")
    args = p.parse_args(argv)

    jobs = []
    if args.url:
        jobs.append((None, args.url))
    if args.urls:
        for line in open(args.urls):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t") if "\t" in line else [None, line]
            jobs.append((parts[0], parts[-1]))
    if not jobs:
        p.error("give a URL or --urls file")

    conn = ensure_db(args.db) if args.db else None
    for product, url in jobs:
        try:
            rec = collect(url, force_audio=args.force_audio)
            tag = f"[{rec['platform']}] {rec['transcript_source']:24} {rec['transcript_chars']:6d} chars  {rec['title'][:54]}"
            print(tag)
            if conn:
                save(conn, rec, product)
        except Exception as e:
            print(f"FAIL {url}: {type(e).__name__}: {str(e)[:140]}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
