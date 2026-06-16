#!/usr/bin/env python3
"""Best-effort X (Twitter) step for the daily digest.

Runs the `twitter-search` browse browser-skill for each target and appends the
tweets to items.jsonl (cwd = the run dir) in the same item shape as extract and
discord. X needs the logged-in browse daemon, which is browser-based and flaky
(session expiry, rate limits), so this step NEVER fails the run: every error is
logged and skipped, and it always exits 0.

Invoked by the flow as: {python: steps/twitter.py, targets: "<path>"}.
"""

import csv
import json
import os
import subprocess
import sys


def find_browse():
    for p in (
        os.path.expanduser("~/.claude/skills/gstack/browse/dist/browse"),
        os.path.join(os.getcwd(), ".claude/skills/gstack/browse/dist/browse"),
    ):
        if os.path.isfile(p) and os.access(p, os.X_OK):
            return p
    return None


def arg_value(name):
    a = sys.argv[1:]
    for i, x in enumerate(a):
        if x == name and i + 1 < len(a):
            return a[i + 1]
    return None


def main():
    targets = arg_value("--targets")
    if not targets or not os.path.exists(targets):
        print("twitter: no targets file; skipping")
        return
    browse = find_browse()
    if not browse:
        print("twitter: browse binary not found; skipping")
        return

    # Wake the daemon and restore the saved X session (best-effort).
    try:
        subprocess.run([browse, "state", "load", "research"], capture_output=True, timeout=60)
    except Exception:
        pass

    rows = list(csv.DictReader(open(targets, encoding="utf-8")))
    kept = 0
    with open("items.jsonl", "a", encoding="utf-8") as f:
        for r in rows:
            typ = (r.get("type") or "").strip()
            val = (r.get("value") or "").strip()
            if not val:
                continue
            key = "handle" if typ == "handle" else "query"
            try:
                p = subprocess.run(
                    [browse, "skill", "run", "twitter-search",
                     "--arg", f"{key}={val}", "--arg", "scrolls=2", "--timeout=120"],
                    capture_output=True, text=True, timeout=180,
                )
                line = next((ln for ln in p.stdout.splitlines() if ln.startswith("{")), "")
                data = json.loads(line) if line else {}
            except Exception as e:
                print(f"twitter: {key}={val} failed: {str(e)[:80]}")
                continue
            src = data.get("source") or f"X {val}"
            for t in data.get("tweets", []):
                text = (t.get("text") or "").strip()
                if not text:
                    continue
                f.write(json.dumps({
                    "source": src, "label": src, "title": text[:80],
                    "url": t.get("url", ""), "link": "", "text": text[:4000],
                    "author": t.get("handle") or t.get("author") or "",
                    "score": None, "comments": None, "ts": t.get("ts"),
                }, ensure_ascii=False) + "\n")
                kept += 1
    print(f"twitter: appended {kept} tweets from {len(rows)} targets")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # never fail the digest run
        print(f"twitter: unexpected error, skipping: {str(e)[:120]}")
