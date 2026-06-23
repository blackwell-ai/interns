#!/usr/bin/env bash
# Send N emails split evenly across all three student senders.
#
# Divides N by 3 (floor), then runs one send per account sequentially.
# Sequential keeps LLM domain generation from throttling (three concurrent
# claude -p calls are slower than one at a time per account).
#
# The Supabase ledger is shared, so contacts never overlap across the three runs.
#
# Usage: send_all.sh <total_emails> [provider]
#   provider: hunter (default) | apollo
#
# Example:
#   bash skills/campaign/send_all.sh 2100          # 700 each, Hunter
#   bash skills/campaign/send_all.sh 2100 apollo   # 700 each, Apollo
set -euo pipefail

TOTAL="${1:?usage: send_all.sh <total_emails> [provider]}"
PROVIDER="${2:-hunter}"

# Validate provider
case "$PROVIDER" in
  hunter|apollo) ;;
  *) echo "Unknown provider '$PROVIDER' — use hunter or apollo" >&2; exit 1 ;;
esac

# Three senders in rotation order.
SENDERS="samarjit armaan ethan"
N_SENDERS=3

PER=$(( TOTAL / N_SENDERS ))
if [ "$PER" -lt 1 ]; then
  echo "Total too small — need at least $N_SENDERS emails" >&2
  exit 1
fi

# Any remainder goes to the first sender (e.g. 2101 -> 701, 700, 700).
REMAINDER=$(( TOTAL - PER * N_SENDERS ))

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

set -a; source credentials/.env; set +a

ROSTER="samarjit:samarjit.deshmukh.29@dartmouth.edu \
armaan:armaan.priyadarshan.29@dartmouth.edu \
ethan:ethanpzhou@berkeley.edu \
shamit:shamitd@stanford.edu"

get_addr() {
  for pair in $ROSTER; do
    [ "${pair%%:*}" = "$1" ] && echo "${pair#*:}" && return
  done
  echo ""
}

get_name() {
  case "$1" in
    samarjit) echo "Samarjit Deshmukh";;
    armaan)   echo "Armaan Priyadarshan";;
    ethan)    echo "Ethan Zhou";;
    shamit)   echo "Shamit";;
  esac
}

get_cc() {
  local sender="$1"; local cc=""
  for pair in $ROSTER; do
    local k="${pair%%:*}"; local addr="${pair#*:}"
    [ "$k" != "$sender" ] && cc="${cc:+$cc,}$addr"
  done
  echo "$cc"
}

echo "=============================="
echo " Split send: $TOTAL emails"
echo " Per sender: $PER (remainder +$REMAINDER to first)"
echo " Provider:   $PROVIDER"
echo "=============================="
echo

IDX=0
for SENDER_KEY in $SENDERS; do
  LIMIT=$PER
  [ "$IDX" -eq 0 ] && LIMIT=$(( PER + REMAINDER ))

  FROM="$(get_addr "$SENDER_KEY")"
  NAME="$(get_name "$SENDER_KEY")"
  CC="$(get_cc "$SENDER_KEY")"

  echo "── Sender $((IDX+1))/$N_SENDERS: $NAME <$FROM>  ($LIMIT emails) ──"
  echo

  toolbox/.venv/bin/python -u skills/campaign/run.py \
    --provider "$PROVIDER" \
    --from "$FROM" --from-name "$NAME" \
    --cc "$CC" \
    --limit "$LIMIT" \
    --concurrency 12

  echo
  echo "── Done: $NAME ──"
  echo

  IDX=$(( IDX + 1 ))
done

echo "=============================="
echo " All senders done."
echo "=============================="
