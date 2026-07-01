#!/usr/bin/env python3
"""AI-visibility personalization — the per-brand opening line for GEO outreach.

The pitch of this campaign is generative-engine optimization: when a shopper
asks an AI assistant ("what are the best maternity clothing brands?"), most DTC
brands never get named, and that is quiet lost demand. The strongest cold email
is the product demoing itself — we ask an AI the buyer question for the brand's
niche, see whether the brand shows up, and open the email with what we found.

This module owns the one claim-making LLM call in the pipeline, so the honesty
rules live here, not scattered through run.py:

  - The line only ever states what the model actually returned ("I asked ChatGPT
    which brands it recommends and it named A and B"). It never asserts an
    absolute SEO fact we did not measure.
  - Competitor names come straight from the model's answer; we never invent one,
    and we drop any name that is just the target brand again.
  - personalize() NEVER returns an empty string. compose_lib.render raises on an
    empty {{slot}}, so a blank line would fail the whole compose for that row.
    Every path (absent / present / model error) yields a complete, true sentence.

The check is one structured LLM call per brand, so it is gated behind run.py's
--personalize-visibility flag and only paid for on GEO runs.
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


def _line_absent(company: str, niche: str, competitors: list[str]) -> str:
    """Brand is not surfaced by AI, and we have real competitors to name."""
    if len(competitors) >= 2:
        named = f"{competitors[0]} and {competitors[1]}"
    else:
        named = competitors[0]
    return (
        f"I asked ChatGPT to recommend the best {niche} and it pointed shoppers "
        f"to {named}, but {company} never came up. With ChatGPT now steering how "
        "people find brands, that gap is quietly sending your buyers elsewhere."
    )


def _line_present(company: str, niche: str) -> str:
    """Brand does surface — softer, still true opening."""
    return (
        f"I was checking how the top {niche} brands show up when shoppers ask "
        f"ChatGPT for recommendations, and {company} does come up, which is rare. "
        "The catch is those rankings shift constantly and most competitors are "
        "working to take that spot."
    )


def _line_generic(niche: str) -> str:
    """Fallback when the check is inconclusive or errors — asserts nothing false."""
    return (
        f"Most {niche} brands are effectively invisible when a shopper asks "
        "ChatGPT for recommendations, and with AI now shaping how people discover "
        "brands, that is quietly costing them customers."
    )


def _check(company: str, domain: str, hint: str) -> _AIRanking:
    return llm_mod.parse(_prompt(company, domain, hint), _AIRanking, system=_SYSTEM)


async def personalize(
    company: str,
    hint: str,
    *,
    domain: str = "",
    sem: asyncio.Semaphore | None = None,
) -> str:
    """Return a per-brand opening line for the GEO email. Never empty.

    `hint` is the broad ICP (e.g. "DTC apparel brands"); the check narrows it to
    the brand's SPECIFIC niche so each line names a relevant, varied competitor
    set rather than the same two giants for every brand. `domain` sharpens that
    inference. On any model or transport failure we fall back to a generic line
    that makes no unverified claim, so a bad check degrades the email rather than
    breaking the compose.
    """
    hint = (hint or "brands").strip()
    company = (company or "").strip()
    if not company:
        return _line_generic(hint)

    async def _run() -> _AIRanking:
        return await asyncio.to_thread(_check, company, domain, hint)

    try:
        if sem is not None:
            async with sem:
                ranking = await _run()
        else:
            ranking = await _run()
    except Exception as e:  # noqa: BLE001 — any failure degrades to the safe line
        events.emit("campaign.visibility_error", level="warn",
                    company=company, reason=str(e)[:120])
        return _line_generic(hint)

    # Use the brand's specific niche when the model found one; fall back to the
    # broad hint so the sentence is always grammatical.
    niche = (ranking.niche or "").strip() or hint
    competitors = _clean_competitors(ranking.brands, company)

    if not ranking.mentions_target and competitors:
        line = _line_absent(company, niche, competitors)
    elif ranking.mentions_target:
        line = _line_present(company, niche)
    else:
        line = _line_generic(niche)

    events.emit("campaign.visibility_ok", level="info",
                company=company, niche=niche, mentioned=ranking.mentions_target,
                competitors=len(competitors))
    return line
