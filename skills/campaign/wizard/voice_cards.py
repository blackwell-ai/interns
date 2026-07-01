"""Per-founder voice cards: a short guide to how a founder writes (tone, sentence
length, sign-off, how they hedge), distilled from their sent mail and injected
into the reply-draft prompt so a novel question still sounds like them.

One row per founder in the `voice_cards` table, refreshable by re-running the
harvest. Service-role key only. Never log raw email bodies.
"""
import logging

import httpx

from toolbox.core import llm as llm_mod

from . import config

log = logging.getLogger(__name__)

_TABLE = "voice_cards"
_MODEL = "claude-sonnet-4-6"

_DISTILL_SYSTEM = """You study how one person writes short business emails and
produce a compact VOICE GUIDE another writer can follow to sound like them.

You are given a sample of emails this person actually sent. Describe, in at most
8 short bullet points: their tone (warm/formal/blunt/etc.), typical greeting and
sign-off, sentence and paragraph length, how they hedge or soften, any recurring
phrasings or quirks, and what they avoid. Be concrete and specific to THIS person,
not generic email advice. Do not quote whole emails and do not invent facts about
them. No em or en dashes. Output only the bullet points."""


def _base() -> str:
    return config.SUPABASE_URL.rstrip("/") + f"/rest/v1/{_TABLE}"


def _headers(extra: dict | None = None) -> dict:
    key = config.SUPABASE_SECRET_KEY
    return {"apikey": key, "Authorization": f"Bearer {key}", **(extra or {})}


def distill_card(sent_samples: list[str]) -> str:
    """Produce a voice guide from a sample of a founder's sent email bodies.
    Returns '' if there is nothing to learn from or the model call fails."""
    samples = [s.strip() for s in sent_samples if s and s.strip()]
    if not samples:
        return ""
    joined = "\n\n---\n\n".join(s[:1200] for s in samples[:25])
    try:
        card = llm_mod.complete(
            "Here are emails this person sent. Write their voice guide.\n\n" + joined,
            system=_DISTILL_SYSTEM, model=_MODEL)
        return (card or "").strip().replace("—", ", ").replace("–", ", ")
    except Exception as e:  # noqa: BLE001
        log.warning("voice card distillation failed: %s", str(e)[:150])
        return ""


async def get_card(founder: str) -> str:
    """The founder's stored voice guide, or '' if none is set yet."""
    try:
        async with httpx.AsyncClient(timeout=20) as s:
            r = await s.get(_base(), params={"select": "card", "founder": f"eq.{founder}",
                                             "limit": "1"}, headers=_headers())
            r.raise_for_status()
            rows = r.json()
            return (rows[0].get("card") or "") if rows else ""
    except Exception as e:  # noqa: BLE001 - a missing card must not block drafting
        log.warning("voice card fetch failed for %s: %s", founder, str(e)[:150])
        return ""


async def upsert_card(founder: str, card: str) -> None:
    """Store (or replace) a founder's voice guide."""
    if not card.strip():
        return
    async with httpx.AsyncClient(timeout=20) as s:
        r = await s.post(
            _base(), params={"on_conflict": "founder"},
            json={"founder": founder, "card": card},
            headers=_headers({"Content-Type": "application/json",
                              "Prefer": "resolution=merge-duplicates,return=minimal"}))
        r.raise_for_status()
