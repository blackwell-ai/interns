#!/usr/bin/env bash
# Daily runner for the token leaderboard.
#
# Role split (this tool is multi-writer, unlike the single-author digest):
#   - feeder (default, every teammate): push THIS machine's Claude Code usage
#     to Supabase. No git writes and no working-tree changes, so it is safe to
#     run on any machine, including one with unrelated work in progress. This
#     is what makes the live board complete.
#   - --push (one canonical machine, clean tree): also regenerate, commit, and
#     push brain/metrics/LEADERBOARD.md, the durable snapshot. Only one machine
#     should write that one shared file, so the snapshot path is opt-in and
#     never runs when the tree has other changes.
#
# Config comes from credentials/.env (gitignored, distributed out-of-band):
#   SUPABASE_URL                 the project URL
#   SUPABASE_PUBLISHABLE_KEY     the public client key (or SUPABASE_KEY)
#   LEADERBOARD_PERSON           your display name on the board, e.g. Armaan
#
# Install the daily cron (idempotent, safe to re-run):
#   skills/token-leaderboard/cron.sh --install          # feeder (default)
#   skills/token-leaderboard/cron.sh --install --push   # canonical snapshot host
#
# Other flags:
#   --dry            run ccusage and print the mapped rows, write nothing
#   --since YYYYMMDD earliest day to collect (default 20260101)
#   --push           maintain the committed snapshot (see role split above)
set -euo pipefail
cd "$(dirname "$0")/../.."
ROOT="$PWD"

SINCE="20260101"; PUSH=""; DRY=""; INSTALL=""
while [ $# -gt 0 ]; do case "$1" in
  --push)    PUSH=1; shift;;
  --dry)     DRY=1; shift;;
  --install) INSTALL=1; shift;;
  --since)   SINCE="$2"; shift 2;;
  *) echo "unknown arg: $1"; exit 2;;
esac; done

SELF="$ROOT/skills/token-leaderboard/cron.sh"

# --install: register a daily 23:00 job for this script, idempotently. Uses
# crontab where it exists (macOS and most Linux); falls back to a systemd user
# timer on machines without cron (e.g. Arch). Both encode the role flag.
if [ -n "$INSTALL" ]; then
  FLAG="${PUSH:+ --push}"
  if command -v crontab >/dev/null 2>&1; then
    LINE="0 23 * * * $SELF$FLAG  # token-leaderboard"
    CUR="$(crontab -l 2>/dev/null || true)"
    if printf '%s\n' "$CUR" | grep -qF "# token-leaderboard"; then
      echo "cron already installed:"; printf '%s\n' "$CUR" | grep -F "# token-leaderboard"
      echo "edit with 'crontab -e' to change it."
    else
      printf '%s\n%s\n' "$CUR" "$LINE" | grep -v '^[[:space:]]*$' | crontab -
      echo "installed daily cron (23:00): $LINE"
    fi
  elif command -v systemctl >/dev/null 2>&1 && systemctl --user list-units >/dev/null 2>&1; then
    UDIR="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
    mkdir -p "$UDIR"
    cat > "$UDIR/token-leaderboard.service" <<UNIT
[Unit]
Description=Token leaderboard daily collector

[Service]
Type=oneshot
ExecStart=$SELF$FLAG
UNIT
    cat > "$UDIR/token-leaderboard.timer" <<'UNIT'
[Unit]
Description=Run the token leaderboard collector daily

[Timer]
OnCalendar=*-*-* 23:00:00
Persistent=true

[Install]
WantedBy=timers.target
UNIT
    systemctl --user daemon-reload
    systemctl --user enable --now token-leaderboard.timer >/dev/null 2>&1
    echo "installed systemd user timer (daily 23:00, flag:${FLAG:- feeder})"
    systemctl --user list-timers token-leaderboard.timer --all 2>/dev/null | sed -n '1,2p'
    if ! loginctl show-user "$(id -un)" -p Linger 2>/dev/null | grep -q 'Linger=yes'; then
      echo "note: run 'sudo loginctl enable-linger $(id -un)' so it runs while logged out"
    fi
  else
    echo "no crontab and no usable 'systemctl --user'. Add a daily job by hand:"
    echo "  0 23 * * * $SELF$FLAG"
  fi
  exit 0
fi

LOG="$ROOT/runs/cron-leaderboard.log"; mkdir -p "$ROOT/runs"
{
  echo "=== token-leaderboard $(date -Is) (push=${PUSH:-0} dry=${DRY:-0}) ==="

  # Headless config. Never echoed; the file is gitignored.
  [ -f credentials/.env ] && { set -a; . credentials/.env; set +a; }

  : "${LEADERBOARD_PERSON:?set LEADERBOARD_PERSON in credentials/.env (your board name, e.g. Armaan)}"
  : "${SUPABASE_URL:?set SUPABASE_URL in credentials/.env}"
  export PERSON="$LEADERBOARD_PERSON"
  export SUPABASE_KEY="${SUPABASE_KEY:-${SUPABASE_PUBLISHABLE_KEY:-}}"
  [ -n "$SUPABASE_KEY" ] || { echo "set SUPABASE_PUBLISHABLE_KEY (or SUPABASE_KEY) in credentials/.env"; exit 1; }

  if [ -n "$DRY" ]; then
    node skills/token-leaderboard/collect-usage.mjs --since "$SINCE" --dry-run
    echo "dry run complete"; exit 0
  fi

  if [ -z "$PUSH" ]; then
    # Feeder: upsert to Supabase only, no snapshot, no working-tree changes.
    node skills/token-leaderboard/collect-usage.mjs --since "$SINCE" --no-snapshot
    echo "fed Supabase as $PERSON"
    exit 0
  fi

  # Canonical: maintain the committed snapshot, but only when the working tree
  # is otherwise clean. Check first, so a dirty tree means we never even
  # regenerate the file; we just feed Supabase like a plain feeder.
  if ! git diff --quiet || ! git diff --cached --quiet; then
    node skills/token-leaderboard/collect-usage.mjs --since "$SINCE" --no-snapshot
    echo "fed Supabase as $PERSON; snapshot skipped (tree not clean)"
    exit 0
  fi
  node skills/token-leaderboard/collect-usage.mjs --since "$SINCE"
  git add brain/metrics/LEADERBOARD.md
  if git diff --cached --quiet; then
    echo "snapshot unchanged"; exit 0
  fi
  git commit -q -m "Token leaderboard snapshot $(date +%F)" \
    -m "Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
  # Tree is clean here, so rebasing onto the remote is safe.
  if git fetch -q origin main && git rebase -q origin/main && git push -q origin main; then
    echo "committed + pushed snapshot"
  else
    git rebase --abort 2>/dev/null || true
    echo "push failed; snapshot committed locally, will retry next run"
  fi
} >> "$LOG" 2>&1
