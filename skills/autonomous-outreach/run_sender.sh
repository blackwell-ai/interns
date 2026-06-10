#!/usr/bin/env bash
# Autonomous outreach sender — one clean command to allow-list.
# Sources credentials itself, then drains the verified-contact queue.
# Usage: bash skills/autonomous-outreach/run_sender.sh [queue.csv]
# Defaults to skills/autonomous-outreach/last_queue.csv.
set -euo pipefail
cd "$(dirname "$0")/../.."
export GOG_KEYRING_PASSWORD="$(grep '^GOG_KEYRING_PASSWORD=' credentials/.env | cut -d= -f2 | awk '{print $1}')"
export $(grep -E '^SUPABASE_(URL|SECRET_KEY)=' credentials/.env | sed 's/ *#.*//' | xargs)
QUEUE="${1:-skills/autonomous-outreach/last_queue.csv}"
exec env PACE="${PACE:-6}" IDLE_CYCLES="${IDLE_CYCLES:-30}" \
     python3 skills/autonomous-outreach/send_fast.py "$QUEUE"
