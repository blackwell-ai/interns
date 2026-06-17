# Good Molecules kickoff: structured-data evaluation and week-one plan

June 17, 2026. Prepared for the first weekly working session. This replaces the
"structured data is missing" picture from the June 1 audit, which is now out of
date. You shipped server-side schema and a real llms.txt since then. This evaluates
what is live today and lays out what we do this week.

Method: fetched 10 product pages across categories plus the homepage and a category
page with an allowlisted crawler user-agent, read the raw server HTML (no
JavaScript), and parsed every JSON-LD block. Findings are consistent across the
catalog, so the fixes are template-level, not per-page.

## What is live and correct today

The structured data is real and server-rendered. An AI crawler sees it without
running JavaScript. That is the thing that was broken at audit, and it is fixed.

On every product page:

- `Product` with `name` (size included, for example "Niacinamide Serum 30ml"),
  `image`, a rich `description`, and `brand`
- `Offer` with `price`, `priceCurrency: USD`, `availability: InStock`,
  `itemCondition: NewCondition`
- `AggregateRating` with real numbers and volume (4.0 to 4.8 across the sample,
  review counts from 18 to 7,627), consistent with the on-site widget
- An `OnlineStore` node with name, url, and logo on every page

The canonical product URL resolves to a size-specific page and the product name
carries the size. That partly addresses the 12ml-versus-30ml price confusion from
the audit. It is a good base to build on.

## Gaps we will close

These are present on every page we checked, so each fix is one template change that
propagates catalog-wide. Ordered by impact on how engines answer.

### 1. No product identifiers (sku, gtin, mpn), highest impact

The `Product` node has no `sku`, `gtin`/`gtin13`, or `mpn`. This is the single
biggest remaining gap. GTIN is the key an engine uses to know that your page and the
Amazon, Ulta, or Target listing are the same physical product. Without it, engines
cannot confidently reconcile your page with the retailer listings, which is exactly
why they fell back to Target and Amazon prices in the audit. Adding GTINs is what
lets your own page win the price.

Dependency: you supply the GTIN/UPC and internal SKU per product from your product
system. We provide the template and field mapping.

### 2. Size and variant relationships are not modeled

Each size is its own page with a single `Offer` at that size's price. There is no
`ProductGroup` linking the sizes and no `hasVariant`/`isVariantOf`, so an engine
that lands on the 30ml page has no signal that other sizes exist or what they cost.
A shopper asking "how much is the niacinamide serum" can still get a single price
with no size context. We model the size set as a `ProductGroup` so engines can
enumerate sizes and prices cleanly.

### 3. Offer is missing commerce fields you already have data for

The `Offer` has no `shippingDetails`, no `hasMerchantReturnPolicy`, no
`priceValidUntil`, and no offer `url`. Your llms.txt already states the shipping
tiers (free over $35, USPS 3 to 5 days, expedited options) and you have a return
policy. Putting those into `OfferShippingDetails` and `MerchantReturnPolicy` makes
the offer complete for agentic checkout and Merchant-style listings. This is the
Transactability dimension from the audit.

### 4. Only aggregate ratings, no review text

You expose `AggregateRating` but no individual `Review` objects, even though you
have thousands of reviews. Engines quote review text in answers. Surfacing a sample
of review nodes feeds Quotability directly.

### 5. Entity schema on the homepage is thin

The homepage carries only the `OnlineStore` node (name, url, logo). There is no
`sameAs` linking your social, Wikipedia/Wikidata, or retailer profiles, no
`contactPoint`, and no `WebSite` node with a `SearchAction`. `sameAs` is how an
engine grounds "Good Molecules" as a confident, single entity, which is the
Reputation and Recommendability dimensions. This is a high-value, low-effort add.

### 6. No breadcrumbs, no collection lists, thin social meta

- No `BreadcrumbList` on product pages, so engines lack category context
- Category pages (/shop/browse) carry no `ItemList`, so the catalog is not
  enumerable from the listing pages
- Only `og:site_name` is present. No `og:title`, `og:type: product`, `og:image`,
  `og:description`, or `product:price` meta, and no Twitter card

### 7. Still absent (from this morning's recon)

- `sitemap.xml` returns 404, so there is no sitemap enumerating your product URLs.
  Your platform should generate one. We specify the format.
- `llms-full.txt`, `agents.md`, and the `/.well-known/` agentic-commerce endpoints
  are still 404. The short llms.txt is strong; these are the deeper layer.
- No `FAQPage` schema and no on-page FAQ. The audit flagged this. FAQ content keyed
  to real query patterns (for example "what should I use for acne") plus `FAQPage`
  markup is content plus schema, started this week and built over the engagement.

## Worked example: niacinamide serum, before and after

Built from your live data. Values marked "you supply" are data only you have.

Current (live today):

```json
{
  "@context": "https://schema.org",
  "@type": "Product",
  "name": "Good Molecules Niacinamide Serum 30ml",
  "brand": { "@type": "Brand", "name": "Good Molecules" },
  "image": "https://.../prod_p.jpg",
  "description": "<h5>About...</h5> ...",
  "offers": {
    "@type": "Offer",
    "priceCurrency": "USD",
    "price": 6.0,
    "itemCondition": "https://schema.org/NewCondition",
    "availability": "https://schema.org/InStock"
  },
  "aggregateRating": { "@type": "AggregateRating", "ratingValue": 4.6, "reviewCount": 1751 }
}
```

Proposed (additions in the same server-rendered block):

```json
{
  "@context": "https://schema.org",
  "@type": "Product",
  "name": "Good Molecules Niacinamide Serum",
  "sku": "GM-NIA-30",                         // you supply
  "gtin13": "0860000000000",                  // you supply (UPC/EAN)
  "brand": { "@type": "Brand", "name": "Good Molecules" },
  "image": "https://.../prod_p.jpg",
  "description": "10% niacinamide serum that refines tone and texture...",
  "url": "https://www.goodmolecules.com/s/good-molecules-niacinamide-serum-30ml",
  "category": "Skincare > Serums",
  "offers": {
    "@type": "Offer",
    "url": "https://www.goodmolecules.com/s/good-molecules-niacinamide-serum-30ml",
    "priceCurrency": "USD",
    "price": 6.0,
    "priceValidUntil": "2026-12-31",
    "itemCondition": "https://schema.org/NewCondition",
    "availability": "https://schema.org/InStock",
    "shippingDetails": {
      "@type": "OfferShippingDetails",
      "shippingRate": { "@type": "MonetaryAmount", "value": 0, "currency": "USD" },
      "shippingDestination": { "@type": "DefinedRegion", "addressCountry": "US" },
      "deliveryTime": { "@type": "ShippingDeliveryTime",
        "transitTime": { "@type": "QuantitativeValue", "minValue": 3, "maxValue": 5, "unitCode": "DAY" } }
    },
    "hasMerchantReturnPolicy": {
      "@type": "MerchantReturnPolicy",
      "applicableCountry": "US",
      "returnPolicyCategory": "https://schema.org/MerchantReturnFiniteReturnWindow",
      "merchantReturnDays": 30                 // confirm your window
    }
  },
  "aggregateRating": { "@type": "AggregateRating", "ratingValue": 4.6, "reviewCount": 1751 },
  "review": [
    { "@type": "Review", "reviewRating": { "@type": "Rating", "ratingValue": 5 },
      "author": { "@type": "Person", "name": "from your review feed" },
      "reviewBody": "pull a sample from your on-site reviews" }
  ]
}
```

Plus a `ProductGroup` to tie the sizes together, `BreadcrumbList` on the page, and a
homepage `Organization` node with `sameAs`.

## Week-one plan

What we deliver this week (drafts ready to deploy on your platform):

- Corrected and enriched `Product`/`Offer` JSON-LD template, with the niacinamide
  serum worked end to end as the reference, plus the `ProductGroup` variant model
- Homepage `Organization` and `WebSite` schema with `sameAs`, `contactPoint`, and a
  `SearchAction`
- `OfferShippingDetails` and `MerchantReturnPolicy` blocks from your published terms
- `BreadcrumbList` for product pages and `ItemList` for category pages
- OpenGraph and product meta tag spec
- `llms-full.txt` and `agents.md` drafts, building on your live llms.txt
- The first FAQ set keyed to real skincare query patterns, with `FAQPage` markup

What we need from you:

- GTIN/UPC and SKU per product from your product system (blocks gap 1)
- Your exact return window and policy text (completes gap 3)
- Access to or a sample export of your review feed (enables gap 4)
- Platform owners to deploy the schema and generate `sitemap.xml` (gaps 6 and 7)

How we measure it: we re-check the structured data and crawler access after each
deploy and validate it against the schema.org and rich-results requirements, so the
before/after is concrete at the technical layer. The live engine answer testing is a
separate step we will schedule with you, not part of this week.

Tiers, so expectations are clear: we draft and hand over every artifact above (ours
to own). Deploying to your server and supplying GTINs/return text is yours to
execute. How third-party listicles and retailers respond is decided by them, and we
guide that work but cannot promise their behavior.
