-- Voice cards: a short per-founder voice guide (tone, sentence length, sign-off,
-- how they hedge) distilled from their sent mail, injected into the reply-draft
-- prompt alongside the retrieved exemplars so a novel question still sounds like
-- the founder (wizard/voice_cards.py). One row per founder, refreshable.
--
-- Distilled from real correspondence: written/read only with the service-role
-- key, so RLS is on with no policies. Apply once against production Supabase.

create table if not exists public.voice_cards (
    founder    text primary key,                  -- sender key: armaan | samarjit | ethan
    card       text        not null default '',    -- the distilled voice guide
    updated_at timestamptz not null default now()
);

alter table public.voice_cards enable row level security;
