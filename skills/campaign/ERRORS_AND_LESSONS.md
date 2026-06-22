# Campaign errors and lessons learned

Covers the June 2026 LLM infra + aerospace campaign runs from Samarjit, Armaan, and Ethan's accounts.

---

## Errors encountered

### Gmail daily send limit hit (Samarjit)

Samarjit's account hit Gmail's daily outbound limit mid-run. Sends after ~102 emails bounced silently (logged as `bounced_gmail_limit`, not hard failures). The campaign continued sending but those emails never delivered. The 122 bounced records had to be manually deleted from the Supabase `contacted` ledger before retrying from a different account.

Fix: distribute sends across multiple accounts. Monitor for `quota_wall` events in the campaign log. Delete bounced rows from Supabase before retrying.

### gog token expired (Armaan)

Armaan's first send attempt failed with `unauthorized_client (401)`. The stored OAuth token had expired.

Fix: run `gog auth add <email> --services gmail` to re-authorize. The token list in `gog auth list` shows the last auth time -- if it's old, re-auth before running.

### gog `invalid_client` error on token refresh (all accounts)

When a token expires mid-session, `gog_auth.py` originally tried to do its own OAuth refresh exchange using a client secret pulled from the macOS keychain. The keychain entry for `gogcli` stores JSON refresh token blobs, not the client secret, so the exchange fails with `invalid_client: The provided client secret is invalid`.

Fix: rewrote `get_access_token()` in `gog_auth.py` to let gog handle refreshes itself -- it calls `gog gmail list` to force an internal token refresh, then re-exports the fresh access token. No client secret needed.

### Two runwayml.com sends failed (403 rate limit)

During Armaan's 367-email run, two sends to `runwayml.com` hit Google's per-minute quota (`Queries per minute per user exceeded`). These were logged as `send.failed`, not `quota_wall`, so the campaign continued without stopping.

Fix: concurrency of 2 reduces the chance of hitting per-minute limits. These contacts can be retried in a later run since they were not marked as sent in the Supabase ledger.

### vultr.com send failed (400 precondition error)

One send to `vultr.com` returned HTTP 400 `Precondition check failed` during the 300-email pipeline run. Treated as a permanent failure; the campaign moved on.

This is a transient Gmail API error. The contact was not marked sent, so it can be retried.

### Wrong CLI flags used

Two flags do not exist in `run.py` and were tried before finding the correct ones:
- `--icp-mix` does not exist. Use `--config` to pass a TOML segment file.
- `--sender` does not exist. Use `--from`.
- `toolbox auth token hunter` is not a valid subcommand. Read the key from `credentials/.env` and pass it as `TOOLBOX_TOKEN_HUNTER=<key>`.

### `--leads` path defaults to template A

When using `--leads` to send from a pre-enriched CSV, the pipeline defaults to `template_a.md` if `--template` is not explicitly passed. This caused the first Ethan send to go out with the wrong template.

Fix: always pass `--template skills/campaign/templates/<template>.md` explicitly when using `--leads`.

### Emails formatted with broken line wrapping (plain text)

Recipients saw sentences breaking mid-line. Root cause: plain text emails are sent with no HTML and Gmail wraps long lines at roughly 76 characters, which breaks paragraphs visually.

Fix: `compose_outbox` now always generates a `body_html` field from the plain text body, making every email multipart with an HTML part. Gmail renders the HTML version, which wraps naturally.

### HTML using `<p>` tags still looked off

The first HTML implementation wrapped each paragraph in `<p>` tags. Gmail strips the `<html>` and `<body>` wrapper entirely, discarding the body-level font styles, and `<p>` tags carry default margins that make spacing look wrong.

Fix: switched to a `<div>` wrapper with `<br><br>` for paragraph breaks and inline styles on the div. No `<p>` tags. Apostrophes are no longer over-escaped as `&#x27;`.

### Duplicate contacts in enrichment log

When both ICP segments (local LLM and data center) generated the same domain, the enrichment cache returned results for each call, making contacts appear multiple times in the log. The Supabase ledger dedup catches this before sending, so no duplicate emails go out, but the log looks confusing.

This is expected behavior. It does not cause duplicate sends.

---

## Things to always do

- Re-auth with `gog auth add <email> --services gmail` before any run where the account has not been used recently.
- Pass `--template` explicitly when using `--leads`.
- Pass `--concurrency 2` to stay under Gmail per-minute rate limits.
- Delete bounced rows from Supabase before retrying from a new account (`mcp__supabase__execute_sql` or the MCP tool).
- Check `gog auth list` before a run -- the timestamp shows the last auth date.
- Pass `TOOLBOX_TOKEN_HUNTER` from `credentials/.env`, not from `toolbox auth token`.

---

## Credit efficiency notes

- Hunter charges 1 credit per domain search, regardless of how many emails are returned.
- `email_status: accept_all` is a filter applied to the response -- no extra credit is charged.
- `min_score` is applied after the API call -- lowering it yields more emails per credit but does not affect credit usage.
- `/v2/email-count` is free and now used as a pre-filter before each paid domain search.
- Prior enriched CSVs are now cached and reused across runs -- domains already searched in a previous run skip the paid Hunter call entirely.
