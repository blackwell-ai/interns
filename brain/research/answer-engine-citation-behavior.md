# Why AI answer engines cite what they cite

Researched June 11, 2026 (background research agent, primary sources verified).
Compiled for the Husqvarna follow-up meeting; durable reference for all GEO
engagements. Every claim carries (source, date, URL).

## 1. The headline: the engines barely agree with each other

- **Profound** ran **100,000 identical prompts** through ChatGPT and Perplexity:
  **~89% of citations came from completely different sources** — only 11%
  overlap. Across all platform pairs, citation overlap ranged from **6%** (AI
  Overviews vs Copilot) to **16.4%** (Perplexity vs AI Overviews). Citation
  breadth also differs: AI Overviews ~7.7 domains/response, Perplexity ~7.3,
  ChatGPT ~5.0, Copilot ~2.5. (Profound, "Answer Engine Citation Overlap
  Strategy," July 1, 2025 — https://www.tryprofound.com/blog/citation-overlap-strategy)
- Implication: **there is no single "rank in AI" — each engine has its own
  retrieval stack and source diet**, so visibility has to be measured and won
  per engine.

## 2. Per-engine citation behavior

| Engine | Source diet (with numbers) | Retrieval backbone / organic overlap | Source |
|---|---|---|---|
| **ChatGPT** | Wikipedia #1 domain at **7.8% of all citations** (47.9% share of its top-10 sources); Reddit 1.8%, Forbes 1.1%, G2 1.1%. By category: **54% brand sites, 25% media, 15% institutions, only 5% social** — the most "institutional" engine. | **Bing, not Google**: **87%+ of SearchGPT citations matched Bing's top-10 organic; only 56% matched Google (median Google rank: 17)** (Seer, Feb 6, 2025). Semrush: pages ChatGPT cites rank **position 21+ in Google ~90% of the time** (July 21, 2025). | Profound, June 5, 2025, 680M citations — https://www.tryprofound.com/blog/ai-platform-citation-patterns ; Profound, Jan 8, 2026, 27M citations — https://www.tryprofound.com/blog/enhanced-citation-categories ; Seer — https://www.seerinteractive.com/insights/87-percent-of-searchgpt-citations-match-bings-top-results ; Semrush — https://www.semrush.com/blog/ai-mode-comparison-study/ |
| **Perplexity** | The **Reddit/review engine**: Reddit **6.6% of ALL citations** (46.7% of top-10-source share); YouTube 2.0%, Gartner 1.0%, Yelp 0.8%. Cites **social/UGC at 19.4% vs ChatGPT's 5.3%** (~4x). | Hugs Google organic hardest: **>91% domain / ~82% URL overlap with Google top-10**. | Profound June 2025 + Jan 2026; Semrush July 2025 (URLs above) |
| **Google AI Overviews** | Most balanced: Reddit 2.2%, YouTube 1.9%, Quora 1.5%, LinkedIn 1.3%; ~69% brand-owned by category. | Overlap with organic **rising**: 32.3% (May 2024) → 54.5% (Sept 2025) (BrightEdge, Sept 18, 2025). SE Ranking: 84.7% of AIOs link ≥1 top-10 organic domain. **E-commerce had the LOWEST convergence growth of 9 industries (+0.6 pp)** — commerce answers still sourced outside classic rankings. | Profound June 2025; BrightEdge — https://www.brightedge.com/resources/weekly-ai-search-insights/rank-overlap-after-16-months-of-aio ; SE Ranking — https://seranking.com/blog/google-ai-overviews-research/ |
| **Google AI Mode** | UGC-heavy: **Reddit, YouTube, Facebook in 68%+ of results**; 92% of responses carry ~7-domain sidebar. | **~54% domain / ~35% URL overlap with Google top-10.** | Semrush AI Mode study, July 21, 2025, 5,000 keywords / 150K+ citations (URL above) |
| **Gemini** | Most brand-site-friendly: **73% brand-owned citations**, 18% media, 2% social. | Google index. | Profound, Jan 8, 2026 |
| **Claude** | 66% brand, **24% media** (second-most media-reliant), 3% social. | Brave-search-based retrieval. | Profound, Jan 8, 2026 |
| **Copilot** | **Most media-dependent: 33% earned media**, 59% brand; stingiest citer (~2.5 domains/response). | Bing index. | Profound, Jan 8, 2026 + July 1, 2025 |

**Volatility caveat:** Semrush's 13-week tracking (230K+ prompts, Jul 14–Oct 12,
2025) caught ChatGPT **cutting Reddit citations from ~60% of responses to ~10%
in a single mid-September algorithm change**; Perplexity and AI Mode untouched.
Source mix is a moving target — monitor, don't memorize. (Semrush, Nov 10,
2025 — https://www.semrush.com/blog/most-cited-domains-ai/)

## 3. What statistically correlates with being cited/mentioned

- **Ahrefs, 75,000 brands, Spearman correlations** (Dec 12, 2025 —
  https://ahrefs.com/blog/ai-brand-visibility-correlations/):
  - **YouTube mentions: r = 0.737 (ChatGPT), 0.740 (AI Mode), 0.712 (AIO)** —
    strongest single factor on all three engines.
  - **Branded web mentions: 0.664 / 0.709 / 0.656** (original AIO finding June
    2025: https://ahrefs.com/blog/ai-overview-brand-correlation/).
  - **Backlinks: only ~0.25–0.29; Domain Rating 0.27–0.33.** Off-site
    *mentions* beat links ~3:1.
- **Seer Interactive** (Jan 7, 2025, 10K queries through GPT-4o —
  https://www.seerinteractive.com/insights/what-drives-brand-mentions-in-ai-answers):
  Google page-1 presence correlated ~0.65 with LLM brand mentions; backlinks
  "weak or even neutral."
- **Semrush AI Visibility Study** (Sept 3, 2025 —
  https://www.semrush.com/blog/ai-search-visibility-study-findings/):
  community + review platforms dominate consumer/tech sourcing — G2 hit 20%
  citation frequency in digital-tech ChatGPT answers.
- **xfunnel** (Feb 26, 2025, 40K responses / 250K citations —
  https://www.xfunnel.ai/blog/what-sources-do-ai-search-engines-choose):
  **earned (third-party/editorial/affiliate) content is the most frequent
  citation type** across ChatGPT, Gemini, Perplexity; UGC spikes mid-journey
  (comparison stage); owned domains dominate only at final evaluation.
  Follow-up (768K citations / 12 weeks): product-related content is 46–70% of
  all citations (SEJ — https://www.searchenginejournal.com/ai-search-study-product-content-makes-up-70-of-citations/544390/).
- **Mentions vs citations (browsing on/off):** recommendations without a
  search step come from parametric memory (no links); citations only appear on
  retrieval. On brand-comparison prompts, social citations jump to **15% vs
  5.4%** on open category prompts — "Husqvarna vs X" sends engines straight to
  Reddit and reviews. (Profound, Jan 8, 2026)

## 4. What drives PRODUCT recommendations (commerce queries)

- **Listicles are the kingmaker.** Ahrefs, 750 "best X" prompts, 26,283
  ChatGPT source URLs (Dec 4, 2025 — https://ahrefs.com/blog/best-lists-research/):
  - **"Best X" lists = 43.8% of all cited page types** — #1 content type
    behind recommendations.
  - **Freshness gates inclusion: 79.1% of cited lists updated in 2025; 26%
    within the prior two months.**
  - **~35% of cited lists sit on low-authority domains** — ChatGPT doesn't
    check Domain Rating the way Google does.
  - For physical products, when ChatGPT cited the brand itself it used
    **product pages 87.2% of the time** — PDP content quality feeds answers.
  - Self-promotional "best of" lists (publisher ranks itself #1) appeared as
    sources in over a third of software responses.
- **ChatGPT Shopping is high-volume and volatile.** Profound, 22.5M ChatGPT
  buy-offers over 10 days (Mar 10–20, 2026 —
  https://www.tryprofound.com/blog/chatgpt-retail-target-walmart): top 20
  merchants take ~40% of offers (Walmart 8.78% of #1 positions); median
  carousel = 5 products; **~95% of product titles appeared in <30% of repeat
  runs of the same prompt**.
- **ChatGPT Shopping Research mode pulls 100+ citations per answer** vs 8–12
  normal — PDPs, expert testers, editorial reviews, forums, video reviews
  (Yotpo, Dec 18, 2025 — https://www.yotpo.com/blog/chatgpts-new-shopping-research/).
- **Amazon Rufus.** Amalytix, 1,300+ Rufus-recommended products (Nov 25,
  2024 — https://www.amalytix.com/en/knowledge/ai/amazon-rufus-pattern-analysis/):
  - **Effectively nothing below 4.0 stars gets recommended; median rating 4.5;
    median review count 2,991.**
  - **92.1% Prime-eligible, 87.2% had A+ content, median 7 images; median
    organic search rank of recommended items: 41** — Rufus isn't reading the
    search ranking.
  - Amazon's own disclosure: Rufus trains on catalog, customer reviews,
    community Q&A, and the open web
    (https://www.amalytix.com/en/knowledge/ai/amazon-rufus-guide-2026/).

## 5. Conflicting numbers — argue both sides

AIO-vs-organic overlap ranges from **20–26%** (Semrush link-level, Sept 2024
data, pub. July 22, 2025 — https://www.semrush.com/blog/ai-overviews-study/)
to **54.5%** (BrightEdge citation-level, Sept 2025) to **84.7%** (SE Ranking,
domain-level). Different units (URL vs citation vs domain) at different times;
trend is overlap rising through 2025.

## 6. Five punchiest stats for a live meeting

1. "Run the same 100,000 prompts through ChatGPT and Perplexity and **89% of
   the cited sources are different**." (Profound, July 1, 2025)
2. "**87% of ChatGPT's search citations match Bing's top-10 — only 56% match
   Google's**, and ~90% of what it cites ranks position 21+ in Google."
   (Seer, Feb 2025; Semrush, July 2025)
3. "Across 75,000 brands, **YouTube mentions are the #1 correlate of AI
   visibility** (r ≈ 0.71–0.74) — backlinks scrape ~0.25." (Ahrefs, Dec 2025)
4. "**43.8% of pages ChatGPT cites for 'best X' recommendations are
   listicles** — 79% updated within the year, 35% on low-authority sites."
   (Ahrefs, Dec 2025)
5. "**Amazon's Rufus essentially never recommends a product under 4.0 stars —
   median pick: 4.5 stars and ~3,000 reviews**; median recommended item sat at
   organic rank 41." (Amalytix, Nov 2024)

Backup: "ChatGPT changed its source mix overnight in September 2025 — Reddit
citations collapsed from ~60% of responses to ~10%. This landscape is
monitored, not memorized." (Semrush, Nov 10, 2025)

## Known gap

Profound has not published per-engine product-category citation shares for
outdoor equipment specifically; closest is their ChatGPT Shopping
retailer-share data (March 2026).
