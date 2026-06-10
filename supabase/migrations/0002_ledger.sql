-- M0: the contact ledger (spec §7, build plan §3.4).
--
-- The scenario this makes impossible: person A's automation emails C on
-- Monday; person X's unrelated automation tries C on Wednesday → X's run
-- silently skips C, with no coordination between A and X. The guarantee is
-- the UNIQUE constraint — the database physically refuses a second row —
-- and claim_contact makes suppression-check + insert one atomic statement
-- (no check-then-act race, and RLS never exposes others' rows to make the
-- conflict check work).

create table if not exists contacted (
  id           uuid primary key default gen_random_uuid(),
  channel      text not null,                 -- 'email' | 'discord' | 'linkedin' | ...
  recipient    text not null,                 -- canonical: lowercased, trimmed
  status       text not null check (status in ('claimed', 'sent', 'failed')),
  sent_by      uuid not null references auth.users(id),
  skill        text not null default '',
  run_id       text not null default '',
  message_hash text not null default '',
  recontacted  boolean not null default false, -- loud marker for force_claim
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (channel, recipient)                  -- THE invariant
);

create table if not exists suppression (
  channel    text not null,
  recipient  text not null,
  reason     text not null default '',
  created_at timestamptz not null default now(),
  primary key (channel, recipient)
);

-- Cross-machine run liveness: the reaper must distinguish a *paused* run
-- (canary gate — keeps its claims for hours, legitimately) from a *dead* one.
-- status.json on a laptop can't be seen from another machine, so heartbeats
-- live here (plan §3.4, correcting spec's "release after 1h").
create table if not exists runs (
  run_id       text primary key,
  skill        text not null default '',
  owner        uuid not null references auth.users(id),
  state        text not null check (state in ('running', 'paused', 'done', 'failed')),
  heartbeat_at timestamptz not null default now(),
  created_at   timestamptz not null default now()
);

alter table contacted enable row level security;
alter table suppression enable row level security;
alter table runs enable row level security;

-- Reads: own sends only (privacy); the cross-person guarantee does NOT need
-- read access — it's enforced inside the functions below.
create policy contacted_select_own on contacted
  for select to authenticated using (sent_by = (select auth.uid()));

-- Suppression list is team-visible (any member may need to honor/record opt-outs).
create policy suppression_select on suppression for select to authenticated using (true);

create policy runs_select on runs for select to authenticated using (true);

-- No direct write policies anywhere: ALL writes go through the SECURITY
-- DEFINER functions below, so no generated flow can bypass the rules.

-- -> 'claimed' | 'skipped' | 'suppressed'
create or replace function claim_contact(
  p_channel text, p_recipient text, p_skill text default '', p_run_id text default ''
) returns text
language plpgsql security definer set search_path = public as $$
declare
  v_recipient text := lower(trim(p_recipient));
  v_inserted  int;
begin
  if exists (select 1 from suppression where channel = p_channel and recipient = v_recipient) then
    return 'suppressed';
  end if;
  insert into contacted (channel, recipient, status, sent_by, skill, run_id)
  values (p_channel, v_recipient, 'claimed', auth.uid(), p_skill, p_run_id)
  on conflict (channel, recipient) do nothing;
  get diagnostics v_inserted = row_count;
  return case when v_inserted = 1 then 'claimed' else 'skipped' end;
end $$;

-- allow_recontact path: takes over an existing row instead of skipping.
-- Deliberate, logged loudly (recontacted flag + notice). Suppression still wins.
create or replace function force_claim_contact(
  p_channel text, p_recipient text, p_skill text default '', p_run_id text default ''
) returns text
language plpgsql security definer set search_path = public as $$
declare
  v_recipient text := lower(trim(p_recipient));
begin
  if exists (select 1 from suppression where channel = p_channel and recipient = v_recipient) then
    return 'suppressed';
  end if;
  insert into contacted (channel, recipient, status, sent_by, skill, run_id, recontacted)
  values (p_channel, v_recipient, 'claimed', auth.uid(), p_skill, p_run_id, false)
  on conflict (channel, recipient) do update
    set status = 'claimed', sent_by = auth.uid(), skill = excluded.skill,
        run_id = excluded.run_id, recontacted = true, updated_at = now();
  raise notice 'RECONTACT: % % by % (skill %)', p_channel, v_recipient, auth.uid(), p_skill;
  return 'claimed';
end $$;

-- Read-only, for --dry-run reporting. -> 'new' | 'contacted' | 'suppressed'
create or replace function check_contact(p_channel text, p_recipient text) returns text
language plpgsql security definer stable set search_path = public as $$
declare v_recipient text := lower(trim(p_recipient));
begin
  if exists (select 1 from suppression where channel = p_channel and recipient = v_recipient) then
    return 'suppressed';
  end if;
  if exists (select 1 from contacted where channel = p_channel and recipient = v_recipient) then
    return 'contacted';
  end if;
  return 'new';
end $$;

-- Status updates only on rows your own runs claimed (no cross-user tampering).
create or replace function mark_contact(
  p_channel text, p_recipient text, p_status text, p_message_hash text default ''
) returns void
language plpgsql security definer set search_path = public as $$
begin
  if p_status not in ('sent', 'failed') then
    raise exception 'invalid status %', p_status;
  end if;
  update contacted
     set status = p_status, message_hash = p_message_hash, updated_at = now()
   where channel = p_channel and recipient = lower(trim(p_recipient))
     and sent_by = auth.uid();
end $$;

create or replace function suppress_contact(p_channel text, p_recipient text, p_reason text)
returns void
language plpgsql security definer set search_path = public as $$
begin
  insert into suppression (channel, recipient, reason)
  values (p_channel, lower(trim(p_recipient)), p_reason)
  on conflict (channel, recipient) do nothing;
end $$;

create or replace function run_heartbeat(p_run_id text, p_skill text, p_state text)
returns void
language plpgsql security definer set search_path = public as $$
begin
  insert into runs (run_id, skill, owner, state, heartbeat_at)
  values (p_run_id, p_skill, auth.uid(), p_state, now())
  on conflict (run_id) do update
    set state = excluded.state, heartbeat_at = now();
end $$;

-- The reaper (runner startup): release claims whose run is dead — no
-- heartbeat for >10 min AND not paused — or whose run was never registered
-- and the claim is >10 min old (hard crash before first heartbeat).
-- Never touches 'sent'/'failed' rows, so a release can't enable a double-send
-- of something already sent.
create or replace function release_stale_claims() returns integer
language plpgsql security definer set search_path = public as $$
declare v_count int;
begin
  delete from contacted c
   where c.status = 'claimed'
     and (
       exists (select 1 from runs r where r.run_id = c.run_id
                 and r.state in ('failed')
       )
       or exists (select 1 from runs r where r.run_id = c.run_id
                 and r.state = 'running' and r.heartbeat_at < now() - interval '10 minutes')
       or (not exists (select 1 from runs r where r.run_id = c.run_id)
           and c.created_at < now() - interval '10 minutes')
     );
  get diagnostics v_count = row_count;
  return v_count;
end $$;

-- RPCs are callable by signed-in people only.
revoke execute on all functions in schema public from anon;
grant execute on function claim_contact(text, text, text, text) to authenticated;
grant execute on function force_claim_contact(text, text, text, text) to authenticated;
grant execute on function check_contact(text, text) to authenticated;
grant execute on function mark_contact(text, text, text, text) to authenticated;
grant execute on function suppress_contact(text, text, text) to authenticated;
grant execute on function run_heartbeat(text, text, text) to authenticated;
grant execute on function release_stale_claims() to authenticated;
