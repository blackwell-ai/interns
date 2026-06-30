"""The triage dismiss list: people a human has marked 'not relevant', so the
reply triage stops surfacing them in any bucket, now and on every future run.

This is deliberately NOT the contacted-ledger suppression (which means 'never
email them again'). Dismissing here only hides a person from triage; campaigns
are untouched. The store is a small Supabase table, read with the service-role
key the triage already uses, so a dismissal is team-wide and survives restarts.

Two halves:
- parse_command(text): pure intent parsing for the Slack thread ("drop a@b.com,
  c@d.com — not our ICP", "undo a@b.com", "show dismissed"). No I/O, so testable.
- the async store calls (load/dismiss/undismiss/list) over PostgREST.
"""
from __future__ import annotations

import re

import httpx

from . import config

_TABLE = "triage_dismissed"

# ---- pure command parsing ----------------------------------------------------

_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_DISMISS_RE = re.compile(
    r"\b(drop|remove|dismiss|ignore|exclude|skip|irrelevant|"
    r"not\s+relevant|not\s+(a\s+)?fit)\b", re.I)
_UNDO_RE = re.compile(r"\b(undo|restore|re-?add|add\s+back|un-?dismiss|un-?remove)\b", re.I)
_SHOW_RE = re.compile(
    r"\b(show|list|which|what|who)\b.*\b(dismiss(ed)?|removed|excluded|ignored)\b", re.I)


def canonical(email: str) -> str:
    return (email or "").strip().lower()


def _emails(text: str) -> list[str]:
    out, seen = [], set()
    for m in _EMAIL_RE.findall(text or ""):
        e = canonical(m)
        if e and e not in seen:
            seen.add(e)
            out.append(e)
    return out


def _reason(text: str, emails: list[str]) -> str:
    """Best-effort free-text reason: whatever the user wrote besides the emails
    and the command verb. Empty when there is nothing meaningful left."""
    rest = text or ""
    for e in emails:
        rest = re.sub(re.escape(e), " ", rest, flags=re.I)
    tail = re.search(r"[—\-:]\s*(.+)$", rest)  # prefer the clause after a dash/colon
    cand = tail.group(1) if tail else rest
    cand = _DISMISS_RE.sub(" ", cand)
    cand = re.sub(r"\b(from|the|list|triage|them|it|please|pls|and)\b", " ", cand, flags=re.I)
    return re.sub(r"\s+", " ", cand).strip(" ,.-—:")[:200]


def parse_command(text: str) -> dict:
    """Classify a triage-thread message into an edit intent. Returns
    {action: 'dismiss'|'undo'|'show'|None, emails: [...], reason: str}.
    A dismiss/undo requires at least one real email so a normal question or send
    request that happens to mention an address is never hijacked."""
    emails = _emails(text)
    if _UNDO_RE.search(text or "") and emails:
        action = "undo"
    elif _SHOW_RE.search(text or ""):
        action = "show"
    elif _DISMISS_RE.search(text or "") and emails:
        action = "dismiss"
    else:
        action = None
    return {"action": action, "emails": emails, "reason": _reason(text, emails)}


# ---- store (PostgREST over the service-role key) -----------------------------

def _headers(extra: dict | None = None) -> dict:
    key = config.SUPABASE_SECRET_KEY
    return {"apikey": key, "Authorization": f"Bearer {key}", **(extra or {})}


def _raise(r: httpx.Response) -> None:
    if r.status_code not in (200, 201, 204, 206):
        raise RuntimeError(f"{r.status_code} {r.text[:300]}")


async def load_dismissed() -> set[str]:
    """All currently-dismissed emails. Best-effort: any failure (including the
    table not existing yet) returns an empty set so triage never breaks."""
    base = config.SUPABASE_URL
    try:
        async with httpx.AsyncClient(timeout=30) as s:
            r = await s.get(f"{base}/rest/v1/{_TABLE}",
                            params={"select": "recipient", "active": "is.true",
                                    "limit": "5000"},
                            headers=_headers())
        if r.status_code != 200:
            return set()
        return {canonical(row["recipient"]) for row in r.json() if row.get("recipient")}
    except Exception:
        return set()


async def dismiss(emails: list[str], reason: str = "", by: str = "") -> list[str]:
    """Upsert each email as active=true. Returns the canonical emails recorded."""
    rows = [{"recipient": e, "reason": reason, "dismissed_by": by, "active": True}
            for e in (canonical(x) for x in emails) if e]
    if not rows:
        return []
    base = config.SUPABASE_URL
    async with httpx.AsyncClient(timeout=30) as s:
        r = await s.post(
            f"{base}/rest/v1/{_TABLE}", params={"on_conflict": "recipient"},
            json=rows,
            headers=_headers({"Content-Type": "application/json",
                              "Prefer": "resolution=merge-duplicates,return=minimal"}))
    _raise(r)
    return [row["recipient"] for row in rows]


async def undismiss(emails: list[str]) -> list[str]:
    """Flip active=false for the given emails. Returns the ones that existed."""
    targets = [e for e in (canonical(x) for x in emails) if e]
    if not targets:
        return []
    base = config.SUPABASE_URL
    in_list = ",".join(targets)
    async with httpx.AsyncClient(timeout=30) as s:
        r = await s.patch(
            f"{base}/rest/v1/{_TABLE}",
            params={"recipient": f"in.({in_list})", "active": "is.true"},
            json={"active": False},
            headers=_headers({"Content-Type": "application/json",
                              "Prefer": "return=representation"}))
    _raise(r)
    return [row["recipient"] for row in (r.json() if r.content.strip() else [])]


async def list_dismissed() -> list[dict]:
    """Currently-dismissed people, newest first, for 'show dismissed'."""
    base = config.SUPABASE_URL
    async with httpx.AsyncClient(timeout=30) as s:
        r = await s.get(f"{base}/rest/v1/{_TABLE}",
                        params={"select": "recipient,reason,dismissed_by,created_at",
                                "active": "is.true", "order": "created_at.desc",
                                "limit": "200"},
                        headers=_headers())
    _raise(r)
    return r.json()
