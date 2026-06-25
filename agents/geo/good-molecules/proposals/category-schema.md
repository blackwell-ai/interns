# Category page schema

> **At a glance**
> | | |
> |---|---|
> | **Priority** | P3 |
> | **Template** | category browse page (`/shop/browse?tag=...`) |
> | **Add to** | two new sibling blocks: `ItemList` and `BreadcrumbList` |
> | **You fill in** | nothing; server-side templating from your catalog |
> | **Authority** | [sources.md](sources.md), Category page schema section |

Prepared by Blackwell Enterprises, June 25, 2026.

We fetched your category pages (`/shop/browse?tag=cleansers`, `toners`,
`facial-treatments`, `eye-treatments`) with a GPTBot user-agent. They load correctly
and serve only the site-wide `OnlineStore` block. None carries an `ItemList`, so the
catalog is not machine-traversable from the listing pages. The category URL format is
`/shop/browse?tag=`.

Without an `ItemList` on category pages, an engine browsing your catalog has no
machine-readable signal about what products exist in each category. It sees a page
full of product names rendered in JavaScript, which many crawlers do not execute.

---

## What your category pages serve today

```json
{
  "@context": "https://schema.org",
  "@type": "OnlineStore",
  "name": "Good Molecules",
  "url": "https://www.goodmolecules.com",
  "logo": "https://dy6g3i6a1660s.cloudfront.net/0VDrsDcpa9lworZ9fqkd8wH2AGQ/orig.jpg"
}
```

This is the same site-wide block that appears on every page. There is no
category-specific `ItemList`.

---

## Recommended: ItemList block for each category page

Add this as a `<script type="application/ld+json">` tag in the `<head>`. The
`itemListElement` array should be generated server-side from your platform's catalog
for that tag, not hardcoded. The niacinamide toner and glycolic toner are the
worked example for the Toners category, and your developer uses the same loop pattern
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
first, or alphabetical, whichever your platform uses).

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

Your category pages carry no `BreadcrumbList` today. Add this as a second block on
the same page:

**Recommended block:**
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

## Data your team fills in

Nothing from your systems is strictly required; the `itemListElement` array is
generated server-side from your catalog for each tag. The one judgment call is the
sort order (bestsellers, alphabetical, or your default), which your team sets in the
template.
