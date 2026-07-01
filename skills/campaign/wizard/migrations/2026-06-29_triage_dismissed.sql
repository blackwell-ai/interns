-- Triage dismiss list: people a human has marked 'not relevant', so the reply
-- triage stops surfacing them in any bucket (server/triage_dismiss.py).
--
-- This is NOT contacted-ledger suppression: dismissing here only hides a person
-- from triage; campaign sending is untouched. Read/written exclusively with the
-- service-role key, so RLS is on with no policies (the service role bypasses it,
-- and no per-user client should see or change the list).
--
-- Apply once against the production Supabase Postgres (SQL editor or psql).

create table if not exists public.triage_dismissed (
    recipient    text primary key,                       -- canonical (lowercased) email
    reason       text        not null default '',
    dismissed_by text        not null default '',         -- slack user id who dismissed
    active       boolean     not null default true,       -- 'undo' flips this to false
    created_at   timestamptz not null default now()
);

alter table public.triage_dismissed enable row level security;

-- Index the common read: load_dismissed() filters active = true.
create index if not exists triage_dismissed_active_idx
    on public.triage_dismissed (active);
