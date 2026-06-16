#!/usr/bin/env python3
"""Best-effort YC Bookface step for the daily digest.

Runs the `bookface-feed` browse skill and appends founder posts to items.jsonl
(cwd = run dir). Bookface auth is the YC SSO session in the browse daemon, which
is browser-based and can expire, so this NEVER fails the run: errors are logged
and skipped, and it always exits 0.

Bookface content is YC-confidential; the operator chose to include it in the
digest (committed + emailed). See the decision doc.
"""

import json
import os
import subprocess


def find_browse():
    for p in (
        os.path.expanduser("~/.claude/skills/gstack/browse/dist/browse"),
        os.path.join(os.getcwd(), ".claude/skills/gstack/browse/dist/browse"),
    ):
        if os.path.isfile(p) and os.access(p, os.X_OK):
            return p
    return None


def main():
    browse = find_browse()
    if not browse:
        print("bookface: browse binary not found; skipping")
        return
    try:
        subprocess.run([browse, "state", "load", "research"], capture_output=True, timeout=60)
    except Exception:
        pass
    try:
        p = subprocess.run(
            [browse, "skill", "run", "bookface-feed", "--arg", "scrolls=3", "--timeout=120"],
            capture_output=True, text=True, timeout=200,
        )
        line = next((ln for ln in p.stdout.splitlines() if ln.startswith("{")), "")
        data = json.loads(line) if line else {}
    except Exception as e:
        print(f"bookface: failed: {str(e)[:100]}")
        return
    kept = 0
    with open("items.jsonl", "a", encoding="utf-8") as f:
        for post in data.get("posts", []):
            text = (post.get("text") or "").strip()
            if not text:
                continue
            who = post.get("author") or ""
            if post.get("company"):
                who = f"{who} / {post['company']}".strip(" /")
            f.write(json.dumps({
                "source": "Bookface", "label": "Bookface", "title": text[:80],
                "url": post.get("url", ""), "link": "", "text": text[:4000],
                "author": who, "score": None, "comments": None, "ts": post.get("ts"),
            }, ensure_ascii=False) + "\n")
            kept += 1
    print(f"bookface: appended {kept} posts")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # never fail the digest run
        print(f"bookface: unexpected error, skipping: {str(e)[:120]}")
