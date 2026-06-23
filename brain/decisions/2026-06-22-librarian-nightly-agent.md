# Decision: a nightly librarian agent maintains the repo autonomously

**Date:** 2026-06-22 · **Source:** internal decision (Armaan, in session).

## What was decided

A new agent, the librarian, runs one autonomous cleanup pass every night and
commits the result to `main`. It deletes the cruft that accumulates (stale
`runs/` dirs, caches, old finished inbox tasks), keeps the file structure and
indexes tidy, repairs internal cross-links, and flags the judgment calls for a
human. Charter: `agents/librarian/AGENT.md`. Nightly flow:
`skills/librarian-nightly/`.

## How it works

- It runs as a systemd user timer (`librarian-nightly`, OnCalendar `*-*-* 03:00`,
  `Persistent=true`), the same scheduling pattern as the researcher digest.
- Cleanup needs judgment, not a fixed pipeline, so the runner drives headless
  Claude Code (`claude -p`) with a checklist (`PROMPT.md`) rather than a
  deterministic toolbox flow. This reuses the `claude -p` LLM path decided in
  `2026-06-10-llm-via-claude-code.md`, but at the agent level (full tools,
  in-repo) instead of the harness `llm.py` level.
- The agent does the file work and stages it; `cron.sh` owns a deterministic
  safety gate (protected paths + a runaway cap) and the single commit + push, so
  the limits are enforced in bash, not left to the model.

## The three posture choices (Armaan, in session)

- **Recovery is git, not an archive.** Stale tracked files are deleted, not moved
  to an archive folder; the nightly commit is the revert point. Chosen for a
  cleaner tree. The cost is that there is no in-tree safety net, which is why the
  protected set and runaway cap do the real work.
- **Commit and push to `main` nightly.** One scoped, revertible commit, pushed,
  so the cleanup is shared. Not a branch-and-PR; the point is full autonomy.
- **Mechanical on the brain, editorial flagged.** The librarian fixes dead links,
  index drift, and missing dates in `brain/`, but never merges, rewrites, or
  prunes brain prose on its own. Duplicates and contradictions become a single
  inbox task for a human. The brain is the company's durable asset; an
  unsupervised agent edits its plumbing, not its meaning.

## Guardrails (the reason this is safe to leave running)

- **Protected paths**, re-checked against the staged diff in `cron.sh`, abort the
  run if touched: `credentials/`, `CLAUDE.md`, `.mcp.json`, `toolbox/src|tests/`,
  `agents/*/AGENT.md`, `brain/company/overview.md`, `brain/decisions/`,
  `.claude/`, `.agents/`, and the librarian's own skill files.
- **Runaway cap**: deleting more than 15 tracked files or changing more than 40
  in one night aborts the run and files an alert, on the logic that a huge
  changeset is a malfunction, not a big cleanup.
- **Dirty-tree refusal**: it will not run if the working tree has uncommitted
  work, so it never sweeps a human's edits into an autonomous commit.
- **Flag, do not guess**: anything ambiguous becomes an inbox task instead of an
  action.

## Tradeoffs accepted

- Autonomous pushes to `main` every night. Mitigated by the gate, the single
  revertible commit, and the per-run report in `agents/librarian/LOG.md`.
- Needs a logged-in `claude` CLI on the host (subscription auth), same constraint
  as every other `claude -p` flow here. Logged out, the run fails closed and
  lands nothing.
- Spends subscription usage nightly for the agent pass.

## Update 2026-06-23: worktree isolation replaces the dirty-tree guard

The first build guarded with "skip the night if the working tree is dirty" and,
on any abort, reverted with a repo-wide `git reset --hard` plus `git clean -fdq`.
Validating it in a live shared checkout exposed two flaws:

- **It would rarely run.** The guard tripped on any uncommitted change, tracked
  or not. This repo routinely has untracked agent output sitting around (for
  example GEO audit files), so the tree is often dirty at 3am and the librarian
  would skip almost every night, defeating the point.
- **It could destroy concurrent work.** The dirty-tree check is time-of-check;
  the revert is time-of-use. If a session started writing after the check, the
  `git clean -fdq` on an abort would delete its untracked files. During the test
  run this very likely grazed a concurrent GEO session's early files (it was
  still running and regenerated them, so no confirmed permanent loss).

The fix removes the dependence on the main checkout's cleanliness entirely. The
flow is now two phases:

- **Disk hygiene** runs on the main checkout in plain bash, deleting only
  gitignored regenerable junk (caches, `*.pyc`, editor backups, old `runs/`
  dirs). It never commits and only removes files git already ignores, so it is
  safe alongside any concurrent work.
- **Tracked-content cleanup** runs the `claude -p` pass inside an isolated git
  worktree checked out from `origin/main`. It sees only committed content, so it
  cannot read or delete anyone's uncommitted work; it commits there and pushes
  the detached HEAD to `main`. Any abort, a rejected push (`origin/main` moved),
  or a clean night just removes the worktree. The main checkout is never `reset`
  or `clean`'d.

Result: the librarian runs every night regardless of what is checked out, and the
class of "autonomous job destroys in-progress work" is gone. The protected-path
and runaway-cap gates are unchanged and now run against the worktree's staged
diff. The posture choices above (delete-not-archive, push to `main`, mechanical
on brain) are unchanged.
