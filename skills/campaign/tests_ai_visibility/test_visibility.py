"""Tests for AI-visibility GEO personalization.

The pilot fills each brand's {{personal_line}} from a live "does this brand show
up when a shopper asks an AI?" check. The load-bearing invariants:

  - personalize() NEVER returns empty. compose_lib.render raises on an empty
    slot, so a blank line would fail the whole compose for that row.
  - the line only ever names real competitors the model returned, never the
    target brand itself, never an invented one.
  - a model/transport failure degrades to a safe generic line, it never drops
    the contact or makes an unverified claim.
  - run.py's _personalize_visibility sets personal_line so it survives
    model_dump() into compose (Row is extra="allow"), and the GEO template
    renders with the produced values (no empty-slot crash).

Covered: happy/absent, present, no-competitors, LLM error, empty company,
competitor cleaning (target/dupes/blanks/substrings), run.py wiring, and a
real template render. Nulls and bad state per the harness test rule. Delete
this folder once the GEO pilot is confirmed in production.

Run:
  cd /Users/shamitd/interns
  PYTHONPATH="$PWD:$PWD/toolbox/src" toolbox/.venv/bin/pytest \
    skills/campaign/tests_ai_visibility/test_visibility.py -v
"""
from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from skills.campaign import run as camp
from skills.campaign import visibility
from toolbox.core import models
from toolbox.primitives.compose import lib as compose_lib

pytestmark = pytest.mark.asyncio

_NICHE = "maternity clothing brands"


def _ranking(brands, mentions, niche="maternity clothing"):
    return visibility._AIRanking(niche=niche, brands=brands, mentions_target=mentions)


def _patch_check(monkeypatch, *, brands, mentions, niche="maternity clothing"):
    monkeypatch.setattr(visibility, "_check",
                        lambda company, domain, hint: _ranking(brands, mentions, niche))


def _patch_raise(monkeypatch):
    def boom(company, domain, hint):
        raise RuntimeError("model unavailable")
    monkeypatch.setattr(visibility, "_check", boom)


# ── personalize: the four branches, all non-empty ──────────────────────────

async def test_absent_names_real_competitor(monkeypatch):
    _patch_check(monkeypatch, brands=["Hatch", "Ingrid & Isabel"], mentions=False)
    line = await visibility.personalize("Acme Maternity", _NICHE)
    assert line
    assert "Hatch" in line
    assert "Acme Maternity" in line          # the gap is framed against the target
    assert "never came up" in line


async def test_present_is_softer_and_nonempty(monkeypatch):
    _patch_check(monkeypatch, brands=["Acme Maternity", "Hatch"], mentions=True)
    line = await visibility.personalize("Acme Maternity", _NICHE)
    assert line
    assert "does come up" in line
    assert "Acme Maternity" in line


async def test_not_mentioned_but_no_competitors_falls_back(monkeypatch):
    # Model says the brand is absent but names nothing usable — no false claim.
    _patch_check(monkeypatch, brands=[], mentions=False)
    line = await visibility.personalize("Acme Maternity", _NICHE)
    assert line
    assert "invisible" in line
    assert "Acme Maternity" not in line      # generic line makes no specific claim


async def test_llm_error_degrades_to_generic(monkeypatch):
    _patch_raise(monkeypatch)
    line = await visibility.personalize("Acme Maternity", _NICHE)
    assert line                              # never empty even on failure
    assert "invisible" in line


async def test_empty_company_is_generic(monkeypatch):
    # Guard: an empty company never calls the model and never returns empty.
    called = {"n": 0}
    monkeypatch.setattr(visibility, "_check",
                        lambda c, d, h: called.__setitem__("n", called["n"] + 1)
                        or _ranking([], False))
    line = await visibility.personalize("", _NICHE)
    assert line
    assert called["n"] == 0


async def test_blank_niche_defaults(monkeypatch):
    _patch_check(monkeypatch, brands=["Hatch", "Ingrid"], mentions=False)
    line = await visibility.personalize("Acme", "")
    assert line                              # "brands" default keeps the sentence valid


# ── structured slots: every slot present and non-empty ─────────────────────

async def test_personalize_slots_all_present_and_nonempty(monkeypatch):
    _patch_check(monkeypatch, brands=["Hatch", "Ingrid"], mentions=False, niche="lingerie")
    slots = await visibility.personalize_slots("Acme", "DTC apparel brands")
    assert set(visibility.SLOTS) <= set(slots)          # every advertised slot returned
    assert all(str(v).strip() for v in slots.values())  # none empty (render would crash)
    assert slots["niche"] == "lingerie"
    assert "Hatch" in slots["competitors"]


async def test_personalize_slots_competitors_fallback_nonempty(monkeypatch):
    # No competitors found -> the {{competitors}} slot must still be non-empty.
    _patch_check(monkeypatch, brands=[], mentions=False, niche="lingerie")
    slots = await visibility.personalize_slots("Acme", "apparel")
    assert slots["competitors"].strip()
    assert slots["competitors"] == visibility._COMPETITORS_FALLBACK


async def test_personalize_slots_error_all_slots_safe(monkeypatch):
    _patch_raise(monkeypatch)
    slots = await visibility.personalize_slots("Acme", "apparel")
    assert all(str(v).strip() for v in slots.values())
    assert slots["niche"] == "apparel"                  # falls back to the hint


# ── competitor cleaning ────────────────────────────────────────────────────

async def test_clean_competitors_drops_target_dupes_blanks():
    raw = ["Acme", "  ", "Hatch", "hatch", "Acme Maternity", "Ingrid"]
    out = visibility._clean_competitors(raw, "Acme")
    assert "Hatch" in out
    assert "Ingrid" in out
    assert out.count("Hatch") == 1           # case-dupe removed
    # "Acme" and "Acme Maternity" both collide with the target and are dropped
    assert not any("acme" in c.lower() for c in out)
    assert "" not in out and "  " not in out


# ── run.py wiring: personal_line survives into compose ──────────────────────

async def test_personalize_visibility_sets_line_and_survives_model_dump(monkeypatch):
    _patch_check(monkeypatch, brands=["Hatch", "Ingrid"], mentions=False)
    contacts = [
        models.Contact(email="a@acme.co", first_name="Alex", company="Acme", domain="acme.co"),
        models.Contact(email="b@bravo.co", first_name="Bea", company="", domain="bravo.co"),
    ]
    out = await camp._personalize_visibility(contacts, _NICHE, concurrency=4)
    assert len(out) == 2
    for c in out:
        dumped = c.model_dump()
        assert dumped["personal_line"]        # present and non-empty via extra="allow"
    # second contact had no company — derived from the domain, still personalized
    assert out[1].model_dump()["personal_line"]


async def test_geo_template_renders_without_empty_slot(monkeypatch):
    _patch_check(monkeypatch, brands=["Hatch", "Ingrid"], mentions=False)
    contacts = [models.Contact(email="a@acme.co", first_name="Alex",
                               company="Acme", domain="acme.co")]
    out = await camp._personalize_visibility(contacts, _NICHE, concurrency=1)

    tpl = Path(camp.__file__).parent / "templates" / "ai_visibility.md"
    subject_t, body_t = compose_lib.parse_template(tpl.read_text(encoding="utf-8"))
    values = {
        **out[0].model_dump(),
        "from_name": "Sam",
        "school": "Stanford",
        "other_schools": "Dartmouth and Berkeley",
    }
    # render raises TemplateError on any empty slot — this asserts every slot filled.
    body = compose_lib.render(body_t, values)
    subject = compose_lib.render(subject_t, values)
    assert "Hatch" in body
    assert "Acme" in subject


# ── wizard wiring: a GEO segment routes to the GEO template + flag ──────────

async def test_divide_routes_geo_segment_to_visibility_template():
    from skills.campaign.server import agent

    segments = [{"label": "DTC apparel", "icp": "DTC apparel brands",
                 "weight": 1, "geo": True}]
    runs, _deferred = agent._divide(20, segments, sender_keys=["ethan"])
    assert runs
    geo_run = runs[0]
    assert geo_run["geo"] is True
    assert geo_run["template"] == agent.AI_VISIBILITY_TEMPLATE


async def test_divide_non_geo_segment_uses_default_template():
    from skills.campaign.server import agent

    segments = [{"label": "3PLs", "icp": "third-party logistics providers",
                 "weight": 1}]  # no geo key -> defaults false
    runs, _deferred = agent._divide(20, segments, sender_keys=["ethan"])
    assert runs
    assert runs[0]["geo"] is False
    assert runs[0]["template"] == agent.DEFAULT_TEMPLATE


# ── geo test command (Slack): parse, source, render finished email ──────────

async def test_geo_test_detection_and_argument():
    from skills.campaign.server import geo_test
    assert geo_test.is_geo_test("geo test women's lingerie")
    assert geo_test.is_geo_test("Test AI Visibility for acme.co")
    assert not geo_test.is_geo_test("40 emails to DTC brands")
    assert geo_test._argument("geo test orange-lingerie.com") == "orange-lingerie.com"
    assert geo_test._company_of("elkmonttradingcompany.com") == "Elkmonttradingcompany"
    assert geo_test._company_of("orange-lingerie.com") == "Orange Lingerie"


async def test_geo_test_domain_arg_renders_finished_email(monkeypatch):
    from skills.campaign.server import geo_test

    # A domain argument skips StoreLeads and tests that exact brand.
    async def fake_slots(company, hint, *, domain="", sem=None):
        return {"personal_line": f"I asked ChatGPT to recommend the best lingerie "
                                 f"and {company} never came up.",
                "niche": "lingerie", "competitors": "ThirdLove and Aerie"}
    monkeypatch.setattr(visibility, "personalize_slots", fake_slots)

    posted: list[str] = []

    async def reply(text=None, blocks=None):
        posted.append(text or "")

    await geo_test.run("geo test orange-lingerie.com", reply)

    joined = "\n".join(posted)
    assert "Orange Lingerie" in joined            # company derived from domain
    assert "never came up" in joined              # the real personalization line
    assert "Subject:" in joined                   # a finished email was rendered
    assert "Nothing was sent" in joined           # read-only reassurance


async def test_geo_test_empty_arg_prompts(monkeypatch):
    from skills.campaign.server import geo_test
    posted: list[str] = []

    async def reply(text=None, blocks=None):
        posted.append(text or "")

    await geo_test.run("geo test", reply)
    assert any("Tell me what to test" in p for p in posted)


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-v"]))
