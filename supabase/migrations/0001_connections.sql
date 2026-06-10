-- M0.1/M0.2: per-person provider connections (spec §8).
-- Metadata is client-visible (own rows only, via RLS). Secrets live in a
-- separate table with NO client policies at all — only edge functions
-- (service role) touch them. Two tables instead of column grants because
-- PostgREST's handling of column-level privileges is easy to get wrong.

create table if not exists connections (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid not null references auth.users(id) on delete cascade,
  provider    text not null,          -- 'gmail' | 'apollo' | 'storeleads' | 'anthropic' | ...
  account     text not null default '', -- e.g. the gmail address connected
  kind        text not null check (kind in ('oauth', 'api_key')),
  org_shared  boolean not null default false, -- team-wide key (e.g. shared Apollo)
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now(),
  unique (user_id, provider, account)
);

create table if not exists connection_secrets (
  connection_id uuid primary key references connections(id) on delete cascade,
  secret        text not null,        -- refresh token or API key; encrypted at rest by Supabase
  updated_at    timestamptz not null default now()
);

-- Transient state for the second OAuth consent (gmail scopes).
create table if not exists oauth_states (
  state      text primary key,
  user_id    uuid not null references auth.users(id) on delete cascade,
  provider   text not null,
  created_at timestamptz not null default now()
);

alter table connections enable row level security;
alter table connection_secrets enable row level security;
alter table oauth_states enable row level security;

-- connections metadata: a person sees their own rows plus org-shared ones.
create policy connections_select on connections
  for select to authenticated
  using (user_id = (select auth.uid()) or org_shared);

-- Inserts/updates/deletes go through edge functions (service role bypasses
-- RLS), so no write policies for authenticated.
-- connection_secrets and oauth_states: no policies at all → clients can
-- never read or write them; only the service role can.
