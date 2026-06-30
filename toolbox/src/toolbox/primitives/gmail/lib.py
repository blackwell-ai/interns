"""Gmail mechanics (port of email_automation_pipeline's gmail.py).

Kept from the old code: multipart MIME construction, base64-url encoding,
quota-error classification, bounce parsing (Final-Recipient extraction).
Swapped out: googleapiclient + local token files → raw Gmail REST with a
short-lived token from core/auth.get_token("gmail").
"""

from __future__ import annotations

import base64
import os
import re
from datetime import UTC, datetime
from email.message import EmailMessage
from email.utils import formataddr

import httpx


def api_base() -> str:
    """Gmail REST base. TOOLBOX_GMAIL_API_BASE override exists for the
    integration tests' fake server — never for production use."""
    root = os.environ.get("TOOLBOX_GMAIL_API_BASE", "https://gmail.googleapis.com")
    return f"{root}/gmail/v1/users/me"

# Hard, non-transient quota signals (old gmail.py review issue): retrying these
# with backoff would spin forever on a *daily* limit — fail the step cleanly
# instead (plan §7 item 6).
_QUOTA_PATTERNS = ("Daily user sending limit exceeded", "quotaExceeded", "dailyLimitExceeded")

# Per-user / per-minute rate limits. Gmail returns these as HTTP 403 (not 429),
# so without this they would be misread as permanent 4xx failures. They are
# transient: back off and retry rather than dropping the recipient.
_RATE_LIMIT_PATTERNS = (
    "rateLimitExceeded", "userRateLimitExceeded", "User-rate limit exceeded",
    "Too many concurrent requests", "Queries per minute",
)

FINAL_RECIPIENT_RE = re.compile(r"^Final-Recipient:\s*[^;]*;\s*(\S+)\s*$", re.IGNORECASE | re.MULTILINE)


class QuotaExceeded(Exception):
    """Provider hard wall (daily cap). Not transient — do not retry."""


class PermanentSendError(Exception):
    """This recipient can't be sent to (invalid address etc.). Skip them."""


def build_raw_message(
    *,
    to: str,
    subject: str,
    body: str,
    from_address: str,
    from_name: str = "",
    reply_to: str = "",
    body_html: str = "",
    cc: str = "",
) -> str:
    msg = EmailMessage()
    msg["To"] = to
    if cc:
        msg["Cc"] = cc
    msg["From"] = formataddr((from_name, from_address)) if from_name else from_address
    msg["Subject"] = subject
    if reply_to:
        msg["Reply-To"] = reply_to
    msg.set_content(body)
    if body_html:
        msg.add_alternative(body_html, subtype="html")
    return base64.urlsafe_b64encode(msg.as_bytes()).decode("ascii")


def classify_send_error(status: int, body_text: str) -> type[Exception] | None:
    """None → transient (retry with backoff). Otherwise the exception to raise."""
    if any(p in body_text for p in _QUOTA_PATTERNS):
        return QuotaExceeded  # daily hard wall: do not retry
    if any(p in body_text for p in _RATE_LIMIT_PATTERNS):
        return None           # per-user rate limit (often 403): back off and retry
    if status == 429 or status >= 500:
        return None
    if 400 <= status < 500:
        return PermanentSendError
    return None


async def send_raw(client: httpx.AsyncClient, raw: str) -> dict:
    r = await client.post(f"{api_base()}/messages/send", json={"raw": raw})
    if r.status_code != 200:
        exc = classify_send_error(r.status_code, r.text)
        if exc is None:
            r.raise_for_status()  # transient → httpx.HTTPStatusError → tenacity retries
        raise exc(f"{r.status_code}: {r.text[:300]}")
    return r.json()


async def list_messages(client: httpx.AsyncClient, query: str, max_results: int = 100) -> list[str]:
    r = await client.get(f"{api_base()}/messages", params={"q": query, "maxResults": max_results})
    if r.status_code == 404:
        return []
    r.raise_for_status()
    return [m["id"] for m in (r.json().get("messages") or [])]


async def get_message(client: httpx.AsyncClient, message_id: str, fmt: str = "full") -> dict:
    r = await client.get(f"{api_base()}/messages/{message_id}", params={"format": fmt})
    r.raise_for_status()
    return r.json()


def extract_text_parts(payload: dict) -> str:
    """Recursively collect base64url-decoded text bodies (ported verbatim idea)."""
    out: list[str] = []

    def walk(part: dict) -> None:
        mime = part.get("mimeType", "")
        data = (part.get("body") or {}).get("data")
        if data and (mime.startswith("text/") or mime == "message/delivery-status"):
            try:
                padded = data + "=" * (-len(data) % 4)
                out.append(base64.urlsafe_b64decode(padded).decode("utf-8", "replace"))
            except Exception:
                pass
        for child in part.get("parts") or []:
            walk(child)

    walk(payload)
    return "\n".join(out)


def header(msg: dict, name: str) -> str:
    for h in (msg.get("payload", {}) or {}).get("headers", []) or []:
        if h.get("name", "").lower() == name.lower():
            return h.get("value", "")
    return ""


def parse_bounce(msg: dict) -> tuple[str, datetime] | None:
    """-> (bounced recipient, bounce date) or None if no Final-Recipient header."""
    text = extract_text_parts(msg.get("payload") or {})
    m = FINAL_RECIPIENT_RE.search(text)
    if not m:
        return None
    recipient = m.group(1).strip().lstrip("<").rstrip(">")
    internal_ms = int(msg.get("internalDate", 0))
    when = datetime.fromtimestamp(internal_ms / 1000, UTC) if internal_ms else datetime.now(UTC)
    return recipient, when


def address_of(from_header: str) -> str:
    """'Jane Doe <jane@x.com>' -> 'jane@x.com'."""
    m = re.search(r"<([^>]+)>", from_header)
    return (m.group(1) if m else from_header).strip().lower()
