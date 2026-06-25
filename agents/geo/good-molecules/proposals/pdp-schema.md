# Product page schema

> **At a glance**
> | | |
> |---|---|
> | **Priorities** | P1 identifiers, P2 Offer fields + variants, P3 reviews + breadcrumbs |
> | **Template** | `/s/` product (size) page |
> | **Add to** | the existing `Product` JSON-LD block, plus two new sibling blocks |
> | **You fill in** | GTIN + SKU (P1), return policy (P2), review sample (P3) |
> | **Authority** | [sources.md](sources.md), Product structured data section |

Prepared by Blackwell Enterprises, June 25, 2026.

Your `/s/` size pages serve a server-rendered `Product` block, which is a strong base.
This file enriches it. Three changes, in priority order: add product identifiers and
commerce fields to the `Product`/`Offer`, model the size variants with a
`ProductGroup`, and add a `BreadcrumbList`. Your `/p/` family URLs redirect to the
default `/s/` size page, so the `/s/` page is the one to edit.

---

## P1 + P2 + P3: enrich the Product and Offer

This is one combined edit to your existing `Product` block. The table below maps each
added field to its priority so you can stage them if needed.

| Added field | Priority | Why |
|---|---|---|
| `gtin13`, `sku` | **P1** | Lets engines match your page to the Amazon/Ulta/Target listing. Fixes price substitution. |
| `priceValidUntil`, offer `url` | P2 | Confirms the price is current and links the offer to its page. No data to gather. |
| `shippingDetails` | P2 | Answers "how much is shipping" from structured data. |
| `hasMerchantReturnPolicy` | P2 | Answers return questions. Uses your return window. |
| `review` | P3 | Surfaces quotable review text. You have the reviews; none reach engines today. |

**Current state (what your page returns now):**
```json
{
  "@context": "https://schema.org",
  "@type": "Product",
  "brand": {"@type": "Brand", "name": "Good Molecules"},
  "name": "Good Molecules Niacinamide Serum 30ml",
  "image": "https://dy6g3i6a1660s.cloudfront.net/ixxDS8a3Xeq2SLYHnHtaogu4C7g/prod_p.jpg",
  "description": "...",
  "offers": {
    "@type": "Offer",
    "priceCurrency": "USD",
    "price": 6.0,
    "itemCondition": "https://schema.org/NewCondition",
    "availability": "https://schema.org/InStock"
  },
  "aggregateRating": {
    "@type": "AggregateRating",
    "ratingValue": 4.6,
    "reviewCount": 1751
  }
}
```

**Recommended (added fields marked inline):**
```json
{
  "@context": "https://schema.org",
  "@type": "Product",
  "name": "Good Molecules Niacinamide Serum 30ml",
  "url": "https://www.goodmolecules.com/s/good-molecules-niacinamide-serum-30ml",
  "sku": "[YOU SUPPLY: internal SKU for this size]",
  "gtin13": "[YOU SUPPLY: UPC/EAN for this size]",
  "category": "Skincare > Serums",
  "brand": {"@type": "Brand", "name": "Good Molecules"},
  "image": "https://dy6g3i6a1660s.cloudfront.net/ixxDS8a3Xeq2SLYHnHtaogu4C7g/prod_p.jpg",
  "description": "10% niacinamide serum that minimizes pores and refines skin tone and texture. Lightweight, water-based formula. Fragrance-free. pH 7.1. 30ml / 1 oz.",
  "offers": {
    "@type": "Offer",
    "url": "https://www.goodmolecules.com/s/good-molecules-niacinamide-serum-30ml",
    "priceCurrency": "USD",
    "price": 6.00,
    "priceValidUntil": "2026-12-31",
    "itemCondition": "https://schema.org/NewCondition",
    "availability": "https://schema.org/InStock",
    "shippingDetails": {
      "@type": "OfferShippingDetails",
      "shippingRate": {"@type": "MonetaryAmount", "value": "5.00", "currency": "USD"},
      "shippingDestination": {"@type": "DefinedRegion", "addressCountry": "US"},
      "deliveryTime": {
        "@type": "ShippingDeliveryTime",
        "transitTime": {"@type": "QuantitativeValue", "minValue": 3, "maxValue": 5, "unitCode": "DAY"}
      }
    },
    "hasMerchantReturnPolicy": {
      "@type": "MerchantReturnPolicy",
      "applicableCountry": "US",
      "returnPolicyCategory": "https://schema.org/MerchantReturnFiniteReturnWindow",
      "merchantReturnDays": "[YOU SUPPLY: return window in days]",
      "returnMethod": "https://schema.org/ReturnByMail",
      "returnFees": "https://schema.org/FreeReturn"
    }
  },
  "aggregateRating": {
    "@type": "AggregateRating",
    "ratingValue": 4.6,
    "reviewCount": 1751
  },
  "review": [
    {
      "@type": "Review",
      "reviewRating": {"@type": "Rating", "ratingValue": 5},
      "author": {"@type": "Person", "name": "[reviewer name from your feed]"},
      "datePublished": "[review date]",
      "reviewBody": "[review text verbatim]"
    }
  ]
}
```

Implementation notes:
- `shippingDetails` here shows the $5 flat rate for orders under $35. Your policy has
  two tiers, so the cleanest version is two `shippingDetails` blocks in an array: one
  under-$35 at $5, one $35+ at $0 (set `shippingRate.value` to `0`). Use the two-block
  form if your platform renders an array here; otherwise the single block is fine.
- Set `priceValidUntil` to year end and refresh it when prices change. Standard
  practice.
- 3 to 5 `review` objects per product is enough for engine quoting. You do not need to
  expose every review.
- The `description` should be plain text, not HTML. Your current schema embeds HTML
  tags in it, which strict parsers may reject. See [sources.md](sources.md).

---

## P2: model the size variants with ProductGroup

Each size page carries a single `Offer` at that size's price, with nothing linking the
sizes. An engine on the 30ml page has no signal that a 12ml exists or what it costs.
Add a `ProductGroup` block to the `/s/` page, alongside the `Product` block, to tie
them together.

**Current state:** no `ProductGroup` anywhere. The 12ml and 30ml are unrelated pages
to an engine.

**Recommended block:**
```json
{
  "@context": "https://schema.org",
  "@type": "ProductGroup",
  "name": "Good Molecules Niacinamide Serum",
  "url": "https://www.goodmolecules.com/p/good-molecules-niacinamide-serum",
  "brand": {"@type": "Brand", "name": "Good Molecules"},
  "category": "Skincare > Serums",
  "description": "10% niacinamide serum that minimizes pores and refines skin tone and texture. Lightweight, water-based formula. Fragrance-free.",
  "image": "[your CDN image URL for this product]",
  "productGroupID": "[YOU SUPPLY: your internal product family ID]",
  "variesBy": "https://schema.org/size",
  "hasVariant": [
    {
      "@type": "Product",
      "name": "Good Molecules Niacinamide Serum 12ml",
      "url": "https://www.goodmolecules.com/s/good-molecules-niacinamide-serum-12ml",
      "sku": "[YOU SUPPLY]",
      "gtin13": "[YOU SUPPLY]",
      "size": "12ml",
      "offers": {
        "@type": "Offer",
        "url": "https://www.goodmolecules.com/s/good-molecules-niacinamide-serum-12ml",
        "priceCurrency": "USD",
        "price": "[YOU SUPPLY]",
        "priceValidUntil": "2026-12-31",
        "availability": "https://schema.org/InStock",
        "itemCondition": "https://schema.org/NewCondition"
      }
    },
    {
      "@type": "Product",
      "name": "Good Molecules Niacinamide Serum 30ml",
      "url": "https://www.goodmolecules.com/s/good-molecules-niacinamide-serum-30ml",
      "sku": "[YOU SUPPLY]",
      "gtin13": "[YOU SUPPLY]",
      "size": "30ml",
      "offers": {
        "@type": "Offer",
        "url": "https://www.goodmolecules.com/s/good-molecules-niacinamide-serum-30ml",
        "priceCurrency": "USD",
        "price": 6.00,
        "priceValidUntil": "2026-12-31",
        "availability": "https://schema.org/InStock",
        "itemCondition": "https://schema.org/NewCondition"
      }
    }
  ],
  "aggregateRating": {
    "@type": "AggregateRating",
    "ratingValue": 4.6,
    "reviewCount": 1751
  }
}
```

This pattern repeats for every product family. Substitute the name, slug, sizes,
prices, and rating. The niacinamide serum is the worked example.

---

## P3: BreadcrumbList

Your product pages carry no `BreadcrumbList` today, so engines lack category context.
Add this as a second `<script type="application/ld+json">` block alongside the
`Product` block. The category name and URL change per product.

**Current state:** no `BreadcrumbList` on any product page.

**Recommended block:**
```json
{
  "@context": "https://schema.org",
  "@type": "BreadcrumbList",
  "itemListElement": [
    {"@type": "ListItem", "position": 1, "name": "Home", "item": "https://www.goodmolecules.com/"},
    {"@type": "ListItem", "position": 2, "name": "Treatments & Serums", "item": "https://www.goodmolecules.com/shop/browse?tag=facial-treatments"},
    {"@type": "ListItem", "position": 3, "name": "Niacinamide Serum"}
  ]
}
```

---

## Data your team fills in for this file

These are the `[YOU SUPPLY]` values in the blocks above, pulled from your own systems:

1. GTIN/UPC and internal SKU per product per size variant. The highest-impact field.
2. Return policy: window in days, and whether return shipping is free.
3. Review text, 3 to 5 per product, from your review system.
4. The size variants and current prices per product, for the `ProductGroup.hasVariant`
   array.
