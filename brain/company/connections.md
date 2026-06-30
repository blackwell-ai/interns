# Platform connections

Last updated June 14, 2026. What agents can reach, through what, as which
account. Update this whenever a connection is added, fixed, or revoked.

Armaan's accounts and their roles (per Armaan, June 10, 2026):

- **armaan.priyadarshan.29@dartmouth.edu** — most cold emailing and customer
  engagements. The address on engagement letters. This is the account the
  outreach agent sends from.
- **armaanp4423@gmail.com** — YC communications. Also the claude.ai account
  (what the claude.ai MCP connectors authenticate as).

These two are the only email accounts agents may *send from* / authenticate as.

## Founding team (digest + internal recipients)

The four co-founders, their personal inboxes (where they read internal mail, so
the addresses the researcher daily digest is sent to) and their `.edu` sending
addresses used for outreach. Recorded June 15, 2026, per Armaan.

| Founder | Personal inbox (digest recipient) | Outreach sending address |
|---|---|---|
| Armaan | armaanp4423@gmail.com | armaan.priyadarshan.29@dartmouth.edu |
| Samarjit | samarjitd391@gmail.com | samarjit.deshmukh.29@dartmouth.edu |
| Shamit | shamit.dsouza@gmail.com | shamitd@stanford.edu |
| Ethan | ezhou1923@gmail.com | ethanpzhou@berkeley.edu |

Sending *to* these is fine; they are recipients, not accounts agents authenticate
as. The digest cron emails this list from Armaan's Dartmouth account.

As of June 17, 2026 (per Armaan) each founder also has a company inbox at
`<firstname>@tryblackwell.com`: armaan@, samarjit@, shamit@, ethan@. These are
the preferred internal-mail recipients going forward. First send to them was the
June 17 off-cycle "new tools" digest; delivery to the new domain is not yet
independently confirmed (watch for bounces).

Update June 26, 2026: `armaan@tryblackwell.com` is now authorized in gogcli as a
send-from / API account (full `user` scopes, same broad set as the Dartmouth
account). Added via the `gog auth add --remote` two-step flow with Armaan doing
the Google consent. Verified working (gmail labels list returned). The other
three tryblackwell addresses are still recipients only.

| Platform | Method | Account | Status (June 10, 2026) |
|---|---|---|---|
| Gmail | claude.ai Gmail connector (MCP) | armaanp4423@gmail.com | ✅ Connected |
| Gmail / Google Workspace | gogcli (`gog`, /sbin/gog) | armaan.priyadarshan.29@dartmouth.edu | ✅ Verified June 10 — full scopes (gmail, calendar, drive, docs, sheets, contacts, tasks, …) |
| Gmail | gogcli | armaanp4423@gmail.com | ✅ Token present (gmail scope only) |
| Gmail / Google Workspace | gogcli | armaan@tryblackwell.com | ✅ Added June 26, 2026 — full `user` scopes (gmail, calendar, drive, docs, sheets, contacts, tasks, …). Token written under the `.env` keyring password (see keyring caveat below). |
| Google Calendar | claude.ai Calendar connector (MCP) | armaanp4423@gmail.com | ✅ Connected |
| Google Drive | claude.ai Drive connector (MCP) | armaanp4423@gmail.com | ✅ Connected (verified June 10 — sees shared docs incl. "Blackwell Work Doc") |
| Granola | MCP, https://mcp.granola.ai/mcp | armaanp4423@gmail.com (workspace: Armaan Priyadarshan) | ✅ Connected (verified June 10). Free tier: AI summaries/notes readable, verbatim transcripts paywalled. Speaker attribution in summaries can be scrambled — corroborate names before relying on them. |
| Apollo (apollo.io, lead sourcing + email) | API key (`TOOLBOX_TOKEN_APOLLO` in `credentials/.env`) | Blackwell account | ✅ Key stored + validated June 18, 2026 (auth/health returned 200, is_logged_in). The only outbound lead/email tool as of 2026-06-18 (see `brain/decisions/2026-06-18-apollo-only-outbound.md`). Usage spec (search filters, sequencing, credit model) pending Armaan's directions. Clay, Prospeo, Hunter, and Origami were dropped — disconnect the Clay claude.ai connector and the Prospeo MCP in connector settings. |
| Supabase (hosted project `lvzvmqeynkwywodcqxkv`) | MCP (project-scoped, `.mcp.json`) + keys in `credentials/.env` (`SUPABASE_URL`/`SUPABASE_PUBLISHABLE_KEY`/`SUPABASE_SECRET_KEY`) | Blackwell project | ✅ Connected + provisioned June 10: both harness migrations applied (6 tables, RLS on, ledger RPCs live) and both edge functions deployed (`oauth-connect` verify_jwt=off per config.toml, `token-refresh`). Remaining: set `GOOGLE_OAUTH_CLIENT_ID`/`GOOGLE_OAUTH_CLIENT_SECRET` via `supabase secrets set`, then `toolbox auth login` + `connect gmail`. |
| Notion | MCP (project-scoped, `.mcp.json`, `https://mcp.notion.com/mcp`) | Per-person Notion workspace (each teammate authenticates their own) | ⏳ Configured June 14, 2026, OAuth pending. On first use, approve the `notion` server prompt, then run `/mcp` in Claude Code and complete Notion sign-in. Interactive connector, so absent in headless/cron runs. |

## Notes for agents

- The claude.ai MCP connectors only see the **personal gmail** account. For the
  Dartmouth account (used for customer-facing email — it's the address on the
  engagement letters), go through **gogcli**.
- gogcli keyring: in headless/agent contexts, export `GOG_KEYRING_PASSWORD`
  from `credentials/.env` before any `gog` call. Pick the account per call with
  `-a <email>` (default is the Dartmouth account).
- Keyring password drift (found and fixed June 26, 2026): the
  `GOG_KEYRING_PASSWORD` in `credentials/.env` had stopped decrypting the
  `armaan.priyadarshan.29@dartmouth.edu` and `armaanp4423@gmail.com` tokens on
  Armaan's machine (`aes.KeyUnwrap(): integrity check failed`); they had been
  written under a different, unknown password. Reconciled by re-adding both
  accounts via the `gog auth add --remote` two-step flow (Armaan did the
  consent) so they were rewritten under the `.env` password. As of June 26 all
  three accounts (Dartmouth, personal gmail, tryblackwell) decrypt and
  authenticate under the single `.env` password; each was verified with
  `gmail labels list`.
- Drift recurred June 28, 2026: all three tokens again failed
  `aes.KeyUnwrap(): integrity check failed` under the `.env` password. Re-added
  `armaan@tryblackwell.com` via the same `gog auth add --remote` two-step flow
  (Armaan did the consent); it now decrypts and was verified with
  `gmail labels list`. The Dartmouth and personal-gmail tokens were left broken
  this time (not needed for the task); re-add them the same way when required.
  This is now a repeating failure mode, so expect to re-auth before any `gog`
  run and budget for the browser consent step.
- Interactively-authenticated MCP connectors (claude.ai ones, Granola) may be
  absent in headless/cron agent runs — plan automations around gogcli and API
  keys where possible.

## Not yet connected (from the founding notes' "necessary context" list)

- Other founders' email accounts as send-from integrations (their inboxes are
  now recorded above as digest recipients, but agents still only send from
  Armaan's accounts)
- Discord, iMessage, Notes app, Slack
- GitHub: repo access is established. On Ethan's machine `gh` and git are authed
  as `ezhou0716`, which has admin on `blackwell-ai/interns` (verified June 14,
  2026). Caveat: keep the `gh` credential helper ahead of `osxkeychain`, because a
  stale keychain token can shadow it and cause a spurious 403 on push. Armaan's
  machine was `gh`-authed as `armaanpriyadarshan` with org access reported pending
  on June 10; that has not been re-verified.
