#!/usr/bin/env bash
# Weekday-morning runner for the researcher daily digest.
#
# Everything here is headless-safe. The claude.ai MCP connectors (Notion, Gmail)
# are interactive and absent in cron (brain/company/connections.md), so this
# script does NOT use them. It:
#   1. runs the researcher-daily-digest skill  -> brain/research/digests/<date>.md
#      plus one inbox/queue task per action item;
#   2. commits those durable artifacts (scoped add, never the whole tree);
#   3. emails the digest to the team via gog (the headless email path).
#
# Notion mirroring is intentionally left to the next interactive session, the
# same way inbox/ mirrors the Notion task hub (CLAUDE.md "Task hub").
#
# Sources: Reddit (public RSS, residential IP only, so run this on a residential
# machine), Hacker News (Algolia API), Discord (REST API + TOOLBOX_TOKEN_DISCORD,
# a self-bot), and X (the browse daemon, best-effort). All but Reddit/HN need
# credentials/.env sourced; X also needs the browse daemon logged in to X on
# this machine. Any source can fail without crashing the digest.
#
# Credentials in credentials/.env (gitignored) cover gog email + the Discord
# token. Reddit needs no key.
#
# SCHEDULED via a systemd USER timer (Arch has no cron daemon), installed on
# Armaan's machine at ~/.config/systemd/user/researcher-digest.{service,timer}
# (OnCalendar=Mon..Fri 08:00, Persistent=true), with `loginctl enable-linger
# armaan` so it runs while logged out. Manage: `systemctl --user {start,
# disable --now} researcher-digest.timer`. See SKILL.md "Operations" to rebuild.
# (If moving to a cron host instead:  0 8 * * 1-5  <abs path to this script>)
#
# Flags:
#   --dry        run the sweep + build the digest, but do not commit or email
#   --to <list>  override recipients (comma-separated)
#   --push       also `git push` the digest commit (default: local commit only)
set -euo pipefail
cd "$(dirname "$0")/../.."
ROOT="$PWD"

# cron runs with a minimal PATH; uv, git, and gog live in /sbin on this machine.
export PATH="/sbin:/usr/bin:/bin:${HOME:-/root}/.local/bin:$PATH"

DRY=""; PUSH=""
# The founding team's personal inboxes (see brain/company/connections.md).
# Override with DIGEST_RECIPIENTS or --to.
RECIPIENTS="${DIGEST_RECIPIENTS:-armaanp4423@gmail.com,samarjitd391@gmail.com,shamit.dsouza@gmail.com,ezhou1923@gmail.com}"
FROM="${DIGEST_FROM:-armaan.priyadarshan.29@dartmouth.edu}"
while [ $# -gt 0 ]; do case "$1" in
  --dry)  DRY=1; shift;;
  --push) PUSH=1; shift;;
  --to)   RECIPIENTS="$2"; shift 2;;
  *) echo "unknown arg: $1"; exit 2;;
esac; done

LOG="$ROOT/runs/cron-digest.log"
mkdir -p "$ROOT/runs"
DATE="$(date +%F)"
DIGEST="brain/research/digests/${DATE}.md"

{
  echo "=== researcher-daily-digest $(date -Is) (dry=${DRY:-0}) ==="

  # Headless secrets (TOOLBOX_TOKEN_REDDIT, GOG_KEYRING_PASSWORD, SUPABASE_*).
  # Never echoed; the file is gitignored.
  [ -f credentials/.env ] && { set -a; . credentials/.env; set +a; }

  # 1) headless sweep -> brain digest + inbox tasks
  uv run --project toolbox toolbox run researcher-daily-digest --yes

  if [ ! -f "$DIGEST" ]; then
    echo "no digest produced at $DIGEST; aborting"; exit 1
  fi

  if [ -n "$DRY" ]; then
    echo "dry run: digest at $DIGEST; skipping commit + email"; exit 0
  fi

  # 2) commit the durable artifacts only (the digest + any new inbox tasks)
  git add "$DIGEST" inbox/queue/ 2>/dev/null || true
  if git diff --cached --quiet; then
    echo "nothing new to commit"
  else
    git commit -q -m "Researcher digest ${DATE}" \
      -m "Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
    echo "committed $DIGEST"
    [ -n "$PUSH" ] && { git push -q && echo "pushed"; } || true
  fi

  # 3) email the digest to the team (headless-safe; NOT the Gmail MCP).
  #    Render markdown -> HTML so the email reads as formatted text; the markdown
  #    is the plain-text fallback part. A render failure must not abort the send.
  HTML="$(uv run --project toolbox python "$ROOT/skills/researcher-daily-digest/render_email.py" "$DIGEST" 2>/dev/null || true)"
  if [ -n "$HTML" ]; then
    SEND=(--body-file "$DIGEST" --body-html "$HTML")
  else
    echo "html render failed; sending plain text"
    SEND=(--body-file "$DIGEST")
  fi
  if /sbin/gog gmail send -a "$FROM" --to "$RECIPIENTS" \
        --subject "Researcher digest, ${DATE}" "${SEND[@]}"; then
    echo "emailed digest to $RECIPIENTS"
  else
    echo "email step failed (digest still saved + committed)"
  fi
} >> "$LOG" 2>&1
