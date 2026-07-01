"""Compatibility facade for the campaign planning + copy code.

The implementation was split into two focused modules:
  - planner.py   — parse a request into runs, sender/cap arithmetic, niche
                   preview, campaign Q&A (`plan`, `_divide`, `SENDERS`, ...).
  - drafting.py  — template rendering, CSV parsing, copy generation
                   (`render_sample`, `parse_contacts_csv`, `refine_template`, ...).

This module re-exports their public API (plus the few private helpers the tests
reach for) so existing callers and tests that import `agent.<name>` keep working
unchanged. New code can import from `planner` / `drafting` directly.
"""
from .drafting import (  # noqa: F401
    PERSONALIZE_MODEL,
    draft_csv_template,
    editable_draft,
    parse_contacts_csv,
    refine_template,
    render_for_lead,
    render_sample,
)
from .planner import (  # noqa: F401
    AI_VISIBILITY_TEMPLATE,
    DEFAULT_TEMPLATE,
    MIN_BATCH,
    PER_ACCOUNT_DAILY_CAP,
    SENDERS,
    _allocate,
    _direct_label,
    _divide,
    answer_about_campaign,
    build_direct_plan,
    plan,
    preview_niches,
    resolve_sender,
    school_for_email,
    senders_in_text,
)
