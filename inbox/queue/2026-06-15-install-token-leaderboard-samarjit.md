---
title: Install the token-leaderboard feeder on Samarjit's machine
created: 2026-06-15
created_by: Armaan
assignee: Samarjit
priority: normal
claimed_by:
claimed_at:
---

## Task

Get Samarjit onto the team token leaderboard. The board ranks how much each
person puts through Claude Code, pooled from local ccusage logs, and a person
appears only once their machine runs the daily feeder.

Follow the onboarding steps in `skills/token-leaderboard/SKILL.md`
("Onboarding a teammate"). In short: confirm `node` and `credentials/.env`
(needs `SUPABASE_URL` + `SUPABASE_PUBLISHABLE_KEY`), add
`LEADERBOARD_PERSON=Samarjit` to `credentials/.env`, run
`skills/token-leaderboard/cron.sh --dry` to verify, then run it once to seed
and `skills/token-leaderboard/cron.sh --install` for the daily feeder. Do not
use `--push`; that role is Armaan's machine only.

## Done when

Samarjit shows on the board: `select * from leaderboard` returns a row for
Samarjit, and `cron.sh --install` reports the daily job is scheduled.
