# token-leaderboard

**Purpose:** a team view of how much each person is putting through Claude
Code, ranked. Everyone is on Claude Max 20x, a flat subscription, so this is
about usage and relative intensity, not a bill.

**Why it is assembled this way:** the Anthropic Console does not show per-token
usage for Pro or Max subscribers, so the only source is the local Claude Code
logs on each machine (the JSONL files under `~/.claude/projects`, newer installs
under `~/.config/claude/projects`). ccusage reads those logs. There is no
org-level view across separate Max subscriptions, so each person pushes their
own daily numbers to Supabase and the board reads a pooled view. One member not
running the collector means that member is missing from the board.
Source: https://github.com/ryoppippi/ccusage.

## Parts

- `collect-usage.mjs` (this dir): runs per person, calls
  `npx ccusage claude daily --json`, upserts one row per day into `daily_usage`,
  then re-renders the snapshot. Reads `SUPABASE_URL` and `SUPABASE_KEY` from the
  environment at runtime, never from the repo. Zero dependencies (bare `node`).
- `supabase/migrations/0003_daily_usage.sql`: the `daily_usage` table and the
  `leaderboard` view. This is the repo-native home of the schema (the spec calls
  it `schema.sql`).
- `token-leaderboard.html` (this dir): the interactive board. Set its `DATA_URL`
  to the Supabase `leaderboard` view (and `SUPABASE_KEY` to the anon key), or to
  a committed `usage.json`.
- `cron.sh` (this dir): the daily runner and installer. Sources
  `credentials/.env`, runs the collector, and registers the schedule. See
  Automation below.
- `brain/metrics/LEADERBOARD.md`: the committed snapshot, regenerated on each
  collector run, so the durable record lives in the repo even though the live
  board is interactive.

## Setup

One-time (human, hosted project): apply the migration with the rest of the repo
schema.

    supabase db push        # applies supabase/migrations/, including 0003

Per person, export the project URL and the anon key (the anon key is a public
client identifier; RLS guards the table, see `supabase/README.md`):

    export SUPABASE_URL="https://<ref>.supabase.co"
    export SUPABASE_KEY="<anon key>"

## How to run

Each machine runs the collector daily (cron, or a harness skill run):

    PERSON="<name>" SUPABASE_URL="..." SUPABASE_KEY="..." \
      node skills/token-leaderboard/collect-usage.mjs --since 20260101

Useful flags: `--dry-run` prints the mapped rows and writes nothing (good for a
first check on a new machine), `--no-snapshot` skips the markdown re-render,
`--snapshot <path>` overrides where the snapshot is written. Any other flags
(for example `--until`) pass straight through to ccusage.

To view the board, open `token-leaderboard.html` after setting `DATA_URL` and
`SUPABASE_KEY` at the top of the file.

## Automation (daily)

`cron.sh` is the daily runner. It has two roles:

- Feeder (default, every teammate): pushes this machine's usage to Supabase.
  No git and no working-tree changes, so it is safe on any machine, including
  one with unrelated work in progress.
- Canonical (`--push`, one machine): also regenerates, commits, and pushes
  `brain/metrics/LEADERBOARD.md`. It only writes that one shared file when the
  tree is otherwise clean, so a background run never commits over work in
  progress. Only one machine should take this role.

Install the daily 23:00 job (idempotent, safe to re-run). It uses `crontab`
where present and falls back to a systemd user timer on machines without cron
(for example Arch):

    skills/token-leaderboard/cron.sh --install          # feeder
    skills/token-leaderboard/cron.sh --install --push   # canonical snapshot host

On a systemd machine, confirm with `systemctl --user list-timers
token-leaderboard.timer`. For it to run while logged out, linger must be on
(`sudo loginctl enable-linger <user>`). Other flags: `--dry` (run ccusage and
print mapped rows, write nothing), `--since YYYYMMDD`.

## Onboarding a teammate (any agent can do this)

Every person shows up on the board only if their machine runs the feeder. An
agent can set this up end to end for its human:

1. Confirm `node` (v18+) is available and the repo is cloned.
2. Confirm `credentials/.env` has `SUPABASE_URL` and `SUPABASE_PUBLISHABLE_KEY`
   (distributed out-of-band, the same file the other automations read).
3. Add the person's board name, using the first name from
   `brain/people/team.md` (Armaan, Samarjit, Ethan, Shamit) so labels stay
   consistent:

       printf 'LEADERBOARD_PERSON=<First>\n' >> credentials/.env

4. Verify wiring with `skills/token-leaderboard/cron.sh --dry` (writes nothing).
5. Seed and schedule: run `skills/token-leaderboard/cron.sh` once to push
   history, then `skills/token-leaderboard/cron.sh --install` for the daily
   feeder. Leave `--push` to the single canonical host.

## Outputs

Daily rows in `daily_usage`, the `leaderboard` view (one row per person, ranked
by lifetime total tokens, with 7-day and 30-day windows), and the regenerated
`brain/metrics/LEADERBOARD.md`. The HTML and the collector are ephemeral; the
snapshot, the migration, and this file are the durable asset.

## Reading the numbers

Total tokens is the rank key and is cache-read heavy by nature: each turn
replays the conversation as cache reads, so a long session accrues hundreds of
millions of read tokens without much new work. The board also shows "driven"
(input plus output), which tracks effort more closely, and stores `total_cost`,
the price-weighted equivalent ccusage computes. That cost is a relative
intensity signal only, not a charged amount.

## Check before relying on this

Confirm the harness runs first-party Claude Code. The April 2026 policy change
blocked Pro and Max subscribers from third-party agent frameworks, and usage
routed outside Claude Code may not appear in the logs ccusage reads. This repo's
LLM steps run headless Claude Code (`claude -p`), which is first-party, so they
are captured. If any automation is billed through the API instead of a
subscription, that usage shows in the Console and needs the Usage and Cost Admin
API, separate from this board.

## Failure mode: ccusage field drift

ccusage field names have changed across releases. The collector maps the v20.x
camelCase names (`inputTokens`, `outputTokens`, `cacheCreationTokens`,
`cacheReadTokens`, `totalTokens`, `totalCost`) and falls back to snake_case
spellings. If a token column reads zero after a ccusage update, the collector
prints a loud warning with a sample row; add the new field name to the `pick()`
calls in `toRow()`. The `ccusage_version` column records which release wrote
each row, so a regression is easy to date.

## Trust model

Rows are low-sensitivity token counts, not a bill and not PII. The collector
authenticates with the anon key and stamps the `person` string, so writes are
not tied to a signed-in identity. A person with the anon key could in principle
write a row under another name, the same trust a shared sheet carries, which is
fine for an internal board. The migration carries a dormant `user_id` column and
a commented hardening policy: once the collector carries a per-person Supabase
session, switch writes to `user_id = auth.uid()` without a rewrite of existing
rows.
