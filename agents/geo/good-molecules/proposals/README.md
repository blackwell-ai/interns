# Good Molecules: AI visibility implementation pack

Prepared by Blackwell Enterprises for the Good Molecules engineering team.
June 25, 2026.

This folder is the implementation pack for the structured-data and AI-visibility work
from our engagement. Each file gives you the exact block to add, where it goes, and
the fields to fill. Everything was verified by fetching goodmolecules.com live with AI
crawler user-agents and reading the raw server HTML, so the "current state" in each
file is what your site returns today.

These are recommendations for your team to implement. We are not deploying anything on
your site and you are not sending anything back to us; the `[YOU SUPPLY]` values are
data your engineers fill in from your own systems as they implement each block.

Start with this page. It maps every change to a priority and a file, lists the data
your team fills in, and ends with a deploy checklist.

---

## How to read this pack

- Changes are grouped **P1 / P2 / P3** by impact, the same order as the presentation.
- Every file opens with an **At a glance** header: priority, which template it touches,
  what it depends on from you, and effort.
- Each change is shown as **Current state** (what your page returns now) next to
  **Recommended** (what to add). Added lines are called out.
- Fields marked `[YOU SUPPLY]` are data only your team holds. They are collected in the
  "Data your team fills in" section below so you can gather them in one pass.

---

## Priority map

| Priority | Change | File | Data you fill in |
|---|---|---|---|
| **P1** | Product identifiers: `sku`, `gtin13` on the Offer | [pdp-schema.md](pdp-schema.md) | GTIN + SKU |
| **P2** | Offer commerce fields: shipping, returns, `priceValidUntil`, offer `url` | [pdp-schema.md](pdp-schema.md) | return policy |
| **P2** | Size variant model: `ProductGroup` | [pdp-schema.md](pdp-schema.md) | none |
| **P3** | Review objects on product pages | [pdp-schema.md](pdp-schema.md) | review text |
| **P3** | Homepage entity: `sameAs`, `contactPoint`, `WebSite` search | [homepage-schema.md](homepage-schema.md) | social/retail URLs |
| **P3** | Category `ItemList` + `BreadcrumbList` | [category-schema.md](category-schema.md) | none |
| **P3** | OpenGraph + product meta, and `sitemap.xml` | [opengraph-meta.md](opengraph-meta.md) | share image |
| **P3** | `llms-full.txt` + `agents.md` guide files | [llms-full.txt](llms-full.txt), [agents.md](agents.md) | return policy |
| **P3** | FAQ content + `FAQPage` markup | [faq-schema.md](faq-schema.md) | return policy |

Reference: [sources.md](sources.md) maps every recommendation to a Google Search
Central or schema.org authority, so your team can verify each one independently.

---

## Already in place (no action needed)

Confirmed live June 25, so you can skip these:

- AI crawler access. GPTBot, ClaudeBot, PerplexityBot, and Perplexity-User all return
  200. This was the heaviest audit finding and it is complete.
- Server-rendered `Product` and `Offer` JSON-LD on `/s/` size pages.
- An `OnlineStore` node on the homepage (name, url, logo).
- A live, well-structured `llms.txt`.

The work in this pack is enrichment on top of that base.

---

## Data your team fills in

These are the `[YOU SUPPLY]` values, pulled from your own systems as you implement.
Gathering them once up front lets you move through the whole pack in one pass. Nothing
here comes to us.

| # | Data | Needed for | Used in |
|---|---|---|---|
| 1 | GTIN/UPC + internal SKU, per product per size | **P1** (highest value) | pdp-schema.md |
| 2 | Return policy: window in days, free returns or not, returns page URL | P2, P3 | pdp-schema.md, faq-schema.md, guide files |
| 3 | Social + retailer profile URLs (Instagram, TikTok, Beautylish, Ulta, Target) | P3 | homepage-schema.md |
| 4 | Review text, 3 to 5 per product, from your review system | P3 | pdp-schema.md, faq-schema.md |
| 5 | Homepage share image, 1200 x 630 | P3 | opengraph-meta.md |
| 6 | Your e-commerce platform, and confirm `/shop/browse?q=` is search | P3 | opengraph-meta.md, homepage-schema.md |

Item 1 is the one that matters most. It fixes the price-substitution problem from the
audit, where engines quoted Amazon and Target prices because they could not match your
page to the retailer listing.

---

## Suggested deploy order

Each change is one template edit that propagates across the catalog. A sensible order:

1. **Quick wins, no data to gather:** `priceValidUntil` and offer `url`,
   `ProductGroup`, `BreadcrumbList`, category `ItemList`, OpenGraph meta. Ship first.
2. **Turn on `sitemap.xml`** in your platform settings and reference it from robots.txt.
3. **Product identifiers (P1)** once you have GTIN/SKU pulled from your product system.
4. **Shipping and return blocks, and the guide files** once your return policy is set.
5. **Review objects and FAQ review references** once you have the review text.
6. **Homepage `sameAs`** once you have the profile URLs.

Tell us when a batch is live and we re-validate the structured data against schema.org
and the rich-results requirements, then schedule the live engine battery as the
before/after proof. That validation and the engine testing are our side of the work.

---

## File index

| File | What it is |
|---|---|
| [pdp-schema.md](pdp-schema.md) | Product page: identifiers, full Offer, ProductGroup, reviews, breadcrumbs |
| [homepage-schema.md](homepage-schema.md) | Homepage: enriched OnlineStore with sameAs, plus WebSite search |
| [category-schema.md](category-schema.md) | Category pages: ItemList and BreadcrumbList |
| [opengraph-meta.md](opengraph-meta.md) | OpenGraph and product meta tags, plus sitemap.xml |
| [faq-schema.md](faq-schema.md) | FAQ content set with FAQPage markup |
| [llms-full.txt](llms-full.txt) | Full AI guide file, ready to upload |
| [agents.md](agents.md) | Agent interaction guide, ready to upload |
| [sources.md](sources.md) | Every recommendation mapped to its authority |
