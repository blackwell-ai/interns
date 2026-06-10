# Platform connections

Last updated June 10, 2026. What agents can reach, through what, as which
account. Update this whenever a connection is added, fixed, or revoked.

Armaan's accounts and their roles (per Armaan, June 10, 2026):

- **armaan.priyadarshan.29@dartmouth.edu** — most cold emailing and customer
  engagements. The address on engagement letters. This is the account the
  outreach agent sends from.
- **armaanp4423@gmail.com** — YC communications. Also the claude.ai account
  (what the claude.ai MCP connectors authenticate as).

These two are the only email accounts agents may touch.

| Platform | Method | Account | Status (June 10, 2026) |
|---|---|---|---|
| Gmail | claude.ai Gmail connector (MCP) | armaanp4423@gmail.com | ✅ Connected |
| Gmail / Google Workspace | gogcli (`gog`, /sbin/gog) | armaan.priyadarshan.29@dartmouth.edu | ✅ Verified June 10 — full scopes (gmail, calendar, drive, docs, sheets, contacts, tasks, …) |
| Gmail | gogcli | armaanp4423@gmail.com | ✅ Token present (gmail scope only) |
| Google Calendar | claude.ai Calendar connector (MCP) | armaanp4423@gmail.com | ✅ Connected |
| Google Drive | claude.ai Drive connector (MCP) | armaanp4423@gmail.com | ✅ Connected (verified June 10 — sees shared docs incl. "Blackwell Work Doc") |
| Granola | MCP, https://mcp.granola.ai/mcp | armaanp4423@gmail.com (workspace: Armaan Priyadarshan) | ✅ Connected (verified June 10). Free tier: AI summaries/notes readable, verbatim transcripts paywalled. Speaker attribution in summaries can be scrambled — corroborate names before relying on them. |
| Clay (clay.com, GTM/enrichment) | claude.ai connector (MCP, https://api.clay.com/v3/mcp) | armaanp4423@gmail.com (claude.ai account) | ✅ Connected June 10 via claude.ai directory. Note: do NOT add Clay directly with `claude mcp add` — Clay's OAuth rejects clients named like known platforms; the claude.ai connector is the only path. |

## Notes for agents

- The claude.ai MCP connectors only see the **personal gmail** account. For the
  Dartmouth account (used for customer-facing email — it's the address on the
  engagement letters), go through **gogcli**.
- gogcli keyring: in headless/agent contexts, export `GOG_KEYRING_PASSWORD`
  from `credentials/.env` before any `gog` call. Pick the account per call with
  `-a <email>` (default is the Dartmouth account).
- Interactively-authenticated MCP connectors (claude.ai ones, Granola) may be
  absent in headless/cron agent runs — plan automations around gogcli and API
  keys where possible.

## Not yet connected (from the founding notes' "necessary context" list)

- Other founders' email accounts (Samarjit, Ethan, Shamit)
- Discord, iMessage, Notes app, Slack
- GitHub: `gh` is authed as armaanpriyadarshan locally; org access to
  blackwell-ai pending
