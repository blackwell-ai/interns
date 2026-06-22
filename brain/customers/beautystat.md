# BeautyStat

DTC skincare brand on Shopify (beautystat.com). Science-led, founded by cosmetic
chemist Ron Robinson; hero product is the Universal C Skin Refiner (20% L-ascorbic
acid, patented stabilization, about $62 for 30ml). Prospect only: audit produced
June 22, 2026 at Ethan's request, no relationship or outreach yet.

Last updated June 22, 2026. Sources: live recon by GEO agent (curl, view-source,
sitemap and products.json reads) and web-search-backed AI-recommendability and
reputation queries, all June 22, 2026.

## Documents

- Audit deck: [documents/beautystat-audit.pdf](documents/beautystat-audit.pdf),
  the repo's heavy AI Visibility Audit format (11 pages). Working source:
  `agents/geo/beautystat/beautystat-ai-visibility-audit.html`.

## Audit findings (verified June 22, 2026)

BeautyStat is the opposite of the Atlas pattern. It did the technical basics
right, so the story is "good bones, absent from the AI answers that matter," and
it lands a D rather than an F.

- **Has**: a strong meta description, an h1, homepage entity schema (OnlineStore,
  WebSite, SearchAction), Product + Offer + Brand + availability (InStock) schema
  on PDPs, and the AI-commerce files (llms.txt, agents.md, UCP) provisioned.
  Google Ads + GA4 + Klaviyo, no Meta pixel. 26 products, 13 collections, roughly
  140 blog posts.
- **Recommendability (32, the weak dimension)**: absent from "best vitamin C
  serum" AI answers, which named SkinCeuticals, TruSkin, La Roche-Posay, and
  CeraVe. Even value brand TruSkin is named, partly because it publishes its own
  "best vitamin C serums" guide that the engines cite. BeautyStat publishes no
  such category content.
- **Reputation real but not machine-readable**: award-winning, Ron Robinson's
  chemist authority, Hailey Bieber association, Daily Beast feature, estheticians
  calling it "12/10," sold on Amazon and Sephora, Yotpo reviews on-site. But the
  Yotpo rating loads in JavaScript and there is no AggregateRating/Review schema,
  so no rich-result stars and nothing for an AI engine to quote.
- **Founder and science not an entity**: no Organization or founder Person schema
  for Ron Robinson or the patents; the authority is in the copy, not structured.
- **Generic homepage title** ("BeautyStat Skincare," no high-intent terms);
  og:image missing on the homepage.
- **llms.txt is the generic 4.3 KB Shopify boilerplate**, not a content map.

Scorecard (five AI-behavior dimensions): Discoverability 62, Quotability 60,
Recommendability 32, Transactability 66, Reputation 64. Composite 57, grade D.
Competitive set SkinCeuticals / The Ordinary / TruSkin averages about 77 (B).

## Competitive set (June 22, 2026)

SkinCeuticals (premium gold standard, always AI-named, site behind a Cloudflare
challenge so its on-page signals are inferred), The Ordinary (descriptive
title/meta, large DTC brand, always named), TruSkin (value brand, AI-named "best
value," publishes its own category guide). All three appear in AI vitamin C
answers; BeautyStat does not. Competitor dimension scores are estimates from
public signals, labeled as such in the deck.

## Engagement framing

If pursued: Phase 1 $1,000 refundable pilot (AggregateRating/Review schema from
the Yotpo data, Organization + founder Person entity, title/meta/share-image
templates, llms.txt content map plus Article schema on the blog, and placement in
the category sources engines cite). Phase 2 ongoing AI visibility. Same playbook
as [[atlas]], tuned to a brand whose gap is recommendability rather than basic
machine-readability.
