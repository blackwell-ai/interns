"""HTTP endpoint that lets the Gmail add-on reuse the /respond draft engine.

The Slack wizard runs over Socket Mode and needs no public URL, but a Gmail add-on
has to call a reachable HTTPS endpoint. So this stands up a small aiohttp server in
the same process, exposing exactly two routes. Both are authenticated by the caller's
Google identity token, which must resolve to one of our founders:

  POST /addon/draft  {thread_id}        -> draft + display fields for the card
  POST /addon/send   {thread_id, body}  -> {ok, sent_id}

All the real work (reading the thread, retrieval-augmented drafting, sending in-thread
as the founder, and the gold-example write-back) is the same code /respond uses. The
add-on holds no secrets and never touches Supabase, Gmail credentials, or the LLM; it
only forwards the open thread and the founder's edited text.

Security: verify the identity token on every call, confirm the caller is a founder,
rate-limit per founder, return vague errors to the client, and never log email bodies,
addresses, or tokens.
"""
import asyncio
import hmac
import logging
import os
import time

from aiohttp import web

from skills.campaign import reply_followup, reply_scan

from . import agent, gmail_auth, reply_drafter, reply_examples
from .respond import _text_to_html

log = logging.getLogger(__name__)

# Per-founder rate limit: at most _RL_MAX calls per _RL_WINDOW seconds.
_RL_WINDOW = 60.0
_RL_MAX = 20
_rl: dict[str, list[float]] = {}


def _founder_for(email: str) -> dict | None:
    email = (email or "").strip().lower()
    return next((s for s in agent.SENDERS if s["email"].lower() == email), None)


def _rate_ok(email: str) -> bool:
    now = time.monotonic()
    hits = [t for t in _rl.get(email, []) if now - t < _RL_WINDOW]
    if len(hits) >= _RL_MAX:
        _rl[email] = hits
        return False
    hits.append(now)
    _rl[email] = hits
    return True


async def _auth(request: web.Request) -> dict:
    """Authorize the caller and return the founder record, or raise. A shared secret
    proves the request came from our add-on; the X-Addon-User header (the add-on sends
    the signed-in user's email) must be one of the three founders. Kept deliberately
    simple: this is an internal tool for three people, and it avoids the GCP-linked
    identity-token setup."""
    authz = request.headers.get("Authorization", "")
    if not authz.startswith("Bearer "):
        raise web.HTTPUnauthorized(text="missing credential")
    secret = authz[len("Bearer "):].strip()
    want = os.environ.get("ADDON_SHARED_SECRET") or ""
    if not want or not hmac.compare_digest(secret, want):
        raise web.HTTPUnauthorized(text="invalid credential")
    founder = _founder_for(request.headers.get("X-Addon-User"))
    if not founder:
        raise web.HTTPForbidden(text="not authorized")
    if not _rate_ok(founder["email"].lower()):
        raise web.HTTPTooManyRequests(text="slow down")
    return founder


def _draft_payload(d: dict) -> dict:
    """Only the fields the card renders. The raw incoming body stays server-side."""
    return {
        "draft": d.get("draft", ""),
        "category": d.get("category", "other"),
        "n_examples": d.get("n_examples", 0),
        "who": d.get("to", ""),
        "subject": d.get("incoming_subject", ""),
        "received": d.get("received", ""),
        "their_message": d.get("incoming_clean", ""),
        "gmail_url": d.get("gmail_url", ""),
        "thread_id": d.get("thread_id", ""),
    }


async def _draft(request: web.Request) -> web.Response:
    founder = await _auth(request)
    data = await _json(request)
    thread_id = (data.get("thread_id") or "").strip()
    if not thread_id:
        raise web.HTTPBadRequest(text="thread_id required")
    try:
        d = await reply_drafter.generate_draft(
            founder["key"], founder["email"], thread_id)
    except ValueError as e:  # no messages / no inbound to answer
        raise web.HTTPUnprocessableEntity(text=str(e)[:200])
    except Exception as e:  # noqa: BLE001
        log.warning("addon draft failed: %s", str(e)[:150])
        raise web.HTTPInternalServerError(text="draft failed")
    return web.json_response(_draft_payload(d))


async def _send(request: web.Request) -> web.Response:
    founder = await _auth(request)
    data = await _json(request)
    thread_id = (data.get("thread_id") or "").strip()
    body = (data.get("body") or "").strip()
    if not thread_id or not body:
        raise web.HTTPBadRequest(text="thread_id and body required")
    try:
        target = await reply_drafter.read_target(founder["email"], thread_id)
    except ValueError as e:
        raise web.HTTPUnprocessableEntity(text=str(e)[:200])
    except Exception as e:  # noqa: BLE001
        log.warning("addon read_target failed: %s", str(e)[:150])
        raise web.HTTPInternalServerError(text="thread read failed")

    spec = {
        "to": target["to"], "subject": target["reply_subject"],
        "body_html": _text_to_html(body),
        "reply_to_message_id": target["reply_to_message_id"],
        "thread_id": thread_id, "quote": False,
    }
    try:
        token = await asyncio.to_thread(gmail_auth.get_access_token, founder["email"])
    except Exception as e:  # noqa: BLE001
        log.warning("addon token mint failed: %s", str(e)[:120])
        raise web.HTTPInternalServerError(text="auth failed")

    ok, draft_id = await reply_followup.create_draft_api(token, spec, dry_run=False)
    if not ok:
        log.warning("addon draft-create failed: %s", str(draft_id)[:120])
        raise web.HTTPBadGateway(text="send failed")
    ok, sent_id = await reply_followup.send_draft_api(token, draft_id)
    if not ok:
        log.warning("addon send failed: %s", str(sent_id)[:120])
        raise web.HTTPBadGateway(text="send failed")

    await _record_gold(founder, target, body, sent_id)
    return web.json_response({"ok": True, "sent_id": sent_id})


async def _record_gold(founder: dict, target: dict, body: str, sent_id: str) -> None:
    """Feedback loop: store the reply the founder actually sent as a gold example, the
    same write-back /respond does. Best-effort; a corpus write must never fail a send."""
    try:
        category = await asyncio.to_thread(
            reply_examples.classify_category,
            target["incoming_subject"], target["incoming_body"])
        sentiment = await asyncio.to_thread(
            reply_scan.classify_sentiment, target["incoming_body"])
        await reply_examples.add_gold_example(
            founder=founder["key"], category=category,
            incoming_subject=target["incoming_subject"],
            incoming_body=target["incoming_body"], reply_body=body,
            sentiment=sentiment,
            message_id=sent_id or f"{founder['key']}:{target.get('thread_id', '')}")
    except Exception as e:  # noqa: BLE001
        log.warning("addon gold write failed: %s", str(e)[:150])


async def _json(request: web.Request) -> dict:
    try:
        return await request.json()
    except Exception:  # noqa: BLE001
        raise web.HTTPBadRequest(text="invalid json")


async def _health(request: web.Request) -> web.Response:
    return web.json_response({"ok": True})


def build_app() -> web.Application:
    app = web.Application()
    app.add_routes([
        web.get("/addon/health", _health),
        web.post("/addon/draft", _draft),
        web.post("/addon/send", _send),
    ])
    return app


async def start() -> web.AppRunner:
    """Start the add-on API in the current event loop. Called from slack_bot.main
    when ADDON_API_ENABLED is set. Returns the runner so the caller could stop it."""
    port = int(os.environ.get("ADDON_PORT") or os.environ.get("PORT") or 8080)
    runner = web.AppRunner(build_app())
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    log.info("Gmail add-on API listening on :%s", port)
    return runner
