#!/usr/bin/env bash
# Daily reply scanner for all campaign logs.
#
# Scans Gmail for replies to every campaign log in ~/.blackwell/campaigns/,
# upserts new replies to Supabase, and syncs the Replied count to Notion.
#
# Install the daily cron (idempotent, safe to re-run):
#   skills/campaign/cron.sh --install
#
# Other flags:
#   --since-days N   look back N days in Gmail (default 7)
#   --no-classify    skip LLM sentiment classification
set -euo pipefail
cd "$(dirname "$0")/../.."
ROOT="$PWD"

SINCE_DAYS=7; NO_CLASSIFY=""; INSTALL=""
while [ $# -gt 0 ]; do case "$1" in
  --install)     INSTALL=1; shift;;
  --since-days)  SINCE_DAYS="$2"; shift 2;;
  --no-classify) NO_CLASSIFY="--no-classify"; shift;;
  *) echo "unknown arg: $1"; exit 2;;
esac; done

SELF="$ROOT/skills/campaign/cron.sh"

if [ -n "$INSTALL" ]; then
  if command -v crontab >/dev/null 2>&1; then
    LINE="0 23 * * * $SELF  # campaign-reply-scan"
    CUR="$(crontab -l 2>/dev/null || true)"
    if printf '%s\n' "$CUR" | grep -qF "# campaign-reply-scan"; then
      echo "cron already installed:"; printf '%s\n' "$CUR" | grep -F "# campaign-reply-scan"
      echo "edit with 'crontab -e' to change it."
    else
      printf '%s\n%s\n' "$CUR" "$LINE" | grep -v '^[[:space:]]*$' | crontab -
      echo "installed daily cron (23:00): $LINE"
    fi
  else
    echo "no crontab found. Add a daily job by hand:"
    echo "  0 23 * * * $SELF"
  fi
  exit 0
fi

LOG="$ROOT/runs/cron-campaign.log"; mkdir -p "$ROOT/runs"
{
  echo "=== campaign-reply-scan $(date -Is) ==="

  [ -f credentials/.env ] && { set -a; . credentials/.env; set +a; }

  : "${SUPABASE_URL:?set SUPABASE_URL in credentials/.env}"

  LOG_DIR="${HOME}/.blackwell/campaigns"
  if [ ! -d "$LOG_DIR" ]; then
    echo "no campaign logs dir at $LOG_DIR — nothing to scan"
    exit 0
  fi

  shopt -s nullglob
  LOGS=("$LOG_DIR"/campaign_*.jsonl)
  if [ ${#LOGS[@]} -eq 0 ]; then
    echo "no campaign logs found in $LOG_DIR"
    exit 0
  fi

  PYTHON="$ROOT/toolbox/.venv/bin/python"

  for log in "${LOGS[@]}"; do
    echo "--- scanning $log"
    "$PYTHON" skills/campaign/reply_scan.py \
      --log "$log" \
      --since-days "$SINCE_DAYS" \
      ${NO_CLASSIFY} || echo "scan failed for $log (exit $?)"
  done

  echo "done"
} >> "$LOG" 2>&1
