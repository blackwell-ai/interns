# Decision: pursue social proof as a neutral, quality-gated layer for AI product discovery

Date: 2026-06-24. Source: founder session with Armaan (this working thread),
grounded in `brain/research/answer-engine-citation-behavior.md` and the GhostBed
audit (`brain/customers/ghostbed.md`).

> Status: thesis adopted as a direction to test, not a committed product. This
> sits inside the exploration mandate (see
> [[2026-06-14-company-is-in-exploration-phase]]); it is a node on the CPG and
> e-commerce value chain (see [[cpg-ecommerce-value-chain]]), not a pivot away
> from it. The test plan that gates further investment is
> `brain/research/2026-06-24-social-proof-drives-chatgpt-test-plan.md`.

## The thesis

Social proof and product sentiment are a primary driver of what AI engines
recommend in commerce, the signal is fragmented and contradictory across the open
web, and no walled platform can be the neutral layer that resolves it. Blackwell
builds that layer. The vision has three rungs that stack into a ladder, where each
rung earns the data and credibility for the next:

1. **Sell the social-proof read to brands as part of GEO.** Diagnose where a
   brand's social proof is weak, contradictory, or invisible to AI engines, and
   fix it. Sellable now, dogfooded by the audit practice, low risk. The wedge.
2. **Sell an aggregated, verified social-proof feed to AI and data companies.** A
   cleaner, structured, de-faked corpus that product-discovery systems can pull
   from. A cross-platform data play.
3. **Run quality-gated advertising inside AI platforms.** Brands stake money on
   their real product quality rather than buying placement regardless of quality.
   The monetization vision and the most original piece.

## Why it is plausible

From `brain/research/answer-engine-citation-behavior.md` (every claim sourced
there):

- YouTube mentions are the single strongest correlate of AI visibility across
  ChatGPT, AI Mode, and AI Overviews (r about 0.71 to 0.74, Ahrefs, 75,000
  brands). Backlinks scrape about 0.25. Off-site mentions beat links roughly 3 to
  1.
- Amazon Rufus essentially never recommends a product under 4.0 stars; median pick
  is 4.5 stars and about 3,000 reviews (Amalytix). Quality gating is already how
  the agents behave.
- Earned and third-party content is the most frequent citation type, and "best X"
  listicles are 43.8% of cited pages for recommendations (Ahrefs).
- On comparison prompts ("X vs Y"), social citations roughly triple, from 5.4% to
  15% (Profound).

The GhostBed audit is the proof the corpus is broken and worth fixing: a
first-party `AggregateRating` of 4.8 over 10,223 reviews against an open-web
reality of Trustpilot 3.5, BBB 1.61, ConsumerAffairs 1.5, with the entity
unlinked (`sameAs: none`) so nothing ties the brand to any of it.

## The crown jewel: make brands bet on quality

The quality-gated advertising mechanic is the piece no incumbent is positioned to
copy. It is congruent with how the engines already act (Rufus's 4.0-star floor),
so it prices a constraint the platforms already enforce instead of fighting it. It
is incentive-aligned: a brand earns amplification by having genuinely good
sentiment and stakes money on it, which removes much of the demand-side incentive
to fake reviews. Protect and develop this mechanic. Amazon and OpenAI cannot run
it cleanly because it would undercut their own placement-for-spend ad businesses.

## The two hard mountains

Rungs 2 and 3 both depend on AI engines actually using our data, and the engines
have no "sentiment slot" to plug into today. They retrieve from search indexes
(ChatGPT off Bing, Perplexity hugs Google at about 91% domain overlap, Claude off
Brave) or, for Rufus, Amazon's own first-party corpus. Two viable paths, and they
need different teams, so the choice is hard to reverse:

- **Win retrieval.** Become a domain the indexes rank and the engines cite, the
  way Trustpilot, G2, and Wirecutter did. Encouraging: 35% of cited "best X"
  listicles sit on low-authority domains (Ahrefs), so authority is not a hard
  gate, freshness and query-match are. Discouraging: this is a multi-year content
  and trust build, not an API sale.
- **Win partnership.** License the feed to the labs. Catch: commerce monetization
  inside the answer is exactly what OpenAI, Perplexity, and Amazon are racing to
  own themselves.

## The central tension

"Cleaner, reputable, AI-optimized" pulls against "brands pay us." Engines lean on
Reddit and YouTube because they read as raw, unpaid, authentic opinion. The more
brands pay and bet on placement, the more the corpus looks like sponsored content,
which engines and users discount. Trustpilot lives this problem; the GhostBed
Trustpilot profile is flagged as paid, responds, uses invitations, a credibility
knock the audit calls out. The product has to make verification visibly
independent so that "brand paid to be here" and "brand earned it on real
sentiment" are the same statement. Nail that and it is the moat. Fudge it and we
are Trustpilot with worse volume.

## The moat

Neutrality. Every walled platform is building its own version, so none can be the
cross-platform layer all of them cite. A product-sentiment layer owned by no
engine is the one position the incumbents structurally cannot take, the same
reason Wirecutter and G2 get cited everywhere. Lead with neutrality, not
aggregation.

## What we do now

- Sell rung 1 and instrument every engagement so it deposits structured, verified
  sentiment into a corpus we own.
- Do not pitch rungs 2 and 3 to anyone until the data and case studies prove the
  quality-gated model on real brands.
- Before building the feed, decide deliberately which mountain we climb (cited
  destination vs platform partnership).
- Run the test plan below before the OpenAI meeting so the thesis rests on our own
  measured numbers, not on secondhand studies.

## Open questions

- Who pays first at scale, brands (rung 1) or labs (rung 2), and does rung 1
  revenue actually fund the climb to rung 2.
- Is "verified and de-faked" a strong enough differentiator over free open-web
  sentiment to make a lab pay, or do they only pay for product data (price,
  availability, specs) and take sentiment for free.
- Can verification be made credible enough to survive the paid-content discount.

## Update, 2026-06-24 (later session): build the platform, the meeting consumes a view

Armaan's call: do not build an artifact tailored to the OpenAI meeting. Build the
actual product and let the meeting consume one view of it. The product is a
consumer review platform whose aggregated, verified stream is clean for three
audiences from a single data model: humans (a consumer review site), agents (a
structured feed an AI shopping system like ChatGPT can pull), and brands (a
reputation dashboard and the quality-gated entry point).

This reorders the ladder. The consumer platform and its aggregation engine come
first; the OpenAI conversation is one consumer of the agent feed, not the reason
to build. The thesis test becomes the build itself: aggregate real open-web review
data (Trustpilot, Reddit, YouTube video reviews, editorial, retailer) into one
clean stream, then prove three things. One, the problem is real, the raw open-web
signal is contradictory and messy. Two, the clean stream changes ChatGPT's answer
for the better. Three, humans trust the clean stream more than the raw open web.

Two-day scope for the OpenAI meeting: one category done deep (mattresses, ground
truth from the GhostBed audit), real scrapers across the sources that work, video
verdicts included, rendered into the three views plus a ChatGPT before-and-after
and a small human trust test. That is the platform in miniature, not a mockup.

Tooling on hand (checked 2026-06-24): yt-dlp for keyless YouTube search and
transcripts, Reddit API credentials, an OpenAI key for verdict extraction,
Supabase for storage and an auto-generated agent API, and the existing
ai-visibility-audit skill for the ChatGPT before-and-after. Amazon and Rufus stay
human-assisted (crawler-blocked).
