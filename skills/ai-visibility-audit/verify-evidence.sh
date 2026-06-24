#!/usr/bin/env bash
# ai-visibility-audit evidence gate.
# Usage: ./verify-evidence.sh <client-dir>   e.g. ./verify-evidence.sh agents/geo/ghostbed
#
# This is the anti-shortcut gate. An audit is NOT done until this prints PASS.
# It checks that the deterministic nine-phase run actually produced its
# artifacts on disk, not that someone wrote prose claiming it did. Every claim
# in the deck must have a file behind it here.
#
# Required artifact contract (same every run):
#   recon-<date>.md                      phase 1+2 truth table + crawlability (recon.sh output)
#   reputation-<date>.md                 phase 3 sentiment corpus notes
#   battery-log.md                       phase 5 per-engine, per-pass log (off + on)
#   assets/<engine>-*-on-*.png           phase 5 browsing-ON capture, one per engine
#   assets/<engine>-*-off-*.png          phase 5 browsing-OFF capture OR a documented
#                                        limitation line in battery-log.md
#   assets/reputation-<source>-*.png     phase 3 capture per sentiment source
#
# Engines (all six required for an ON capture):
ENGINES="chatgpt perplexity gemini claude googleaio copilot"
# Sentiment sources (capture or an explicit N/A line in reputation-<date>.md).
# youtube and retailer (Amazon/Sephora/Ulta/etc) are required too: the
# methodology corpus is Reddit, YouTube, Trustpilot, BBB, and retailer listings.
REP_SOURCES="trustpilot bbb consumeraffairs reddit youtube retailer"

set -uo pipefail
DIR="${1:?usage: verify-evidence.sh <client-dir>}"
DIR="${DIR%/}"
A="$DIR/assets"
fail=0
note(){ printf '  %-22s %s\n' "$1" "$2"; }

echo "# Evidence gate: $DIR"

# --- phase 1+2: recon truth table ---
if ls "$DIR"/recon-*.md >/dev/null 2>&1; then
  rf=$(ls -t "$DIR"/recon-*.md | head -1)
  if grep -qi "bot user-agents" "$rf" && grep -qi "Agentic commerce layer" "$rf"; then
    note "recon (phase 1+2)" "PASS ($rf)"
  else
    note "recon (phase 1+2)" "FAIL -$rf missing bot-UA matrix or agentic-layer section"; fail=1
  fi
else
  note "recon (phase 1+2)" "FAIL -no recon-<date>.md (run recon.sh > recon-<date>.md)"; fail=1
fi

# --- phase 6: competitor recon (same-day, same signals) ---
if ls "$DIR"/competitors-*.md >/dev/null 2>&1; then
  cf="$(ls -t "$DIR"/competitors-*.md | head -1)"
  ncomp=$(grep -ci "^# Recon:" "$cf")
  if [ "$ncomp" -ge 2 ]; then
    note "competitor recon" "PASS ($ncomp competitors in $cf)"
  else
    note "competitor recon" "FAIL -$cf has <2 competitor recon blocks (need recon.sh on each competitor)"; fail=1
  fi
else
  note "competitor recon" "FAIL -no competitors-<date>.md (run recon.sh on each competitor)"; fail=1
fi

# --- phase 3: reputation corpus ---
if ls "$DIR"/reputation-*.md >/dev/null 2>&1; then
  note "reputation notes" "PASS"
else
  note "reputation notes" "FAIL -no reputation-<date>.md"; fail=1
fi
for s in $REP_SOURCES; do
  if ls "$A"/reputation-"$s"-*.png >/dev/null 2>&1; then
    note "  rep:$s" "PASS (capture)"
  elif ls "$DIR"/reputation-*.md >/dev/null 2>&1 && grep -qiE "^[[:space:][:punct:]]*$s\b.*(N/A|not applicable|no profile|404|blocked, snippet)" "$DIR"/reputation-*.md; then
    note "  rep:$s" "PASS (documented N/A)"
  else
    note "  rep:$s" "FAIL -no assets/reputation-$s-*.png and no documented N/A line"; fail=1
  fi
done

# --- phase 5: engine battery, two passes ---
if [ -f "$DIR/battery-log.md" ]; then
  # The incognito requirement: a logged-in profile carries Memory and history that
  # inflate recommendability. The log must show clean sessions were used where
  # available, or name the contamination. Force the operator to address it.
  if grep -qiE "incognito|temporary chat|guest|contaminat" "$DIR/battery-log.md"; then
    note "battery-log.md" "PASS"
  else
    note "battery-log.md" "FAIL -battery-log.md never mentions incognito/temporary/guest/contamination (incognito-where-logged-in is required)"; fail=1
  fi
else
  note "battery-log.md" "FAIL -no battery-log.md (record engine/pass/incognito/result)"; fail=1
fi
for e in $ENGINES; do
  on=$(ls "$A"/"$e"-*-on-*.png 2>/dev/null | wc -l | tr -d ' ')
  off=$(ls "$A"/"$e"-*-off-*.png 2>/dev/null | wc -l | tr -d ' ')
  if [ "$on" -ge 1 ]; then
    if [ "$off" -ge 1 ]; then
      note "engine:$e" "PASS (on+off)"
    elif [ -f "$DIR/battery-log.md" ] && grep -qiE "$e.*(off|parametric).*(limitation|declined|login-gated|N/A)" "$DIR/battery-log.md"; then
      note "engine:$e" "PASS (on; off documented limitation)"
    else
      note "engine:$e" "FAIL -has ON capture but no OFF capture and no documented limitation"; fail=1
    fi
  else
    note "engine:$e" "FAIL -no assets/$e-*-on-*.png (browsing-ON battery capture missing)"; fail=1
  fi
done

echo
if [ "$fail" -eq 0 ]; then
  echo "RESULT: PASS -evidence complete, deck may ship to human sign-off."
  exit 0
else
  echo "RESULT: FAIL -do not ship. Missing artifacts above are shortcuts; run the phase, do not narrate it."
  exit 1
fi
