# discord — read recent channel messages via the Discord API (read-only)

Connection: `TOOLBOX_TOKEN_DISCORD` (a Discord account token). WARNING: driving a
personal account this way is a self-bot and violates Discord's Terms of Service
(account-ban risk). Used only because the operator opted in. Read-only.

## discord.fetch
- in: CSV with `guild_id`, `channel_id`, `label` columns → out: items.jsonl
- flags: `--limit 50` (messages per channel), `--min-chars 15`
- one record per kept message, in the `extract` item shape
  (`{source, label, title, url, text, author, ts}`), so it folds into the same
  items.jsonl the digest filters.
- drops bot messages and sub-`min-chars` chatter; pulls an embed's
  title/description when the body is just a link; cleans `<@id>` / `<#id>` /
  `<:emoji:>` syntax.
- a channel that errors or rate-limits (after retrying on 429) is recorded and
  skipped, never crashing the sweep.
- API-only (no browser), so unlike the X scraper it can run in the headless cron.
