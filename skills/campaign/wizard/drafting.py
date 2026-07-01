"""Email copy: render a template for preview or for a specific lead, parse an
uploaded contacts CSV, draft one audience-fit template for a direct send, and
refine a template from a free-text instruction. All the Claude "copy" prompts
live here; the planning/arithmetic lives in `planner.py`.

`agent.py` re-exports this module's public names, so callers and tests that use
`agent.render_sample`, `agent.parse_contacts_csv`, `agent.refine_template`, etc.
keep working.
"""
import json
import re

import anthropic

from . import config
from .planner import _CAMPAIGN_DIR, school_for_email

# For a direct/CSV send, the wizard drafts a shared template that fits the
# audience with this model. The per-audience voice matters more here than for the
# cheap intent-parsing the planner does, so it uses the latest Opus.
PERSONALIZE_MODEL = "claude-opus-4-8"


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
