# HUM Nutrition live engine battery, June 16, 2026

Captures from the live two-pass prompt battery. This file holds the engines I drive
headless via /browse (Gemini, Google AI Mode, Google AI Overviews, Perplexity). The
login-gated engines (ChatGPT, Claude, Microsoft Copilot) and Amazon Rufus are run by
Armaan and pasted in under "Operator-run" below.

Truth table to grade against is frozen in `truth-table-raw.csv`. Competitor set for
category queries: Ritual, Olly, Nature Made, Care/of, Nutrafol (hair).

Grade each capture on: shows HUM, cites humnutrition.com, facts right (vs truth table),
which competitors named, where the answer is sourced from.

## Prompt battery

Quotability / facts (truth in parentheses):
- Q1. "How much does HUM Nutrition Collagen Love cost and what's in it?" (truth: $40.00, 4.53/198 reviews)
- Q2. "What is HUM Nutrition Daily Cleanse and what does it do?" (truth: $27.00, 4.59/2,493, most-reviewed)

Recommendability / category (does HUM get named vs the competitor set):
- Q3. "What are the best vitamins for skin?"
- Q4. "Best supplement for hair growth?" (HUM Hair Strong Gummies vs Nutrafol)
- Q5. "Best collagen supplement to take?" (HUM Collagen Love)
- Q6. "What's a good supplement for bloating and digestion?" (HUM Flatter Me, 2,869 reviews)
- Q7. "Best vitamins for stress and sleep?" (HUM Calm, Mighty Night)

Comparison / reputation / transactability:
- Q8. "HUM Nutrition vs Ritual, which is better?"
- Q9. "Is HUM Nutrition worth it and is it legit?"
- Q10. "Where can I buy HUM Nutrition supplements?" (does it route to humnutrition.com, Sephora, Amazon)

---

## Engine: Google AI Overviews

Run headed, June 16, 2026. Googlebot is allowed at HUM's WAF, so Google reaches the site.

- "best collagen supplement to buy": AI Overview names Vital Proteins (budget/top),
  California Gold Nutrition CollagenUP (best overall), Codeage marine, Ancient Nutrition.
  Sources Rolling Stone, GNC. **HUM Collagen Love absent.** Same roundup-driven gap as
  Perplexity, on the surface that can read HUM's own page.
- "is HUM Nutrition Collagen Love worth it and what does it cost": **cites humnutrition.com**
  and Amazon. Price right ($40.00 for a 30-day supply, 90 capsules, 3 daily, about $34 on
  Amazon or subscription). Ingredients right (Type I and III collagen from grass-fed beef,
  vitamin C). Carries an editorial frame that hurts HUM: "as a pill/capsule it delivers a
  much smaller dose of collagen (milligrams) compared to powder-based supplements, which
  provide much higher yields for a similar price." So on a direct query Google is accurate
  and cites the brand, but it repeats the listicle framing that capsules underdose vs powders.

## Engine: Google AI Mode

- "best collagen supplement to buy" (udm=50): names Vital Proteins (top overall),
  California Gold Nutrition, Transparent Labs, Ancient Nutrition. Sources Health.com,
  Rolling Stone. **HUM absent.** Confirms the category gap on Google's deeper AI surface too.

## Engine: Perplexity

Run headed (Cloudflare bot-check blocks headless). Six queries, June 16, 2026.

Pattern: direct brand queries read humnutrition.com and get facts right; category and
shopping queries omit HUM and pull from third-party roundups and medical sources.

- Q1 Collagen Love facts: **cites humnutrition.com**, price right ($40 regular, $32
  subscribe, matches truth table $40.00), ingredients right (grass-fed beef collagen,
  vitamin C, hyaluronic acid, chondroitin, grape seed, red wine extract), notes not
  vegan, 3 capsules daily. Other sources: grove. Quotability: strong.
- Q3 "best vitamins for skin": nutrient-education answer (vitamin C, A, E, D, biotin,
  zinc). No brands at all, no HUM, no competitors. Sources: WebMD, NCBI, AAD, VA. This
  phrasing returns medical info, not a shopping list.
- Q5 "best collagen supplement to buy 2026": recommends California Gold Nutrition
  CollagenUP, Vital Proteins, Transparent Labs, Ancient Nutrition, Sports Research.
  **HUM Collagen Love absent.** Sources: Rolling Stone, iHerb, Target, vitaminshoppe.
  Driven by affiliate roundups that omit HUM. Recommendability: gap.
- Q4 "best supplement for hair growth": nutrient answer (iron, vitamin D, zinc, folate)
  plus commercial Nutrafol and Viviscal. **HUM Hair Strong Gummies absent** (1,219
  reviews). Nutrafol/Viviscal own the commercial-product slot.
- Q9 "Is HUM Nutrition worth it and legit?": **cites humnutrition.com** plus Medical
  News Today, Chicago Tribune, Trustpilot, BBB. Verdict "legit yes, essential no."
  Positives: triple-tested, Clean Label Project certified, GMP, third-party tested.
  Watchouts: expensive, subscription complaints, some shipping/CS issues, BBB not
  accredited. Reputation: solid and mostly positive, brand site is a source.

Takeaway: on Perplexity, HUM is readable and accurately represented when named, and
invisible when the shopper asks by category. The gap is the third-party roundup corpus,
not the brand's own page.

## Engine: Gemini

Login-gated (gemini.google.com needs a Google account). Moved to the operator-run pass.

## Reputation corpus (read live, June 16, 2026)

- Trustpilot: 1.8/5 over 72 reviews (JSON-LD aggregateRating on the claimed profile).
  Low volume and negative-skewed, the usual Trustpilot pattern for a DTC brand.
- BBB: A- rating, NOT BBB-accredited.
- On-site reviews (frozen truth table): 4.2 to 4.75 across the catalog, several products
  over 1,000 reviews. The first-party corpus is strong and deep.
- Engine-synthesized sentiment (Perplexity, citing Medical News Today, Chicago Tribune,
  Trustpilot, BBB): "legit yes, essential no." Positives are triple-testing, Clean Label
  Project certification, GMP, third-party testing. Watchouts are price, the subscription
  model, and some shipping or customer-service complaints.

The split that matters: first-party reviews glow, third-party Trustpilot is 1.8, and the
engines that read Trustpilot carry the negative note. The brand does not control the
third-party corpus the engines lean on.

---

## Provisional scorecard (open-engine pass only, pending operator engines)

Graded against the frozen truth table and the evidence above. Provisional because
ChatGPT, Claude, and Microsoft Copilot are not yet run, and Copilot (Bing-fed) will move
Discoverability and Recommendability once known, given the Bingbot block.

| Dimension | Provisional | Basis |
|---|---|---|
| Discoverability | ~74 | AI crawlers all allowed and Googlebot allowed (strong), but Bingbot blocked at the WAF and no agent discovery files (llms.txt, .well-known) |
| Quotability | ~85 | Server-rendered, canonical, well-formed Product/Offer/AggregateRating/FAQPage; engines get price and actives right and cite humnutrition.com. The strength. |
| Recommendability | ~48 | Absent from collagen, hair, and skin category answers on Perplexity, Google AI Overviews, and Google AI Mode. Roundup corpus omits HUM; capsule-vs-powder frame works against it. The core gap. |
| Transactability | ~55 | Pricing is agent-readable, but no llms.txt, UCP, ACP, AP2, or MCP, so no first-party agent checkout |
| Reputation | ~68 | Strong on-site reviews, weak Trustpilot (1.8/72), BBB A- not accredited; engines pass along a balanced "legit but not essential" |

Provisional composite about 66 (low C / high D), the same ballpark as Good Molecules but
the opposite shape: HUM is highly quotable and poorly recommended, where Good Molecules
was blocked across the board. The headline is "readable but under-recommended."

---

## Operator engines, run in the headed browser (logged-in profile), June 16, 2026

### ChatGPT (GPT-5.5, web search on, logged in)

- "best collagen supplement to buy in 2026": recommends Sports Research (best overall),
  Momentous, BUBS Naturals, Vital Proteins. Sources: those brands plus PMC, FDA. **HUM
  absent.** Explicit rule in the answer: "choose powder over gummies or capsules because
  you can realistically get a full 10 to 20 g serving." That rule structurally excludes
  HUM's capsule collagen.
- "How much does HUM Collagen Love cost and what is in it?": price right ($40 one-time,
  $32 Subscribe & Save, 90 capsules / 30 servings), full ingredient table correct
  (vitamin C 60 mg, hydrolyzed collagen 600 mg, chondroitin 150 mg, grape seed 150 mg,
  hyaluronic acid 120 mg, red wine 30 mg), notes not vegan, allergen-free. Sources cited:
  HUM Nutrition (Sanity CDN, their CMS). Quotability strong.

### Microsoft Copilot (guest, Bing-fed)

This is the engine the Bing block was expected to hurt. It does not, much.

- "How much does HUM Collagen Love cost and what is in it?": answers correctly ($40,
  $32 subscribe, $39.99 on Amazon), ingredients right, and **cites "HUM Nutrition
  (official site)"** plus Amazon and the NIH Dietary Supplement Label Database. So despite
  the Bingbot 403, Copilot still surfaces HUM's own facts and labels the official site as a
  source (likely via cache or a non-Bingbot path). The Bing-block consequence is milder
  than recon implied: Copilot is not blind to HUM.
- "best collagen supplement to buy in 2026": recommends Sports Research, Ancient Nutrition,
  Momentous, Black Girl Vitamins, Garden of Life Beauty. **HUM absent.** Same category gap.

### Claude (logged in)

Could not capture this session: the composer renders, but after sending, the conversation
view stayed on a loading spinner in the headed browser (streaming/websocket render issue),
not a HUM-specific result. Retry needed, or run manually.

### Amazon Rufus

Human-only (Amazon blocks crawlers). Not run.

### Gemini (guest)

Guest mode accepted the prompt but hung on a loading spinner without producing an answer
or sources. Needs a signed-in Google session to capture. Not measured this pass.

### Claude (Opus 4.8, web search on, Armaan's account)

Captured after Armaan refreshed the login and the daemon was restarted (the earlier
spinner was a stale-session 401, fixed by re-auth).

- "best collagen supplement to buy 2026": recommends Transparent Labs Grass-Fed Collagen
  (best overall), Nutricost Collagen Hydrolysate (budget), Wellah The Afterglow (hair),
  CollagenUP / California Gold Nutrition (value). Sources: Fortune and Rolling Stone tested
  roundups. **HUM absent.** Note it flagged "no added vitamin C" as a downside for the top
  pick, which is exactly what HUM Collagen Love has, and still did not surface HUM.
- "How much does Collagen Love cost and what is in it?": facts right ($39.99, ~$33.99 on
  Amazon, full ingredient table to the milligram). But the citations were **Grove
  Collaborative, Healf, and Amazon, not humnutrition.com.** ClaudeBot is allowed to read
  HUM's site, yet Claude sourced this answer from retailers. Facts accurate, brand not the
  cited source.

### Gemini (3.5 Flash, signed-in Google account)

- "best collagen supplement to buy 2026": **refused.** "I want to help as much as I can,
  but my safety filters kicked in." Gemini declines to recommend supplements, so it is not
  a recommendation surface for this category at all, for HUM or anyone.
- "How much does Collagen Love cost and what is in it?": facts right ($40 one-time, ~$32
  subscription, Types I and III collagen from grass-fed beef, vitamin C, hyaluronic acid,
  chondroitin, red wine and grape seed extracts), and **cites HUM Nutrition.** Quotability
  strong; some odd secondary citations (NicholsMD, Anthropologie).

### Amazon Rufus

Human-only (Amazon blocks crawlers). Not run.

## Recommendability gap is universal

"Best collagen supplement" omits HUM Collagen Love on every engine tested: Perplexity,
Google AI Overviews, Google AI Mode, ChatGPT, and Copilot (5 of 5). The named winners vary
(Sports Research, Vital Proteins, California Gold, Ancient Nutrition, Momentous, Transparent
Labs), but they are powders, and HUM's capsule format is penalized by an explicit
"powder over capsules" rule on ChatGPT and a "capsules underdose" frame on Google. The
brand's own page is readable everywhere; the category answer is built from roundups that do
not list HUM.

## Quotability confirmed strong (operator engines)

Direct HUM queries return correct price and ingredients and cite the official site on
ChatGPT and Copilot, matching the Perplexity and Google AI Overview brand-query results.
