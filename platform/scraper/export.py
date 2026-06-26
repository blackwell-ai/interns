#!/usr/bin/env python3
"""
Export the dataset from videos.db to a human-readable JSON file.

The SQLite database is the source of truth; this produces a browsable snapshot
(GitHub can't render a binary .db). Groups by product, with each product's
discovered quality dimensions and one structured preference record per video.

Usage:
    python export.py                              # -> data/preference_data.json
    python export.py --out data/full.json --include-transcripts
    python export.py --only "Oura Ring" --out oura.json
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3


def export(db_path: str, out_path: str, only: str | None, include_transcripts: bool) -> dict:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    # discovered dimensions per product
    dims_by_product = {
        r["product"]: {"category": r["category"], "dimensions": json.loads(r["dimensions"])}
        for r in conn.execute("SELECT product, category, dimensions FROM product_dimensions")
    }

    products: dict[str, dict] = {}
    rows = conn.execute(
        """
        SELECT v.product, v.video_id, v.title, v.channel, v.url, v.view_count,
               v.like_count, v.published_at, v.duration_seconds,
               v.language, v.is_generated, v.transcript,
               a.status, a.model, a.analyzed_at, a.extracted
        FROM videos v
        LEFT JOIN video_analysis a ON a.video_id = v.video_id
        ORDER BY v.product, v.view_count DESC
        """
    ).fetchall()

    for r in rows:
        if only and r["product"].lower() != only.lower():
            continue
        p = products.setdefault(r["product"], {
            "product": r["product"],
            "category": dims_by_product.get(r["product"], {}).get("category"),
            "dimensions": dims_by_product.get(r["product"], {}).get("dimensions", []),
            "videos": [],
        })
        video = {
            "video_id": r["video_id"], "title": r["title"], "channel": r["channel"],
            "url": r["url"], "view_count": r["view_count"], "like_count": r["like_count"],
            "published_at": r["published_at"], "duration_seconds": r["duration_seconds"],
            "language": r["language"], "is_generated": r["is_generated"],
            "analysis_status": r["status"], "model": r["model"], "analyzed_at": r["analyzed_at"],
            "extracted": json.loads(r["extracted"]) if r["extracted"] else None,
        }
        if include_transcripts:
            video["transcript"] = r["transcript"]
        p["videos"].append(video)

    conn.close()

    payload = {
        "source": os.path.basename(db_path),
        "product_count": len(products),
        "video_count": sum(len(p["videos"]) for p in products.values()),
        "analyzed_count": sum(1 for p in products.values()
                              for v in p["videos"] if v["analysis_status"] == "complete"),
        "products": list(products.values()),
    }

    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    return payload


def main() -> int:
    ap = argparse.ArgumentParser(description="Export videos.db dataset to JSON.")
    ap.add_argument("--db", default="videos.db")
    ap.add_argument("--out", default="data/preference_data.json")
    ap.add_argument("--only", default=None, help="single product by name")
    ap.add_argument("--include-transcripts", action="store_true",
                    help="also embed full transcript text (larger file)")
    args = ap.parse_args()

    payload = export(args.db, args.out, args.only, args.include_transcripts)
    size = os.path.getsize(args.out)
    print(f"wrote {args.out}  ({size:,} bytes)")
    print(f"  products={payload['product_count']}  videos={payload['video_count']}  "
          f"analyzed={payload['analyzed_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
