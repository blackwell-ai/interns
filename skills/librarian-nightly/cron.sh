#!/usr/bin/env bash
# Nightly librarian: an autonomous repo-cleanup pass.
#
# Unlike the researcher digest (a deterministic toolbox flow), the librarian
# needs judgment -- is this brain entry a duplicate, is this file junk or
# load-bearing -- so this runner drives headless Claude Code (`claude -p`) inside
# the repo with the librarian's nightly checklist (PROMPT.md), then enforces a
# deterministic safety gate in bash before anything is committed.
#
# Duties are split on purpose:
#   - claude -p does the file operations, writes agents/librarian/LOG.md, stages
#     its changes (git add -A), and writes a commit message to
#     runs/librarian-commit-msg.txt. It does NOT commit or push.
#   - this script enforces the protected-path + runaway guard on the STAGED diff,
#     then makes one scoped commit on main and pushes. If the guard trips it
#     hard-reverts the working tree, files an inbox alert, and lands nothing.
#
# Recovery is git: every change is one revertible commit on main. Nothing is
# archived; stale tracked files are deleted and live on in history.
#
# SCHEDULED via a systemd USER timer (Arch has no cron daemon), installed on
# Armaan's machine at ~/.config/systemd/user/librarian-nightly.{service,timer}
# (OnCalendar=*-*-* 03:00, Persistent=true) with `loginctl enable-linger armaan`
# so it runs while logged out. Manage: `systemctl --user {start,disable --now}
# librarian-nightly.timer`. See SKILL.md "Operations" to rebuild from scratch.
# (On a real cron host instead:  0 3 * * *  <abs path to this script>)
#
# Requires a logged-in `claude` CLI on this machine (subscription auth); see
# brain/decisions/2026-06-10-llm-via-claude-code.md.
#
# Flags:
#   --dry      run the full cleanup pass but commit nothing (reverts the tree)
#   --no-push  commit locally but do not push
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

# Runaway-guard thresholds (env-overridable).
MAX_DELETE="${LIBRARIAN_MAX_DELETE:-15}"
MAX_CHANGE="${LIBRARIAN_MAX_CHANGE:-40}"

# Paths the librarian must never touch. A staged change matching this aborts the
# whole run, even if the agent decided otherwise.
PROTECTED='^(credentials/|CLAUDE\.md$|\.mcp\.json$|toolbox/(src|tests)/|agents/[^/]+/AGENT\.md$|brain/company/overview\.md$|brain/decisions/|\.claude/|\.agents/|skills/librarian-nightly/(cron\.sh|SKILL\.md|PROMPT\.md)$)'

LOG="$ROOT/runs/cron-librarian.log"
mkdir -p "$ROOT/runs"
DATE="$(date +%F)"
MSG_FILE="$ROOT/runs/librarian-commit-msg.txt"
rm -f "$MSG_FILE"

# Discard everything the agent did this run (tracked + untracked), back to a
# clean tree. Gitignored files (runs/, credentials/.env) are preserved.
revert_all() { git reset --hard -q || true; git clean -fdq || true; }

# File a human-facing alert into the inbox queue and commit just that file.
# Assumes the tree was already reverted to clean.
alert() {
  local f="$ROOT/inbox/queue/${DATE}-librarian-alert.md"
  {
    echo "# Librarian alert ($DATE)"; echo
    echo "The nightly librarian aborted and landed nothing: $1"; echo
    echo "Check runs/cron-librarian.log and agents/librarian/LOG.md, then rerun"
    echo "by hand once it looks right:"; echo
    echo '    skills/librarian-nightly/cron.sh --dry'
  } > "$f"
  git add "$f" 2>/dev/null || return 0
  git commit -q -F - <<EOF || return 0
librarian: alert ($DATE), aborted run

$1

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
EOF
  [ -z "$NOPUSH" ] && git push -q 2>/dev/null || true
}

{
  echo "=== librarian-nightly $(date -Is) (dry=${DRY:-0}) ==="

  # Never sweep a human's uncommitted work into an autonomous commit. A dirty
  # tree at start means someone is mid-edit; skip tonight.
  if [ -n "$(git status --porcelain)" ]; then
    echo "working tree dirty at start; skipping to avoid committing human WIP"
    git status --short
    exit 0
  fi

  # Headless secrets if any flow needs them (gitignored, never echoed).
  [ -f credentials/.env ] && { set -a; . credentials/.env; set +a; }

  # 1) the judgment pass: headless Claude Code cleans up and stages its changes.
  if ! timeout 20m "$CLAUDE" -p "$(cat "$ROOT/skills/librarian-nightly/PROMPT.md")" \
        --dangerously-skip-permissions --output-format text; then
    echo "claude run failed or timed out; reverting"
    revert_all
    exit 1
  fi

  # 2) deterministic safety gate on the STAGED diff.
  STAGED="$(git diff --cached --name-only)"
  if [ -z "$STAGED" ]; then
    echo "nothing staged; clean night, nothing to commit"
    revert_all   # drop any unstaged disk churn so the tree stays clean
    exit 0
  fi

  # 2a) protected paths
  if echo "$STAGED" | grep -qE "$PROTECTED"; then
    echo "staged changes touch protected paths:"
    echo "$STAGED" | grep -E "$PROTECTED"
    revert_all
    alert "staged a change to a protected path"
    exit 1
  fi

  # 2b) runaway thresholds
  N_DEL="$(git diff --cached --name-only --diff-filter=D | grep -c . || true)"
  N_ALL="$(printf '%s\n' "$STAGED" | grep -c . || true)"
  echo "staged: $N_ALL changed, $N_DEL deleted (caps: change=$MAX_CHANGE delete=$MAX_DELETE)"
  if [ "$N_DEL" -gt "$MAX_DELETE" ] || [ "$N_ALL" -gt "$MAX_CHANGE" ]; then
    echo "changeset exceeds runaway cap; aborting for human review"
    revert_all
    alert "changeset too large ($N_ALL changed, $N_DEL deleted)"
    exit 1
  fi

  if [ -n "$DRY" ]; then
    echo "dry run: would commit these:"
    git diff --cached --stat
    revert_all
    exit 0
  fi

  # 3) one scoped, revertible commit on main.
  if [ -s "$MSG_FILE" ]; then
    git commit -q -F "$MSG_FILE" \
      -m "Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
  else
    git commit -q -m "librarian: nightly cleanup ${DATE}" \
      -m "Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
  fi
  echo "committed: $(git log -1 --format='%h %s')"

  if [ -z "$NOPUSH" ]; then
    if git push -q; then echo "pushed"; else echo "push failed (commit is local)"; fi
  fi
} >> "$LOG" 2>&1
