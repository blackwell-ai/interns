---
title: Install the token-leaderboard feeder on Shamit's machine
created: 2026-06-15
created_by: Armaan
assignee: Shamit
priority: normal
claimed_by: Shamit
claimed_at: 2026-06-16
---

## Task

Get Shamit onto the team token leaderboard. The board ranks how much each
person puts through Claude Code, pooled from local ccusage logs, and a person
appears only once their machine runs the daily feeder.

Follow the onboarding steps in `skills/token-leaderboard/SKILL.md`
("Onboarding a teammate"). In short: confirm `node` and `credentials/.env`
(needs `SUPABASE_URL` + `SUPABASE_PUBLISHABLE_KEY`), add
`LEADERBOARD_PERSON=Shamit` to `credentials/.env`, run
`skills/token-leaderboard/cron.sh --dry` to verify, then run it once to seed
and `skills/token-leaderboard/cron.sh --install` for the daily feeder. Do not
use `--push`; that role is Armaan's machine only.

## Done when

Shamit shows on the board: `select * from leaderboard` returns a row for
Shamit, and `cron.sh --install` reports the daily job is scheduled.

## Result

Created `credentials/.env` from `.env.example`, added `SUPABASE_URL`,
`SUPABASE_PUBLISHABLE_KEY`, and `LEADERBOARD_PERSON=Shamit`. Verified with
`cron.sh --dry`, then ran `cron.sh` once (upserted 16 days of history to
Supabase) and `cron.sh --install` (daily cron at 23:00, no `--push`).

Verified: `leaderboard.mjs --once --window 30d` shows Shamit at rank 2 (52.1M
tokens, 628.5K driven, 16 days). `crontab -l` confirms the job is registered.
