"""Notion sync for campaign metrics.

Writes one row per campaign run to the Campaign Metrics database in Notion.
reply_scan.py calls update_reply_count() whenever new replies come in.

Auth: NOTION_TOKEN env var — the shared integration token all team members
add to their credentials/.env. The integration must be invited to the
Campaign Metrics database (database settings → Connections → add integration).

Database: https://app.notion.com/p/00b1d4354b7f475faeca57a13d426204
"""

from __future__ import annotations

import os

import httpx

from toolbox.core import events

_NOTION_DB_ID = "00b1d4354b7f475faeca57a13d426204"
_NOTION_API = "https://api.notion.com/v1"
_NOTION_VERSION = "2022-06-28"


def _token() -> str | None:
    return os.environ.get("NOTION_TOKEN", "").strip() or None


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {_token()}",
        "Notion-Version": _NOTION_VERSION,
        "Content-Type": "application/json",
    }


def create_campaign_row(
    run_id: str,
    sender: str,
    date: str,
    provider: str,
    template_name: str,
    icp: str,
    experiment: bool,
    sent_count: int,
) -> str | None:
    """Create a row in the Campaign Metrics database. Returns the Notion page ID.

    Returns None if NOTION_TOKEN is not set or the request fails — the
    campaign itself is unaffected either way.
    """
    if not _token():
        return None

    title = f"{sender} — {provider} — {date}"
    r = httpx.post(
        f"{_NOTION_API}/pages",
        headers=_headers(),
        json={
            "parent": {"database_id": _NOTION_DB_ID},
            "properties": {
                "Campaign": {
                    "title": [{"type": "text", "text": {"content": title}}]
                },
                "Sender": {"select": {"name": sender}},
                "Date": {"date": {"start": date}},
                "Provider": {"select": {"name": provider}},
                "Template": {
                    "rich_text": [{"type": "text", "text": {"content": template_name}}]
                },
                "ICP": {
                    "rich_text": [{"type": "text", "text": {"content": icp[:500]}}]
                },
                "Experiment": {"checkbox": experiment},
                "Sent": {"number": sent_count},
                "Replied": {"number": 0},
                "Run ID": {
                    "rich_text": [{"type": "text", "text": {"content": run_id}}]
                },
                # Run ID is intentionally last — drag it to the end in the Notion view.
            },
        },
        timeout=30,
    )
    if r.status_code == 200:
        page_id = r.json()["id"]
        events.emit("notion.campaign_created", run_id=run_id, page_id=page_id)
        return page_id
    events.emit("notion.create_failed", level="warn",
                status=r.status_code, body=r.text[:300])
    return None


def update_reply_count(page_id: str, replied: int) -> bool:
    """Update the Replied count on an existing Notion row."""
    if not _token() or not page_id:
        return False
    r = httpx.patch(
        f"{_NOTION_API}/pages/{page_id}",
        headers=_headers(),
        json={"properties": {"Replied": {"number": replied}}},
        timeout=30,
    )
    if r.status_code == 200:
        events.emit("notion.reply_count_updated", page_id=page_id, replied=replied)
        return True
    events.emit("notion.update_failed", level="warn",
                status=r.status_code, body=r.text[:300])
    return False


def find_page_id_by_run_id(run_id: str) -> str | None:
    """Query the database to find a page ID by run_id (for recovery/repair)."""
    if not _token():
        return None
    r = httpx.post(
        f"{_NOTION_API}/databases/{_NOTION_DB_ID}/query",
        headers=_headers(),
        json={
            "filter": {
                "property": "Run ID",
                "rich_text": {"equals": run_id},
            }
        },
        timeout=30,
    )
    if r.status_code != 200:
        return None
    results = r.json().get("results") or []
    return results[0]["id"] if results else None
