# Automation Harness — Build Plan v1

**Repo:** `blackwell-ai/interns` · **Date:** 2026-06-10 · **Status:** draft for team review
**Implements:** `automation-harness-spec.md` (Spec v0.2). Read the spec first — this document does not restate *what* we're building or *why*; it specifies *how* and *in what order*, with concrete technology choices, file-by-file work items, tests, and a self-critique of the risky parts.

This plan is written to be readable by someone who does not already know Python, Supabase, or OAuth. Where a term of art appears for the first time it is defined inline.

---

## 0. Reading order

1. **§1 Tech stack** — the concrete tools we commit to, and why (with the alternatives we rejected).
2. **§2 Repo layout to create** — the directories and files that don't exist yet.
3. **§3 Foundational contracts** — the exact shape of a primitive, a run folder, the events stream, and the file schemas. Everything in §5+ depends on these.
4. **§4 Phase 0 → M4** — the actual build, phase by phase, each task with *what / why / how / files / tests / done-when*.
5. **§5 Testing strategy** — the four correctness tests the whole project lives or dies on.
6. **§6 Security review** — mapped to the company's security requirements in `/CLAUDE.md`.
7. **§7 Self-critique** — where the spec is under-specified or wrong, and what we do about it.
8. **§8 Proposed answers to the spec's open questions (§12).**

---

## 1. Tech stack (decisions, with rationale)

The spec writes every shared module as `*.py` (`runner.py`, `core/auth.py`, `gmail.py`). So the toolbox is **Python**. The rest follows from "primitives are small CLIs with `--in/--out`, parallel by default, talking to a Postgres-backed Supabase."

| Concern | Choice | Why this and not the alternative |
|---|---|---|
| Language | **Python 3.12** | Spec assumes it; the port targets (`gmail.py`, `template_render.py`) are Python. |
| Dependency/venv manager | **`uv`** | One fast tool for virtualenv + lockfile. Alternative `poetry` is slower and heavier; `pip` alone gives no lockfile (no reproducibility). |
| CLI framework | **Typer** | Each primitive is a CLI with subcommands (`apollo enrich`, `gmail send`) and typed `--in/--out/--concurrency` flags. Typer generates `--help` and parses types for free. Raw `argparse` works but is verbose; Click is Typer without the type inference. |
| Data validation | **Pydantic v2** | The "file in, file out" contract only holds if a CSV/JSON written by step A is *exactly* what step B expects. Pydantic models are the schema; they validate on read and serialize on write. This is the modern replacement for the spec's `csv_schema.py`. |
| HTTP | **httpx** (async) | Async lets one primitive fan out N concurrent requests (the `--concurrency` flag) without threads. `requests` is sync-only. |
| Retry/backoff | **tenacity** | Spec §9 mandates "reactive backoff, never proactive throttle." Tenacity gives declarative exponential backoff on transient errors (429/5xx) without hand-rolling sleep loops. |
| Token storage (laptop) | **`keyring`** | Stores the Supabase session token in the OS keychain (macOS Keychain), never in the repo. Spec §8 requires exactly this. |
| LLM | **Anthropic SDK** (`anthropic`) | Spec §2: provider swapped to Anthropic. Default model for personalization: **`claude-haiku-4-5`** (cheap, fast, fine for a one-paragraph hook); escalate a flow to **`claude-sonnet-4-6`** if a segment needs better copy. Model id is a flow input, not hardcoded. |
| Database / auth / functions | **Supabase** (hosted) | Spec §7–8 names it. Postgres gives us the `UNIQUE` constraint that *is* the cross-person guarantee. Auth (GoTrue) gives Google sign-in. Edge Functions (Deno/TypeScript) hold the OAuth client-secret server-side. |
| DB migrations + local test stack | **Supabase CLI** | `supabase start` runs the whole stack (Postgres + Auth + Edge runtime) locally in Docker, so we test the race condition and RLS offline before touching the hosted project. |
| Testing | **pytest** + **pytest-asyncio** | Smoke tests (offline, per primitive) and integration tests (against the local Supabase stack). |
| Lint/format | **ruff** | One tool for both, fast. |
| YAML parsing (flows) | **ruamel.yaml** | Preserves comments/order when the runner or a fork edits a `flow.yaml`. PyYAML drops comments. |

**One non-obvious call: the contact-claim is a Postgres function, not client-side table writes.** The spec describes the claim as `INSERT … ON CONFLICT DO NOTHING` issued from the primitive. We instead wrap it in a **`SECURITY DEFINER` Postgres function** `claim_contact(channel, recipient)` (see §3.4). Reasoning in §7, item 3 — short version: it keeps the invariant and the suppression check atomic and on the server, so Row-Level Security never has to expose one person's contacts to another just to make the conflict check work.

---

## 2. Repo layout to create

Everything below is **new** unless marked. Folders that exist (`brain/`, `inbox/`) are untouched except for the charter/doc edits in M1/M4.

```
toolbox/                      # the only maintained code (NEW)
  pyproject.toml              # uv project: deps, console-script entry points
  uv.lock
  TOOLBOX.md                  # the primitive contract, written for agents (spec §5)
  core/
    __init__.py
    runner.py                 # executes a flow.yaml top-to-bottom; pause/resume
    auth.py                   # get_token(provider) → fresh token via Supabase
    ledger.py                 # claim()/mark_sent()/mark_failed()/is_suppressed()
    events.py                 # append structured events to runs/<id>/events.jsonl
    io.py                     # atomic read/write of run-folder artifacts (CSV/JSON)
    llm.py                    # Anthropic client wrapper
    models.py                 # Pydantic models for every artifact schema
  primitives/
    gmail/        (TOOL.md, cli.py, send.py, read.py, tests/)
    apollo/       (TOOL.md, cli.py, tests/)
    storeleads/   (TOOL.md, cli.py, tests/)
    domains/      (TOOL.md, cli.py, tests/)
    verify/       (TOOL.md, cli.py, tests/)
    compose/      (TOOL.md, cli.py, tests/)
    throttle/     (TOOL.md, cli.py, tests/)   # exists; in no default chain (spec §9)
  process/                    # process primitives (spec §5)
    plan_write.py  clarify_ask.py  test_smoke.py  test_dryrun.py
    canary_run.py  report_write.py
  tests/
    integration/              # against local supabase stack (race, resume, two-person)

skills/                       # upgraded (exists today as just README.md)
  PROTOCOL.md                 # how agents compose/fork flows (spec §6)
  INDEX.md                    # one line per registered skill
  apollo-cold-email/          # the first real skill (M2)
    SKILL.md  flow.yaml  inputs.yaml

runs/                         # one folder per execution (NEW, gitignored)
  .gitignore                  # ignore everything here

supabase/                     # backbone (NEW)
  config.toml
  migrations/                 # 0001_auth.sql, 0002_connections.sql, 0003_ledger.sql …
  functions/
    token-refresh/index.ts    # exchanges session → fresh provider token
    oauth-connect/index.ts    # completes Gmail/provider OAuth, writes connections row
```

**Deletions** (staged across M1/M4, never in one commit without rotation — see §6): `credentials/` and `agents/outreach/contacted.md` (the latter doesn't exist yet as a file — the charter references it; we delete the *reference*).

---

## 3. Foundational contracts

These four sub-sections are the spine. Get them wrong and every primitive inherits the bug.

### 3.1 The run folder

Every execution gets `runs/<run_id>/`. `run_id` is `<skill>-<UTC-timestamp>-<short-random>` (timestamp+random because the runtime has no `Date.now()`/`random` inside workflow scripts, but the *runner is a normal Python process*, so `datetime.utcnow()` + `secrets.token_hex(3)` is fine here).

```
runs/apollo-cold-email-20260610T1400Z-a1b2c3/
  flow.resolved.yaml     # the flow with {{inputs}} substituted — the audit record
  inputs.yaml            # the actual inputs used
  events.jsonl           # append-only structured event log (§3.3)
  ledger.jsonl           # local mirror of this run's claims (for crash-safe resume)
  status.json            # {step_index, state: running|paused|done|failed, heartbeat}
  domains.csv apollo.csv verified.csv outbox.csv   # step artifacts
  dryrun/                # what send-class steps *would* have done
  report.md             # written by report.write
```

**Atomic writes (critical for resume).** `io.py` writes every artifact to `name.csv.tmp` then `os.rename()` to `name.csv`. Rename is atomic on POSIX, so a crash never leaves a half-written CSV that resume mistakes for complete. A step is "done" only when its `out` artifact exists *and* `events.jsonl` has its `step.completed` event.

### 3.2 The primitive contract (codifies spec §5, the 8 rules)

Each work primitive is a Typer CLI exposing subcommands. Skeleton every primitive follows:

```python
# primitives/apollo/cli.py
import typer
from toolbox.core import io, events, auth
app = typer.Typer()

@app.command()
def enrich(in_: str = typer.Option(..., "--in"),
           out: str = typer.Option(..., "--out"),
           roles: str = "",
           concurrency: int = 20,
           dry_run: bool = typer.Option(False, "--dry-run")):
    rows = io.read_csv(in_, model=models.Domain)        # validated on read
    token = auth.get_token("apollo")                     # never from env/argv
    results = asyncio.run(_enrich_all(rows, roles, token, concurrency))
    if dry_run:
        io.write_json(f"{run}/dryrun/apollo.json", results); return
    io.write_csv(out, results, model=models.Contact)     # validated on write
    events.emit("step.completed", primitive="apollo.enrich", count=len(results))
```

The 8 rules from spec §5, made concrete:

1. **File in, file out** — `--in/--out` are paths inside the run folder. Primitives `import` only `toolbox.core`; never each other. The **runner** is the only sequencer.
2. **`--dry-run` on anything irreversible** — does everything except the irreversible call, writes the would-be result to `runs/<id>/dryrun/`.
3. **Ledger check on anything irreversible (non-removable)** — send-class primitives call `ledger.claim()` (§3.4) *before* the side effect. This lives in the primitive + a DB constraint, so no minimal flow can skip it.
4. **Concurrency built in** — `--concurrency N`, async fan-out, **no internal throttle/cap**. Transient errors (HTTP 429/5xx, connection resets) retry via tenacity: `wait_exponential(multiplier=1, max=60), stop_after_attempt(6)`. A hard quota error (e.g. Gmail daily cap) is *not* transient — it surfaces as a failed step with a clear message, not an infinite retry (§7 item 6).
5. **Structured events** — every primitive emits to `events.jsonl` via `events.emit()`.
6. **Auth via `core/auth.py` only** — no `.env`, no secrets in argv (argv is visible in `ps`), nothing logged.
7. **`TOOL.md` per primitive** — purpose, subcommands, in/out schemas, connection needed, dry-run behavior, failure modes. Agents compose by reading `TOOL.md`, never the source.
8. **Offline smoke test per primitive** — `tests/test_smoke.py` runs with network mocked; `test.smoke` runs all of them for the primitives a flow uses.

### 3.3 The events stream

One JSON object per line in `events.jsonl`. Minimum schema:

```json
{"ts":"2026-06-10T14:00:03Z","run_id":"...","step_index":2,"primitive":"apollo.enrich","event":"step.completed","level":"info","count":812}
```

Event types: `run.started`, `step.started`, `step.completed`, `step.failed`, `step.paused`, `claim.skipped` (recipient already contacted), `send.ok`, `send.failed`, `run.finished`. This is the spec's ported `observability.py`. `report.write` reads this file to build the report; the runner reads it on resume to know the last completed step.

### 3.4 The ledger contract (the heart — spec §7)

Tables (migration `0003_ledger.sql`):

```sql
create table contacted (
  id uuid primary key default gen_random_uuid(),
  channel      text not null,
  recipient    text not null,          -- canonical: lowercased, trimmed
  status       text not null check (status in ('claimed','sent','failed')),
  sent_by      uuid not null references auth.users(id),
  skill        text, run_id text, message_hash text,
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (channel, recipient)          -- THE invariant, enforced by Postgres
);
create table suppression (
  channel text, recipient text, reason text,
  created_at timestamptz default now(),
  primary key (channel, recipient)
);
```

The claim is a **`SECURITY DEFINER` function** so the suppression check + insert are atomic and server-side:

```sql
create function claim_contact(p_channel text, p_recipient text,
                              p_skill text, p_run_id text)
returns text  -- 'claimed' | 'skipped' (already contacted) | 'suppressed'
language plpgsql security definer as $$
declare did_insert int;
begin
  if exists (select 1 from suppression
             where channel=p_channel and recipient=lower(trim(p_recipient))) then
    return 'suppressed';
  end if;
  insert into contacted(channel, recipient, status, sent_by, skill, run_id)
  values (p_channel, lower(trim(p_recipient)), 'claimed', auth.uid(), p_skill, p_run_id)
  on conflict (channel, recipient) do nothing;
  get diagnostics did_insert = row_count;
  return case when did_insert = 1 then 'claimed' else 'skipped' end;
end $$;
```

`core/ledger.py` exposes:
- `claim(channel, recipient) -> 'claimed'|'skipped'|'suppressed'` — calls the function; on `'claimed'` also appends to the local `ledger.jsonl` mirror *before* the send.
- `mark_sent(channel, recipient, message_hash)` / `mark_failed(...)` — update the row's status.
- The **claim pattern** in a send primitive: `claim` → if not `'claimed'`, emit `claim.skipped`/`suppressed` and continue to next recipient → else send → `mark_sent` (or `mark_failed` on a permanent bounce). `allow_recontact: true` routes through a separate `force_claim` that updates instead of skipping, and logs loudly.

**Stale-claim release — corrected from the spec.** The spec says "release claims older than an hour." That is wrong for paused runs (a canary gate can hold claims for hours legitimately). Correction (§7 item 2): `status.json` writes a `heartbeat` timestamp every 30s while a run is *actively executing a step*; paused runs explicitly mark themselves paused. The startup reaper releases a `claimed` row only if its `run_id` is `failed`/abandoned (no heartbeat for >10 min **and** not in `paused` state). This prevents both permanent blocking (crash) and accidental release (long legit run).

---

## 4. Build phases

Phase 0 is new (foundational scaffolding the spec assumes). M0–M4 map 1:1 to spec §11.

### Phase 0 — Scaffolding (½ day)

| Task | How | Done when |
|---|---|---|
| 0.1 `uv` project | `uv init toolbox`; add deps (§1); define console-scripts so `apollo`, `gmail`, etc. are runnable | `uv run apollo --help` works |
| 0.2 `core/io.py`, `core/events.py`, `core/models.py` | Atomic CSV/JSON read/write (§3.1); Pydantic models `Domain`, `Contact`, `VerifiedContact`, `OutboxRow`; `events.emit()` | unit tests green |
| 0.3 Local Supabase | `supabase init`; `supabase start` (Docker) | local Postgres reachable; `supabase status` healthy |
| 0.4 `runs/.gitignore`, `pyproject` lint/test config | — | `uv run pytest` and `ruff check` run clean on empty suite |

### M0 — Supabase backbone

*Spec done-when: two people's sessions each fetch a Gmail token for their own account; a simultaneous double-claim admits exactly one winner.*

| Task | How | Files |
|---|---|---|
| M0.1 Migrations | `0001_auth.sql` (enable Google provider config notes), `0002_connections.sql` (per-person provider creds, RLS so `auth.uid() = user_id`), `0003_ledger.sql` (§3.4 tables + `claim_contact` + suppression) | `supabase/migrations/*` |
| M0.2 RLS policies | `connections`: select/insert/update only own rows. `contacted`/`suppression`: writes go through `claim_contact`/RPCs only (no direct client insert); reads limited to own `sent_by` (cross-person conflict still works because it's enforced in the function, not via reading others' rows). | in migrations |
| M0.3 `oauth-connect` edge function | Completes a **second, separate** Google OAuth consent requesting `gmail.send`+`gmail.readonly` scopes (distinct from sign-in — see §7 item 5), exchanges code→refresh token, writes encrypted `connections` row. Client-secret lives only here. | `supabase/functions/oauth-connect/` |
| M0.4 `token-refresh` edge function | Given the caller's session, exchanges the stored refresh token → fresh access token. Refresh secret never leaves the server. | `supabase/functions/token-refresh/` |
| M0.5 `core/auth.py` | `login()` opens browser for Supabase Google sign-in, stores session in OS keychain via `keyring`. `get_token(provider)` calls `token-refresh`. `connect(provider)` drives `oauth-connect`. | `toolbox/core/auth.py` |
| M0.6 `core/ledger.py` | `claim/mark_sent/mark_failed/is_suppressed` over the RPCs (§3.4) | `toolbox/core/ledger.py` |
| M0.7 `toolbox auth login` CLI | Typer command wrapping `auth.login()` | `toolbox/core/cli.py` |

**M0 tests (integration, against local stack):**
- `test_two_people_tokens`: seed two `auth.users`; each session fetches its own Gmail token; assert person A can't read person B's `connections` row (RLS).
- `test_claim_race` (**the keystone test**): spawn 20 asyncio tasks calling `claim_contact('email','c@x.com')` concurrently; assert **exactly one** returns `'claimed'`, 19 return `'skipped'`, and `contacted` has exactly one row.
- `test_suppressed_skips`: insert suppression row; `claim` returns `'suppressed'`, no `contacted` row created.

### M1 — Toolbox + runner + protocol

*Spec done-when: all smoke tests pass offline; a fresh Claude Code session scaffolds a toy skill as a `flow.yaml` composition unprompted.*

**Port (from `email_automation_pipeline`, auth/provider swapped):**

| Primitive | Ported from | Changes |
|---|---|---|
| `gmail` (send side) | `gmail.py` | MIME build + send kept; auth → `core/auth.get_token("gmail")`; **claim before send**; per-recipient `mark_sent/failed` |
| `compose` | `template_render.py`, `first_name.py` | render + LLM personalization via `core/llm.py` (Anthropic) |
| `verify` | `verifiers/` | MX/DNS + mailbox checks; async |
| `domains` | `source_domains` internals | web-search domain sourcing |
| (`csv_schema`, `observability`, `llm`) | folded into `core/models.py`, `core/events.py`, `core/llm.py` | not standalone primitives |

**Drop from port (spec §2):** `rate_limit.py`, Phase-A ramp, `dedup.py`'s file-locking (idea survives as the Supabase ledger).

**New primitives:** `apollo` (people/company search + enrichment), `storeleads` (store search). Each: `TOOL.md`, Typer CLI, async fan-out, offline smoke test with HTTP mocked (`respx`).

**The runner — `core/runner.py` (the most important new code):**
- Parse `flow.yaml` (ruamel), resolve `{{inputs}}` from `inputs.yaml`, write `flow.resolved.yaml`.
- Execute steps top-to-bottom: for each, shell out to the primitive CLI with resolved args, stream its events, update `status.json` (index + heartbeat).
- **Resume:** on start, read `status.json` + `events.jsonl`; skip steps already `step.completed`; for a partially-done send step, replay `ledger.jsonl` so already-sent recipients are skipped (the local mirror is why a crash mid-send doesn't double-send — §7 item 1).
- **Pause/resume protocol:** `clarify.ask` and `canary.run` exit with a distinct "paused" code; runner writes `state: paused` and stops. A human acts, then `toolbox resume <run_id>` continues. (Heartbeat reaper ignores paused runs — §3.4.)
- A step may be `python: steps/foo.py` for trivial glue; if it grows, that's the signal to promote to a primitive (spec §6/§12.5).

**Process primitives:** `plan.write`, `clarify.ask`, `test.smoke`, `test.dryrun`, `canary.run`, `report.write` (behaviors per spec §5).

**Docs:** `TOOLBOX.md`, `skills/PROTOCOL.md`, `skills/INDEX.md`.

**Charter/rule edits (spec §11 M1):**
- `agents/outreach/AGENT.md`: route automation requests through the protocol; **delete the ≤25/day guardrail and the warmup language** (spec §9); replace `contacted.md` references with "the ledger (Supabase, via the harness)"; note gogcli retires in favor of the `gmail` primitive (spec §12.4).
- `/CLAUDE.md`: replace "Source credentials from `credentials/.env`" with `toolbox auth login`; keep the rest.

**M1 tests:** every primitive's offline smoke test green; a runner unit test executes a 3-step toy flow end-to-end with all network mocked, then a kill-and-resume test asserts completed steps are skipped.

### M2 — First skill end to end

Build `skills/apollo-cold-email/` (`SKILL.md` + the `flow.yaml` from spec §6 + `inputs.yaml`) and run it on a **real** segment from `brain/company/targets.md` (agentic-commerce / DTC), sending from **armaan.priyadarshan.29@dartmouth.edu**.

*Spec done-when:* ≤1 clarification round; 1,000-contact flow completes same-day; **kill mid-send → rerun → zero duplicates**; **two people's overlapping runs → zero duplicates**; skill registered with report.

**M2 tests = §5.** Run the live two-person and resume tests here for real (a small live batch, plus the local-stack simulation for the full 1,000-scale race).

### M3 — Fork proof

Fork `apollo-cold-email` → a new segment (e.g. yoga studios), delete `clarify.ask` + `canary.run` lines, run.
*Done when:* fork ships in <1 min human time, zero toolbox edits, and `events.jsonl` shows the removed steps **did not run** (assert absence of their `step.started` events). The ledger silently skips any overlap with the first run.

### M4 — Brain-breadth proof + cleanup

- **Non-outreach flow** proving this is brain infra, not an outreach feature: the **researcher** watchlist sweep as a flow — `fetch sources → llm filter → file inbox tasks` — using the same runner/primitives, writing tasks into `inbox/queue/` (per `agents/researcher/AGENT.md`). New primitive only if no existing one fits (one-sentence justification rule).
- **Reply detection:** finish the `gmail` read side; positive replies become `inbox/queue/` tasks with full context (per the outreach charter step 6).
- **Cleanup / migration (spec §8):** delete `credentials/`; **rotate every secret that ever lived in `credentials/.env`** at the provider (deleting from the file does not un-leak from git history — §6); update remaining doc references.

---

## 5. Testing strategy (the four tests the project lives on)

Per `/CLAUDE.md`: tests cover edge cases (null fields, empty enrichment, provider 0-results, concurrent writes). Two classes of tests, with different lifecycles:

- **Durable smoke tests** (`primitives/*/tests/`) are *architecture*, not throwaway — `test.smoke` runs them. They stay. (This is the exception to the global "clean up tests after the feature" rule, which still applies to scratch/scaffolding test harnesses written while building.)
- **Integration tests** (`toolbox/tests/integration/`) run against the local Supabase stack.

The four that matter most:

1. **Claim race** (M0) — 20 concurrent claims, exactly one winner. If this fails, the cross-person guarantee is a lie.
2. **Crash-and-resume** (M1/M2) — kill a run mid-send, rerun; zero duplicate sends; completed steps skipped. Exercises atomic writes + `ledger.jsonl` mirror + runner resume.
3. **Two-person overlap** (M2) — two distinct JWTs, overlapping recipient lists, runs fired concurrently against one stack; union sent exactly once. This is the spec §7 scenario, tested without two laptops.
4. **Dry-run grading** (M2) — `test.dryrun` renders 10 messages, asserts no empty `{{personalization_hook}}` against `SKILL.md#acceptance-checks` (the bug the worked example §10 catches).

Edge cases each primitive smoke test must cover: empty input CSV; a row with a null/blank email; provider returns 0 results; provider returns a 429 (assert backoff, not crash); a malformed row (assert Pydantic rejects it, doesn't silently pass).

---

## 6. Security review (mapped to `/CLAUDE.md` security requirements)

- **Server-side authority.** The contact invariant and suppression check live in a Postgres `SECURITY DEFINER` function + a `UNIQUE` constraint — not in client code that a buggy generated flow could skip. Token refresh and the OAuth client-secret live in edge functions; laptops never hold provider client-secrets. ✅
- **Secrets management.** No `.env` in the repo after M4. Session token in OS keychain; provider refresh tokens encrypted at rest in `connections` with RLS. Secrets never in argv (visible in `ps`), never logged, never in events/reports. ✅
- **Input/output handling.** Pydantic validates every artifact at each step boundary (treats CSV as data, never code). Recipients canonicalized (`lower(trim())`) before the uniqueness check so casing can't bypass dedup. Error messages in reports stay vague about internals; full stack traces only in `events.jsonl` server-side-style (local run folder, not surfaced to recipients). ✅
- **The rate-limit tension, named honestly.** The company's general security guidance favors rate-limiting sensitive actions; spec §9 deliberately deletes throttles based on empirical evidence (months of multi-thousand/day sends, zero repercussions). We honor the spec's speed posture **and** keep the safety valves it already allows: reactive backoff on transient errors, a non-default `throttle` primitive, and — added here — treating a hard provider quota error (Gmail daily cap, 429 quotaExceeded) as a *clean failed step with a clear message*, not an infinite retry and not a silent drop. Speed by default; graceful, visible failure at the provider's hard wall.
- **Git-history rotation (M4).** Deleting `credentials/.env` does not remove it from history. The migration **must** rotate every secret at its provider (Apollo key, StoreLeads key, Google OAuth client-secret, `GOG_KEYRING_PASSWORD`). Optionally scrub history with `git filter-repo`, but rotation-at-provider is the authoritative fix and the spec's stated requirement.

---

## 7. Self-critique (where the spec is thin or wrong — and the fix)

Adopting the code-reviewer persona against both the spec and the first draft of this plan:

1. **"Local mirror for resume" is under-specified and is where double-sends hide.** If `gmail.send` claims → sends → crashes *before* `mark_sent`, the row is `claimed` and the runner must not resend on resume. **Fix:** append to `runs/<id>/ledger.jsonl` the moment a send's Gmail API call returns a message id, *before* the Supabase `mark_sent` round-trip. Resume replays this file first. The DB is the source of truth for *cross-person*; the local mirror is the source of truth for *did-this-run-already-send-this-one*.
2. **The spec's "release claims older than an hour" is a latent double-send bug.** A canary-gated run legitimately holds claims for hours. Auto-releasing at 1h would let a second run re-claim and re-send. **Fix:** heartbeat-based reaper that only releases claims from runs with no heartbeat AND not in `paused` state (§3.4).
3. **RLS vs. the conflict check.** If reads are restricted to your own `sent_by` rows (correct, for privacy), a naive client `INSERT … ON CONFLICT` still works (the DB enforces uniqueness regardless of what you can *read*), but you'd be tempted to "check first then insert," which is a race. **Fix:** the single-statement `claim_contact` function — no check-then-act, no need to read others' rows, suppression folded in atomically.
4. **Sign-in ≠ Gmail-send authorization.** Supabase Google sign-in yields an identity session; it does *not* by itself grant `gmail.send`. The spec's §8 conflates the two. **Fix:** two OAuth flows — sign-in (identity) and `oauth-connect` (a separate consent requesting Gmail scopes, refresh token stored in `connections`). M0.3 builds the second explicitly.
5. **gogcli retirement has a dependency the charter still relies on.** `brain/company/connections.md` says the Dartmouth account is only reachable via gogcli, and the claude.ai connectors only see the personal gmail. So the `gmail` primitive's `oauth-connect` must obtain Gmail scopes for **armaan.priyadarshan.29@dartmouth.edu** directly. **Fix:** M0.3 connects the Dartmouth account; only after that send-path is proven (M2) do we retire gogcli from agent use (spec §12.4) — not before.
6. **"No throttles anywhere" can turn a recoverable quota event into a dead run.** Backoff retries a 429 forever if it's a *daily* quota, not a transient burst. **Fix:** classify errors — transient (retry with backoff) vs. hard quota/auth (fail the step cleanly with a clear message and a partial report). Already folded into rule 4 of §3.2 and §6.
7. **"Files are the interface" needs a completion marker or resume is unsafe.** Existence of `out.csv` ≠ done (could be mid-write). **Fix:** atomic tmp-then-rename (§3.1) + the `step.completed` event as the authoritative "done" signal.
8. **Scope risk: M1 is large.** Porting four primitives, writing two, building the runner and six process primitives, and editing charters is a lot for one milestone. **Mitigation:** land the runner + `gmail` + `compose` + `clarify.ask`/`report.write` first (enough for a trivial end-to-end), then fill in `apollo`/`storeleads`/`verify`/`domains` and the remaining process primitives. The "fresh session scaffolds a toy skill" done-when only needs the runner + a couple of primitives.

---

## 8. Proposed answers to the spec's open questions (§12)

1. **Cross-channel identity** — v1: channels independent (`(channel, recipient)` key). Defer resolution to a later brain capability. *Agree with spec.*
2. **Recontact policy** — keep `allow_recontact: false` default + loud override for v1. Don't add `sequence_step` until real follow-up sequences are built (YAGNI). *Agree with spec.*
3. **Supabase hosting** — hosted project (fast default). Org-shared provider keys (team Apollo) live as org-scoped `connections` rows readable by all members via RLS; the Google OAuth client-secret and refresh logic live *only* in edge functions.
4. **gogcli** — retire from agent use *after* the `gmail` primitive proves the Dartmouth send path in M2 (see §7 item 5), not at M1.
5. **Runner ergonomics** — YAML steps + a `python:` escape hatch. Add a lint in `report.write` that flags any run whose `python:` script exceeded ~40 lines, as evidence a primitive is missing (spec §12.5).

---

## 9. Sequencing summary

```
Phase 0  scaffolding (uv, core/io+events+models, local supabase)        ½ day
M0       migrations + auth + ledger + claim_contact + the race test     2–3 days
M1       runner + ported/new primitives + process primitives + docs     4–6 days
M2       apollo-cold-email live; resume + two-person tests for real      2–3 days
M3       fork proof                                                      hours
M4       researcher flow (breadth) + reply detection + credential purge  2–3 days
```

Critical path runs through **M0's claim-race test** (everything downstream trusts it) and **M1's runner** (every skill is just data fed to it). Build and prove those two first.

---

## 10. As-built notes (2026-06-10)

The build landed the same day as this plan. Deviations and additions, so the document stays the source of truth:

1. **Package layout:** `toolbox/src/toolbox/{core,primitives,process}` (src layout for packaging hygiene) instead of §2's flat `toolbox/core`. Everything else matches §2.
2. **Run liveness moved into the database.** §3.4's heartbeat lived in `status.json`; a cross-*machine* reaper can't read a laptop's file, so a `runs` table (run_id, owner, state, heartbeat_at) was added (`0002_ledger.sql`) and the runner heartbeats both places. The reaper releases claims of `failed`/dead runs only; `paused` runs keep theirs.
3. **Resume claims:** when a run fails mid-send, its unsent `claimed` rows are released by `release_stale_claims()` at the next runner startup (the run is marked failed), then re-claimed by the resumed run. Proven end-to-end in `tests/integration/test_e2e_crash_resume.py`.
4. **Pause protocol:** pausing steps exit code 75 and leave a marker file (`.clarify.confirmed` / `.canary.approved`) so the re-run of the same step after `toolbox resume` completes instead of pausing again. The runner re-resolves `flow.resolved.yaml` from the skill's `flow.yaml` after `clarify.ask` completes, so input edits made at the gate reach later steps.
5. **Extra primitives for M4 breadth:** `fetch.urls`, `llm.filter`, `inbox.file` (researcher sweep). `gmail.replies`/`gmail.bounces` implement the read side (M4) with `--file-inbox-tasks` feeding `inbox/queue/`.
6. **Test hooks (never production paths):** `TOOLBOX_SESSION_TOKEN`, `TOOLBOX_TOKEN_<PROVIDER>`, `TOOLBOX_GMAIL_API_BASE` env overrides exist so the integration tests can run the real runner + real Postgres against a fake Gmail.
7. **Proven (52 tests green):** claim race (one winner of 20), two-person overlap (zero duplicates), crash-mid-send → resume (zero duplicates, real DB), RLS isolation, reaper paused-vs-dead, fork-removed-step-didn't-run, dry-run grading, quota wall fails cleanly.
8. **Human-gated remainder:** hosted Supabase project + Google OAuth secrets (`supabase/README.md` has the steps); `ANTHROPIC_API_KEY` (the `credentials/.env` slot is empty — llm-dependent primitives need it until `toolbox auth connect anthropic` is used); connect the Dartmouth Gmail via `toolbox auth connect gmail`; first live M2 segment; then M4 rotation + `credentials/` deletion. gogcli stays until the live M2 proof per §7 item 5.
