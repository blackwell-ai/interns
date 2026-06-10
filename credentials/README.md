# credentials/

Local credentials for human and agent employees.

## How it works (since 2026-06-10)

- `credentials/.env` is **gitignored** — it lives on each machine, never in
  git. GitHub push protection forced the issue, and it aligns with the
  harness direction (secrets fetched at runtime from Supabase).
- `.env.example` (committed) documents the expected keys. To set up a new
  machine: `cp credentials/.env.example credentials/.env`, then get the real
  values **from a teammate out-of-band** (Signal/in person — not email, not
  git, not Slack).
- One entry per credential, `UPPER_SNAKE_CASE`, with a comment saying what
  it's for. Never copy secret values anywhere else in the repo — not into
  brain files, task files, code, or commit messages.

## Where credentials actually live, by kind

- **Harness flows** — Supabase (`toolbox auth login` / `connect`); nothing in
  `.env` at all. Gmail refresh tokens and provider keys stay server-side.
- **Transitional tools** (gogcli) and direct API use (Clay HTTP, Supabase
  keys) — this `.env`.
- **History note:** earlier today the `.env` *was* committed (the original
  stopgap decision). Those blobs remain in git history — anything that was in
  them (notably `GOG_KEYRING_PASSWORD`) should be treated as repo-visible and
  rotated at the provider when convenient; the M4 milestone covers this.
