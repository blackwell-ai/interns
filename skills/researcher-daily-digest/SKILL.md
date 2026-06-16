# researcher-daily-digest

The researcher agent's external-signal radar, as a headless flow. Sweeps the
watchlist's machine-readable sources every weekday morning, filters hard for
problems we could solve and ideas worth stealing, and produces a digest. Runs
on the same runner and primitives as outreach (spec §11 breadth proof); it is
brain infrastructure, not an outreach feature.

Forked in spirit from `researcher-watchlist-sweep`, which filed whole-page
blobs as inbox tasks. This skill differs by: per-post granularity (`extract`),
a synthesized digest (`llm.digest`), and four source types folded into one
filtered digest.

## Sources

All five fold into one `items.jsonl`, so the filter and digest treat them alike.

- Reddit: r/ecommerce, r/shopify, r/ai_agents, r/solopreneur, r/smallbusiness,
  via the public `.rss` Atom feed (no key). Works from a residential IP only and
  Reddit rate-limits hard, so the cron runs on a residential machine and fetches
  one source at a time (a throttled subreddit is logged, not a crash). See
  fetch/TOOL.md.
- Hacker News: front page plus standing queries via the Algolia API (no auth).
- Discord: channels in `discord-channels.csv`, via the REST API + account token
  (`discord.fetch`, appends to items.jsonl). Headless-safe. NOTE: this is a
  self-bot (ToS / ban risk); the operator opted in. See the decision doc.
- X/Twitter: handles + searches in `twitter-targets.csv`, via the `twitter-search`
  browse browser-skill (`steps/twitter.py`, best-effort: never fails the run).
  Needs the browse daemon logged in to X on the cron machine.
- YC Bookface: the home feed, via the `bookface-feed` browse skill
  (`steps/bookface.py`, best-effort). Auth is the YC SSO session in the daemon.
  CONFIDENTIAL: YC-private content; the operator chose to include it in the
  committed + emailed digest (see the decision doc).

## Inputs

- `sources_csv`: Reddit + HN CSV (`url`, optional `label`). Default `sources.csv`.
- `discord_csv`: `guild_id,channel_id,label`. Default `discord-channels.csv`.
- `twitter_targets`: `type,value` (handle|query). Default `twitter-targets.csv`.
- `relevance_bar`: the plain-English filter handed to `llm.filter`.

## Steps

1. `fetch.urls`: pull Reddit (RSS) + HN. Failures recorded per-row, never crash.
2. `extract.items`: explode each listing into one record per post/story.
3. `discord.fetch --append`: append Discord messages (bots/chatter filtered).
4. `python steps/twitter.py`: append X tweets, best-effort (browser daemon).
5. `python steps/bookface.py`: append YC Bookface posts, best-effort (SSO session).
6. `llm.filter`: strict per-item relevance + a 1-2 sentence summary each (batched).
7. `llm.digest`: synthesize the themed digest, append a `## Sources indexed`
   coverage list, write a dated copy to `brain/research/digests/<date>.md`.
8. `inbox.file`: file each cleared item as an `inbox/queue/` task for a human.
9. `report.write`: run report plus changelog.

## Delivery

The flow produces the durable artifacts: the dated brain digest and the inbox
tasks. The other two channels are handled by the outer cron agent, on purpose:

- Notion + team email use the cron agent's MCP (Notion, Gmail). They do NOT use
  the `gmail.send` primitive, whose outreach ledger would suppress a repeat
  send to the same teammate after day one.

See `agents/researcher/AGENT.md` ("Daily digest") for the cron wiring.

## Operations (machine-local; not reproducible from the repo alone)

The schedule and the X/Bookface logins live on Armaan's machine, not in git.

- **Schedule**: a systemd user timer, `~/.config/systemd/user/
  researcher-digest.{service,timer}` (OnCalendar `Mon..Fri 08:00`,
  `Persistent=true`), `ExecStart=` this folder's `cron.sh`, plus
  `loginctl enable-linger armaan`. Rebuild: write those two unit files,
  `systemctl --user daemon-reload`, `systemctl --user enable --now
  researcher-digest.timer`. Logs: `runs/cron-digest.log` + `journalctl --user
  -u researcher-digest.service`.
- **Secrets** (`credentials/.env`, gitignored): `TOOLBOX_TOKEN_DISCORD` (Discord
  account token, a self-bot) and `GOG_KEYRING_PASSWORD` (gog email). Reddit + HN
  need none.
- **X + Bookface auth** is the browse daemon's saved state `research` (cookies
  imported from Firefox: X via `.x.com` cookies, Bookface via `.ycombinator.com`
  SSO incl. `_sso.key`). These EXPIRE. When X or Bookface go missing from the
  digest, re-auth: extract the cookies from Firefox's `cookies.sqlite`
  (`expiry` is in ms, divide by 1000), `browse cookie-import <json>` per domain
  (must be on that domain first), then `browse state save research`. Until
  re-authed those two drop out gracefully; Reddit + HN + Discord still send.

## Acceptance checks

- Each item explains the concrete problem the poster hit or the development
  itself, in plain terms. It does not strain to connect the item to our own
  work (the team is brainstorming, so a wider aperture is intended).
- Sources that fail to fetch or parse are recorded (pages.jsonl error / extract
  "unparsed" count), never silently dropped.
- The digest contains no em or en dashes (humanizer; `llm.digest` strips them).

## Changelog
- 2026-06-16 04:20 UTC: run `researcher-daily-digest-20260616T041918Z-ca8997` — 0 sent, 0 skipped, 0 failed
- 2026-06-16 04:24 UTC: run `researcher-daily-digest-20260616T042058Z-f78538` — 0 sent, 0 skipped, 0 failed
- 2026-06-16 06:54 UTC: run `researcher-daily-digest-20260616T064531Z-731166` — 0 sent, 0 skipped, 0 failed
- 2026-06-16 15:10 UTC: run `researcher-daily-digest-20260616T150016Z-a9dc51` — 0 sent, 0 skipped, 0 failed
- 2026-06-16 17:56 UTC: run `researcher-daily-digest-20260616T172102Z-86f009` — 0 sent, 0 skipped, 0 failed
- 2026-06-16 18:40 UTC: run `researcher-daily-digest-20260616T180613Z-66097d` — 0 sent, 0 skipped, 0 failed
