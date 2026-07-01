"""Campaign planning: turn a natural-language request into concrete per-(sender,
ICP) runs, do the sender/daily-cap arithmetic, preview the target niches, and
answer questions about a finished run. No platform code and no email copy: the
template rendering and copy generation live in `drafting.py`.

`agent.py` re-exports this module's public names, so existing callers and tests
that use `agent.plan`, `agent._divide`, `agent.SENDERS`, etc. keep working.
"""
import json
import math
import re
from pathlib import Path

import anthropic

from . import config

# skills/campaign — templates live under here.
_CAMPAIGN_DIR = Path(__file__).resolve().parents[1]

# Every send uses the brand template by default; the school is filled per sender
# so a mixed-sender campaign never misstates who is emailing.
DEFAULT_TEMPLATE = "templates/brands.md"

# GEO pilot: when a segment is framed around AI visibility (showing up when a
# shopper asks ChatGPT for recommendations), it uses this template and run.py
# fills {{personal_line}} per brand from a live AI-visibility check.
AI_VISIBILITY_TEMPLATE = "templates/ai_visibility.md"

# Team schools, Stanford pinned first (matches run.school_for_email).
_TEAM_SCHOOLS = ["Stanford", "Dartmouth", "Berkeley"]

SENDERS = [
    {
        "key": "armaan",
        "email": "armaan.priyadarshan.29@dartmouth.edu",
        "from_name": "Armaan",
        "cc": "samarjit.deshmukh.29@dartmouth.edu,ethanpzhou@berkeley.edu,shamitd@stanford.edu",
    },
    {
        "key": "samarjit",
        "email": "samarjit.deshmukh.29@dartmouth.edu",
        "from_name": "Samarjit",
        "cc": "armaan.priyadarshan.29@dartmouth.edu,ethanpzhou@berkeley.edu,shamitd@stanford.edu",
    },
    {
        "key": "ethan",
        "email": "ethanpzhou@berkeley.edu",
        "from_name": "Ethan",
        "cc": "samarjit.deshmukh.29@dartmouth.edu,armaan.priyadarshan.29@dartmouth.edu,shamitd@stanford.edu",
    },
]

# Per-Gmail-account daily send cap. Each sender is a real mailbox; exceeding its
# daily limit risks bounces and account suspension. The divider fills senders up
# to this cap before recruiting another, so small campaigns use one sender and
# large ones use only as many as the volume requires.
PER_ACCOUNT_DAILY_CAP = 800

# Don't spawn a run smaller than this. Tiny per-(sender, ICP) batches waste the
# fixed sourcing overhead (their own niche generation + Hunter pre-checks) and
# under-deliver because of run.py's _FILL_TOLERANCE. Sub-threshold segments are
# merged into larger ones rather than run on their own.
MIN_BATCH = 10


_SYSTEM = f"""You are a campaign planning assistant for Blackwell, a B2B SaaS startup.
Your ONLY job is to read a natural-language request and extract intent. You do
NOT decide how many senders to use or how to split numbers across them — code
does the arithmetic. Do not do math beyond reading the requested total.

The user names whichever ICPs (target markets) the day calls for, in plain
English — there is no fixed menu. Take the ICPs from the request as written.

DIRECT-SEND MODE: If the user provides specific people to email — meaning actual
email addresses, or names paired with company names from which an email can be
inferred, or a pasted CSV/table of contacts — return this shape instead:
{{
  "direct": true,
  "leads": [
    {{"email": "<email address>",
      "first_name": "<first name or empty string>",
      "last_name": "<last name or empty string>",
      "company": "<company name or empty string>",
      "title": "<job title or empty string>",
      "domain": "<company domain inferred from email, or empty string>",
      "context": "<any EXTRA detail about this person or their company found in the input beyond the basic fields above — role specifics, what the company does, recent news, products, a note the user wrote, anything that could make an email more specific. Copy or lightly summarize it. Empty string if there is none.>"}}
  ],
  "senders": ["<first names of the accounts to send from, if named, lowercased>"]
}}
Parse any format: a casual mention ("email John Smith at Acme, john@acme.com"),
a pasted CSV block, a table, a JSON snippet. Infer domain from the email when
not given. Use empty string for unknown optional fields. Only use direct mode
when at least one real email address is present. IMPORTANT: when a CSV or table
has columns beyond name/email/company (a bio, a description, notes, recent
activity, anything), do NOT discard them — gather them into each lead's
"context" so the email can be personalized. Never invent context that is not in
the input.

STANDARD MODE (ICP campaign): Return ONLY a JSON object, no prose:
{{
  "total": <total number of emails the user wants sent>,
  "segments": [
    {{"label": "<short name for the ICP, from the user's words>",
      "icp": "<one-line description of who to target, for domain sourcing>",
      "weight": <relative weight, any positive number>,
      "geo": <true if the user frames this outreach around AI visibility / GEO —
              getting the brand named when shoppers ask ChatGPT or other AI
              assistants for recommendations, showing up in AI search — else false>}}
  ],
  "senders": ["<first names of the accounts to send from, if the user names any, lowercased>"],
  "clarify": "<a question to ask the user, or empty string>"
}}

Rules for standard mode:
- "total" is the overall email count across the whole campaign, not per sender.
- One segment per distinct ICP the user names. Write a clear one-line "icp"
  description for each so the sourcing step can find the right companies.
- "senders" lists the accounts the user asks to send from, by first name. One
  name -> ["samarjit"]; several -> ["ethan","samarjit"]. Honor negations by
  excluding them (e.g. "Ethan and Samarjit, not Armaan" -> ["ethan","samarjit"]).
  Known senders: armaan, samarjit, ethan. If the user names none, use [].
- Set "clarify" to a SHORT question when EITHER:
    - the user names no ICP at all — ask which ICPs to target today; or
    - the user names two or more ICPs without saying how to split between them
      — ask for the split, e.g. "What split — e.g. 60% DTC / 40% neo labs?".
- If there is a single ICP, or the split is explicit (percentages or counts),
  set clarify = "" and fill weights to match.
- Weights are relative; they do not need to sum to 1.
- When you do set "clarify", phrase the question briefly in a light, playful
  wizard voice (a small arcane flourish is welcome), while staying clear. No em
  or en dashes."""


def _allocate(total: int, weights: list[float]) -> list[int]:
    """Split `total` into integer counts proportional to `weights`, summing
    exactly to `total` (largest-remainder method)."""
    if total <= 0 or not weights:
        return [0 for _ in weights]
    tw = sum(weights) or 1.0
    raw = [total * w / tw for w in weights]
    counts = [int(x) for x in raw]
    remainder = total - sum(counts)
    order = sorted(range(len(raw)), key=lambda i: -(raw[i] - int(raw[i])))
    for i in order[:remainder]:
        counts[i] += 1
    return counts


def _split_with_min_batch(total: int, weighted: list[tuple[dict, float]]) -> list[tuple[dict, int]]:
    """Allocate `total` across weighted segments, but never produce a run below
    MIN_BATCH: drop the lowest-weight segment and reallocate until every run
    clears the floor, collapsing to the single top segment if needed."""
    weighted = sorted([(s, w) for s, w in weighted if w > 0], key=lambda x: -x[1])
    if total <= 0 or not weighted:
        return []
    n = len(weighted)
    while n > 1:
        counts = _allocate(total, [w for _, w in weighted[:n]])
        if all(c == 0 or c >= MIN_BATCH for c in counts):
            return [(weighted[i][0], counts[i]) for i in range(n) if counts[i] > 0]
        n -= 1
    return [(weighted[0][0], total)]


def resolve_sender(name: str) -> str | None:
    """Map a first name, key, or email to a sender key, or None if unrecognized.
    Tolerant of the model returning a full name or address ("Ethan Zhou")."""
    name = (name or "").strip().lower()
    if not name:
        return None
    for s in SENDERS:
        local = s["email"].split("@")[0].lower()
        if name in (s["key"], s["from_name"].lower(), local, s["email"].lower()):
            return s["key"]
    # Loose match: a sender key, name, or email local part appearing as a token.
    tokens = name.replace("@", " ").split()
    for s in SENDERS:
        local = s["email"].split("@")[0].lower()
        if s["key"] in tokens or s["from_name"].lower() in tokens or local in tokens:
            return s["key"]
    return None


def _divide(total: int, segments: list[dict],
            sender_keys: list[str] | None = None) -> tuple[list[dict], int]:
    """Turn (total, ICP weights) into concrete per-(sender, ICP) runs.

    With no senders named, recruit the fewest accounts that cover the volume at
    PER_ACCOUNT_DAILY_CAP. When the user names accounts, use exactly those (all of
    them), splitting the volume across them and capping at their combined daily
    limit. Each sender's share is split across ICPs with a minimum batch size.
    Returns (runs, deferred) where `deferred` is volume beyond capacity.
    """
    total = max(0, int(total or 0))

    if sender_keys:
        # Honor exactly the accounts the user named, in canonical order.
        pool = [s for s in SENDERS if s["key"] in sender_keys]
    else:
        pool = list(SENDERS)
    if not pool:
        pool = list(SENDERS)

    if not total:
        n_senders = 0
    elif sender_keys:
        n_senders = len(pool)  # spread across every named account
    else:
        n_senders = min(len(pool), max(1, math.ceil(total / PER_ACCOUNT_DAILY_CAP)))
    capacity = n_senders * PER_ACCOUNT_DAILY_CAP
    deferred = max(0, total - capacity)
    to_send = min(total, capacity)
    if to_send <= 0:
        return [], deferred

    # Every ICP is free text from the request: {label, icp} straight through.
    weighted: list[tuple[dict, float]] = []
    for seg in segments:
        w = float(seg.get("weight", 0) or 0)
        label = (seg.get("label") or "").strip()
        if w <= 0 or not label:
            continue
        weighted.append((
            {"label": label,
             "icp": (seg.get("icp") or label).strip(),
             "geo": bool(seg.get("geo", False))},
            w,
        ))
    if not weighted:  # no ICP given — nothing to send (clarify normally prevents this)
        return [], deferred

    # Even split across the chosen senders, each at or under the cap.
    base, rem = divmod(to_send, n_senders)
    volumes = [base + (1 if i < rem else 0) for i in range(n_senders)]

    runs: list[dict] = []
    for sender, vol in zip(pool[:n_senders], volumes):
        for sd, n in _split_with_min_batch(vol, weighted):
            geo = sd.get("geo", False)
            runs.append({
                "sender_key": sender["key"],
                "email": sender["email"],
                "from_name": sender["from_name"],
                "cc": sender["cc"],
                "icp_label": sd["label"],
                "icp_desc": sd["icp"],
                "template": AI_VISIBILITY_TEMPLATE if geo else DEFAULT_TEMPLATE,
                "geo": geo,
                "n_emails": n,
            })
    return runs, deferred


def _direct_label(leads: list[dict]) -> str:
    if len(leads) == 1:
        first = (leads[0].get("first_name") or "").strip()
        company = (leads[0].get("company") or "").strip()
        if first and company:
            return f"Direct: {first} at {company}"
        if leads[0].get("email"):
            return f"Direct: {leads[0]['email']}"
    return f"Direct to {len(leads)} contact{'s' if len(leads) != 1 else ''}"


def build_direct_plan(leads: list[dict], raw_senders) -> dict:
    """Turn a known list of leads into a single direct-send run. Shared by the
    Claude direct path and the deterministic CSV path."""
    if isinstance(raw_senders, str):
        raw_senders = [raw_senders]
    keys: list[str] = []
    for nm in (raw_senders or []):
        k = resolve_sender(nm)
        if k and k not in keys:
            keys.append(k)
    pool = [s for s in SENDERS if s["key"] in keys] if keys else list(SENDERS)
    sender = pool[0]
    return {
        "runs": [{
            "sender_key": sender["key"],
            "email": sender["email"],
            "from_name": sender["from_name"],
            "cc": sender["cc"],
            "icp_label": _direct_label(leads),
            "icp_desc": "direct send",
            "n_emails": len(leads),
            "direct_leads": leads,
            "template": DEFAULT_TEMPLATE,
        }],
        "deferred": 0,
    }


def senders_in_text(text: str) -> list[str]:
    """Sender keys named in free text ("send these via Ethan"). Word-boundary
    matched so it does not fire on substrings."""
    keys: list[str] = []
    for token in re.findall(r"[A-Za-z]+", text or ""):
        k = resolve_sender(token)
        if k and k not in keys:
            keys.append(k)
    return keys


def plan(user_message: str, allow_clarify: bool = True) -> dict:
    """Parse a request into either a clarification question or concrete runs.

    Returns {"clarify": "<question>"} when the ICP split is ambiguous (and
    allow_clarify is True), otherwise {"runs": [...], "deferred": <int>}. The LLM
    only extracts intent; _divide() does the sender/cap arithmetic.
    """
    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=8192,  # a pasted (non-file) table can echo many rows
        system=_SYSTEM,
        messages=[{"role": "user", "content": user_message}],
    )
    raw = msg.content[0].text.strip()
    if raw.startswith("```"):
        raw = "\n".join(raw.split("\n")[1:]).rsplit("```", 1)[0]
    intent = json.loads(raw)

    # Direct-send mode: leads are already known, skip Hunter sourcing entirely.
    if intent.get("direct"):
        leads = [l for l in (intent.get("leads") or []) if (l.get("email") or "").strip()]
        if not leads:
            return {"clarify": "By my arts — I found no email addresses in that. "
                               "Share the contacts (email, name, company) and I shall dispatch at once."}
        return build_direct_plan(leads, intent.get("senders") or [])

    question = (intent.get("clarify") or "").strip()
    if allow_clarify and question:
        return {"clarify": question}
    raw = intent.get("senders") or intent.get("sender") or []
    if isinstance(raw, str):
        raw = [raw]
    keys = []
    for nm in raw:
        k = resolve_sender(nm)
        if k and k not in keys:
            keys.append(k)
    sender_keys = [s["key"] for s in SENDERS if s["key"] in keys] or None
    runs, deferred = _divide(intent.get("total", 0), intent.get("segments", []),
                             sender_keys)
    return {"runs": runs, "deferred": deferred}


async def preview_niches(plan_runs: list[dict], sample_niches: int = 2,
                         max_icps: int = 4) -> list[dict]:
    """Surface the niches sourcing will target, so a human can catch intent drift
    before any send. Returns one entry per distinct sourced ICP:
    {"label", "icp", "niches": [...], "samples": [{"niche", "domains"}]}.

    The niches are generated into the same SubcategoryCache the run.py pipeline
    reads (keyed on the ICP string the executor passes as --icp), so this preview
    is the exact set that will be used, not a throwaway, and the real run reuses
    it instead of regenerating. Direct/CSV sends carry no sourced ICP and are
    skipped. Failures degrade to an empty preview rather than blocking the plan.
    """
    import asyncio

    # Imported lazily: run.py pulls in the whole sourcing stack (toolbox
    # primitives, gog_auth, storeleads), which we do not want at bot startup.
    from skills.campaign import run as campaign_run

    out: list[dict] = []
    seen: set[str] = set()
    for p in plan_runs:
        icp = (p.get("icp_desc") or "").strip()
        label = p.get("icp_label") or icp
        if not icp or icp.lower() == "direct send" or icp in seen:
            continue
        seen.add(icp)
        if len(seen) > max_icps:
            break
        try:
            cache = campaign_run.SubcategoryCache(icp)
            niches = cache.all_labels()
            if not niches:
                niches = await asyncio.to_thread(
                    campaign_run.generate_subcategories, icp)
                cache.add(niches)
        except Exception:  # noqa: BLE001 - a preview must never break planning
            continue
        if not niches:
            continue
        samples: list[dict] = []
        for sub in niches[:sample_niches]:
            try:
                domains = await campaign_run.source_domains_for_subcat(sub, count=4)
            except Exception:  # noqa: BLE001
                domains = []
            if domains:
                samples.append({"niche": sub, "domains": domains[:4]})
        out.append({"label": label, "icp": icp, "niches": niches,
                    "samples": samples})
    return out


_QA_SYSTEM = """You are the email_wizard, a helpful wizard who runs cold outreach
campaigns for Blackwell and answers a teammate's question in a Slack thread.

Speak in a light, playful wizard voice: a touch of arcane flavor, the odd
"scroll" (email), "sending" (campaign), or "divining" (sourcing leads), and an
occasional flourish like "Behold" or "By my arts". Keep it tasteful and always
clear and useful; never let the theatrics obscure the facts.

Answer ONLY from the campaign plan, status, and log provided. If the log does
not hold the answer, say so plainly rather than guessing. Be concise and
specific: cite counts, senders, ICPs, and progress from the log. Plain text for
Slack, no markdown headers, no em or en dashes. If the campaign is still
running, frame the answer as a snapshot of progress so far."""


def answer_about_campaign(question: str, *, plan_summary: str, status: str,
                          results: str | None, progress: str, log_text: str) -> str:
    """Answer a question grounded in one campaign's plan, status, and log."""
    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    context = (
        f"Campaign status: {status}\n"
        f"Plan:\n{plan_summary}\n"
        f"Latest progress snapshot: {progress or 'none yet'}\n"
        f"Final results: {results or 'not finished'}\n\n"
        f"Campaign log (most recent output):\n{log_text or '(no log yet)'}\n\n"
        f"Question: {question}"
    )
    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=700,
        system=_QA_SYSTEM,
        messages=[{"role": "user", "content": context}],
    )
    return msg.content[0].text.strip()


def school_for_email(email: str) -> tuple[str, str]:
    """(school, other_schools) for a sender — mirrors run.school_for_email."""
    domain = (email or "").rsplit("@", 1)[-1].lower()
    if "dartmouth" in domain:
        school = "Dartmouth"
    elif "berkeley" in domain:
        school = "Berkeley"
    else:
        school = "Stanford"
    others = "/".join(s for s in _TEAM_SCHOOLS if s != school)
    return school, others
