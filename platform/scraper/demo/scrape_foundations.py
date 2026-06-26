#!/usr/bin/env python3
"""Scrape foundation review videos into a separate DB, reusing scraper.py wholesale.

We only swap the product list (and force a demo DB) so the committed scraper config
and videos.db stay untouched.

  cd platform/scraper && source .venv/bin/activate
  python demo/scrape_foundations.py --db demo/foundation.db          # full run
  python demo/scrape_foundations.py --db demo/foundation.db --only "Estée Lauder Double Wear" --target 2 --candidates 8
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import scraper  # noqa: E402

# Spread across skin type, finish, coverage, and price so the recommendation
# genuinely depends on the shopper's stated profile. Queries lean on "wear test"
# / "honest review" to pull persona-rich, long-form reviews (not 30s hauls).
scraper.PRODUCTS = [
    ("Estée Lauder Double Wear",        "Estee Lauder Double Wear foundation review wear test"),
    ("NARS Sheer Glow",                 "NARS Sheer Glow foundation review wear test"),
    ("Charlotte Tilbury Beautiful Skin","Charlotte Tilbury Beautiful Skin foundation review wear test"),
    ("Fenty Pro Filt'r Soft Matte",     "Fenty Beauty Pro Filtr Soft Matte foundation review wear test"),
    ("L'Oréal Infallible Fresh Wear",   "Loreal Infallible Fresh Wear foundation review wear test"),
    ("Maybelline Fit Me Matte",         "Maybelline Fit Me Matte Poreless foundation review wear test"),
    ("Armani Luminous Silk",            "Armani Luminous Silk foundation review wear test"),
    ("Rare Beauty Liquid Touch",        "Rare Beauty Liquid Touch Weightless foundation review wear test"),
    ("e.l.f. Halo Glow",                "elf Halo Glow Liquid Filter review wear test"),
    ("Ilia Super Serum Skin Tint",      "Ilia Super Serum Skin Tint foundation review wear test"),
]

if __name__ == "__main__":
    raise SystemExit(scraper.main(sys.argv[1:]))
