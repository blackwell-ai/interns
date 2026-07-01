#!/usr/bin/env python3
"""AI-visibility facts — modular per-brand slots for GEO outreach.

The pitch of this campaign is generative-engine optimization: when a shopper
asks an AI assistant ("what are the best maternity clothing brands?"), most DTC
brands never get named, and that is quiet lost demand.

This module runs one structured LLM call per brand and exposes the RAW FACTS it
returns as individual template slots — the brand's niche, and the real
competitors an AI surfaces for it. It deliberately does NOT write a sentence for
you: the whole point of the tool is that the copy is visible and modular, so the
user writes the email themselves out of these slots (like {{first_name}} or
{{company}}). See visibility.SLOTS for the full list.

Honesty rules (this is the one claim-making call in the pipeline):
  - Competitor names come straight from the model's answer; we never invent one,
    and we drop any name that is just the target brand again.
  - Every slot is guaranteed non-empty. compose_lib.render raises on an empty
    {{slot}}, so a blank value would fail the whole compose for that row; a gap
    (e.g. the check named fewer rivals than we expose) gets a graceful stand-in.
  - `mentioned` reflects whether the AI already surfaces the brand — a template
    that says "but not {{company}}" is only true when the brand does NOT appear,
    so GEO lists should target brands that are absent (check with `geo test`).

The check is gated behind run.py's --personalize-visibility flag and only paid
for on GEO runs.
"""
from __future__ import annotations

import asyncio

from pydantic import BaseModel, Field

from toolbox.core import events
from toolbox.core import llm as llm_mod


class _AIRanking(BaseModel):
    """What an AI assistant names when asked for the best brands in a niche."""

    niche: str = ""                                   # the specific niche the brand competes in
    brands: list[str] = Field(default_factory=list)  # named brands, most prominent first
    mentions_target: bool = False                     # is the target brand among them


_SYSTEM = (
    "You model how a mainstream AI shopping assistant (ChatGPT, Claude, Gemini) "
    "answers buyer questions. You only name brands a good assistant would "
    "actually surface today. You never invent brands to pad a list."
)


def _prompt(company: str, domain: str, hint: str) -> str:
    return (
        f"A brand called \"{company}\" (website {domain}) sells in the "
        f"{hint} space.\n"
        "1. niche: name the SPECIFIC product niche this brand is best known "
        "for, as a shopper would phrase it (e.g. \"lingerie\", \"men's "
        "formalwear\", \"running shoes\") — not the broad category. Infer it "
        "from the brand name and domain.\n"
        "2. brands: a shopper asks an AI assistant to recommend the best brands "
        "in that specific niche. List up to 6 real brands it would most likely "
        "name, most prominent first. No invented names, no duplicates.\n"
        f"3. mentions_target: true only if \"{company}\" genuinely belongs in "
        "that list."
    )


def _clean_competitors(brands: list[str], company: str) -> list[str]:
    """Drop blanks, the target brand itself, and near-duplicates; keep order."""
    target = company.strip().lower()
    seen: set[str] = set()
    out: list[str] = []
    for b in brands:
        name = b.strip()
        key = name.lower()
        if not name or key == target or target in key or key in target:
            continue
        if key in seen:
            continue
        seen.add(key)
        out.append(name)
    return out


# A safe, non-empty stand-in for {{competitors}} when the check named none.
# Every exposed slot must be non-empty or compose_lib.render fails the row.
_COMPETITORS_FALLBACK = "the established names in the space"


def _competitors_phrase(competitors: list[str]) -> str:
    """A natural phrase naming up to two real competitors. Never empty."""
    if len(competitors) >= 2:
        return f"{competitors[0]} and {competitors[1]}"
    if competitors:
        return competitors[0]
    return _COMPETITORS_FALLBACK


# How many individual {{competitor_N}} slots to expose. The check returns up to
# ~6 brands, so a real name usually fills each; the rare gap gets a graceful,
# non-empty stand-in (a slot can never be empty or the row fails compose).
_N_COMPETITOR_SLOTS = 3
_INDIVIDUAL_FALLBACKS = (
    "a top brand in the space",
    "another established name",
    "a well-known competitor",
)


def _competitor_slots(competitors: list[str]) -> dict[str, str]:
    """{{competitor_1..N}}, each non-empty. Real names first; positions past the
    real ones use a graceful descriptor so the slot is never blank."""
    out: dict[str, str] = {}
    for i in range(_N_COMPETITOR_SLOTS):
        if i < len(competitors):
            out[f"competitor_{i + 1}"] = competitors[i]
        else:
            out[f"competitor_{i + 1}"] = _INDIVIDUAL_FALLBACKS[i]
    return out


def _check(company: str, domain: str, hint: str) -> _AIRanking:
    return llm_mod.parse(_prompt(company, domain, hint), _AIRanking, system=_SYSTEM)


# The modular template slots this module fills — the raw facts, no prewritten
# prose. Kept in one place so the wizard can show the user which {{parameters}}
# a GEO email can use. Every one is guaranteed non-empty by personalize_slots.
SLOTS = ("niche", "competitors") + tuple(
    f"competitor_{i + 1}" for i in range(_N_COMPETITOR_SLOTS))


async def personalize_slots(
    company: str,
    hint: str,
    *,
    domain: str = "",
    sem: asyncio.Semaphore | None = None,
) -> dict[str, str]:
    """Return the per-brand GEO template slots. Every value is non-empty.

    Keys (all usable as {{slot}} in a template the user writes):
      - niche: the brand's specific niche, e.g. "women's lingerie".
      - competitors: a phrase naming up to two real rivals the AI surfaced.
      - competitor_1..N: those rivals individually, for listing them separately.

    `hint` is the broad ICP (e.g. "DTC apparel brands"); the check narrows it to
    the brand's SPECIFIC niche so the facts are relevant per brand. On any model
    or transport failure every slot degrades to a safe value that makes no
    unverified claim, so a bad check degrades the email rather than breaking
    compose.
    """
    hint = (hint or "brands").strip()
    company = (company or "").strip()

    def _slots(niche: str, competitors: list[str]) -> dict[str, str]:
        return {"niche": niche, "competitors": _competitors_phrase(competitors),
                **_competitor_slots(competitors)}

    if not company:
        return _slots(hint, [])

    async def _run() -> _AIRanking:
        return await asyncio.to_thread(_check, company, domain, hint)

    try:
        if sem is not None:
            async with sem:
                ranking = await _run()
        else:
            ranking = await _run()
    except Exception as e:  # noqa: BLE001 — any failure degrades to safe slots
        events.emit("campaign.visibility_error", level="warn",
                    company=company, reason=str(e)[:120])
        return _slots(hint, [])

    # Use the brand's specific niche when the model found one; fall back to the
    # broad hint so every {{niche}} stays grammatical.
    niche = (ranking.niche or "").strip() or hint
    competitors = _clean_competitors(ranking.brands, company)

    events.emit("campaign.visibility_ok", level="info",
                company=company, niche=niche, mentioned=ranking.mentions_target,
                competitors=len(competitors))
    return _slots(niche, competitors)
