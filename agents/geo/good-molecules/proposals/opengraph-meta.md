# OpenGraph and product meta tags

> **At a glance**
> | | |
> |---|---|
> | **Priority** | P3 |
> | **Template** | product page `<head>`, homepage `<head>`, and site root |
> | **Add to** | new `<meta>` tags, plus a generated `sitemap.xml` |
> | **You fill in** | homepage share image, platform confirmation |
> | **Authority** | the Authority section at the end of this file |

Prepared by Blackwell Enterprises, June 25, 2026.

We read the raw server HTML of your homepage and several product pages with a GPTBot
user-agent. Your pages carry `og:site_name` and little else. There is no `og:title`,
`og:type`, `og:image`, `og:description`, no `product:price` meta, and no Twitter
card. There is also no `sitemap.xml` served.

These tags are a second structured signal that sits alongside your JSON-LD. They are
what social platforms and many AI crawlers read first to build a link preview and a
quick understanding of the page. They are cheap to add, they do not change rendering,
and they reinforce the same facts your JSON-LD states.

---

## What your product pages serve today

```html
<meta property="og:site_name" content="Good Molecules">
```

That is the full set. A link to a product page unfurls with no title, image, or
price, and an engine gets no OpenGraph-level product signal.

---

## Recommended: product page meta

Add these to the `<head>` of every `/s/` page. The values come from the same data
already in your JSON-LD `Product` block, so this is a template change, not new data
entry.

```html
<meta property="og:type" content="product">
<meta property="og:title" content="Good Molecules Niacinamide Serum 30ml">
<meta property="og:description" content="10% niacinamide serum that minimizes pores and refines skin tone and texture. Fragrance-free.">
<meta property="og:url" content="https://www.goodmolecules.com/s/good-molecules-niacinamide-serum-30ml">
<meta property="og:image" content="https://dy6g3i6a1660s.cloudfront.net/.../prod_p.jpg">
<meta property="og:site_name" content="Good Molecules">

<!-- product-specific OpenGraph, read by shopping surfaces -->
<meta property="product:price:amount" content="6.00">
<meta property="product:price:currency" content="USD">
<meta property="product:availability" content="in stock">
<meta property="product:retailer_item_id" content="[YOU SUPPLY: your SKU]">
<meta property="product:brand" content="Good Molecules">

<!-- Twitter card -->
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="Good Molecules Niacinamide Serum 30ml">
<meta name="twitter:description" content="10% niacinamide serum that minimizes pores and refines skin tone and texture. Fragrance-free.">
<meta name="twitter:image" content="https://dy6g3i6a1660s.cloudfront.net/.../prod_p.jpg">
```

Map each field from your product data the same way your JSON-LD does. The
`product:price:amount` and `og:image` are the two that most change how a shared link
looks and how a shopping surface reads the page.

---

## Recommended: homepage meta

Add these to the homepage `<head>`:

```html
<meta property="og:type" content="website">
<meta property="og:title" content="Good Molecules: science-backed, affordable skincare">
<meta property="og:description" content="Clinically-studied active ingredients at honest prices. Fragrance-free, vegan, Leaping Bunny certified cruelty-free.">
<meta property="og:url" content="https://www.goodmolecules.com">
<meta property="og:image" content="[YOU SUPPLY: a homepage share image, ideally 1200x630]">
<meta property="og:site_name" content="Good Molecules">
<meta name="twitter:card" content="summary_large_image">
```

---

## Recommended: serve a sitemap.xml

`https://www.goodmolecules.com/sitemap.xml` returns 404, so there is no machine
index of your product URLs. Most platforms generate one with a setting toggled on.
It should enumerate your `/s/` product URLs and your category URLs, with `lastmod`
dates so crawlers know what changed.

```xml
<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://www.goodmolecules.com/s/good-molecules-niacinamide-serum-30ml</loc>
    <lastmod>2026-06-25</lastmod>
  </url>
  <!-- one entry per product and category URL, generated from your catalog -->
</urlset>
```

Reference it from `robots.txt` with a `Sitemap:` line so crawlers discover it.

---

## Authority

- The Open Graph protocol, ogp.me. Defines `og:title`, `og:type`, `og:image`, and the
  `product:` namespace used above.
- X (Twitter) Cards documentation, developer.x.com, for the `twitter:card` tags.
- sitemaps.org, the sitemap XML format specification.
- Google Search Central sitemap guidelines,
  https://developers.google.com/search/docs/crawling-indexing/sitemaps/build-sitemap.

---

## Data your team fills in

1. A homepage share image (1200x630 works for every surface), or reuse an existing
   brand image.
2. Your platform's `sitemap.xml` setting. Most generate one from a toggle; if yours
   does not, tell us which platform you run and we will give exact steps.
