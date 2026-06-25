# Test plan: does product sentiment drive what ChatGPT recommends

Date: 2026-06-24. Owner: GEO. Purpose: produce our own measured evidence that
social proof drives ChatGPT product recommendations, robust enough to survive an
OpenAI startups GTM person poking at it, and reusable as a standing benchmark.
Backs [[2026-06-24-social-proof-layer-thesis]].

## What we are actually testing

Three falsifiable claims, in priority order. We want each to come out as a number,
not a vibe.

1. **Sentiment predicts recommendation.** Across a fixed set of products in a
   category, real open-web sentiment predicts how often ChatGPT recommends each
   product. If true, social proof is the lever. If the correlation is near zero,
   the thesis is wrong and we should know before the meeting.
2. **Open-web beats first-party.** Where a brand's own `AggregateRating` contradicts
   the open-web corpus (GhostBed: 4.8 first-party vs 1.5 to 3.5 open web), ChatGPT
   tracks the open web. If true, brands cannot fake their way in by editing their
   own schema, which is the wedge for a verified neutral layer.
3. **The surface is unstable.** Repeat the same prompt many times and the
   recommendation set churns. Profound found about 95% of product titles appeared
   in under 30% of repeat runs. Instability is both a robustness control and a
   selling point: a stable, trusted feed has value precisely because the live
   surface is noisy.

## Why naive versions fail (the robustness controls)

An OpenAI GTM person will poke at exactly these, so we build the controls in from
the start:

- **Single runs are noise.** Recommendations churn run to run, so every prompt is
  repeated K times and the metric is a frequency, not a one-shot capture. K >= 10
  for the fast path, >= 15 for the robust path.
- **Browsing on vs off are different systems.** Off is parametric memory (no
  links, reflects training), on is live retrieval (citations). We run both and
  report them separately. Never conflate.
- **Real sessions, not WebSearch.** Per the audit evidence gate
  (`skills/ai-visibility-audit/`), the battery is real `/browse` sessions against
  ChatGPT, captured to artifacts with timestamps. WebSearch is never the battery.
  A finding with no screenshot does not exist.
- **Ground truth is frozen before we prompt.** We assemble and freeze the
  per-product sentiment table before running a single prompt, so the correlation
  is pre-registered, not fit after the fact. Same discipline as the audit truth
  table.
- **Confounds named.** Sentiment correlates with brand size, ad spend, and SEO
  presence. We cannot fully isolate causation from observation alone, so we report
  it as correlation, note the confounds out loud, and treat the causal claim as
  the next experiment (move a brand's sentiment, watch the recommendation move),
  not this one.

## Design

**Categories.** Start with mattresses, because we already hold ground-truth data
from the GhostBed audit (GhostBed, Saatva, Purple, Nectar). Add one second
category for the robust path so a single-category fluke cannot carry the result.

**Products.** 6 to 10 per category, chosen to span the sentiment range and to
include at least one first-party-vs-open-web contradiction case (GhostBed is the
built-in one).

**Ground-truth signals, frozen per product** (the independent variables):

| Signal | Source |
|---|---|
| Trustpilot score and volume | Trustpilot profile |
| BBB rating and complaint count | BBB profile |
| ConsumerAffairs / Sitejabber | those sites |
| Reddit sentiment (manual read of top threads) | Reddit |
| YouTube mention volume and tone | YouTube search |
| Amazon stars x review count | Amazon PDP (human, crawler-blocked) |
| Editorial review average | category review publishers |
| Listicle appearances ("best X" lists) | search |
| First-party `AggregateRating` | brand PDP schema |

GhostBed's row is already assembled in `brain/customers/ghostbed.md`. The other
products' rows are the main prep cost and need real browsing.

**Prompt battery** (the treatment). Each prompt run K times, browsing on and off,
captured. Mix of discovery, comparison, and constraint prompts:

- Discovery: "What is the best [category] to buy in 2026?" / "Recommend a [category]
  for [common use case]."
- Comparison: "[Brand A] vs [Brand B], which should I buy?" for several pairs,
  including a contradiction-case brand.
- Constraint: "Best [category] under [budget]" / "Most reliable [category] brand."
- First-party probe: a prompt that surfaces whether ChatGPT echoes the brand's own
  rating or the open-web reality for the contradiction case.

**Recommendation metric** (the dependent variable): for each product, recommendation
frequency = number of the K runs in which the product appears in the recommended
set, divided by K. Captured per prompt, per browsing mode.

## Analysis

1. **Correlation.** Spearman rank correlation between each frozen ground-truth
   signal and recommendation frequency, per browsing mode. Expectation from the
   literature: off-site mentions, editorial, YouTube, and listicle presence
   predict; first-party `AggregateRating` is weak. Report whichever way it lands.
2. **Citation breakdown** (browsing-on only): categorize every cited source (brand
   PDP, editorial, Reddit, YouTube, Trustpilot or review site, listicle, other)
   and report the distribution for product queries.
3. **Contradiction outcome:** for the contradiction case, state plainly which
   signal ChatGPT tracked.
4. **Stability:** report the churn (share of recommended products that appear in
   under 30% of repeat runs), as our own replication of the volatility finding.

## Two paths, pick by meeting date

- **Fast path (about 1 day, first signal and de-risk):** mattresses only, ChatGPT
  only, browsing on, 8 to 10 prompts, K = 10. Produces the correlation, the
  citation breakdown, and the contradiction result. Enough to walk in with real
  numbers and know whether the thesis has legs.
- **Robust path (about 3 to 4 days):** two categories, ChatGPT plus a Perplexity
  contrast (shows no single source of truth, which is itself a selling point),
  browsing on and off, K = 15 to 20, full frozen ground-truth tables. This is the
  version that survives scrutiny.

Recommendation: run the fast path immediately to confirm the thesis holds, then
extend to the robust path if the meeting is more than a few days out. The fast
path doubles as the safety check; if mattress sentiment does not predict ChatGPT's
picks at all, we rethink before we pitch.

## The artifact for OpenAI

A two-page memo plus the raw battery data: "We ran N product prompts through
ChatGPT, here is the exact source distribution, here is how strongly real sentiment
predicts what it recommends, here is the first-party-vs-reality gap, and here is how
unstable the surface is run to run." It tests our thesis for us and shows OpenAI a
packaged view of their own product-discovery behavior they may not have in this
form. Whatever the correlation turns out to be, the measured numbers are the asset.

## Honesty note on effort

The battery is human-paced real browser sessions, not an agent fan-out, and Amazon
or Rufus data is human-only (crawler-blocked, see memory). Budget real hours for
the prompt runs and the ground-truth assembly.
