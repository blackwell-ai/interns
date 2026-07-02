# Mozi Wash

Luxury perfume-inspired concentrated laundry detergent brand (moziwash.com),
founded by "Matt" per the site's own llms.txt, based in Los Angeles, made in
California. Positioning: perfume-grade scents inspired by named fragrances
(Central Coast after DIOR Sauvage, Hollywood Rouge after Baccarat Rouge 540,
Vanilla Moon after YSL Black Opium), plant-based and enzyme-powered, safe for
sensitive and eczema-prone skin, recyclable metal tin. Detergent tins are $39.99
(50+ loads), subscribe and save ~25%, bundles to $160, plus candles, linen mists,
and stain tools. Shopify store, DTC, US shipping only, wholesale via Faire.
Audited by the GEO agent starting 2026-07-01.

Last updated 2026-07-01. Sources: nine-phase AI visibility audit
(`skills/ai-visibility-audit/`), artifacts under `agents/geo/moziwash/` dated
2026-07-01. All nine phases complete; deck rendered and gated the same day.

## Engagement framing

Requested audit from cold outbound, confirmed 2026-07-01 from the email thread
"Stanford Student Question" in Armaan's Dartmouth inbox. Sequence: Ethan Zhou
(ethanpzhou@berkeley.edu) cold-emailed geno@moziwash.com and jessica@moziwash.com
on 2026-06-30 (founders cc'd) with the standard AI-visibility pitch referencing
Public Goods. **Geno Quaid** (geno@moziwash.com) replied the same day, skeptical:
"Can you share some results from Publicgoods? I get 5-10 of these emails a week.
So before we do the call, want to make sure that you can deliver." Armaan replied
2026-06-30 evening PT with the Public Goods findings (40% discount, incorrect
shipping, and member-pricing details in AI answers) and offered the Mozi Wash
audit. Geno answered 2026-07-01: "Okay, please send it over. I will review and if
there is something worth chating about, Ill reach out to connect." Jessica never
replied on her thread.

So: not a paid engagement and not a Leandro referral. It is a requested
leave-behind for a skeptical owner who filters 5 to 10 pitches a week and asked
for proof of delivery. Recipient when approved: Geno Quaid, geno@moziwash.com, as
a reply on the existing thread from Armaan's Dartmouth address. Note the site's
llms.txt names the founder as "Matt"; Geno's role is not stated in the thread, so
do not assert a title for him.

Armaan requested the full audit deck (house 14 to 22 page format) on 2026-07-01.

Competitor set for the scorecard and battery, agent-selected from public category
research on 2026-07-01 (not owner-named): **Laundry Sauce** (laundrysauce.com,
cologne-inspired premium detergent pods, title literally "The World's Best
Smelling Detergent", the phrase Mozi named a collection after), **DedCool**
(dedcool.com, LA perfume house whose detergent line shares Mozi's
fragrance-first, non-toxic positioning), **The Laundress** (thelaundress.com,
the luxury laundry incumbent). All three verified live, in-category, and on
Shopify the same day.

## Recon (phase 1+2, frozen 2026-07-01)

Source: `agents/geo/moziwash/recon-2026-07-01.md` (script output plus same-session
manual verification, all before any engine query).

- **Crawlability: clean.** All seven AI bot user-agents (GPTBot, OAI-SearchBot,
  ClaudeBot, PerplexityBot, Google-Extended, Amazonbot, Bingbot) return HTTP 200
  on a product page. robots.txt has no AI-bot blocks (one PowerMapper-specific
  block on a few pages).
- **llms.txt: a genuine strength.** 19.5KB custom file with founder story, scent
  portfolio with perfume inspirations, pricing table, subscription terms, FAQ,
  testimonials, and the claim "4.8 stars across 40,000+ reviews / 100,000+
  customers". Far beyond the ~4KB Shopify boilerplate other audited brands serve.
- **Agentic / UCP: live (Shopify-native).** `/agents.md` (standard Shopify
  template), `/.well-known/ucp` (real merchant profile, version 2026-04-08, MCP
  transport, backend mozy-wash.myshopify.com; the backend MCP endpoint answers
  JSON-RPC), `sitemap_agentic_discovery.xml` 200. Apex `/api/ucp/mcp` 404/422 is
  the usual red herring; the live endpoint is the myshopify backend.
- **Schema: present but flawed.** Homepage is Organization + WebSite +
  SearchAction; the Organization `sameAs` array is six empty strings plus
  Facebook shop, Instagram, TikTok (social only, invalid empty values). PDP ships
  two overlapping Product JSON-LD blocks, one typing `brand` as `Thing`. **No
  AggregateRating or Review markup anywhere** even though Okendo runs on-site
  with the brand's claimed 40,000+ first-party reviews. Homepage title is just
  "Mozi Wash" (server-rendered but no category keywords).
- **Catalog / content depth.** 64 products, 38+ collections (including
  keyword-targeted ones like "Non-Toxic Laundry Detergent", "Laundry Detergent
  for Men"), 153 blog URLs.

## Scorecard: composite 60, grade C, one point above D (verified 2026-07-01)

Discoverability 66, Quotability 66, Recommendability 30, Transactability 86,
Reputation 50. Competitive set (estimates from same-day public signals): Laundry
Sauce ~80 (B), The Laundress ~72, DedCool ~65; set average ~72. Mozi trails by
~12 points, nearly all of it Recommendability and Reputation.

### Findings (verified 2026-07-01, battery + reputation captures)

- **Recommendability 30 (flagship).** Named in 1 of 8 battery passes across six
  engines, and the one yes did not survive a same-day re-run. ChatGPT and
  Claude OFF passes map the category (Gain/Tide mass, Mrs. Meyer's/Method
  natural, Tyler/The Laundress/Laundry Sauce luxury) with no Mozi; ChatGPT OFF
  on "Mozi Wash vs Laundry Sauce" confabulates a profile that inverts the brand
  ("less of a perfume-forward detergent experience"). Live answers on all six
  engines are assembled from roundups (PureWow, Allure, The Quality Edit, Who
  What Wear, Yahoo, Marie Claire, Good Housekeeping) plus retailer data (Ulta on
  Copilot) and Reddit; Laundry Sauce is named in every live pass, usually
  first. Gemini render 1 (clean, logged out) named Mozi in its luxury tier
  citing moziwash.com; render 2 the same day sourced Marie Claire/PureWow and
  dropped it. ChatGPT ON picked Laundry Sauce in the head-to-head, citing
  "stronger scent-centered reputation, more reviews on its own site, and at
  least one direct luxury-detergent comparison." Evidence: `battery-log.md` +
  11 captures.
- **Reputation 50.** On-site llms.txt claims "4.8 stars across 40,000+ reviews"
  (Okendo first-party). Open web: no Trustpilot (404), no BBB, no
  ConsumerAffairs; Amazon brand storefront real and heavily sponsored ("5K+
  bought past month") but ratings 3.8 to 4.2 across ~1,500 (Cozy Cashmere
  3.9/491, Alpine Woods 3.8/339, Central Coast 4.1/319); r/laundry (739K
  weekly visitors) threads lead with rusted/leaking tin reports ("recurring
  packaging issue") and a top-1% commenter calling it "pretty horrible...
  Jeeves NY rated it as one of the worst detergents of 2025" (Jeeves claim
  attributed to the comment, not independently verified). Positives exist:
  scents praised, support replaced failed tins, formula 3.0 called
  "surprisingly legit." YouTube thin and ad-skewed. See
  `reputation-2026-07-01.md`.
- **Transactability 86 (strength).** Full Shopify UCP layer live; MCP endpoint
  answers JSON-RPC on the myshopify backend; all agent-discovery surfaces 200.
- **Discoverability 66 / Quotability 66.** All seven AI bots 200. llms.txt is
  best-in-set (19.5KB custom vs 4.3 to 6.3KB competitor boilerplate) and is the
  plausible reason the one Gemini render recommended the brand. But: bare
  homepage title ("Mozi Wash"), sameAs with six empty strings and social links
  only (no Amazon/YouTube), two overlapping Product JSON-LD blocks with one
  brand-as-Thing, zero AggregateRating/Review markup despite the Okendo corpus.
  Blog posts carry valid Article schema and the category post ranks page-1
  organic for "best smelling laundry detergent 2026" while the AI Overview
  above it skips the brand (and absorbed Topanga Scents' own blog instead).

### Competitive note

All four brands share Shopify UCP rails, so plumbing does not separate them.
Laundry Sauce owns the live answer via the citation layer (roundups, Ulta
retail data 4.3/1.4K, a third-party comparison page that decides the
head-to-head). None of the four emits AggregateRating, so structured review
data is an open lane; Mozi has the largest first-party corpus to publish there.

## Deliverables (2026-07-01)

- Audit deck: `brain/customers/documents/moziwash-audit.pdf` (18 pages, house
  format; verify-evidence PASS, dash gates 0/0, 18-page visual QA clean).
- Working source: `agents/geo/moziwash/moziwash-ai-visibility-audit.html` plus
  `assets/` (8 reputation captures, 11 battery captures incl. the Gemini
  re-render).
- Battery log: `agents/geo/moziwash/battery-log.md`. Reputation:
  `reputation-2026-07-01.md`. Competitors: `competitors-2026-07-01.md`. Recon:
  `recon-2026-07-01.md`.
- Sign-off task: `inbox/queue/2026-07-01-review-moziwash-audit-deck.md`.

## Open items

- Deck awaits Armaan's review and approval (charter guardrail: human sign-off
  required). Engagement context is confirmed (requested audit, recipient Geno
  Quaid, see Engagement framing above); the send is a reply on the existing
  email thread once approved. Geno's reply promised only to review and reach
  out if interested, so the deck is the one shot at the "can you deliver"
  question he asked.
- Perplexity ran logged-in (no reachable in-app incognito); low contamination,
  disclosed in battery-log.md and the deck methodology.
- Gemini and Google AI Overview presence is per-render; any re-benchmark should
  run multiple renders per engine.
