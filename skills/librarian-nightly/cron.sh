#!/usr/bin/env bash
# Nightly librarian: autonomous repo cleanup, isolated from concurrent work.
#
# Two phases, deliberately split so the agent can NEVER touch a teammate's or
# another session's uncommitted work:
#
#   Phase A -- disk hygiene, on the MAIN checkout. Deletes only gitignored,
#     regenerable junk (caches, *.pyc, editor backups, old runs/ dirs). It never
#     stages and never commits, and it only removes files git already ignores, so
#     it is safe to run while anything else is going on.
#
#   Phase B -- tracked-content cleanup, in an ISOLATED git worktree checked out
#     from origin/main. Headless Claude Code (`claude -p`) prunes finished inbox
#     tasks, repairs indexes + cross-links, flags judgment calls, writes
#     agents/librarian/LOG.md, and stages its changes. Because the worktree is a
#     separate directory holding only committed content, the agent cannot see or
#     delete the main checkout's uncommitted files. This script runs the safety
#     gate on the worktree's staged diff, commits, and pushes HEAD:main. On any
#     abort the whole worktree is just removed -- the main checkout is never
#     reset or cleaned, so there is no path to destroying in-progress work.
#
# This replaces the first design, which guarded with "skip if the tree is dirty"
# (so any leftover untracked file disabled it) and reverted with a repo-wide
# `git reset --hard` + `git clean` (which could delete a concurrent session's
# work). See brain/decisions/2026-06-22-librarian-nightly-agent.md for the why.
#
# SCHEDULED via a systemd USER timer (Arch has no cron daemon):
#   ~/.config/systemd/user/librarian-nightly.{service,timer}
#   (OnCalendar=*-*-* 03:00, Persistent=true) + `loginctl enable-linger armaan`.
#   Manage: systemctl --user {start,disable --now} librarian-nightly.timer
#
# Requires a logged-in `claude` CLI (subscription auth; see
# brain/decisions/2026-06-10-llm-via-claude-code.md) and push access to origin.
#
# Flags:
#   --dry      both phases read-only: report disk junk without deleting; build
#              the worktree + run the pass; print the staged diff; commit nothing.
#   --no-push  commit inside the worktree but do not push (the commit is then
#              discarded with the worktree, so this is an inspection mode).
set -euo pipefail
cd "$(dirname "$0")/../.."
ROOT="$PWD"

# cron/systemd run with a minimal PATH; claude, git, uv live under these.
export PATH="/sbin:/usr/bin:/bin:${HOME:-/root}/.local/bin:$PATH"
CLAUDE="${HOME:-/root}/.local/bin/claude"

DRY=""; NOPUSH=""
while [ $# -gt 0 ]; do case "$1" in
  --dry)     DRY=1; shift;;
  --no-push) NOPUSH=1; shift;;
  *) echo "unknown arg: $1"; exit 2;;
esac; done

# Runaway-guard thresholds and run-dir retention (env-overridable).
MAX_DELETE="${LIBRARIAN_MAX_DELETE:-15}"
MAX_CHANGE="${LIBRARIAN_MAX_CHANGE:-40}"
RUNS_KEEP="${LIBRARIAN_RUNS_KEEP:-7}"

# Staged paths the librarian must never change; a hit aborts the commit.
PROTECTED='^(credentials/|CLAUDE\.md$|\.mcp\.json$|toolbox/(src|tests)/|agents/[^/]+/AGENT\.md$|brain/company/overview\.md$|brain/decisions/|\.claude/|\.agents/|skills/librarian-nightly/(cron\.sh|SKILL\.md|PROMPT\.md)$)'

LOG="$ROOT/runs/cron-librarian.log"
mkdir -p "$ROOT/runs"
DATE="$(date +%F)"

WT=""
cleanup() {
  if [ -n "${WT:-}" ]; then
    [ -d "$WT" ] && git worktree remove --force "$WT" 2>/dev/null || true
    rmdir "$(dirname "$WT")" 2>/dev/null || true
  fi
}
trap cleanup EXIT

{
  echo "=== librarian-nightly $(date -Is) (dry=${DRY:-0}) ==="

  # ---- Phase A: disk hygiene on the main checkout (gitignored junk only) ----
  echo "-- phase A: disk hygiene --"
  # Skip .git, virtualenvs, and node_modules: fast, and we never churn those.
  PRUNE=( -path "$ROOT/.git" -o -name .venv -o -name node_modules )
  junk_dirs()  { find "$ROOT" \( "${PRUNE[@]}" \) -prune -o -type d \
      \( -name __pycache__ -o -name .ruff_cache -o -name .pytest_cache \) -print 2>/dev/null; }
  junk_files() { find "$ROOT" \( "${PRUNE[@]}" \) -prune -o -type f \
      \( -name '*.pyc' -o -name '.DS_Store' -o -name '*~' -o -name '*.orig' \) -print 2>/dev/null; }
  old_runs()   { ls -1dt "$ROOT"/runs/*/ 2>/dev/null | tail -n +$((RUNS_KEEP + 1)); }

  nd=$(junk_dirs | grep -c . || true)
  nf=$(junk_files | grep -c . || true)
  nr=$(old_runs | grep -c . || true)
  echo "  found caches:$nd junk-files:$nf old-run-dirs:$nr (keep newest $RUNS_KEEP runs)"
  if [ -z "$DRY" ]; then
    junk_dirs  | while read -r d; do [ -n "$d" ] && rm -rf "$d"; done
    junk_files | while read -r f; do [ -n "$f" ] && rm -f "$f"; done
    old_runs   | while read -r d; do [ -n "$d" ] && { echo "  prune $d"; rm -rf "$d"; }; done
    echo "  disk hygiene applied"
  else
    echo "  dry: nothing deleted"
  fi

  # ---- Phase B: tracked-content cleanup in an isolated worktree ----
  echo "-- phase B: tracked-content cleanup (isolated worktree) --"
  git worktree prune -q 2>/dev/null || true
  if ! git fetch -q origin main 2>/dev/null; then
    echo "  git fetch failed; skipping phase B (disk hygiene already done)"
    exit 0
  fi
  WT="$(mktemp -d)/lib-wt"
  if ! git worktree add -q --detach "$WT" origin/main; then
    echo "  worktree add failed; skipping phase B"
    exit 1
  fi
  mkdir -p "$WT/runs"
  echo "  worktree $WT @ $(git -C "$WT" rev-parse --short HEAD) (origin/main)"

  MSG="$WT/runs/librarian-commit-msg.txt"; rm -f "$MSG"

  # The judgment pass runs with its cwd INSIDE the worktree, so every file op and
  # `git add` it does is confined to the worktree, not the main checkout.
  if ! ( cd "$WT" && timeout 20m "$CLAUDE" -p "$(cat "$WT/skills/librarian-nightly/PROMPT.md")" \
          --dangerously-skip-permissions --output-format text ); then
    echo "  claude run failed or timed out; discarding worktree"
    exit 1
  fi

  # Safety gate on the worktree's staged diff.
  STAGED="$(git -C "$WT" diff --cached --name-only)"
  if [ -z "$STAGED" ]; then
    echo "  nothing staged; clean night, nothing to commit"
    exit 0
  fi
  if echo "$STAGED" | grep -qE "$PROTECTED"; then
    echo "  ABORT: staged a protected path:"
    echo "$STAGED" | grep -E "$PROTECTED" | sed 's/^/    /'
    exit 1
  fi
  N_DEL=$(git -C "$WT" diff --cached --name-only --diff-filter=D | grep -c . || true)
  N_ALL=$(printf '%s\n' "$STAGED" | grep -c . || true)
  echo "  staged: $N_ALL changed, $N_DEL deleted (caps: change=$MAX_CHANGE delete=$MAX_DELETE)"
  if [ "$N_DEL" -gt "$MAX_DELETE" ] || [ "$N_ALL" -gt "$MAX_CHANGE" ]; then
    echo "  ABORT: changeset exceeds runaway cap; discarding worktree"
    exit 1
  fi

  if [ -n "$DRY" ]; then
    echo "  dry run: would commit:"
    git -C "$WT" diff --cached --stat | sed 's/^/    /'
    exit 0
  fi

  # One scoped, revertible commit, then push the detached HEAD to main.
  if [ -s "$MSG" ]; then
    git -C "$WT" commit -q -F "$MSG" \
      -m "Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
  else
    git -C "$WT" commit -q -m "librarian: nightly cleanup ${DATE}" \
      -m "Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
  fi
  echo "  committed $(git -C "$WT" rev-parse --short HEAD)"

  if [ -n "$NOPUSH" ]; then
    echo "  --no-push: commit stays in the worktree and is discarded on cleanup"
    exit 0
  fi
  if git -C "$WT" push -q origin HEAD:main; then
    echo "  pushed to origin/main (local main fast-forwards on next pull)"
  else
    echo "  push rejected (origin/main moved); landing nothing, retry next run"
  fi
} >> "$LOG" 2>&1
