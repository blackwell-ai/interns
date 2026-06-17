# TOOLBOX.md — the primitive contract

The toolbox is the **only maintained code** in this repo (spec §5). Everything
else — flows, skills, runs — is data. Agents compose flows by reading each
primitive's `TOOL.md`, never its source.

## Vocabulary

A **primitive** is a small tested CLI doing one job. A **flow** is a
declarative step list (`flow.yaml`) combining primitives, executed by
`core/runner.py`. A **skill** is a remembered flow (`skills/<name>/`). A
**run** is one execution with its own folder (`runs/<id>/`). The **ledger** is
the Supabase record of irreversible actions.

## Setup

```bash
cd toolbox && uv sync          # install
uv run toolbox auth login      # once per person: Google sign-in (keychain)
uv run toolbox auth connect gmail      # second consent: gmail.send for the SENDING account
uv run toolbox auth connect clay       # paste API key (use --org-shared for team keys)
# LLM steps need no key: they run headless Claude Code (`claude -p`) under the
# machine's logged-in Claude subscription.
uv run toolbox run <skill> [-i key=value] [--yes]
uv run toolbox resume <run_id>
uv run toolbox fork <src> <dst>
```

## The contract (every primitive obeys all 8)

1. **File in, file out.** Invoked as a CLI with `--in/--out` paths inside the
   run folder (cwd = run folder, so plain filenames work). Primitives never
   import each other; only the runner sequences them.
2. **`--dry-run` on anything irreversible.** Does everything except the
   irreversible part; writes what *would* happen to `runs/<id>/dryrun/`.
3. **Ledger check on anything irreversible — non-removable.** Send-class
   primitives claim the recipient (`core/ledger.py` → `claim_contact` RPC →
   UNIQUE constraint) *before* acting. Lives inside the primitive + the
   database, so no generated flow can compose it away.
   **Two-table caveat:** harness send-class primitives record to `contacted`,
   but the standalone volume sender (`skills/autonomous-outreach/send_fast.py`)
   runs on the service key and records to `suppression` instead (it can't set
   `auth.uid()` for `contacted.sent_by`). So contact history is split across
   both tables. To dedup a list, call the `check_contact` RPC (it unions both)
   or query both tables — never `contacted` alone. See
   `harness/learnings/07-ledger-split-contacted-vs-suppression.md`.
4. **Concurrency built in.** Network primitives take `--concurrency N` and
   fan out by default. No internal throttles or caps. Transient errors
   (429/5xx/connection) retry with exponential backoff; **hard quota errors
   fail the step cleanly** instead of retrying forever.
5. **Structured events** to `runs/<id>/events.jsonl` via `core/events.py`
   (`TOOLBOX_RUN_DIR` env). `step.completed` (runner-level) is the
   authoritative "done" signal for resume.
6. **Auth via `core/auth.py` only.** No env files, no secrets in argv, nothing
   logged. `get_token(provider)` fetches at runtime from Supabase.
7. **`TOOL.md` per primitive** — purpose, subcommands, file schemas,
   connection needed, dry-run behavior, failure modes.
8. **Offline smoke test per primitive** in `tests/test_smoke.py` (all network
   mocked), runnable by the `test.smoke` process step and by
   `uv run pytest -m "not integration"`.

**New-primitive bar:** writing one requires a sentence of justification in the
calling skill's SKILL.md ("no existing primitive can X").

## Current primitives

| Step | What it does | Connection |
|---|---|---|
| `gmail.send` / `gmail.replies` / `gmail.bounces` | send mail; read replies/bounces | gmail (oauth) |
| `domains.source` | web-search domain sourcing (Claude Code WebSearch) | Claude subscription (`claude` CLI login) |
| `findemail.find` / `findemail.find-exec` | name+domain → verified work email; or domain → decision-maker + email (the headless lead-enrichment step) | hunter or findymail (API key) |
| `verify.check` | MX/DNS deliverability | — |
| `compose.render` | template render + LLM personalization | Claude subscription (optional) |
| `fetch.urls` | pull web sources → pages.jsonl | — |
| `llm.filter` | LLM relevance filter over JSONL | Claude subscription |
| `inbox.file` | file findings as inbox/queue/ tasks | — |
| `throttle.wait` | explicit pacing (in NO default chain) | — |

Lead enrichment: **Clay cannot be driven fully headlessly** — it has no API to
create a table or configure its enrichment recipe (the waterfall lives in the
UI; "Clay doesn't have a traditional API"). So the headless enrichment step is
`findemail`, which calls the same underlying providers Clay waterfalls across
(Hunter, Findymail) via their REST APIs — one key, zero manual setup. A Clay
CSV export passed via `-i` remains a valid input too. The former
`apollo`/`storeleads` primitives were removed under the Clay decision
(`brain/decisions/2026-06-10-clay-is-the-lead-workbench.md`).

**Process primitives** (removable lines like any other): `plan.write`,
`clarify.ask`, `test.smoke`, `test.dryrun`, `canary.run`, `report.write`.
See `skills/PROTOCOL.md` for how flows compose them and the default chains.

## Tests

```bash
uv run pytest -m "not integration"   # offline smoke + unit (always green)
uv run pytest -m integration         # needs `supabase start` (Docker)
```

The four correctness tests the harness lives on: claim race (exactly one
winner), crash-and-resume (zero duplicate sends), two-person overlap (zero
duplicates across people), dry-run grading (no empty personalization).
