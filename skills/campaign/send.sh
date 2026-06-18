#!/usr/bin/env bash
# Non-interactive campaign send.
#
# Distributes N emails across the ICPs in icp_mix.toml (each segment using its
# own template) and CCs the cofounders who are not the sender, per FOUNDERS.md.
# This is the entrypoint behind the /campaign slash command.
#
# Usage: send.sh <total_emails> [sender_key]
#   sender_key: samarjit (default) | armaan | ethan | shamit
set -euo pipefail

N="${1:?usage: send.sh <total_emails> [sender_key]}"
SENDER_KEY="${2:-samarjit}"

# Repo root is two levels up from this script (skills/campaign/ -> repo).
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

# Load shared credentials: SUPABASE_*, TOOLBOX_TOKEN_HUNTER, NOTION_TOKEN.
# run.py does not auto-load .env, so the values must be in the environment.
set -a; source credentials/.env; set +a

# Ensure ~/.blackwell/session.json exists so cron reply scan can auth headlessly.
toolbox/.venv/bin/python skills/campaign/ensure_session_file.py || exit 1

# Founder roster + the "CC everyone but the sender" convention.
# Canonical doc: skills/campaign/FOUNDERS.md. Kept here as a flat list so the
# script stays portable (no bash 4 associative arrays needed on macOS).
ROSTER="samarjit:samarjit.deshmukh.29@dartmouth.edu \
armaan:armaan.priyadarshan.29@dartmouth.edu \
ethan:ethanpzhou@berkeley.edu \
shamit:shamitd@stanford.edu"

FROM=""; CC=""
for pair in $ROSTER; do
  k="${pair%%:*}"; addr="${pair#*:}"
  if [ "$k" = "$SENDER_KEY" ]; then
    FROM="$addr"
  else
    CC="${CC:+$CC,}$addr"
  fi
done
if [ -z "$FROM" ]; then
  echo "Unknown sender '$SENDER_KEY' — use one of: samarjit armaan ethan shamit" >&2
  exit 1
fi

case "$SENDER_KEY" in
  samarjit) NAME="Samarjit Deshmukh";;
  armaan)   NAME="Armaan Priyadarshan";;
  ethan)    NAME="Ethan Zhou";;
  shamit)   NAME="Shamit";;
esac

echo "Campaign: $N emails as $NAME <$FROM>"
echo "CC: $CC"
echo "Distribution: per icp_mix.toml"
echo

exec toolbox/.venv/bin/python skills/campaign/run.py \
  --provider hunter \
  --from "$FROM" --from-name "$NAME" \
  --cc "$CC" \
  --limit "$N" \
  --concurrency 12
