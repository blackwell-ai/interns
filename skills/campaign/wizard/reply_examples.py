"""The `reply_examples` corpus: store and retrieve (incoming email, reply we
sent) pairs, and classify an incoming email's category.

These pairs are the retrieval-augmented few-shot exemplars the reply drafter
(`reply_drafter.py`) uses so a founder's drafted reply matches how we have
actually answered similar emails. Rows come from two places: the Sent-folder
harvest (`harvest_reply_examples.py`, source='harvest') and the feedback loop
that writes back every reply a founder sends from the /respond queue
(source='queue', gold).

All reads and writes use the service-role key (the bodies are real prospect
correspondence; RLS is on with no policies). Never log the body fields.
"""
import logging

import httpx
from pydantic import BaseModel

from toolbox.core import llm as llm_mod

from . import config

log = logging.getLogger(__name__)

_TABLE = "reply_examples"

# The retrieval taxonomy. Kept small on purpose: it only has to be good enough to
# fetch same-kind exemplars, not to be a precise label.
CATEGORIES = ("pricing", "capabilities", "scheduling", "objection", "referral", "other")

# Model for the cheap category tag. Sentiment reuses reply_scan.classify_sentiment.
_CATEGORY_MODEL = "claude-sonnet-4-6"


def _base() -> str:
    return config.SUPABASE_URL.rstrip("/") + f"/rest/v1/{_TABLE}"


def _headers(extra: dict | None = None) -> dict:
    key = config.SUPABASE_SECRET_KEY
    return {"apikey": key, "Authorization": f"Bearer {key}", **(extra or {})}


# ---- category classification ------------------------------------------------

class _Category(BaseModel):
    category: str


def classify_category(incoming_subject: str, incoming_body: str) -> str:
    """Tag an incoming email with one of CATEGORIES. Best-effort: any failure or
    an unexpected label falls back to 'other', so a draft is never blocked on it."""
    prompt = (
        "Classify what this inbound reply to our cold outreach is mainly about. "
        "Return exactly one of: pricing (cost, budget, discounts), capabilities "
        "(what the product does, features, fit, technical questions), scheduling "
        "(booking or moving a call, availability), objection (not interested, bad "
        "timing, a concern to overcome), referral (pointing us to another person "
        "or team), other (anything else).\n\n"
        f"Subject: {incoming_subject}\n\n{incoming_body[:2000]}"
    )
    try:
        result = llm_mod.parse(prompt, _Category, model=_CATEGORY_MODEL)
        cat = (result.category or "").strip().lower()
        return cat if cat in CATEGORIES else "other"
    except Exception:  # noqa: BLE001 - classification must never break the pipeline
        return "other"


# ---- corpus writes ----------------------------------------------------------

async def upsert_examples(rows: list[dict]) -> int:
    """Insert reply-example rows, skipping any whose `message_id` already exists
    (a re-harvest never double-inserts, and a harvested pair is never clobbered by
    a later run). Returns the number newly inserted. `rows` fields: founder,
    category, incoming_subject, incoming_body, reply_body, sentiment, source,
    is_gold, message_id."""
    rows = [r for r in rows if (r.get("message_id") or "").strip()]
    if not rows:
        return 0
    inserted = 0
    async with httpx.AsyncClient(timeout=30) as s:
        # One row per request so a single duplicate (409) does not drop the batch.
        for r in rows:
            try:
                resp = await s.post(
                    _base(), json=r,
                    headers=_headers({"Content-Type": "application/json",
                                      "Prefer": "resolution=ignore-duplicates,return=minimal"}))
                if resp.status_code in (200, 201):
                    inserted += 1
                elif resp.status_code == 409:
                    pass  # duplicate message_id — already have this example
                else:
                    resp.raise_for_status()
            except Exception as e:  # noqa: BLE001 - never let one bad row abort the harvest
                log.warning("reply_examples upsert failed (%s): %s",
                            r.get("message_id", "?"), str(e)[:150])
    return inserted


async def add_gold_example(founder: str, category: str, incoming_subject: str,
                           incoming_body: str, reply_body: str, sentiment: str,
                           message_id: str) -> bool:
    """Record one reply a founder sent from the queue as a gold example (the
    feedback loop). Returns True if newly inserted."""
    n = await upsert_examples([{
        "founder": founder, "category": category,
        "incoming_subject": incoming_subject, "incoming_body": incoming_body,
        "reply_body": reply_body, "sentiment": sentiment,
        "source": "queue", "is_gold": True, "message_id": message_id,
    }])
    return n > 0


# ---- corpus reads (retrieval) -----------------------------------------------

_SELECT = "incoming_subject,incoming_body,reply_body,category,sentiment,is_gold"


async def _query(params: dict) -> list[dict]:
    async with httpx.AsyncClient(timeout=30) as s:
        r = await s.get(_base(), params=params, headers=_headers())
        r.raise_for_status()
        return r.json()


async def retrieve(founder: str, category: str, limit: int = 5) -> list[dict]:
    """Best exemplars for this founder and category: gold first, then most recent.
    v1 retrieval is a category match; semantic (pgvector) similarity is a noted
    future upgrade."""
    return await _query({
        "select": _SELECT,
        "founder": f"eq.{founder}",
        "category": f"eq.{category}",
        "order": "is_gold.desc,created_at.desc",
        "limit": str(limit),
    })


async def retrieve_any(founder: str, limit: int = 3) -> list[dict]:
    """Founder exemplars regardless of category, for a novel/empty category so the
    draft still lands in-voice. Gold first, then most recent."""
    return await _query({
        "select": _SELECT,
        "founder": f"eq.{founder}",
        "order": "is_gold.desc,created_at.desc",
        "limit": str(limit),
    })
