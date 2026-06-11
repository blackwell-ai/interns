#!/usr/bin/env python3
"""Filter a findemail-enriched CSV into a clean send queue.

Drops what shouldn't be cold-emailed:
  - email_status == 'invalid'   (would bounce -> hurts domain reputation)
  - generic/role local-parts    (info@, hello@, pr@, ... -> not a decision-maker)
  - empty first_name            (weak personalization / often a parked address)

Input : enriched CSV (findemail output: email, first_name, domain, brand,
        email_status, ...). Output: queue CSV with the columns send_fast.py
        reads (brand, domain, email, first_name).

Usage: python3 prep_queue.py <enriched.csv> <queue.csv> [min_score]
"""
import csv
import sys

GENERIC = {"info", "hello", "support", "team", "contact", "sales", "press", "hi",
           "care", "help", "admin", "orders", "service", "wholesale", "pr", "media",
           "ohi", "hey", "hq", "newsletter", "no-reply", "noreply"}


def main(in_path: str, out_path: str, min_score: int = 0) -> None:
    rows = list(csv.DictReader(open(in_path)))
    queue, dropped = [], {"invalid": 0, "generic": 0, "no_name": 0, "low_score": 0}
    for r in rows:
        email = (r.get("email") or "").strip().lower()
        if not email or "@" not in email:
            continue
        if r.get("email_status") == "invalid":
            dropped["invalid"] += 1; continue
        if email.split("@")[0] in GENERIC:
            dropped["generic"] += 1; continue
        if not (r.get("first_name") or "").strip():
            dropped["no_name"] += 1; continue
        try:
            if min_score and int(r.get("email_score") or 0) < min_score:
                dropped["low_score"] += 1; continue
        except ValueError:
            pass
        queue.append({"brand": r.get("brand", ""), "domain": r.get("domain", ""),
                      "email": email, "first_name": r["first_name"].strip().title()})
    with open(out_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["brand", "domain", "email", "first_name"])
        w.writeheader(); w.writerows(queue)
    print(f"queue: {len(queue)} leads (dropped {dropped})")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit("usage: prep_queue.py <enriched.csv> <queue.csv> [min_score]")
    main(sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 0)
