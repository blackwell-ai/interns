---
description: Show the team Claude Code token leaderboard
allowed-tools: Bash(node:*)
---

Below is the current team token leaderboard (how much each person is putting
through Claude Code over the last 7 days, ranked, pooled from everyone's local
logs via Supabase). It first refreshes your own usage, so your number is live.

!`node skills/token-leaderboard/leaderboard.mjs --once --window 7d --refresh`

Show the board above to the user in a fenced code block, exactly as produced,
with no edits. Add at most one short line if anything stands out. The full
interactive version (auto-refresh, window toggles) runs in a real terminal with
`node skills/token-leaderboard/leaderboard.mjs`.
