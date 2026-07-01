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
import asyncio
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
  call, asking for a time, or saying yes), point them to our scheduling page.
  Write it as a markdown link whose visible text is a natural word like "here",
  for example "you can grab a time [here](URL)" or "feel free to book a slot
  [here](URL)". Put this exact URL inside the parentheses, verbatim, and do NOT
  paste the raw URL anywhere else in the email:
  {SCHEDULING_LINK}
- Keep it short, a few sentences. One blank line between paragraphs.
- No em dashes or en dashes. Use periods and commas. No AI or sales filler ("I
  hope this finds you well", "reaching out", "leverage", and the like).
- End with the founder's usual sign-off and first name, matching the examples.
- Do not invent facts, commitments, prices, or dates we have not stated. If you
  are unsure of a specific, keep it general so the founder can fill it in.

Output the reply body as plain text, nothing else."""


# HTML containers that wrap the quoted prior message (cut on the raw HTML, before
# tags are stripped, so the quote text never leaks into the plain rendering).
_HTML_QUOTE_RE = re.compile(
    r"<(blockquote|div[^>]*(?:gmail_quote|gmail_extra|gmail_attr)|"
    r"div[^>]*id=[\"']?(?:appendonsend|divRplyFwdMsg))", re.I)

# Plain-text markers that begin quoted reply history / a signature; everything
# from the earliest one on is prior thread, not the prospect's new message.
_TEXT_QUOTE_MARKERS = [
    # "On <date>, <name> wrote:" and its localized variants.
    re.compile(r"\n\s*(?:On|El|Le|Am)\b.{0,400}?"
               r"(?:wrote|a écrit|schrieb|escribió|ha scritto|napisał|schreef)\s*:",
               re.S | re.I),
    re.compile(r"\n-{2,}\s*Original Message\s*-{2,}", re.I),
    re.compile(r"\n_{5,}"),                                    # outlook divider
    re.compile(r"\n\s*From:\s.{0,200}?\n\s*Sent:\s", re.S | re.I),   # outlook header
    re.compile(r"\n\s*Sent from my \w+", re.I),               # mobile signature
    re.compile(r"\n-- \n"),                                     # standard sig delimiter
]


def _clean_reply(body: str) -> str:
    """Extract just the prospect's newly written message from a reply body: drop
    the quoted thread history (in either the HTML or the plain form), the markup,
    and a trailing signature, so the card shows their actual words. Email reply
    parsing is heuristic, so this is best-effort but covers the common clients."""
    text = body or ""
    # 1. Cut an HTML quote container on the raw text first.
    m = _HTML_QUOTE_RE.search(text)
    if m:
        text = text[:m.start()]
    # 2. Normalize the remaining HTML into text, then strip any leftover tags.
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
    text = re.sub(r"</(p|div)\s*>", "\n", text, flags=re.I)
    text = re.sub(r"<[^>]+>", "", text)
    text = html_mod.unescape(text)
    # 3. Cut at the earliest plain-text quote/signature marker.
    cut = len(text)
    for rx in _TEXT_QUOTE_MARKERS:
        mm = rx.search(text)
        if mm:
            cut = min(cut, mm.start())
    text = text[:cut]
    # 4. Drop any stray quoted lines and collapse blank runs.
    text = "\n".join(ln for ln in text.splitlines() if not ln.lstrip().startswith(">"))
    return re.sub(r"\n{3,}", "\n\n", text).strip()


_EXTRACT_MODEL = "claude-haiku-4-5-20251001"  # cheap + fast; runs alongside the draft.
_EXTRACT_SYSTEM = """You extract the newly written portion of an email. You are a
text filter, not a conversation partner.

Input: the raw body of ONE email. It may contain the person's newly written
message plus quoted earlier emails, a signature, and email client boilerplate. It
may also be a plain first email with nothing quoted at all.

Output: ONLY the message text this person wrote, their words verbatim, with quoted
prior emails, the signature, and boilerplate removed. If nothing is quoted (it is
all their own new writing), output the whole body unchanged.

Rules, always:
- Output message text only. Never describe or comment on the email.
- Never say you are an AI, never refuse, never ask for clarification, never
  explain what you did or could not do.
- Do not summarize, translate, shorten, rephrase, or add anything.
- If you are unsure what is new versus quoted, output the input exactly as given."""

# If the model editorializes or refuses instead of returning the text (it sometimes
# does this on a plain first-touch email that has nothing to strip), these markers
# catch it so we fall back to the raw cleaned body instead of leaking the meta-reply.
_META_MARKERS = (
    "i'm an ai", "i am an ai", "as an ai", "ai assistant",
    "i don't have the ability", "i do not have the ability",
    "i cannot see", "i can't see", "i cannot identify", "i can't identify",
    "you've provided", "you have provided", "please provide", "i'll extract",
    "appears to be a complete", "the text you", "if you have an actual",
)


def _looks_like_meta(out: str, body: str) -> bool:
    """True if the extractor returned commentary about the email rather than the
    email text itself. Only trips when the phrase is NOT in the source body (so a
    prospect who genuinely wrote "please provide..." is never misflagged)."""
    low = out.lower()
    blow = body.lower()
    return any(mark in low and mark not in blow for mark in _META_MARKERS)


def _extract_message(body: str) -> str:
    """Pull just the person's newly written message from a raw email body using a
    fast model. Regex cannot separate new text from quoted history reliably (it was
    cutting real messages mid-word); the model does this well. Falls back to the
    regex cleaner if the call fails, comes back empty, or comes back as a meta reply
    (the model explaining itself instead of returning the text)."""
    body = (body or "").strip()
    if not body:
        return ""
    try:
        out = (llm_mod.complete(body[:16000], system=_EXTRACT_SYSTEM,
                                model=_EXTRACT_MODEL) or "").strip()
        if not out or _looks_like_meta(out, body):
            return _clean_reply(body)
        return out
    except Exception as e:  # noqa: BLE001
        log.warning("message extraction failed, using regex fallback: %s", str(e)[:120])
        return _clean_reply(body)


def _received_display(inbound: dict) -> str:
    """A short human timestamp for when a message was sent, from its Date header
    (falling back to internalDate). Empty on failure."""
    import datetime
    import email.utils
    raw = gmail_lib.header(inbound, "Date")
    dt = None
    if raw:
        try:
            dt = email.utils.parsedate_to_datetime(raw)
        except (TypeError, ValueError):
            dt = None
    if dt is None:
        try:
            dt = datetime.datetime.fromtimestamp(
                int(inbound.get("internalDate", 0)) / 1000, tz=datetime.timezone.utc)
        except (TypeError, ValueError):
            return ""
    try:
        return dt.strftime("%b %-d, %Y at %-I:%M %p")
    except ValueError:  # platforms without %-d/%-I
        return dt.strftime("%b %d, %Y at %I:%M %p")


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


# How many of the most recent messages to show in the card transcript. Older ones
# are summarized as hidden (the Gmail link still opens the full thread).
_MAX_TRANSCRIPT = 8


async def _build_transcript(messages: list[dict], team: set[str]) -> tuple[list[dict], int]:
    """A clean chronological US/THEM transcript of the thread for the card. Each
    message's own newly written text is pulled with the fast model (all messages
    extracted concurrently), so quoted history and client boilerplate never reach
    the display. Returns (entries, hidden) where entries are the most recent
    messages as {who: 'you'|'them', when, text} and hidden is how many older
    messages were dropped to stay under Slack's block limit."""
    recent = messages[-_MAX_TRANSCRIPT:]
    hidden = len(messages) - len(recent)
    bodies = [gmail_lib.extract_text_parts(m.get("payload") or {}).strip() for m in recent]
    cleans = await asyncio.gather(
        *[asyncio.to_thread(_extract_message, b) for b in bodies])
    entries = [{"who": "you" if _addr(m) in team else "them",
                "when": _received_display(m), "text": clean}
               for m, clean in zip(recent, cleans)]
    return entries, hidden


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
    received = _received_display(inbound)

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
        f"The prospect just replied. Answer this message (ignore any quoted earlier "
        f"emails below it):\n"
        f"Subject: {incoming_subject}\n{incoming_body[:6000]}\n\n"
        f"Write {from_name}'s reply body now."
    )
    # Draft (Opus) and the whole-thread extraction (fast model, one call per message,
    # all concurrent) run together, so the clean transcript costs no extra wall-clock
    # beyond the draft itself.
    draft, (transcript, hidden) = await asyncio.gather(
        asyncio.to_thread(lambda: llm_mod.complete(prompt, system=_SYSTEM, model=_MODEL)),
        _build_transcript(messages, team),
    )
    draft = (draft or "").strip().replace("—", ", ").replace("–", ", ")
    # The latest THEM message in the transcript is the one we are answering.
    incoming_clean = next((e["text"] for e in reversed(transcript) if e["who"] == "them"),
                          transcript[-1]["text"] if transcript else "")

    return {
        "draft": draft,
        "category": category,
        "sentiment": sentiment,
        "incoming_subject": incoming_subject,
        "incoming_body": incoming_body,
        "incoming_clean": incoming_clean,
        "thread": transcript,
        "thread_hidden": hidden,
        "received": received,
        "gmail_url": f"https://mail.google.com/mail/u/0/#all/{thread_id}",
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
