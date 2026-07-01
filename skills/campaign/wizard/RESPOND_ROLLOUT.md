# /respond rollout checklist

The `/respond` reply-review queue is code-complete (see ARCHITECTURE.md flow 6).
These four steps make it live. They need credentials/consoles the build could not
reach, so they are done by a human. Do them in order: step 4 (deploy) must come
after step 1 (tables) or `/respond` errors on missing tables.

## 1. Apply the two Supabase migrations (prod)

Run both against the production Supabase Postgres (SQL editor or psql). They are
`create table if not exists`, so re-running is safe.

- `migrations/2026-07-01_reply_examples.sql`
- `migrations/2026-07-01_voice_cards.sql`

## 2. Register the `/respond` slash command in the Slack app

There is no manifest in the repo; the app is configured in the Slack dashboard.
In api.slack.com → your app → App Manifest, merge this into the manifest (or add
the command under Features → Slash Commands, and confirm Interactivity is on).
Socket Mode carries the command and the modal interactions, so no Request URL is
needed.

```yaml
features:
  slash_commands:
    - command: /respond
      description: Review and send replies to prospects, in your voice
      should_escape: false
settings:
  interactivity:
    is_enabled: true
  socket_mode_enabled: true
```

Scopes: the bot already posts and opens modals, so `commands` is the only scope
to confirm is present. Reinstall the app if Slack prompts for the new scope.

## 3. Seed the corpus from each founder's Sent mail

Needs the wizard env (SUPABASE_URL, SUPABASE_SECRET_KEY, ANTHROPIC_API_KEY or the
`claude` CLI) and a `gog` token for each account (`gog auth add`), or the
`GMAIL_TOKEN_<SENDER>` env fast path. Dry-run first to see counts, then live.

```bash
# counts only, writes nothing
python3 skills/campaign/harvest_reply_examples.py --account armaan.priyadarshan.29@dartmouth.edu --dry-run

# seed for real (writes reply_examples + a voice card)
python3 skills/campaign/harvest_reply_examples.py --account armaan.priyadarshan.29@dartmouth.edu
python3 skills/campaign/harvest_reply_examples.py --account samarjit.deshmukh.29@dartmouth.edu
python3 skills/campaign/harvest_reply_examples.py --account ethanpzhou@berkeley.edu
```

Until seeded, `/respond` still works but drafts are plainer (no exemplars or voice
card yet). The feedback loop also fills the corpus over time as founders send.

## 4. Deploy the wizard

After step 1 is done:

```bash
railway up --service slack_wiz --ci
```

## Verify

Run `/respond` in the wizard's Slack, pick a founder, and confirm: a draft appears
that reads in that founder's voice, editing + Send delivers in-thread from the
right account, and the email does not return in the next triage digest. Skipped
emails still appear next time.
