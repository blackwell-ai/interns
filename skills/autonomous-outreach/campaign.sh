#!/usr/bin/env bash
# One-command headless cold-email campaign. Source -> enrich -> filter -> send.
# Everything proven on 2026-06-10 (166 sends) baked in as defaults.
#
# Usage:
#   bash skills/autonomous-outreach/campaign.sh [--from <key>] [--domains <csv>]
#                                               [--min-score N] [--pace S] [--dry]
#
#   --from      co-founder short name: samarjit | armaan | ethan | shamit   (default samarjit)
#   --domains   domains CSV with a `domain` column (default: lead_bank.csv)
#   --min-score Hunter confidence floor (default 72)
#   --pace      seconds between sends (default 8)
#   --dry       enrich + build the queue, but DO NOT send (prints the queue size)
#
# Prereqs (all already satisfied after the 2026-06-10 setup):
#   - credentials/.env has TOOLBOX_TOKEN_HUNTER + SUPABASE_URL + SUPABASE_SECRET_KEY
#   - gog is authed for the sending account (keyring unlocked)
# Dedup is automatic via the Supabase suppression ledger — already-contacted
# people are skipped, so re-running over the same bank is always safe.
set -euo pipefail
cd "$(dirname "$0")/../.."
ROOT="$PWD"; DIR="skills/autonomous-outreach"

FROM_KEY="samarjit"; DOMAINS="$DIR/lead_bank.csv"; MIN=72; PACE=8; DRY=""; THOROUGH=""
while [ $# -gt 0 ]; do case "$1" in
  --from) FROM_KEY="$2"; shift 2;;
  --domains) DOMAINS="$2"; shift 2;;
  --min-score) MIN="$2"; shift 2;;
  --pace) PACE="$2"; shift 2;;
  --dry) DRY=1; shift;;
  --thorough) THOROUGH="--thorough"; shift;;   # 3 credits/domain, better founder precision
  *) echo "unknown arg: $1"; exit 2;;
esac; done

# co-founder short-name → address (case, not assoc array — macOS ships bash 3.2)
case "$FROM_KEY" in
  samarjit) SEND_ACCOUNT=samarjit.deshmukh.29@dartmouth.edu;;
  armaan)   SEND_ACCOUNT=armaan.priyadarshan.29@dartmouth.edu;;
  ethan)    SEND_ACCOUNT=ethanpzhou@berkeley.edu;;
  shamit)   SEND_ACCOUNT=shamitd@stanford.edu;;
  *)        SEND_ACCOUNT="$FROM_KEY";;   # allow passing a full address
esac

set -a; source credentials/.env; set +a
# resolve domains to an absolute path (accept absolute or repo-relative)
case "$DOMAINS" in /*) DOMAINS_ABS="$DOMAINS";; *) DOMAINS_ABS="$ROOT/$DOMAINS";; esac
[ -f "$DOMAINS_ABS" ] || { echo "domains file not found: $DOMAINS_ABS"; exit 1; }
STAMP="$(date +%Y%m%d-%H%M%S)"
ENRICHED="$ROOT/$DIR/run_${STAMP}_enriched.csv"
QUEUE="$ROOT/$DIR/run_${STAMP}_queue.csv"

# Persistent enrichment cache: each domain costs a Hunter credit ONCE, ever.
# Re-runs and the growing lead bank are then free. (gitignored — holds emails.)
CACHE="$ROOT/$DIR/enrichment_cache.jsonl"
echo "1/3  enrich: find-exec over $(tail -n +2 "$DOMAINS_ABS" | wc -l | tr -d ' ') domains"
echo "     (1 Hunter credit/new domain; cached domains free.${THOROUGH:+  --thorough: 3/domain})"
( cd toolbox && TOOLBOX_RUN_DIR=/tmp uv run python -m toolbox.primitives.findemail.cli find-exec \
    --in "$DOMAINS_ABS" --out "$ENRICHED" --min-score "$MIN" --concurrency 5 \
    --cache "$CACHE" $THOROUGH )

echo "2/3  filter -> send queue"
python3 "$DIR/prep_queue.py" "$ENRICHED" "$QUEUE"

N=$(tail -n +2 "$QUEUE" | wc -l | tr -d ' ')
if [ -n "$DRY" ]; then
  echo "DRY RUN: $N leads ready in $QUEUE (not sent). Re-run without --dry to send."
  exit 0
fi

echo "3/3  send from $SEND_ACCOUNT (HTML, co-founders CC'd, ledger-deduped, ${PACE}s pacing)"
echo "     progress = ledger count, NOT Gmail search (which lags minutes). See harness/learnings/03."
SEND_ACCOUNT="$SEND_ACCOUNT" PACE="$PACE" IDLE_CYCLES=1 \
  python3 "$DIR/send_fast.py" "$QUEUE"
