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

# For a direct/CSV send, the wizard drafts a shared template that fits the
# audience with this model. The per-audience voice matters more here than for the
# cheap intent-parsing the planner does, so it uses the latest Opus.
PERSONALIZE_MODEL = "claude-opus-4-8"

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


_EMAIL_RE = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")
# Header synonyms for the structured fields; everything else becomes context.
_COL_EMAIL = ("email", "e-mail", "email address", "work email")
_COL_FIRST = ("first name", "first_name", "firstname", "given name")
_COL_LAST = ("last name", "last_name", "lastname", "surname", "family name")
_COL_NAME = ("name", "full name", "contact", "contact name")
_COL_COMPANY = ("company", "affiliation", "organization", "organisation", "org",
                "employer", "brand", "account")
_COL_TITLE = ("title", "job title", "role", "position", "headline")
# Operational columns that should not bleed into the personalization context.
_COL_SKIP = ("status", "source", "verified", "verification", "domain", "linkedin",
             "url", "website", "id", "score")


def _split_name(full: str) -> tuple[str, str]:
    parts = (full or "").strip().split()
    if not parts:
        return "", ""
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], " ".join(parts[1:])


def parse_contacts_csv(text: str) -> list[dict]:
    """Parse CSV/TSV text into lead dicts deterministically (no LLM), so a large
    upload never truncates. Maps common headers to email/name/company/title and
    folds every other non-empty column into a 'context' string for
    personalization. Returns [] when no row carries a valid email."""
    import csv as _csv
    import io as _io

    sample = text[:4096]
    try:
        dialect = _csv.Sniffer().sniff(sample, delimiters=",\t;")
    except Exception:
        dialect = _csv.excel
    reader = _csv.DictReader(_io.StringIO(text), dialect=dialect)
    if not reader.fieldnames:
        return []

    # Resolve which header maps to which structured field (first match wins).
    def find(cands: tuple) -> str | None:
        for h in reader.fieldnames:
            if (h or "").strip().lower() in cands:
                return h
        return None

    h_email, h_first, h_last, h_name = (find(_COL_EMAIL), find(_COL_FIRST),
                                        find(_COL_LAST), find(_COL_NAME))
    h_company, h_title = find(_COL_COMPANY), find(_COL_TITLE)
    structural = {h for h in (h_email, h_first, h_last, h_name, h_company, h_title) if h}

    leads: list[dict] = []
    for row in reader:
        email = ""
        if h_email:
            m = _EMAIL_RE.search(row.get(h_email) or "")
            email = m.group(0).strip() if m else ""
        if not email:  # no usable email in this row — skip it
            continue
        if h_first or h_last:
            first = (row.get(h_first) or "").strip() if h_first else ""
            last = (row.get(h_last) or "").strip() if h_last else ""
        else:
            first, last = _split_name(row.get(h_name) or "" if h_name else "")
        company = (row.get(h_company) or "").strip() if h_company else ""
        title = (row.get(h_title) or "").strip() if h_title else ""
        # Context: every remaining column that is not structural, skip, or noise.
        bits = []
        for h in reader.fieldnames:
            if h in structural or (h or "").strip().lower() in _COL_SKIP:
                continue
            v = (row.get(h) or "").strip()
            if v:
                bits.append(f"{h.strip()}: {v}")
        leads.append({
            "email": email, "first_name": first, "last_name": last,
            "company": company, "title": title,
            "domain": email.split("@", 1)[1] if "@" in email else "",
            "context": "; ".join(bits),
        })
    return leads


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


def _strip_html(html: str) -> str:
    text = re.sub(r"<br\s*/?>", "\n", html, flags=re.I)
    text = re.sub(r"</p\s*>", "\n\n", text, flags=re.I)
    text = re.sub(r"<[^>]+>", "", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def _split_template(raw: str) -> tuple[str, str]:
    """Split a template's frontmatter subject from its body. Returns
    (subject, body); subject is "" when there is no frontmatter."""
    subject, body = "", raw
    if raw.startswith("---"):
        parts = raw.split("---", 2)
        if len(parts) == 3:
            fm, body = parts[1], parts[2]
            m = re.search(r"subject:\s*(.+)", fm)
            subject = m.group(1).strip() if m else ""
    return subject, body


def editable_draft(run: dict) -> tuple[str, str]:
    """(subject, plain-text body) of a run's template with the {{slots}} left
    intact, for hand-editing in the Slack modal. Unlike render_sample it fills
    no placeholder values, so what the user edits is the real template and the
    personalization slots survive."""
    raw = (_CAMPAIGN_DIR / run["template"]).read_text(encoding="utf-8")
    subject, body = _split_template(raw)
    return subject.strip(), _strip_html(body)


def _fill(s: str, values: dict) -> str:
    """Substitute {{slot}} (and {{ slot }}) with values, ignoring unknown slots."""
    for k, v in values.items():
        s = s.replace("{{" + k + "}}", v).replace("{{ " + k + " }}", v)
    return s


def render_sample(run: dict, first_name: str = "Alex", company: str = "Acme Brands",
                  extra: dict | None = None) -> tuple[str, str]:
    """Render one example email (subject, plain-text body) for a run using a
    placeholder contact and the sender's school. No network, no credits.

    `extra` fills additional slots (e.g. {{personal_line}} for a GEO preview);
    unknown slots are left untouched by _fill."""
    raw = (_CAMPAIGN_DIR / run["template"]).read_text(encoding="utf-8")
    subject, body = _split_template(raw)
    school, other = school_for_email(run["email"])
    values = {
        "first_name": first_name,
        "company": company,
        "from_name": run["from_name"],
        "school": school,
        "other_schools": other,
        **(extra or {}),
    }
    return _fill(subject, values).strip(), _strip_html(_fill(body, values))


def render_for_lead(run: dict, lead: dict) -> tuple[str, str]:
    """Render the real email a specific direct-send lead would receive: the run's
    template filled with the lead's actual fields (including a {{personal_line}}
    when one was drafted) and the sender's school. For per-person preview."""
    raw = (_CAMPAIGN_DIR / run["template"]).read_text(encoding="utf-8")
    subject, body = _split_template(raw)
    school, other = school_for_email(run["email"])
    company = (lead.get("company") or "").strip()
    if not company and lead.get("domain"):
        company = lead["domain"].split(".")[0].title()
    values = {
        "first_name": (lead.get("first_name") or "there").strip(),
        "company": company,
        "title": (lead.get("title") or "").strip(),
        "from_name": run["from_name"],
        "school": school,
        "other_schools": other,
        "personal_line": (lead.get("personal_line") or "").strip(),
    }
    return _fill(subject, values).strip(), _strip_html(_fill(body, values))


_CSV_TEMPLATE_SYSTEM = """You write ONE shared cold-email template that a student
will mail-merge to everyone in the audience below. It is sent by a real
undergraduate doing genuine outreach, not by a marketer.

You are given: a sample of the recipients (names, companies, titles, and any
notes) and what the sender wants from them (an "instruction", which may be blank).

The email is mail-merged, so write these placeholders as the LITERAL tokens shown,
never the actual values: {{first_name}} (recipient), {{company}} (their company),
{{school}} (sender's school), {{other_schools}} (the friends' schools),
{{from_name}} (sender's name). Do not write a real school name or person's name.

Write the template body. Hard requirements:
- Open with exactly this line: Hi {{first_name}},
- Early on, in your own words, say the sender is a student at {{school}} working
  with a couple of friends from {{other_schools}}. Use those exact tokens. This
  student framing stays in, it is the whole point of the outreach.
- End by signing off with the sender's name on its own line: Thanks, {{from_name}}
- The MIDDLE is yours. Explain, in a way that genuinely fits THIS audience and the
  instruction, why the sender is writing and what they are asking for. The reason
  and the ask should make sense for these specific people (researchers, operators,
  founders, and so on each get different framing). If the instruction is blank,
  default to a short honest ask for a 10 minute call or a one line reply about the
  biggest challenge in their world.
- You may use {{company}} where it reads naturally. Do not invent other slots.
- Keep it SHORT. At most three short paragraphs between the greeting and the
  sign-off, and aim for under 90 words of body. Cut every sentence that is not
  pulling weight. Plain text, one blank line between paragraphs. Brevity is the
  point: a busy person should be able to read the whole thing in a few seconds.

Voice and hard rules:
- Sound like a real, curious student. Warm, plain, a little informal. Not
  corporate, not salesy.
- Do NOT use em dashes or en dashes anywhere. Use periods and commas.
- No AI or sales filler. Ban these and anything like them: "I hope this finds you
  well", "I came across", "reaching out to", "impressive", "exciting",
  "passionate", "innovative", "leverage", "in today's landscape", "love what
  you're doing". No flattery, no hype, no rule-of-three lists.
- Only claim what is reasonable for a student doing research outreach. Do not
  fabricate credentials or company facts. You may mention being backed by YC if it
  helps, but do not name-drop unrelated brands.
- Also write a subject line: short, lowercase-leaning, human, specific to the
  audience. No clickbait.

Return ONLY JSON, no prose: {"subject": "...", "body": "..."}, with every {{slot}}
left intact in both fields."""


def draft_csv_template(leads: list[dict], instruction: str, school: str,
                       other_schools: str, from_name: str) -> tuple[str, str]:
    """Draft one shared, audience-fit email template (subject, plain-text body
    with {{slots}}) for a direct/CSV send, with the student + school self-intro
    kept and the rest left to the model. Raises if the result drops a required
    slot, so the caller can fall back to the default template."""
    audience = [
        {"first_name": l.get("first_name", ""), "company": l.get("company", ""),
         "title": l.get("title", ""), "notes": (l.get("context") or "").strip()}
        for l in leads[:20]
    ]
    # Note: school/other_schools/from_name are deliberately NOT passed as values
    # so the model writes the {{slots}} verbatim instead of hardcoding them.
    payload = {"audience": audience, "instruction": (instruction or "").strip()}
    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    msg = client.messages.create(
        model=PERSONALIZE_MODEL,
        max_tokens=1500,
        system=_CSV_TEMPLATE_SYSTEM,
        messages=[{"role": "user", "content": json.dumps(payload, ensure_ascii=False)}],
    )
    raw = msg.content[0].text.strip()
    if raw.startswith("```"):
        raw = "\n".join(raw.split("\n")[1:]).rsplit("```", 1)[0]
    obj = json.loads(raw)
    # Belt and braces: scrub any dash the model slipped in.
    subject = (obj.get("subject") or "").strip().replace("—", ", ").replace("–", ", ")
    body = (obj.get("body") or "").strip().replace("—", ", ").replace("–", ", ")
    for slot in ("{{first_name}}", "{{school}}", "{{from_name}}"):
        if slot not in body:
            raise ValueError(f"generated template missing {slot}")
    if not subject:
        raise ValueError("generated template missing subject")
    return subject, body


_REFINE_SYSTEM = """You revise an existing cold-email TEMPLATE for a student doing
outreach, following the user's instruction.

The email is mail-merged, so keep every {{slot}} token (for example {{first_name}},
{{company}}, {{school}}, {{other_schools}}, {{from_name}}) exactly as written and
still present in the email. Do not drop, rename, or add slots.

Apply the instruction faithfully, but always keep the result:
- human and concise, in a curious-student voice, not corporate or salesy,
- free of em dashes and en dashes (use periods and commas),
- free of AI or sales filler ("I hope this finds you well", "reaching out",
  "impressive", "leverage", and the like).

Return ONLY JSON: {"subject": "...", "body": "..."}."""

_SLOT_RE = re.compile(r"\{\{\s*\w+\s*\}\}")


def refine_template(subject: str, body: str, instruction: str) -> tuple[str, str]:
    """Revise a template (subject, body) per a free-text instruction, preserving
    every {{slot}} that was present. Raises if the model drops a slot or the
    instruction empties the email, so the caller can keep the pre-refine copy."""
    def _slots(s: str) -> set:
        return {re.sub(r"\s+", "", t) for t in _SLOT_RE.findall(s)}

    before = _slots(subject) | _slots(body)
    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    payload = {"subject": subject, "body": body,
               "instruction": (instruction or "").strip()}
    msg = client.messages.create(
        model=PERSONALIZE_MODEL,
        max_tokens=1500,
        system=_REFINE_SYSTEM,
        messages=[{"role": "user", "content": json.dumps(payload, ensure_ascii=False)}],
    )
    raw = msg.content[0].text.strip()
    if raw.startswith("```"):
        raw = "\n".join(raw.split("\n")[1:]).rsplit("```", 1)[0]
    obj = json.loads(raw)
    rs = (obj.get("subject") or "").strip().replace("—", ", ").replace("–", ", ")
    rb = (obj.get("body") or "").strip().replace("—", ", ").replace("–", ", ")
    if not rs or not rb:
        raise ValueError("refine returned an empty subject or body")
    missing = before - (_slots(rs) | _slots(rb))
    if missing:
        raise ValueError(f"refine dropped slots: {missing}")
    return rs, rb
