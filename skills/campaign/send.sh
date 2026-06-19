#!/usr/bin/env bash
# Non-interactive campaign send.
#
# Distributes N emails across the ICPs in icp_mix.toml (each segment using its
# own template) and CCs the cofounders who are not the sender, per FOUNDERS.md.
# This is the entrypoint behind the /campaign slash command.
#
# Usage: send.sh <total_emails> [sender_key] [provider]
#   sender_key: samarjit (default) | armaan | ethan | shamit
#   provider  : hunter (default) | apollo  -- source that finds + verifies emails
#
# The provider may also be given alone in the sender slot, so `send.sh 1000
# apollo` keeps the default sender and just switches the email provider.
set -euo pipefail

N="${1:?usage: send.sh <total_emails> [sender_key] [provider]}"
ARG2="${2:-}"
ARG3="${3:-}"

# Resolve sender + provider from the two optional positionals. A positional that
# names a provider (hunter/apollo) is read as the provider; anything else is the
# sender key. So `... armaan apollo`, `... apollo`, and `... armaan` all work.
SENDER_KEY="samarjit"
PROVIDER="hunter"
for a in "$ARG2" "$ARG3"; do
  [ -z "$a" ] && continue
  case "$a" in
    hunter|apollo) PROVIDER="$a" ;;
    *)             SENDER_KEY="$a" ;;
  esac
done

# Repo root is two levels up from this script (skills/campaign/ -> repo).
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

# Load shared credentials: SUPABASE_*, NOTION_TOKEN, and the provider key in use
# (TOOLBOX_TOKEN_HUNTER or TOOLBOX_TOKEN_APOLLO).
# run.py does not auto-load .env, so the values must be in the environment.
set -a; source credentials/.env; set +a

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
echo "Provider: $PROVIDER"
echo "Distribution: per icp_mix.toml"
echo

exec toolbox/.venv/bin/python -u skills/campaign/run.py \
  --provider "$PROVIDER" \
  --from "$FROM" --from-name "$NAME" \
  --cc "$CC" \
  --limit "$N" \
  --concurrency 12
