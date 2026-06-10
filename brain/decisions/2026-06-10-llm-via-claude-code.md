# Decision: harness LLM calls run through Claude Code, not the Anthropic API

**Date:** 2026-06-10 · **Source:** internal decision (Armaan, in session).

## What was decided

`toolbox/core/llm.py` shells out to **headless Claude Code** (`claude -p
--output-format json`) instead of calling the Anthropic API with an API key.
Usage bills to the team's Claude subscription. The `ANTHROPIC_API_KEY` slot
was removed from `credentials/.env`; no Anthropic key is needed anywhere in
the harness.

## How it works

- Same three entry points (`parse`, `complete`, `web_search`) with unchanged
  signatures — primitives and tests needed no changes (39 offline tests green;
  live structured-parse verified end-to-end).
- Structured output: schema embedded in the system prompt, strict-JSON reply,
  Pydantic validation with one repair retry.
- `web_search()` uses Claude Code's WebSearch tool (`--tools WebSearch`)
  instead of the hosted web_search server tool.
- Calls run from the temp dir with `--no-session-persistence` so the repo's
  CLAUDE.md / MCP servers don't leak into harness prompts, and
  `ANTHROPIC_API_KEY` is stripped from the subprocess env so usage can never
  silently flip to API billing.

## Tradeoffs accepted

- Requires a logged-in `claude` CLI on the machine running flows (cron/CI
  hosts must have the subscription auth set up).
- Subject to the subscription's rate limits (5-hour usage windows) rather
  than API rate limits — a very large flow can exhaust the window; the
  runner's clean-fail-and-resume handles it.
- No per-response `max_tokens` cap and no token-level cost accounting.
- Each call spawns a CLI process (~1–2s overhead vs an HTTP call) — fine at
  outreach scale.
