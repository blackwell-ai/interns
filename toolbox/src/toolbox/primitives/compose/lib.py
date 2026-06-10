"""Template render + first-name rules (port of template_render.py / first_name.py).

Changes from the port: ALLOWED_SLOTS is gone — flows define their own columns,
so any {{slot}} that matches a row field (or a generated one like first_name /
personalization_hook) is legal. A slot with no value is an error per row; the
caller decides drop-vs-fail. Templates carry the subject in YAML-ish
frontmatter:

    ---
    subject: Quick question about {{company}}
    ---
    Hi {{first_name}}, ...
"""

from __future__ import annotations

import re

SLOT_RE = re.compile(r"\{\{\s*(\w+)\s*\}\}")

TITLE_PATTERN = re.compile(r"^(Dr|Mr|Mrs|Ms|Prof|Sir|Lord|Lady)\.?\s+", re.IGNORECASE)
SUFFIX_TOKENS = frozenset({"Jr.", "Sr.", "II", "III", "IV", "Jr", "Sr"})
NOT_A_NAME = frozenset({"the", "mr", "ms", "mrs", "dr", "prof", "sir", "dame", "lord", "lady", "rev"})
MIDDLE_INITIAL = re.compile(r"^[A-Z]\.$")


class TemplateError(Exception):
    pass


def parse_template(text: str) -> tuple[str, str]:
    """-> (subject_template, body_template)."""
    m = re.match(r"\s*---\s*\nsubject:\s*(.+?)\s*\n---\s*\n", text)
    if not m:
        raise TemplateError("template needs frontmatter: ---\\nsubject: ...\\n---\\n<body>")
    return m.group(1), text[m.end():]


def find_slots(template_text: str) -> set[str]:
    return set(SLOT_RE.findall(template_text))


def render(template_text: str, values: dict) -> str:
    def repl(m: re.Match) -> str:
        slot = m.group(1)
        v = values.get(slot, "")
        if v is None or str(v).strip() == "":
            raise TemplateError(f"slot {{{{{slot}}}}} is empty for this row")
        return str(v)

    return SLOT_RE.sub(repl, template_text)


# ---- first-name extraction (deterministic part of the port) -----------------


def strip_title(name: str) -> str:
    return TITLE_PATTERN.sub("", name.strip(), count=1)


def naive_first(name: str) -> str:
    tokens = name.strip().split()
    return tokens[0] if tokens else name


def is_ambiguous(name: str) -> bool:
    tokens = name.split()
    if not tokens:
        return False
    first = tokens[0]
    if "-" in first:
        return True
    if any(t in SUFFIX_TOKENS for t in tokens):
        return True
    if any(ord(ch) > 0x024F for ch in first):
        return True
    if first.lower() in NOT_A_NAME:
        return True
    if len(tokens) >= 3:
        t1, t2 = tokens[0], tokens[1]
        if len(t1) <= 8 and len(t2) <= 8 and not MIDDLE_INITIAL.match(t1) and not MIDDLE_INITIAL.match(t2):
            return True
    return False


def first_name(full_name: str, llm_fallback=None) -> str:
    """Deterministic rules first; `llm_fallback(name) -> str` only when the
    rules say the name is ambiguous (the old code's exact behavior)."""
    stripped = strip_title(full_name)
    if not is_ambiguous(stripped) or llm_fallback is None:
        return naive_first(stripped)
    try:
        return llm_fallback(stripped) or naive_first(stripped)
    except Exception:
        return naive_first(stripped)
