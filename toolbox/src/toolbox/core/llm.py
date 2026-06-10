"""Anthropic client wrapper (port of llm.py, provider swapped per spec §2).

Three entry points:
  * parse(...)      — structured output via client.messages.parse (Pydantic).
  * complete(...)   — plain text completion.
  * web_search(...) — completion with the hosted web_search server tool,
                      handling the `pause_turn` continuation loop.

The SDK already retries 429/5xx with exponential backoff (max_retries below);
we do not hand-roll retry here. A safety refusal is surfaced as LLMRefusal —
callers MUST NOT retry those.

Auth: ANTHROPIC_API_KEY from the environment, or the team key fetched via
core/auth.get_token("anthropic") once connections hold it. No key in the repo.
"""

from __future__ import annotations

from typing import TypeVar

from pydantic import BaseModel

from toolbox.core import config

M = TypeVar("M", bound=BaseModel)

_MAX_RETRIES = 4
_WEB_SEARCH_TOOL = {"type": "web_search_20260209", "name": "web_search"}
_MAX_CONTINUATIONS = 5


class LLMRefusal(Exception):
    """Model safety-refused. Do not retry, do not escalate."""


def _client():
    import anthropic

    return anthropic.Anthropic(max_retries=_MAX_RETRIES)


def parse(prompt: str, schema: type[M], *, system: str = "", model: str | None = None) -> M:
    """One structured-output call; returns a validated instance of `schema`."""
    client = _client()
    resp = client.messages.parse(
        model=model or config.DEFAULT_LLM_MODEL,
        max_tokens=4096,
        system=system or "You are a precise data-processing assistant.",
        messages=[{"role": "user", "content": prompt}],
        output_format=schema,
    )
    if resp.stop_reason == "refusal":
        raise LLMRefusal(getattr(resp.stop_details, "explanation", "") or "refused")
    if resp.parsed_output is None:
        raise ValueError("model returned no parseable output")
    return resp.parsed_output


def complete(prompt: str, *, system: str = "", model: str | None = None, max_tokens: int = 2048) -> str:
    client = _client()
    resp = client.messages.create(
        model=model or config.DEFAULT_LLM_MODEL,
        max_tokens=max_tokens,
        system=system or "You are a helpful assistant.",
        messages=[{"role": "user", "content": prompt}],
    )
    if resp.stop_reason == "refusal":
        raise LLMRefusal(getattr(resp.stop_details, "explanation", "") or "refused")
    return "".join(b.text for b in resp.content if b.type == "text")


def web_search(prompt: str, *, system: str = "", model: str | None = None, max_searches: int = 8) -> str:
    """Completion with the hosted web_search tool. The server runs its own
    sampling loop; on `pause_turn` we re-send to resume (per API docs) up to
    _MAX_CONTINUATIONS times."""
    client = _client()
    tool = dict(_WEB_SEARCH_TOOL, max_uses=max_searches)
    messages: list[dict] = [{"role": "user", "content": prompt}]
    for _ in range(_MAX_CONTINUATIONS):
        resp = client.messages.create(
            model=model or config.DEFAULT_LLM_MODEL,
            max_tokens=4096,
            system=system or "You are a careful web researcher. Cite the source URL for every fact.",
            messages=messages,
            tools=[tool],
        )
        if resp.stop_reason == "refusal":
            raise LLMRefusal(getattr(resp.stop_details, "explanation", "") or "refused")
        if resp.stop_reason == "pause_turn":
            messages = [messages[0], {"role": "assistant", "content": resp.content}]
            continue
        return "".join(b.text for b in resp.content if b.type == "text")
    return "".join(b.text for b in resp.content if b.type == "text")
