-- Token leaderboard: one row per person per day of Claude Code usage.
--
-- Source of truth is each person's local Claude Code logs, read by ccusage
-- (npx ccusage claude daily --json). The collector upserts one row per day
-- here; the leaderboard view pools every person's rows into a ranked board.
-- There is no org-level view across separate Claude Max subscriptions, so the
-- board has to be assembled from rows each machine pushes on its own.
--
-- Trust model (deliberate, internal tool): rows are low-sensitivity token
-- counts, not a bill and not PII. Identity is the `person` string the
-- collector stamps. The anon key is a public client identifier (see
-- supabase/README.md), so anon may read the board and upsert its own daily
-- rows. That means a person with the anon key could in principle write a row
-- under someone else's name, the same trust a shared sheet carries. The
-- hardening path is wired but dormant: `user_id` is here now so we can later
-- require authenticated writes (user_id = auth.uid()) without a migration that
-- rewrites existing rows. See the commented policy at the bottom.

create table if not exists daily_usage (
  id                     uuid primary key default gen_random_uuid(),
  person                 text not null,                 -- display identity, e.g. 'Armaan'
  day                    date not null,                 -- ccusage row date, person-local
  user_id                uuid references auth.users(id),-- null today; for the hardening path
  -- token columns mirror ccusage field names one-to-one (v20.x camelCase,
  -- mapped to snake_case here). bigint: a heavy day is ~300M+ tokens.
  input_tokens           bigint not null default 0,     -- ccusage inputTokens
  output_tokens          bigint not null default 0,     -- ccusage outputTokens
  cache_creation_tokens  bigint not null default 0,     -- ccusage cacheCreationTokens
  cache_read_tokens      bigint not null default 0,     -- ccusage cacheReadTokens
  total_tokens           bigint not null default 0,     -- ccusage totalTokens (the rank key)
  -- ccusage totalCost: price-weighted equivalent, NOT a charged amount. We are
  -- on a flat Max subscription. Stored as a secondary intensity signal only.
  total_cost             numeric not null default 0,
  models                 text[] not null default '{}',  -- ccusage modelsUsed
  ccusage_version        text not null default '',       -- guards the field-drift failure mode
  updated_at             timestamptz not null default now(),
  unique (person, day)                                  -- the upsert key: one row per person per day
);

create index if not exists daily_usage_day_idx on daily_usage (day);

alter table daily_usage enable row level security;

-- Team board: everyone reads, every collector upserts its own day. No delete
-- policy, so rows can only be corrected by re-upsert, never silently dropped.
create policy daily_usage_select on daily_usage
  for select to anon, authenticated using (true);

create policy daily_usage_insert on daily_usage
  for insert to anon, authenticated with check (true);

create policy daily_usage_update on daily_usage
  for update to anon, authenticated using (true) with check (true);

-- The pooled board: one row per person, ranked by lifetime total tokens.
-- security_invoker so it respects the base-table RLS above (and avoids the
-- security-definer-view advisor warning). Windowed columns (7d/30d) let the
-- HTML offer a recent-activity toggle without a second query.
create or replace view leaderboard
with (security_invoker = on) as
select
  person,
  sum(total_tokens)                                                      as total_tokens,
  sum(input_tokens)                                                      as input_tokens,
  sum(output_tokens)                                                     as output_tokens,
  sum(cache_creation_tokens)                                             as cache_creation_tokens,
  sum(cache_read_tokens)                                                 as cache_read_tokens,
  sum(total_cost)                                                        as total_cost,
  sum(total_tokens) filter (where day >= current_date - 7)              as tokens_7d,
  sum(total_tokens) filter (where day >= current_date - 30)             as tokens_30d,
  count(*)                                                               as days_active,
  min(day)                                                              as first_active,
  max(day)                                                              as last_active
from daily_usage
group by person
order by total_tokens desc;

grant select on leaderboard to anon, authenticated;

-- Hardening path (enable once the collector carries a per-person Supabase
-- session and stamps user_id): replace the open insert/update policies above
-- with writes scoped to the signed-in user.
--
--   drop policy daily_usage_insert on daily_usage;
--   drop policy daily_usage_update on daily_usage;
--   create policy daily_usage_write_own on daily_usage
--     for all to authenticated
--     using (user_id = (select auth.uid()))
--     with check (user_id = (select auth.uid()));
