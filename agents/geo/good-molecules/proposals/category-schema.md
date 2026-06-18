# Category page schema

Prepared by Blackwell Enterprises for the Good Molecules engineering team.
June 18, 2026.

We fetched `goodmolecules.com/shop/browse?tag=cleansers` on June 18 using a GPTBot
user-agent. The page loaded correctly (title: "Good Molecules - Cleansers") but
contains no JSON-LD.

Without structured data on category pages, an engine browsing your catalog has no
machine-readable signal about what products exist in each category. It sees a page
full of product names rendered in JavaScript, which many crawlers do not execute.

---

## Before (what a bot sees today — confirmed June 18 across all category pages)

```
(no JSON-LD block in page source)
```

---

## After: ItemList block for each category page

Add this as a `<script type="application/ld+json">` tag in the `<head>`. The
`itemListElement` array should be generated server-side from your platform's catalog
for that tag, not hardcoded. The niacinamide toner and glycolic toner are the
worked example for the Toners category — your developer uses the same loop pattern
for every category.

```json
{
  "@context": "https://schema.org",
  "@type": "ItemList",
  "name": "Toners",
  "url": "https://www.goodmolecules.com/shop/browse?tag=toners",
  "description": "Lightweight toners that prep skin, minimize pores, and deliver active ingredients after cleansing.",
  "itemListElement": [
    {
      "@type": "ListItem",
      "position": 1,
      "url": "https://www.goodmolecules.com/p/good-molecules-niacinamide-brightening-toner",
      "name": "Niacinamide Brightening Toner"
    },
    {
      "@type": "ListItem",
      "position": 2,
      "url": "https://www.goodmolecules.com/p/good-molecules-glycolic-exfoliating-toner",
      "name": "Glycolic Exfoliating Toner"
    }
  ]
}
```

Position numbers are sequential. Order can match your default sort (bestsellers
first, or alphabetical — whichever your platform uses).

---

## Category descriptions

Use these in the `description` field above. One per category:

- Cleansers: Gentle, effective cleansers for all skin types. Soap-free formulas that remove makeup, sunscreen, and impurities without stripping the skin barrier.
- Toners: Lightweight toners that prep skin, minimize pores, and deliver active ingredients after cleansing.
- Treatments and serums: Targeted serums with clinically-studied actives for brightening, pore minimizing, hydration, and anti-aging.
- Moisturizers: Lightweight to rich moisturizers for all skin types. Strengthens the skin barrier and maintains hydration.
- Sunscreens: Mineral and chemical SPF options that protect without white cast or heavy texture.
- Eye treatments: Gels and patches that target puffiness, dark circles, and fine lines around the eye area.
- Exfoliants: Chemical exfoliants with AHAs and BHAs that resurface, clear pores, and smooth texture.
- Body: Treatments and cleansers formulated for body skin, including discoloration and hydration solutions.

---

## BreadcrumbList alongside the ItemList

Add this as a second block on the same page:

**Before:** no BreadcrumbList on any category page (confirmed June 18).

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
      "name": "Toners"
    }
  ]
}
```

---

## Implementation note

This is a server-side template change, not a per-page manual entry. Your developer
adds the JSON-LD block to the category page template, and the product list populates
from your CMS data for that tag. The schema renders in the raw HTML so crawlers
that do not execute JavaScript can read it.

---

## What we need from you

The full product list per category, in your preferred sort order, so we can verify
the `itemListElement` entries are complete before you deploy. We can derive product
names and URLs from your live site, but you know your catalog better than we do.
