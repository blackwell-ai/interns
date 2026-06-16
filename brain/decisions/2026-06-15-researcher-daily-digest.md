# Researcher agent becomes a daily external-signal radar

Decided June 15, 2026. Source: founder direction from Armaan (this session).

## Decision

The researcher agent's main job is now a daily digest of problems and ideas
from our space, pulled from external sources and delivered every weekday
morning. It runs as the `researcher-daily-digest` skill on the automation
harness, with two phases of sources.

- Phase 1, live and headless: Reddit (r/ecommerce, r/shopify, r/ai_agents,
  r/solopreneur, r/smallbusiness) and Hacker News.
- Phase 2: Twitter/X via the gstack `/browse` browser-skill (`twitter-search`,
  needs the logged-in browser, so assisted), and Discord via its REST API
  (`discord.fetch` primitive, API + account token, so headless-cron-friendly).

Discord, ToS note (decided June 16, 2026): there is no clean way to read
arbitrary servers Armaan does not admin. A bot needs an admin invite; cookie
import does not authenticate Discord web (its token lives in localStorage, not
cookies). Using the account token against the REST API is a "self-bot", which
violates Discord's ToS and risks an account ban. Armaan was told this plainly
and chose to proceed with his personal account. The token is stored as
`TOOLBOX_TOKEN_DISCORD` in `credentials/.env` (gitignored, never committed).
`discord.fetch` is read-only (GET /channels/<id>/messages), drops bot and
chatter messages, and degrades gracefully on restricted channels (403).

YC Bookface, confidentiality note (decided June 16, 2026): the digest also reads
the Bookface home feed via the `bookface-feed` browse skill, authenticated by
the YC SSO cookies in the browse daemon (no separate login). Bookface content is
YC-private, and the digest is committed to the GitHub repo and emailed to the
team. Armaan was told this plainly and chose to fold Bookface in like any other
source (full digest). It is read-only and best-effort (a lost SSO session just
drops Bookface from that day's run).

The flow is `fetch → extract → llm.filter → llm.digest → inbox.file → report`.
It writes a dated digest to `brain/research/digests/<date>.md`, files an inbox
task per action item, and the cron wrapper (`skills/researcher-daily-digest/
cron.sh`) commits those artifacts and emails the digest to the team.

## Why these sources, and what changed

Armaan named the four subreddits, Hacker News, Twitter, and Discord. r/solopreneur
replaced r/smallbusiness (the prior watchlist entry) because solo store owners
are closer to where AI-visibility pain surfaces first. The relevance bar is the
researcher charter's bar applied to our space: surface problems we could solve
and ideas worth stealing, not routine chatter.

## Real-world constraints that shaped the build

- Reddit is the hard source. Its public `.json` returns 403 from any IP we
  tried (an HTML anti-bot page), and the API self-serve path is closed: as of
  the Responsible Builder Policy (November 11, 2025) all API access needs
  pre-approval, so you can no longer mint keys at reddit.com/prefs/apps. The one
  key-free path that works is the public `.rss` Atom feed, which is not gated.
  It only succeeds from a residential IP (cloud IPs get 403/429), so the cron
  must run on a residential machine. It is also rate-limited hard for anonymous
  reads, so fetch is serialized (concurrency 1) and patient (retries across a
  ~90s window); a throttled subreddit is logged as an error, not a crash. This
  makes Reddit best-effort. The reliable upgrade, if needed, is reading the
  subreddits through the phase-2 logged-in browser. Hacker News needs no auth
  (the Algolia API) and is solid.
- The authenticated `oauth.reddit.com` path is built and dormant: if Reddit ever
  grants API access, drop `TOOLBOX_TOKEN_REDDIT=client_id:client_secret` into
  `credentials/.env` (matching `TOOLBOX_TOKEN_HUNTER`) and fetch switches to it
  with no code change.
- The claude.ai MCP connectors (Notion, Gmail) are interactive and absent in
  headless or cron runs (brain/company/connections.md). So delivery uses the
  headless-safe channels: the git-committed brain digest, inbox tasks, and email
  via gog. Notion mirroring stays an interactive step in the next session, the
  same way inbox/ mirrors the Notion task hub.

## New harness code

- `extract` primitive: explodes fetched listings into one record per post, which
  the filter and digest both need. Parses Reddit's Atom RSS, Reddit listing JSON
  (for the dormant OAuth path), and HN Algolia JSON.
- `fetch`: reads Reddit via the public `.rss` feed by default, or
  `oauth.reddit.com` if a `reddit` token exists.
- `llm.digest`: synthesizes the themed markdown digest, humanizer-compliant.

## Open items (need Armaan)

1. Reddit needs no key (it reads the public RSS feed), but the cron must run on
   a residential machine, and Reddit is best-effort. If it proves too flaky,
   read the subreddits through the phase-2 logged-in browser.
2. Install the weekday cron line (see the skill's SKILL.md / cron.sh header).
3. Confirm digest recipients (default is Armaan) and whether to mirror into
   Notion. Phase 2 (Twitter, Discord) needs specific handles and servers, which
   go in `agents/researcher/watchlist.md`.
