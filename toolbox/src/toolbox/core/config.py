"""Central configuration for the toolbox.

Nothing here is a secret. The Supabase *anon* key is a public client identifier
by design (RLS is what protects data); real secrets (provider tokens, API keys)
live in Supabase `connection_secrets` and are only ever fetched at runtime via
`core/auth.py` — never from the repo, never from env files.

Env overrides exist so tests and local dev can point at the local stack.
"""

from __future__ import annotations

import os
from pathlib import Path

# Local `supabase start` defaults. For the hosted project, set both env vars
# (e.g. in your shell profile — they are not secrets).
DEFAULT_LOCAL_SUPABASE_URL = "http://127.0.0.1:54321"

KEYRING_SERVICE = "blackwell-toolbox"


def supabase_url() -> str:
    return os.environ.get("SUPABASE_URL", DEFAULT_LOCAL_SUPABASE_URL).rstrip("/")


def supabase_anon_key() -> str:
    return os.environ.get("SUPABASE_ANON_KEY", "")


def repo_root(start: Path | None = None) -> Path:
    """Walk upward to the repo root (the directory containing .git)."""
    p = (start or Path.cwd()).resolve()
    for candidate in (p, *p.parents):
        if (candidate / ".git").exists():
            return candidate
    raise RuntimeError(f"not inside the interns repo (no .git above {p})")


def runs_dir(root: Path | None = None) -> Path:
    d = repo_root(root) / "runs"
    d.mkdir(exist_ok=True)
    return d


def skills_dir(root: Path | None = None) -> Path:
    return repo_root(root) / "skills"


# Anthropic model defaults (see harness build plan §1). Personalization and
# filtering are short, high-volume tasks — haiku is the right default; flows
# escalate to sonnet via inputs when a segment needs better copy.
DEFAULT_LLM_MODEL = "claude-haiku-4-5"
ESCALATION_LLM_MODEL = "claude-sonnet-4-6"

# Exit code a process primitive uses to signal "paused, human action needed".
# 75 = EX_TEMPFAIL, repurposed: the runner stops and prints resume instructions.
PAUSE_EXIT_CODE = 75
