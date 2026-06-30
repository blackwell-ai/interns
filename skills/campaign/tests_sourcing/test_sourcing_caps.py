"""Tests for the sourcing-ceiling fixes.

Two changes in run.py removed the ~1000-contact-per-run ceiling that made a
2000 ask impossible to fill:

  1. `_niche_cap(limit)` scales the per-run niche budget with the requested
     contact count (floor of `_MAX_SOURCING_NICHES`), so the loop no longer quits
     at 60 niches on a large ask.
  2. `_normalize_icp(icp)` is hashed for the sub-category cache key, so casing /
     whitespace / trailing-punctuation variants of one ICP share a single niche
     and exclusion memory instead of fragmenting into separate caches.

These tests cover boundaries, nulls, and bad state. Delete this folder once the
next large run is confirmed to fill past ~1000.

Run:
  cd /Users/shamitd/interns
  python -m pytest skills/campaign/tests_sourcing/ -v
"""

from __future__ import annotations

import importlib
import math
import re
from pathlib import Path

import pytest

from skills.campaign import run as camp


# ---------------------------------------------------------------------------
# _niche_cap — per-run niche budget scales with the ask
# ---------------------------------------------------------------------------

class TestNicheCap:
    def test_small_ask_uses_floor(self):
        # ceil(100/8) == 13, below the 60 floor, so the floor wins.
        assert camp._niche_cap(100) == camp._MAX_SOURCING_NICHES

    def test_floor_constant_is_sixty(self):
        # Guards the documented assumption the rest of these tests rely on.
        assert camp._MAX_SOURCING_NICHES == 60

    def test_large_ask_scales_above_floor(self):
        # The whole point: a 2000 ask must allow far more than 60 niches.
        cap = camp._niche_cap(2000)
        assert cap == 250
        assert cap > camp._MAX_SOURCING_NICHES

    def test_exact_floor_boundary(self):
        # 8 * 60 == 480 -> still exactly the floor; 481 tips one niche over.
        assert camp._niche_cap(480) == 60
        assert camp._niche_cap(481) == 61

    def test_monotonic_non_decreasing(self):
        caps = [camp._niche_cap(n) for n in range(0, 5000, 137)]
        assert caps == sorted(caps)

    def test_matches_formula(self):
        for n in (0, 50, 480, 1000, 2000, 9999):
            assert camp._niche_cap(n) == max(camp._MAX_SOURCING_NICHES,
                                             math.ceil(max(0, n) / 8))

    # --- nulls / bad state ---

    def test_zero_limit_is_floor_not_crash(self):
        assert camp._niche_cap(0) == camp._MAX_SOURCING_NICHES

    def test_negative_limit_clamped_to_floor(self):
        # A bad/negative quota must not produce a cap below the floor.
        assert camp._niche_cap(-500) == camp._MAX_SOURCING_NICHES

    def test_cap_is_int(self):
        # niche_num (an int counter) is compared against this; keep it an int.
        assert isinstance(camp._niche_cap(2000), int)

    def test_loop_uses_scaled_cap_not_raw_constant(self):
        """Regression guard: the sourcing loop must compare against the scaled
        cap, not the flat `_MAX_SOURCING_NICHES`, or the ceiling comes back."""
        src = Path(camp.__file__).read_text()
        body = src.split("async def source_contacts_pipeline", 1)[1]
        body = body.split("\nasync def ", 1)[0].split("\ndef ", 1)[0]
        assert "max_niches = _niche_cap(limit)" in body
        assert "niche_num >= max_niches" in body
        assert "niche_num >= _MAX_SOURCING_NICHES" not in body


# ---------------------------------------------------------------------------
# _normalize_icp — canonical cache key
# ---------------------------------------------------------------------------

class TestNormalizeIcp:
    @pytest.mark.parametrize("variant", [
        "DTC brands",
        "dtc brands",
        "DTC  brands",          # doubled internal space
        "  DTC brands  ",       # surrounding whitespace
        "DTC brands.",          # trailing period
        "DTC brands!!!",        # trailing punctuation run
        "\tDTC\nbrands\n",      # mixed whitespace
    ])
    def test_variants_collapse_to_one_form(self, variant):
        assert camp._normalize_icp(variant) == "dtc brands"

    def test_typo_is_not_normalized_away(self):
        # We must not guess intent — a typo legitimately forks its own cache.
        assert camp._normalize_icp("consumeres") != camp._normalize_icp("consumers")

    def test_internal_punctuation_preserved(self):
        # Only *trailing* punctuation is stripped; meaning-bearing inner punctuation stays.
        assert camp._normalize_icp("B2B, DTC & retail.") == "b2b, dtc & retail"

    def test_empty_string(self):
        assert camp._normalize_icp("") == ""

    def test_whitespace_only(self):
        assert camp._normalize_icp("   \t\n ") == ""

    def test_idempotent(self):
        once = camp._normalize_icp("  DTC Brands.  ")
        assert camp._normalize_icp(once) == once


# ---------------------------------------------------------------------------
# SubcategoryCache — variants share one cache file; the cache still works
# ---------------------------------------------------------------------------

class TestSubcategoryCacheKeying:
    @pytest.fixture
    def tmp_subcat_dir(self, tmp_path, monkeypatch):
        d = tmp_path / "subcats"
        monkeypatch.setattr(camp, "_SUBCAT_DIR", d)
        return d

    def test_variants_map_to_same_file(self, tmp_subcat_dir):
        a = camp.SubcategoryCache("DTC brands")
        b = camp.SubcategoryCache("  dtc   brands.  ")
        assert a._path == b._path

    def test_typo_maps_to_different_file(self, tmp_subcat_dir):
        a = camp.SubcategoryCache("brands selling products to consumers")
        b = camp.SubcategoryCache("brands selling products to consumeres")
        assert a._path != b._path

    def test_shared_memory_across_variants(self, tmp_subcat_dir):
        """The real payoff: niches added under one spelling are visible to a
        differently-cased re-run, so it does not re-explore from scratch."""
        first = camp.SubcategoryCache("DTC Brands")
        first.add(["DTC sleep supplements", "DTC men's grooming"])
        first.mark_searched("DTC sleep supplements")

        # A later run types it differently; same underlying cache.
        second = camp.SubcategoryCache("dtc brands")
        assert set(second.all_labels()) == {"DTC sleep supplements", "DTC men's grooming"}
        assert second.unsearched() == ["DTC men's grooming"]

    def test_add_dedups_against_stored_and_drops_blank(self, tmp_subcat_dir):
        # The guarantee that matters for cross-run memory: a label already stored
        # is not re-added on a later call, and blank labels are ignored.
        c = camp.SubcategoryCache("DTC brands")
        c.add(["DTC sleep supplements", " "])
        c.add(["DTC sleep supplements", "DTC men's grooming"])
        assert c.all_labels() == ["DTC sleep supplements", "DTC men's grooming"]

    def test_persists_to_disk(self, tmp_subcat_dir):
        camp.SubcategoryCache("DTC brands").add(["DTC pet supplements"])
        files = list(tmp_subcat_dir.glob("*.json"))
        assert len(files) == 1
        reloaded = camp.SubcategoryCache("DTC brands")
        assert reloaded.all_labels() == ["DTC pet supplements"]

    # --- bad state / missing resources ---

    def test_corrupt_cache_file_falls_back(self, tmp_subcat_dir):
        # A truncated/garbage cache must not crash a run — it resets cleanly.
        c = camp.SubcategoryCache("DTC brands")
        c._path.parent.mkdir(parents=True, exist_ok=True)
        c._path.write_text("{ this is not json")
        recovered = camp.SubcategoryCache("DTC brands")
        assert recovered.all_labels() == []

    def test_missing_dir_created_on_write(self, tmp_subcat_dir):
        assert not tmp_subcat_dir.exists()
        camp.SubcategoryCache("DTC brands").add(["DTC candles"])
        assert tmp_subcat_dir.exists()

    def test_mark_searched_unknown_label_is_noop(self, tmp_subcat_dir):
        c = camp.SubcategoryCache("DTC brands")
        c.add(["DTC candles"])
        c.mark_searched("not a real niche")  # must not raise
        assert c.unsearched() == ["DTC candles"]
