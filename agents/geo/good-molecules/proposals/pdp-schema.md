# Product page schema

Prepared by Blackwell Enterprises for the Good Molecules engineering team.
June 18, 2026.

We fetched goodmolecules.com on June 18 using GPTBot and ClaudeBot user-agents to
see exactly what AI crawlers see today. Two issues found.

---

## Issue 1: /p/ pages have no schema

Your `/p/` URLs are the canonical product family pages. They are the URLs your
`llms.txt` links to. An AI that reads your llms.txt and follows a link to
`goodmolecules.com/p/good-molecules-vitamin-c-serum-with-oryzanol` finds a page
with no JSON-LD at all.

We confirmed this on June 18 for:
- `goodmolecules.com/p/good-molecules-vitamin-c-serum-with-oryzanol` — no JSON-LD
- `goodmolecules.com/p/good-molecules-discoloration-correcting-serum` — no JSON-LD

**Before (what a bot sees today):**
```
(no JSON-LD block in page source)
```

**After (what we propose):**

Add a `ProductGroup` block that covers all size variants. This tells engines that
the sizes are the same product at different prices, and gives them a structured
entry point from your llms.txt links.

```json
{
  "@context": "https://schema.org",
  "@type": "ProductGroup",
  "name": "Good Molecules Niacinamide Serum",
  "url": "https://www.goodmolecules.com/p/good-molecules-niacinamide-serum",
  "brand": {
    "@type": "Brand",
    "name": "Good Molecules"
  },
  "category": "Skincare > Serums",
  "description": "10% niacinamide serum that minimizes pores and refines skin tone and texture. Lightweight, water-based formula. Fragrance-free.",
  "image": "[your CDN image URL for this product]",
  "productGroupID": "[YOU SUPPLY — your internal product family ID]",
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

This pattern repeats for every product family. Substitute the product name, slug,
sizes, prices, and aggregate rating. The niacinamide serum is the worked example.

---

## Issue 2: /s/ pages have schema but it is missing critical fields

Your `/s/` size-specific pages do have a JSON-LD block — that is a real improvement
since the audit. But it is missing the fields engines need to answer the questions
real users ask: what does shipping cost, what is the return policy, can I trust
this price.

**Before (what a bot sees today — confirmed live June 18):**
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

What is missing and why it matters:

- No `sku` or `gtin13`: engines cannot match this page to the same product on Amazon,
  Ulta, or Target. This is the root cause of the price-substitution finding — Claude
  fell back to Amazon for prices because it could not confidently match your page to
  the product.
- No `url` in the `Offer`: the offer is not linked to its canonical page.
- No `priceValidUntil`: the price looks unverified to strict parsers.
- No `shippingDetails`: engines cannot answer "how much is shipping" from structured
  data. They guess from page text or third-party sources.
- No `hasMerchantReturnPolicy`: same issue for return questions.
- No `Review` objects: 1,751 reviews exist but none are surfaced to engines. Paula's
  Choice (your closest competitor with good schema) surfaces actual review text and
  outranks you on quotability for this reason.

**After (proposed replacement):**
```json
{
  "@context": "https://schema.org",
  "@type": "Product",
  "name": "Good Molecules Niacinamide Serum 30ml",
  "url": "https://www.goodmolecules.com/s/good-molecules-niacinamide-serum-30ml",
  "sku": "[YOU SUPPLY — internal SKU for this size variant]",
  "gtin13": "[YOU SUPPLY — UPC/EAN for this size variant]",
  "category": "Skincare > Serums",
  "brand": {
    "@type": "Brand",
    "name": "Good Molecules"
  },
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
      "shippingRate": {
        "@type": "MonetaryAmount",
        "value": "5.00",
        "currency": "USD"
      },
      "shippingDestination": {
        "@type": "DefinedRegion",
        "addressCountry": "US"
      },
      "deliveryTime": {
        "@type": "ShippingDeliveryTime",
        "transitTime": {
          "@type": "QuantitativeValue",
          "minValue": 3,
          "maxValue": 5,
          "unitCode": "DAY"
        }
      }
    },
    "hasMerchantReturnPolicy": {
      "@type": "MerchantReturnPolicy",
      "applicableCountry": "US",
      "returnPolicyCategory": "https://schema.org/MerchantReturnFiniteReturnWindow",
      "merchantReturnDays": "[YOU SUPPLY — return window in days]",
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

Notes for your developer:
- `shippingDetails` uses the $5 flat rate (for orders under $35). Your shipping
  policy has two tiers. The cleanest implementation is two `shippingDetails` blocks
  in an array: one for under-$35 orders at $5, and one for $35+ orders at $0. We
  can provide the two-block version once you confirm your platform supports it.
- `priceValidUntil` should be updated when prices change. Setting it to end of year
  is standard.
- `gtin13` alone is the highest-return single field. Everything else can follow.
- Surfacing 3 to 5 `Review` objects per product is sufficient for engine quoting.
  You do not need to expose all reviews.

---

## BreadcrumbList (add to all product pages)

Add this as a second `<script type="application/ld+json">` block alongside the
Product or ProductGroup block. The category name and URL change per product.

**Before:** no BreadcrumbList on any product page (confirmed June 18).

**After:**
```json
{
  "@context": "https://schema.org",
  "@type": "BreadcrumbList",
  "itemListElement": [
    {
      "@type": "ListItem",
      "position": 1,
      "name": "Home",
      "item": "https://www.goodmolecules.com/"
    },
    {
      "@type": "ListItem",
      "position": 2,
      "name": "Treatments & Serums",
      "item": "https://www.goodmolecules.com/shop/browse?tag=facial-treatments"
    },
    {
      "@type": "ListItem",
      "position": 3,
      "name": "Niacinamide Serum"
    }
  ]
}
```

---

## What we need from you

1. GTIN/UPC and internal SKU per product per size variant. Without this we cannot
   complete the highest-impact field in this template.
2. Return policy window in days and whether return shipping is free.
3. A sample of 3 to 5 reviews per product from your review feed.
4. Confirmation of all size variants and current prices per product, so we can
   populate the `ProductGroup.hasVariant` array accurately.
