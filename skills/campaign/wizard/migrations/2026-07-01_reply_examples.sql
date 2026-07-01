-- Reply examples: (incoming email, the reply we sent) pairs, used as
-- retrieval-augmented few-shot exemplars when drafting a founder's reply in the
-- Slack /respond review queue (wizard/reply_examples.py, wizard/reply_drafter.py).
--
-- Two sources. 'harvest' rows are backfilled from each founder's Gmail Sent
-- folder (harvest_reply_examples.py). 'queue' rows are written back every time a
-- founder edits Claude's draft and sends it from the queue, so the corpus
-- compounds toward what founders actually choose to send; those are marked gold.
--
-- Bodies are real prospect correspondence: written and read ONLY with the
-- service-role key, so RLS is on with no policies (the service role bypasses it,
-- and no per-user client should see this). Never log the body columns.
--
-- Apply once against the production Supabase Postgres (SQL editor or psql).

create table if not exists public.reply_examples (
    id               bigint generated always as identity primary key,
    founder          text        not null,                 -- sender key: armaan | samarjit | ethan
    category         text        not null,                 -- pricing | capabilities | scheduling | objection | referral | other
    incoming_subject text        not null default '',
    incoming_body    text        not null default '',      -- the prospect message we answered
    reply_body       text        not null default '',      -- what we actually sent
    sentiment        text        not null default 'unknown',-- of the thread, for curation
    source           text        not null,                 -- 'harvest' (backfilled Sent) | 'queue' (feedback loop)
    is_gold          boolean     not null default false,   -- true for queue sends + human-approved harvest
    message_id       text        not null unique,          -- Gmail message id of OUR reply; dedupe key
    created_at       timestamptz not null default now()
);

alter table public.reply_examples enable row level security;

-- Index the common read: retrieve(founder, category) ordered by is_gold, recency.
create index if not exists reply_examples_founder_category_idx
    on public.reply_examples (founder, category);
