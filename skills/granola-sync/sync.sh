#!/usr/bin/env bash
#
# granola-sync — pull every Granola meeting that is not already in the repo and
# publish it to context/samarjit-granola/ in one step: export, commit, push.
#
# Idempotent. When there is nothing new it makes no commit and exits 0. The
# export half is delegated to skills/granola-export/export.js (default mode
# already skips notes whose document id is on disk), so this script never
# touches Granola's encrypted store itself; it only orchestrates and publishes.
#
# Usage (from anywhere in the repo):
#   skills/granola-sync/sync.sh            # export new notes, commit, push
#   skills/granola-sync/sync.sh --no-push  # export and commit, leave the push to you
#   skills/granola-sync/sync.sh --list     # show in-repo vs NEW, write nothing

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

OUTDIR="context/samarjit-granola"
PUSH=1

for arg in "$@"; do
  case "$arg" in
    --no-push) PUSH=0 ;;
    --list|--dry-run)
      node skills/granola-export/export.js --list
      exit 0
      ;;
    *) echo "granola-sync: unknown argument '$arg'" >&2; exit 2 ;;
  esac
done

# 1. Export anything not already committed (idempotent default mode).
node skills/granola-export/export.js

# 2. Stage only the meeting-notes folder and bail early when it is unchanged.
git add "$OUTDIR"
if git diff --cached --quiet -- "$OUTDIR"; then
  echo "granola-sync: nothing new to upload."
  exit 0
fi

echo "granola-sync: publishing these notes:"
git diff --cached --name-only -- "$OUTDIR" | sed 's/^/  /'
COUNT=$(git diff --cached --name-only -- "$OUTDIR" | wc -l | tr -d ' ')

# 3. Commit.
git commit -m "context: sync ${COUNT} Granola meeting note(s) to samarjit-granola

Exported via skills/granola-export (idempotent default mode): verbatim
transcripts plus AI summaries, same format as the existing notes.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"

if [ "$PUSH" = 0 ]; then
  echo "granola-sync: committed locally; skipped push (--no-push)."
  exit 0
fi

# 4. Push. The shared notes repo moves often, so a plain push is frequently
#    rejected as non-fast-forward. These are brand-new files, so a rebase onto
#    the latest remote is conflict-free in practice; abort loudly if it is not.
BRANCH="$(git branch --show-current)"
if git push; then
  echo "granola-sync: pushed."
  exit 0
fi

# --autostash sets aside any unrelated uncommitted work in the tree before the
# rebase and restores it after, so a dirty working tree no longer blocks the
# retry with "cannot rebase: You have unstaged changes". A genuine overlap (your
# uncommitted edits touch a file that also moved on the remote) still surfaces as
# a conflict for you to resolve by hand; the notes commit is independent, so it
# rebases and pushes cleanly regardless.
echo "granola-sync: push rejected (remote moved); rebasing onto origin/${BRANCH} and retrying."
git fetch origin
if ! git rebase --autostash "origin/${BRANCH}"; then
  git rebase --abort || true
  echo "granola-sync: rebase hit a conflict. Resolve it by hand, then run 'git push'." >&2
  exit 1
fi
git push
echo "granola-sync: pushed after rebase."
