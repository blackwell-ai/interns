# Mozi Wash AI engine battery (phase 5)

Run 2026-07-01, headed Chromium + stealth via `/browse`. Two passes per engine:
OFF = training only ("without searching the web"); ON = live web retrieval
("search the web"). Captures in
`assets/<engine>-<query-slug>-<pass>-2026-07-01.png`.

Competitor set (agent-selected): Laundry Sauce, DedCool, The Laundress (and any
others the engines name).

## Fixed queries (written before any engine was queried)

- **Q1 category (primary, run on every engine):** `best smelling laundry
  detergent 2026` (the category phrase Mozi itself targets; its flagship
  collection is named "World's Best Smelling Laundry Detergent") — slug
  `best-smelling-detergent`
- **Q2 adjacent:** `best luxury laundry detergent 2026` — slug
  `luxury-detergent` (not run this session; Q1 answers already split into a
  luxury tier on every engine, so Q1 covered the luxury read; noted as scope,
  not a blocked limitation)
- **Q3 brand-defense:** `Mozi Wash vs Laundry Sauce` — slug
  `mozi-vs-laundry-sauce` (run on ChatGPT, both passes)

## Result table (Q1)

| Engine | Pass | Incognito/clean | Mozi Wash named? | How / other brands |
|---|---|---|---|---|
| ChatGPT | off | Temporary Chat | **NO** | Best-smelling map: Tyler Glamorous Wash Diva (top luxury), Tide, Gain, The Laundress Signature, Mrs. Meyer's, Persil, Method, Dirty Labs. No Mozi, also no Laundry Sauce or DedCool. |
| ChatGPT | on | Temporary Chat | **NO** | Product carousel (Tide, Gain, Persil, Method, Mrs. Meyer's, Seventh Generation, ECOS) plus "top picks by scent style": Laundry Sauce best perfume-like overall (cites PureWow 2026), DedCool best luxury fragrance-brand (cites Allure, Drew & Jonathan), Tyler Diva longest-lasting. Mozi absent. |
| Claude | off | fresh claude.ai/new chat | **NO** | Gain, Tide, Arm & Hammer (mass), Mrs. Meyer's, Method, Puracy, Dirty Labs (natural), The Laundress ("the boutique standard", notes its recall). Mozi absent. |
| Claude | on | fresh claude.ai/new chat | **NO** | "Laundry Sauce is the standout" for boutique/luxury; The Laundress, DedCool, Dirty Labs also named; Gain/Tide mass tier; Mrs. Meyer's, Molly's Suds, ECOS natural tier. Sources: The Quality Edit, Tide, Consumer Reports. Mozi absent, including from the eczema/sensitive-skin caveat, Mozi's own core positioning. |
| Perplexity | on | logged-in (no in-app incognito reachable; low contam.) | **NO (answer body)** | Laundry Sauce ("most perfume-like"), Snif Old Money, The Laundress Beauty Sleep, L'Avant Collective, Tyler Diva, Method, Safely, Tide. Single dominant source: shopping.yahoo roundup. Mozi appears ONLY in an auto-generated follow-up chip ("specialty sites like Mozi Wash and DedCool"), never in the answer. |
| Gemini | on | logged-out guest (clean) | **YES in 1 of 2 renders (only engine to name it at all)** | Render 1: named in the "Bougie & Perfume-Inspired" tier: "Mozi Wash... has exploded in popularity for creating detergents inspired by luxury colognes and perfumes" (Golden Hour, Vanilla Moon), with moziwash.com itself cited as a source, plus a care tip naming Mozi again. Other brands: Gain, Tide, Tyler, DedCool, Mrs. Meyer's, Method, Dirty Labs. Sources: Laundry Labs, Reddit, Mozi Wash, Good Housekeeping. Render 2 (same day, fresh guest session, capture `gemini-...on-run2`): Mozi ABSENT; luxury tier was Laundry Sauce, Snif, Maison Francis Kurkdjian, then The Laundress, Dirty Labs, DedCool; sources shifted to PureWow, The Quality Edit, Marie Claire, Who What Wear, Laundry Labs. Gemini presence is render-dependent, like the AI Overview. |
| Google AI Overview | on | logged-out | **NO (this render)** | AIO: Gain Moonlight Breeze (best fresh), Dirty Labs Signature (best eco/subtle), Topanga Scents (best luxury), Tide PurClean, Arm & Hammer. Sources: Who What Wear, Reviewed, Yahoo, Topanga Scents' own blog. Mozi absent from the AIO while its own blog post ("Best Smelling Laundry Detergent — Top Picks for 2026", May 15, 2026) ranks on organic page 1 of the same results page and Mozi products sit in the shopping units. First render attempt showed "can't generate an AI overview right now" before this one rendered; non-deterministic as documented. |
| Copilot | on | guest (clean, no login) | **NO** | Shopping-card list: Laundry Sauce Himalayan Cashmere (at Ulta, 4.3/1.4K), Snif Old Money (Ulta, 4.8/365), Tyler Diva, Mavwicks (23 reviews), Forever New, Gain, Safely, The Laundress, Molly's Suds, Amway SA8 (5 reviews). Mozi absent even though brands with two dozen reviews made the list. |

## Result table (Q3 brand-defense: "Mozi Wash vs Laundry Sauce", ChatGPT)

| Engine | Pass | Incognito/clean | What it said about Mozi Wash |
|---|---|---|---|
| ChatGPT | off | Temporary Chat | Does not know the brand and confabulates a profile that INVERTS its positioning: calls Mozi "a more straightforward everyday wash", "less of a perfume-forward detergent experience", "less emphasis on luxury scent/branding", possibly "minimalist/eco-leaning". Mozi's actual identity is perfume-inspired luxury scent. Picks Laundry Sauce for scent and presentation. |
| ChatGPT | on | Temporary Chat | Retrieves moziwash.com product cards (Free and Clear, Signature Cozy, 9 Pack) and correctly identifies both as luxury fragrance detergents. Verdict: "Laundry Sauce is probably the better luxury scented detergent... stronger scent-centered reputation, more reviews on its own site, and at least one direct luxury-detergent comparison picked Laundry Sauce over Mozi." Mozi wins only on liquid dosing / fragrance-free option / cost per load. |

## OFF-pass coverage limitations (documented per methodology)

- **Perplexity off:** N/A by design (always retrieves); no in-app incognito
  reachable in this build's account menu (checked: menu shows only settings /
  upgrade / apps / appearance / language / help / sign out). ON run logged-in;
  limitation and contamination disclosed below.
- **Copilot off:** N/A (guest grounds on Bing shopping/search, no retrieval
  toggle); ON captured clean.
- **Gemini off:** N/A (logged-out guest Gemini grounds on Google Search; no
  from-training-only mode reachable). ON captured clean.
- **Google AI Overview (googleaio) off:** N/A limitation by design (always
  web-grounded). Non-deterministic: first render attempt returned "can't
  generate an AI overview right now"; the captured render followed.

## Read

Mozi Wash was named in **1 of 8 Q1 passes** across the six engines: only Gemini
(clean, logged-out) named it, citing moziwash.com directly, so the brand's own
content (the 19.5KB llms.txt, 153-post blog) is reaching at least one retrieval
stack. A same-day Gemini re-render did NOT repeat the mention (sources shifted
to Marie Claire / PureWow), so even the single yes is per-render, not a stable
position. Everywhere else the brand is absent from both memory and live
retrieval:

- **No parametric memory anywhere.** ChatGPT and Claude OFF passes both map the
  category (mass, natural, luxury tiers) without Mozi. Asked head-to-head,
  ChatGPT OFF invents a description that is the opposite of the brand: a
  practical, NON-perfume-forward everyday detergent. Absence in a Temporary
  Chat / fresh chat is robust evidence (contamination biases toward presence,
  not absence).
- **Live answers are owned by Laundry Sauce.** Named in every live category
  answer on every engine (6 of 6), usually first and framed as the luxury
  standout. The citation graph behind the live answers: PureWow, Allure, Drew &
  Jonathan, The Quality Edit, Who What Wear, Reviewed, Yahoo shopping, Good
  Housekeeping, Consumer Reports, plus retailer data (Ulta) on Copilot. Mozi
  appears in none of these sources; its sole citation-graph presence is its own
  blog and site.
- **The gap is citations, not crawl access.** ChatGPT ON fetched Mozi product
  cards instantly when asked directly, and Google ranks Mozi's blog on page 1
  organic for the exact category query while the AIO above it skips the brand.
  Topanga Scents, a comparably small brand, made the AIO on the same query with
  the same play (own blog), showing the surface is winnable.
- **Brand-defense risk is live.** ChatGPT ON's verdict on "Mozi Wash vs Laundry
  Sauce" chose Laundry Sauce, citing reviews and a third-party comparison. A
  shopper asking an engine to compare loses the sale today.

## Contamination notes

- **ChatGPT:** both Q1 passes and both Q3 passes in Temporary Chat (true clean
  session, no memory/history). Account history contains no laundry queries.
- **Claude:** fresh claude.ai/new chats for both passes; no incognito mode
  exists, this is the cleanest available. Account history has no
  laundry-related chats (prior audit topics: sunscreen, pomade, serums,
  mattresses).
- **Perplexity:** logged-in profile; in-app incognito not reachable (see
  limitations). History sidebar holds only unrelated priors (mowers, snorkel
  masks, sunscreen, pomade, mattresses), so laundry contamination is low;
  disclosed. Note contamination biases toward naming a searched brand, and
  Mozi was still absent, which is the conservative direction.
- **Copilot:** guest session, no login, clean by default.
- **Gemini:** logged-out guest, clean (no personalization). The one YES for
  Mozi came from this clean session, so it is trustworthy.
- **Google AI Overview:** logged out; always web-grounded and
  non-deterministic (one failed render before the captured one). Presence
  language in the deck must be per-render.
