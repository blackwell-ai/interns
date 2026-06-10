# PROTOCOL.md — how agents compose, run, and fork flows

This is spec §5–§6 written for agents. Read `toolbox/TOOLBOX.md` for the
primitive contract; read each primitive's `TOOL.md` before using it. Never
read primitive source to compose a flow.

## Routing preference (in order)

1. **Rerun** an existing skill (check `INDEX.md`) with different `-i key=value` inputs.
2. **Fork** one: `toolbox fork <src> <dst>`, edit `inputs.yaml`, delete unwanted
   flow lines, run. Seconds, zero new code. Note "forked from X, differs by Y"
   in the fork's SKILL.md (the fork command scaffolds this).
3. **Compose** a new flow from existing primitives (a new `skills/<name>/` folder).
4. **Write a new primitive** — the only deliberate act; requires a sentence of
   justification in the calling skill's SKILL.md.

## A skill folder

```
skills/<name>/
  SKILL.md      # canonical: purpose, inputs, step list explained, acceptance checks, changelog
  flow.yaml     # the executable composition
  inputs.yaml   # parameters with defaults — the one-pass clarification form
  template.md   # (outreach skills) subject frontmatter + body, slots = {{column}}
  steps/        # (optional) tiny python: escape-hatch scripts
```

`flow.yaml` is a list of steps; each step is one line; `{{var}}` pulls from
`inputs.yaml` (plus builtins `run_id`, `run_dir`, `skill_dir`, `repo_root`).
Removing a process step = deleting one line. A `python: steps/x.py` escape
hatch exists; if such a script grows past trivial, that's the signal to
promote it to a primitive.

## Default chains (defaults, not law)

- **New skill, irreversible actions:** `plan.write → clarify.ask → test.smoke
  → test.dryrun → canary.run → <work steps> → report.write`
- **Rerun of a proven skill:** `<work steps> → report.write`
- **Fork:** `test.dryrun → <work steps> → report.write`
- **One-off "just run it":** `<work steps>` alone, unregistered, lives only in `runs/`.

Strip any step the human waives ("no questions, no canary, just send it").
The ONE thing no flow can strip is the ledger check — it lives inside the
send-class primitives and in the database, not in the flow.

## Running

```bash
uv run --project toolbox toolbox run <skill> [-i key=value ...] [--yes]
uv run --project toolbox toolbox resume <run_id>     # after a pause or crash
```

Pauses: `clarify.ask` (headless) and `canary.run` stop the run with
instructions; a human acts, then resumes. Crashes: just resume — completed
steps are skipped, and the ledger + per-run mirror make re-sends impossible.

## Registration

A *registered* skill has a SKILL.md (`plan.write` drafts one) and a row in
`INDEX.md`; `report.write` keeps the changelog + INDEX row fresh. One-off
flows can skip the ceremony entirely.

## The invariant (never work around it)

No person is ever contacted twice across any automation, any teammate, any
machine — enforced by `UNIQUE (channel, recipient)` in Supabase plus the claim
RPC inside send-class primitives. `allow_recontact: true` exists for
deliberate follow-up sequences, is logged loudly, and never overrides the
suppression list (bounces, opt-outs).
