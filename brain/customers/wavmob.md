# WavMob

Used wheelchair accessible vehicle (WAV) dealer (wavmob.co.uk), UK, based in
Waterlooville on the south coast, delivers UK-wide. Sells professionally converted
used WAVs (ramp/lift, side/rear access, drive-from and passenger) to individuals,
families, care providers, and taxi operators, with finance and part-exchange.
Non-transactional lead-gen site, not a store; the conversion is an enquiry or call.
Referred by the e-commerce agency (Leandro) on 2026-06-30 alongside [[stream2sea]]
and [[guardian]]. Harder to measure than a store; the agency lead suggested payment
on result. No direct contact yet.

Last updated 2026-06-30. Sources: recon `agents/geo/wavmob/recon-2026-06-30.md`
(recon.sh) plus reputation checks the same day. Live engine battery run 2026-07-01
across six engines via `/browse`; see `battery-log.md`. Split: ChatGPT, Perplexity,
and Google AI Overview omit WavMob; Copilot (prominently), Claude, and Gemini name it,
but only from third-party directories, not from wavmob.co.uk (consistent with the 403
block). The national leaders (Allied Mobility, Jubilee, WavsGB) appear in all six.

## Findings (2026-06-30)

- **Flagship: all AI crawlers are blocked.** Every one of the seven AI bot
  user-agents (GPTBot, OAI-SearchBot, ClaudeBot, PerplexityBot, Google-Extended,
  Amazonbot, Bingbot) returns HTTP 403 on the site, while a normal browser UA gets
  200. Assistants cannot read a single page, so they answer WAV questions from
  directories (AutoTrader, MotaClarity, Able Magazine) and larger converters. This
  is the Good Molecules WAF-block pattern and the precondition for every other fix.
- **Not Shopify; no agentic layer.** Custom site. `/agents.md`, `/llms.txt`,
  `/.well-known/ucp`, agentic sitemap all 404.
- **Inventory is not machine-readable.** Homepage JSON-LD is AutomotiveBusiness +
  Organization + PostalAddress + OpeningHoursSpecification (decent local-business
  schema), but no Vehicle/Product/Offer schema for the stock and no AggregateRating.
- **Reputation is a real, stranded strength.** Genuine Trustpilot profile
  (uk.trustpilot.com/review/wavmob.co.uk), plus Google reviews, Car Dealer Reviews
  (5/5), and an active Facebook presence; "Excellent, rated by hundreds." None of
  it is in schema (only two `sameAs` links on the homepage), and all of it is behind
  the crawler wall, so engines cannot see it.
- **Server-rendered title present** (unlike the Shopify brands): "Wheelchair
  Accessible Vehicles for Sale - Approved UK Dealer", meta description present.

## Deliverable

One-pager built 2026-06-30, awaiting human sign-off:
`agents/geo/wavmob/wavmob-one-pager.pdf` (6 fixes led by unblocking the crawlers,
30-day KPIs, $1,000 money-back like the others; the pilot is judged on the crawler,
inclusion, and schema checks since the site is non-transactional). Agency target
2026-07-05.

## Open items

- Confirm the 403 block is a deliberate WAF/bot rule vs. an incidental block, and
  scope the unblock with whoever runs the site.
- Battery done 2026-07-01. WavMob omitted by 3 of 6 (ChatGPT, Perplexity, Google
  AIO); named by 3 (Copilot prominently, Claude, Gemini) but only from third-party
  directories. Leaders in all six: Allied Mobility, Jubilee, WavsGB, GowringsVersa.
