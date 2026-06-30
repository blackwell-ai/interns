# Stream2Sea reputation corpus (phase 3) — 2026-06-29

Fixed source list (methodology): Trustpilot, BBB, ConsumerAffairs, Reddit, YouTube,
retailer (Amazon — Stream2Sea's main third-party marketplace). Each captured live to
`assets/reputation-<source>-2026-06-29.png`. Then checked whether the site entity
links to any of it via `sameAs` (recon shows homepage JSON-LD = Organization +
WebSite only, no sameAs array — flag if confirmed).

| Source | Rating | Reviews | Claimed? | Sentiment split | Capture |
|---|---|---|---|---|---|
| Trustpilot | 3.8 | 2 | **Claimed** (Jun 2019) | Both 5-star, tiny sample; "no history of asking for reviews" | reputation-trustpilot-2026-06-29.png |
| BBB | N/A | N/A | No profile | BBB search returns "No Results" for Stream2Sea | reputation-bbb-2026-06-29.png |
| ConsumerAffairs | N/A | N/A | No profile | Search returns no Stream2Sea listing (404); CA covers large service categories, not niche DTC | reputation-consumeraffairs-2026-06-29.png |
| Reddit | n/a | low volume | n/a | Positive but thin and niche: r/scuba defog praise (15 votes, "first thing that worked, love it"), old r/SkincareAddiction product question (6y, 4 votes). Reddit's own AI search: "No relevant content found." Name collides with streaming-site queries. | reputation-reddit-2026-06-29.png |
| YouTube | n/a | low reach | n/a | Brand-owned channel + scattered low-view third-party clips ("sunscreens tested - Stream2Sea #reefsafe #diving" 540 views; "Stream2Sea in 8 Seconds" 103 views). High-view videos are general roundups, not S2S-focused. No high-reach independent reviews. | reputation-youtube-2026-06-29.png |
| Amazon (retailer) | 4.0–4.6 | 1,000+ (flagship) | Active seller, branded store | Flagship Water Sport SPF 30 at 4.0★ with 1,000+ ratings; Every Day Active SPF 45 4.6★ (203); Tint SPF 45 4.1★ (144). "Overall Pick" badge on a S2S SKU. Strongest reputation surface by volume. | reputation-retailer-amazon-2026-06-29.png |

## Notes

**The reputation is real, positive, and stranded.** Sentiment is positive wherever
it shows up, but volume is low and the equity is concentrated almost entirely on
Amazon (flagship Water Sport SPF 30 over 1,000 ratings at 4.0★, Every Day Active SPF
45 at 4.6★/203, catalog 4.0–4.6). Off Amazon the footprint is thin:
Trustpilot is claimed but dormant (3.8, 2 reviews, "no history of asking for
reviews"), there is no BBB or ConsumerAffairs profile, Reddit is a handful of
positive but low-volume diving-community posts, and YouTube is mostly brand-owned
content plus scattered low-view third-party clips with no high-reach independent
reviews.

**The connective-tissue gap.** The homepage `Organization` entity carries **no
`sameAs` array** and **no `AggregateRating`** (verified live 2026-06-29). So none of
the reputation that exists is linked to Stream2Sea's machine-readable identity, and
an engine resolving the brand entity finds nothing pointing to Amazon, Trustpilot,
social, or YouTube. Raw Elements, by contrast, ships `AggregateRating` + `Brand` in
its homepage JSON-LD.

**Tie to Recommendability.** Off-site mentions are the strongest correlate of AI
visibility, and the editorial roundups the engines actually cite (Treeline Review,
NYT Wirecutter, Travel+Leisure, Good Housekeeping, Vogue, Project Reef's blog)
under-feature Stream2Sea. The reputation lives in places engines do not weight for
category recommendations (Amazon listings, diver word-of-mouth) and is absent from
the ones they do.

**Minor discoverability note:** the homepage has no server-rendered `<head>` `<title>`
(only inline SVG payment-icon titles); the title is injected client-side. `og:title`
is present ("Stream2Sea - Reef safer sunscreens and skin care"), so JS-rendering bots
recover it, but non-rendering crawlers see only the OG tag.
