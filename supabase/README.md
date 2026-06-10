# supabase/ — the backbone

Per-person auth, provider connections, and the contact ledger (spec §7–8).

## Local development / tests

```bash
supabase start          # Docker; migrations auto-apply
cd toolbox && uv run pytest -m integration
supabase stop           # when done
```

## Hosted project setup (one-time, human)

1. Create a project at supabase.com; enable the **Google** auth provider
   (Supabase dashboard → Authentication → Providers) with a Google OAuth
   client (type "Web application").
2. `supabase link --project-ref <ref>` then `supabase db push` (applies
   `migrations/`).
3. Create a SECOND Google OAuth client config (or reuse the same client) for
   the Gmail-scopes consent, with the deployed `oauth-connect` function URL as
   an authorized redirect URI, then:

   ```bash
   supabase secrets set GOOGLE_OAUTH_CLIENT_ID=... GOOGLE_OAUTH_CLIENT_SECRET=...
   supabase functions deploy oauth-connect token-refresh
   ```

4. Everyone on the team: export `SUPABASE_URL` + `SUPABASE_ANON_KEY` (NOT
   secrets — the anon key is a public client identifier; RLS protects data),
   then `toolbox auth login`, then `toolbox auth connect gmail|clay|...`.

## What lives where

| Table | Purpose | Client access (RLS) |
|---|---|---|
| `connections` | provider connection metadata per person | read own + org-shared |
| `connection_secrets` | refresh tokens / API keys | none — edge functions only |
| `contacted` | the ledger; `UNIQUE (channel, recipient)` is the invariant | read own; writes via RPCs only |
| `suppression` | bounces + opt-outs, permanent, no override | read all; insert via RPC |
| `runs` | run liveness (heartbeats) for the stale-claim reaper | read all; write via RPC |
| `oauth_states` | one-time tokens for the Gmail consent flow | none |

Functions: `oauth-connect` (start/complete the Gmail consent; store API keys),
`token-refresh` (session → fresh provider token; secrets never reach laptops).
