"""Headless Claude Code wrapper (provider swapped per the 2026-06-10 decision:
harness LLM calls run through `claude -p` so usage bills to the team's Claude
subscription, not an Anthropic API key).

Three entry points (signatures unchanged from the API-client version, so all
primitives and their monkeypatching tests keep working):
  * parse(...)      — structured output: prompt for strict JSON, validate with
                      Pydantic; one repair retry on a malformed response.
  * complete(...)   — plain text completion.
  * web_search(...) — completion with Claude Code's WebSearch tool enabled
                      (replaces the hosted web_search server tool; Claude Code
                      runs its own search loop, so no pause_turn handling).

A safety refusal is surfaced as LLMRefusal — callers MUST NOT retry those.

Auth: the `claude` CLI's logged-in Claude subscription. ANTHROPIC_API_KEY is
stripped from the subprocess env so a stray key can never silently flip usage
back to API billing. Calls run from the system temp dir so the repo's
CLAUDE.md and project MCP servers are not loaded into the prompt.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from toolbox.core import config

M = TypeVar("M", bound=BaseModel)

_TIMEOUT_S = 600
_FENCE_RE = re.compile(r"^\s*```(?:json)?\s*|\s*```\s*$")

# Global token/cost accumulator — call get_usage() to read, reset_usage() to clear.
_usage: dict[str, float] = {
    "input_tokens": 0,
    "output_tokens": 0,
    "cache_read_input_tokens": 0,
    "cache_creation_input_tokens": 0,
    "calls": 0,
    "cost_usd": 0.0,
}


def get_usage() -> dict[str, float]:
    return dict(_usage)


def reset_usage() -> None:
    for k in _usage:
        _usage[k] = 0


class LLMRefusal(Exception):
    """Model safety-refused. Do not retry, do not escalate."""


def _run(prompt: str, *, system: str, model: str | None, tools: str = "") -> str:
    """One headless Claude Code invocation; returns the result text.

    `tools` is the value for `--tools` ("" disables every built-in tool).
    Transient process/parse failures raise RuntimeError, which the runner's
    step-level retry treats like any other transient error.
    """
    cmd = [
        "claude",
        "-p",
        "--output-format", "json",
        "--model", model or config.DEFAULT_LLM_MODEL,
        "--system-prompt", system,
        "--tools", tools,
        "--no-session-persistence",
    ]
    env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
    proc = subprocess.run(
        cmd,
        input=prompt,
        capture_output=True,
        text=True,
        timeout=_TIMEOUT_S,
        env=env,
        cwd=tempfile.gettempdir(),
    )
    if proc.returncode != 0:
        raise RuntimeError(f"claude -p exited {proc.returncode}: {proc.stderr.strip()[:500]}")
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"claude -p returned non-JSON output: {proc.stdout[:200]}") from e
    if data.get("stop_reason") == "refusal":
        raise LLMRefusal(data.get("result") or "refused")
    if data.get("is_error"):
        raise RuntimeError(f"claude -p error result: {str(data.get('result'))[:500]}")
    # Accumulate token usage from this call.
    u = data.get("usage") or {}
    _usage["input_tokens"] += u.get("input_tokens", 0)
    _usage["output_tokens"] += u.get("output_tokens", 0)
    _usage["cache_read_input_tokens"] += u.get("cache_read_input_tokens", 0)
    _usage["cache_creation_input_tokens"] += u.get("cache_creation_input_tokens", 0)
    _usage["calls"] += 1
    _usage["cost_usd"] += data.get("total_cost_usd") or 0.0
    return data.get("result") or ""


def _extract_json(text: str) -> str:
    return _FENCE_RE.sub("", text.strip())


def parse(prompt: str, schema: type[M], *, system: str = "", model: str | None = None) -> M:
    """One structured-output call; returns a validated instance of `schema`."""
    schema_json = json.dumps(schema.model_json_schema())
    sys_prompt = (
        (system or "You are a precise data-processing assistant.")
        + "\nRespond with ONLY a single JSON object that validates against this"
        + f" JSON Schema — no prose, no markdown fences:\n{schema_json}"
    )
    raw = _run(prompt, system=sys_prompt, model=model)
    try:
        return schema.model_validate(json.loads(_extract_json(raw)))
    except (json.JSONDecodeError, ValidationError) as first_error:
        repair = (
            f"{prompt}\n\nYour previous reply was:\n{raw}\n\n"
            f"It failed validation with: {first_error}\n"
            "Reply again with ONLY a corrected JSON object."
        )
        raw = _run(repair, system=sys_prompt, model=model)
        try:
            return schema.model_validate(json.loads(_extract_json(raw)))
        except (json.JSONDecodeError, ValidationError) as e:
            raise ValueError("model returned no parseable output") from e


def complete(prompt: str, *, system: str = "", model: str | None = None, max_tokens: int = 2048) -> str:
    """Plain text completion. `max_tokens` is kept for signature compatibility;
    Claude Code headless has no per-response token cap flag."""
    del max_tokens
    return _run(prompt, system=system or "You are a helpful assistant.", model=model)


def web_search(prompt: str, *, system: str = "", model: str | None = None, max_searches: int = 8) -> str:
    """Completion with Claude Code's WebSearch tool. There is no hard search
    cap flag; the limit is stated in the system prompt."""
    sys_prompt = (
        (system or "You are a careful web researcher. Cite the source URL for every fact.")
        + f"\nUse at most {max_searches} web searches."
    )
    return _run(prompt, system=sys_prompt, model=model, tools="WebSearch")
