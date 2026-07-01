"""Draft a founder's reply to a prospect, grounded in how we have actually
answered similar emails (retrieval-augmented few-shot), for the /respond queue.

Given a founder and a Gmail thread, it reads the thread, classifies the incoming
email's category, retrieves the best-matching `reply_examples` for that founder
and category plus the founder's voice card, and prompts Claude to MATCH the voice
and reasoning of those examples (not reuse them). It returns the draft plus the
threading anchors the send path needs, and the incoming fields the feedback loop
writes back after a send.

Runs on the wizard server, so LLM calls go through `toolbox.core.llm` (routes to
the Anthropic SDK when ANTHROPIC_API_KEY is set). Never log email bodies.
"""
import html as html_mod
import logging
import re

import httpx

from toolbox.core import llm as llm_mod
from toolbox.primitives.gmail import lib as gmail_lib

from skills.campaign import reply_scan

from . import agent, gmail_auth, reply_examples, voice_cards

log = logging.getLogger(__name__)

_MODEL = "claude-opus-4-8"  # the reply must sound like the founder; use the best model.
_MIN_CATEGORY_EXAMPLES = 2  # below this, backfill with any-category founder exemplars.

# Our scheduling page. When a reply proposes a time or the prospect wants to book,
# the draft points them here (rendered as a real hyperlink when the email is sent).
SCHEDULING_LINK = "https://cal.com/team/blackwell/30-min?overlayCalendar=true"

_SYSTEM = f"""You draft a reply that a real founder will review and send to a
prospect who answered their cold outreach. You write in the founder's own voice.

You are given: a voice guide for this founder, a few worked examples of how they
have actually replied to similar emails (each an incoming message and the reply
they sent), and the prospect's latest message to answer.

Write ONLY the reply body the founder would send. Hard rules:
- Match the VOICE and the REASONING of the examples. Do not reuse their wording or
  copy sentences; this is a new email to a different person. Fit the actual
  question they asked.
- Sound like the founder: a real person, warm, concise, specific. Not corporate,
  not salesy. Answer what they asked; if a call makes sense, propose it plainly.
- SCHEDULING: whenever it fits to get time on the calendar (they are open to a
  call, asking for a time, or saying yes), point them to our scheduling page and
  paste this exact URL on its own line so they can pick a slot:
  {SCHEDULING_LINK}
  Use it verbatim, do not shorten or alter it. Do not invent any other link.
- Keep it short, a few sentences. One blank line between paragraphs.
- No em dashes or en dashes. Use periods and commas. No AI or sales filler ("I
  hope this finds you well", "reaching out", "leverage", and the like).
- End with the founder's usual sign-off and first name, matching the examples.
- Do not invent facts, commitments, prices, or dates we have not stated. If you
  are unsure of a specific, keep it general so the founder can fill it in.

Output the reply body as plain text, nothing else."""


# Markers that begin quoted reply history; everything from the earliest one is the
# prior thread, not the prospect's new message.
_QUOTE_MARKERS = [
    re.compile(r"\nOn .{0,300}? wrote:", re.S),        # gmail "On <date>, <name> wrote:"
    re.compile(r"\n_{5,}"),                             # outlook divider
    re.compile(r"\n-----Original Message-----"),
    re.compile(r"\nFrom:\s.*\nSent:\s", re.S),         # outlook header block
    re.compile(r"<div[^>]*gmail_quote", re.I),          # gmail quote container
]


def _clean_reply(body: str) -> str:
    """Extract just the prospect's newly written message from a reply body:
    drop the quoted thread history, HTML markup, and a trailing signature, so the
    review card shows their actual words instead of the whole ugly thread."""
    text = body or ""
    # Normalize the common HTML into text, then strip any remaining tags.
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
    text = re.sub(r"</p\s*>", "\n\n", text, flags=re.I)
    text = re.sub(r"<[^>]+>", "", text)
    text = html_mod.unescape(text)
    # Cut at the earliest quote marker (the start of the prior thread).
    cut = len(text)
    for rx in _QUOTE_MARKERS:
        m = rx.search(text)
        if m:
            cut = min(cut, m.start())
    text = text[:cut]
    # Drop any stray quoted lines and a trailing signature block.
    text = "\n".join(ln for ln in text.splitlines() if not ln.lstrip().startswith(">"))
    text = re.split(r"\n--\s*\n", text)[0]
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def _team_addrs() -> set[str]:
    """Every address that counts as US (the three founders plus the CC'd
    teammates), so a CC'd founder is never mistaken for the prospect."""
    addrs: set[str] = set()
    for s in agent.SENDERS:
        addrs.add(s["email"].lower())
        for c in (s.get("cc") or "").split(","):
            c = c.strip().lower()
            if c:
                addrs.add(c)
    return addrs


def _addr(m: dict) -> str:
    return gmail_lib.address_of(gmail_lib.header(m, "From")).lower()


async def _get_thread(client: httpx.AsyncClient, thread_id: str) -> dict:
    r = await client.get(f"{gmail_lib.api_base()}/threads/{thread_id}",
                         params={"format": "full"})
    r.raise_for_status()
    return r.json()


def _render_preview(messages: list[dict], team: set[str], cap: int = 2500) -> str:
    """A compact US/THEM transcript of the thread for the modal, newest emphasis,
    truncated to stay under Slack's text limit."""
    blocks = []
    for m in messages:
        who = "You" if _addr(m) in team else "Them"
        date = gmail_lib.header(m, "Date")
        body = gmail_lib.extract_text_parts(m.get("payload") or {}).strip()
        blocks.append(f"[{who} · {date}]\n{body[:900]}")
    text = "\n\n".join(blocks)
    return text if len(text) <= cap else text[-cap:]


def _latest_inbound(messages: list[dict], team: set[str]) -> dict | None:
    """The last message from the prospect (THEM) — the one we are replying to."""
    inbound = [m for m in messages if _addr(m) not in team]
    return inbound[-1] if inbound else None


def _reply_subject(incoming_subject: str) -> str:
    s = (incoming_subject or "").strip()
    if not s:
        return "Re:"
    return s if s.lower().startswith("re:") else f"Re: {s}"


def _format_examples(examples: list[dict]) -> str:
    out = []
    for i, ex in enumerate(examples, 1):
        subj = (ex.get("incoming_subject") or "").strip()
        inc = (ex.get("incoming_body") or "").strip()[:900]
        rep = (ex.get("reply_body") or "").strip()[:900]
        out.append(f"### Example {i}\nIncoming (subject: {subj}):\n{inc}\n\n"
                   f"How the founder replied:\n{rep}")
    return "\n\n".join(out)


async def _gather_examples(founder: str, category: str) -> list[dict]:
    """Category matches first; if too few, backfill with any-category founder
    exemplars so a novel question still has in-voice examples to imitate."""
    examples = await reply_examples.retrieve(founder, category, limit=5)
    if len(examples) < _MIN_CATEGORY_EXAMPLES:
        seen = {ex.get("reply_body") for ex in examples}
        for ex in await reply_examples.retrieve_any(founder, limit=3):
            if ex.get("reply_body") not in seen:
                examples.append(ex)
    return examples


async def generate_draft(founder_key: str, founder_email: str, thread_id: str) -> dict:
    """Draft a reply for `founder_key` to the latest inbound message in
    `thread_id`. Returns a dict with the draft and everything the send path and
    feedback loop need:
      draft, category, sentiment, incoming_subject, incoming_body,
      reply_subject, to, anchor_message_id (RFC Message-ID for In-Reply-To),
      thread_id, thread_preview, n_examples.
    Raises on a thread that cannot be read or has no inbound message to answer."""
    team = _team_addrs()
    token = await _to_thread(gmail_auth.get_access_token, founder_email)
    async with httpx.AsyncClient(
            headers={"Authorization": f"Bearer {token}"}, timeout=60) as gmail:
        thread = await _get_thread(gmail, thread_id)
    messages = thread.get("messages") or []
    if not messages:
        raise ValueError(f"thread {thread_id} has no messages")
    inbound = _latest_inbound(messages, team)
    if inbound is None:
        raise ValueError(f"thread {thread_id} has no inbound message to reply to")

    incoming_subject = gmail_lib.header(inbound, "Subject") or gmail_lib.header(messages[0], "Subject")
    incoming_body = gmail_lib.extract_text_parts(inbound.get("payload") or {}).strip()
    # The Gmail message id of the inbound we answer. reply_followup.create_draft_api
    # re-fetches it to read the RFC Message-ID for In-Reply-To/References, so we
    # pass the Gmail id (not the RFC header) as spec["reply_to_message_id"].
    reply_to_message_id = inbound.get("id", "")
    to = _addr(inbound)
    # Just the prospect's newly written words, for both the prompt and the card.
    incoming_clean = _clean_reply(incoming_body)

    category = await _to_thread(reply_examples.classify_category,
                                incoming_subject, incoming_body)
    sentiment = await _to_thread(reply_scan.classify_sentiment, incoming_body)
    examples = await _gather_examples(founder_key, category)
    voice = await voice_cards.get_card(founder_key)

    from_name = next((s["from_name"] for s in agent.SENDERS
                      if s["key"] == founder_key), founder_key.title())
    prompt = (
        f"Founder: {from_name}\n\n"
        f"Voice guide:\n{voice or '(none on file — infer their voice from the examples)'}\n\n"
        f"Worked examples of how {from_name} has replied before:\n"
        f"{_format_examples(examples) or '(no examples on file yet — write a plain, honest, human reply)'}\n\n"
        f"The prospect just replied. Answer this message:\n"
        f"Subject: {incoming_subject}\n{incoming_clean or incoming_body[:1500]}\n\n"
        f"Write {from_name}'s reply body now."
    )
    draft = await _to_thread(
        lambda: llm_mod.complete(prompt, system=_SYSTEM, model=_MODEL))
    draft = (draft or "").strip().replace("—", ", ").replace("–", ", ")

    return {
        "draft": draft,
        "category": category,
        "sentiment": sentiment,
        "incoming_subject": incoming_subject,
        "incoming_body": incoming_body,
        "incoming_clean": incoming_clean,
        "reply_subject": _reply_subject(incoming_subject),
        "to": to,
        "reply_to_message_id": reply_to_message_id,
        "thread_id": thread_id,
        "n_examples": len(examples),
    }


async def _to_thread(fn, *args):
    """Run a blocking call off the event loop (mirrors how the wizard offloads
    the synchronous Anthropic/httpx-sync helpers)."""
    import asyncio
    return await asyncio.to_thread(fn, *args)
