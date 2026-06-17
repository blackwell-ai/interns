# Researcher watchlist

What the researcher agent monitors. Keep this current — the agent is only as
good as this list. Relevance is defined by `brain/company/targets.md`.

## Communities

- **Agentic Commerce Consortium (Basis Theory)** — Armaan is a member. Slack
  workspace (invite landed in the Dartmouth inbox May 18, 2026, from Peyton
  McGovern) + monthly meetings. Watch for: market intel, partnership and
  customer leads, who's building what.

## Freelancer job marketplaces

- **Upwork, Fiverr** — standing instruction from Armaan (June 10, 2026): watch
  posted jobs as lead signals. Queries to cover: website build / online
  ordering for local retail, Shopify store setup, SEO/AI-visibility/GEO help,
  inventory or POS software work. A merchant posting one of these is a warm
  lead → file as a task in `inbox/queue/` for the outreach agent.

## Merchant-contact events

- Standing instruction from Armaan (June 10, 2026): surface **any** opportunity
  to get in front of merchants — farmers markets, conventions, retail expos,
  local business associations, pop-ups. Prioritize SF/Bay Area (YC batch) and
  the team's current locations.

## Daily digest sources (phase 1, headless)

These run unattended every weekday morning via the `researcher-daily-digest`
skill. Keep `skills/researcher-daily-digest/sources.csv` in sync with this list.

### Subreddits

Confirmed by Armaan (r/solopreneur swapped in for r/smallbusiness, June 15, 2026):

- **r/ecommerce** — DTC operators discussing AI visibility, agent traffic,
  store-management pain
- **r/shopify** — merchants on the platform Blackwell's customers run on;
  app/tooling gaps, GEO questions
- **r/ai_agents** — agentic-commerce developments, competitor launches,
  consumer-use-case signals
- **r/solopreneur**: solo founders running their own stores, where storefront,
  tooling, and AI-visibility pain tends to surface first
- **r/smallbusiness**: local merchants and small retail, where storefront,
  online-ordering, and POS/inventory pain shows up (re-added June 16, 2026,
  alongside r/solopreneur per Armaan)

The digest reads Reddit via its public `.rss` feed, no key. Reddit's `.json` is
IP-blocked and its API needs pre-approval as of November 2025, but the Atom feed
is not gated. It works from a residential IP only, so the cron must run on a
residential machine, and it is best-effort because Reddit rate-limits anonymous
reads. If RSS proves too flaky, read these through the phase-2 logged-in browser
instead. See `toolbox/src/toolbox/primitives/fetch/TOOL.md`.

### Hacker News

The Algolia API (no auth): front page plus standing queries for "agentic
commerce" and "AI shopping". Catches launches, protocol news, and competitor
moves the day they hit the front page.

### Papers

One step (`steps/papers.py`) pulls three key-free providers into a single Papers
section, deduped on arXiv id so a paper surfaced by more than one never repeats:

- **arXiv** — recent papers matching the queries in
  `skills/researcher-daily-digest/papers-queries.csv` (the commerce/agent terms).
  Query-targeted and recency-bounded; this is the precision source. Tune by
  editing that CSV.
- **Hugging Face Papers** (huggingface.co/papers) — the community-curated
  "trending today" set via the public `daily_papers` API. Broad AI, no recency
  cutoff (a paper trending now may be older); dedup stops repeats. Added by
  Armaan, June 17, 2026.
- **alphaXiv** (alphaxiv.org) — the community Hot feed over a rolling window
  (default 7 days). Surfaces what researchers are discussing, including native
  posts not on arXiv. Added by Armaan, June 17, 2026.

Caps and the alphaXiv window live in `skills/researcher-daily-digest/inputs.yaml`
(`papers_hf_max`, `papers_alphaxiv_max`, `papers_alphaxiv_interval`). HF and
alphaXiv are broad AI, not commerce-filtered at the source; the digest's
`llm.filter` applies the relevance bar afterward.

## Computer-use sources (phase 2, in progress)

No clean read API, so these need a logged-in browser session via the gstack
`/browse` skill (one-time `$B handoff` login, personal accounts) and run as an
assisted sweep, not the headless cron. The scrapers are codified as browse
browser-skills (`~/.claude/skills/gstack/browser-skills/`): `twitter-search`
exists (validate against the live DOM after first login); `discord-channel` is
next. Output normalizes into the same items.jsonl the digest filters.

Proposed starter set below (brainstormed June 16, 2026). Prune freely. Handles
are unverified guesses; the twitter-search skill will confirm each resolves
during live validation.

### Twitter/X handles (read each profile's recent tweets)

- Protocols and platforms: `@OpenAI`, `@stripe`, `@patrickc`, `@collision`,
  `@tobi` (Shopify), `@perplexity_ai`, `@AravSrinivas`
- Agentic-commerce ecosystem: `@basistheory` (Agentic Commerce Consortium host)
- Commerce / DTC analysis: `@web_smith` (2PM)
- AI search visibility / GEO: `@iPullRank` (Mike King)

### Twitter/X searches (live search terms)

- `agentic commerce`
- `agentic checkout`
- `AI shopping agent`
- `ChatGPT checkout`
- `instant checkout`
- `agent traffic`
- `generative engine optimization`

### Discord servers and channels

Researched June 16, 2026 (member counts verified live via the logged-in
session). The sweep reads through Armaan's logged-in session, so it can only
read servers he is a member of. As of June 16, 2026 he is in **all the servers
below except n8n**, plus the **Catena Labs** company server. Next he notes which
channels matter so the sweep does not pull whole servers. The dropshipping /
arbitrage / "spy tools" servers that fill the e-commerce directories were
excluded as low signal.

Agentic commerce / payments / protocols (closest to our space):

- **MCP Community** (12,947) https://discord.com/invite/model-context-protocol-1312302100125843476
- **MCP Contributors** (3,963) https://discord.com/invite/6CSzBmMkjX
- **Coinbase Developer Platform / x402** (24,611) https://discord.com/invite/CDP
- **Stripe** (135,348) https://discord.gg/stripe
- **Crossmint** (8,192) https://discord.gg/crossmint
- **OpenAI** (851,521) https://discord.gg/openai
- **Catena Labs** (company server, Armaan is a member; no public invite)

AI builder communities (agentic / AI signal):

- **n8n** (80,952) https://discord.com/invite/n8n (not joined)
- **Hugging Face** (222,883) https://discord.com/invite/hugging-face-879548962464493619
- **Latent Space / AI Engineer** (11,052) https://discord.gg/xJJMRaWCRt
- **Anthropic** (1,178) https://discord.gg/anthropic (small, likely community-run)

E-commerce / Shopify store owners:

- **Shopify Community** (10,290) https://discord.com/invite/shopify-community-1294619579838103647
- **Talk Shop** (1,834) https://discord.gg/talk-shop
- **Shopify Founders** (465) https://discord.gg/knAR3YUyu7

Dead ends (verified June 16, 2026): Payman AI and Shopify Developers invites are
expired; LangChain is Slack-only (langchain.com/join-community); Skyfire,
Nevermined, Circle/Arc have no confirmed public Discord (site/Slack gated).
Company Discord like Catena Labs: Coinbase, Stripe, Crossmint above are the
confirmed peers.

Small-business operators: thin on Discord; that signal stays on r/smallbusiness.
Higher-end DTC operator communities (eCommerceFuel, 2PM, Operators) are paid
Slack/forums, not Discord.

## Researchers

_TODO — name, where they publish (arXiv, X, blog, GitHub)_

## Conferences

_TODO — specific named conferences beyond the standing merchant-event
instruction above (e.g. Fashionology-type events — see
brain/research/henry-labs-agentic-commerce.md)_
