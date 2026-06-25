# Sources and authority behind each recommendation

Prepared by Blackwell Enterprises, June 25, 2026.

Every recommendation in the proposal documents links to a specific, citable source.
This document maps each proposal to its authority so the Good Molecules engineering
team can verify the recommendation independently.

---

## Product structured data (pdp-schema.md)

### Authority: Google Search Central, Merchant listing structured data
URL: https://developers.google.com/search/docs/appearance/structured-data/merchant-listing

Google's documentation for Merchant Listing structured data, the schema type that
makes a product eligible for Shopping knowledge panels, Google Images product results,
and product snippets in Search and AI Mode. Key claims from this page:

- `gtin`, `mpn`, and `sku` are recommended fields for merchant listings. Google
  states that GTIN specifically enables them to "match your product to other sources
  of information about that product", meaning without GTIN, Google cannot reconcile
  your product page with the same item listed on Amazon, Ulta, or Target.
- `shippingDetails` (via `OfferShippingDetails`) and `hasMerchantReturnPolicy` are
  recommended fields that unlock shipping and return annotations in merchant listing
  experiences.
- `Review` objects (distinct from `AggregateRating`) are recommended to surface
  review text in product snippets.
- `priceValidUntil` on the `Offer` is recommended to confirm the price is current.

### Authority: Google Search Central, Merchant return policy structured data
URL: https://developers.google.com/search/docs/appearance/structured-data/merchant-return-policy

Dedicated documentation for `MerchantReturnPolicy` structured data. Google provides
this as a separate schema type specifically to help engines answer return policy
questions from structured data rather than from page text.

### Authority: Google Search Central, Merchant shipping policy structured data
URL: https://developers.google.com/search/docs/appearance/structured-data/merchant-shipping-policy

Dedicated documentation for `OfferShippingDetails`. Same rationale as above, Google
recommends putting shipping costs and timing in structured data so engines can answer
shipping questions with confidence.

### Authority: Google Search Central, Product snippet structured data
URL: https://developers.google.com/search/docs/appearance/structured-data/product-snippet

Google's specification for basic product snippets. Covers required vs recommended
fields for `Product` and `Offer` types. `Review` objects (not just `aggregateRating`)
are explicitly described here as enabling star ratings and review text in snippets.

### Authority: schema.org, Product type specification
URL: https://schema.org/Product

The underlying schema specification that Google, Bing, and all major search engines
implement. Defines `gtin13`, `sku`, `mpn`, `ProductGroup`, `hasVariant`, and all
other fields referenced in our proposal. This is the original authority; Google's
documentation is an implementation guide on top of it.

### Additional note: plain text in description fields
Google's structured data guidelines explicitly state that the `description` field
should be plain text, not HTML. Good Molecules' current schema contains raw HTML
tags (`<h5>`, `<p>`, `<ul>`) in the `description` field, which violates this
requirement and may cause parsers to reject or truncate the field.
Source: https://developers.google.com/search/docs/appearance/structured-data/sd-policies

---

## Homepage schema (homepage-schema.md)

### Authority: Google Search Central, Organization structured data
URL: https://developers.google.com/search/docs/appearance/structured-data/organization

Google recommends `Organization` schema with `sameAs` links to consolidate a
brand's entity signals. The `sameAs` field explicitly enables Google to recognize
that a brand's Instagram account, Wikipedia page, and retailer storefront all
refer to the same entity, which is what drives confident brand answers in AI
Mode and Knowledge Panels.

### Authority: Google Search Central, Sitelinks Searchbox
URL: https://developers.google.com/search/docs/appearance/structured-data/sitelinks-searchbox

Google documents the `WebSite` schema with `SearchAction` as the method for
enabling a sitelinks search box in Google results. This is the schema behind
"search [brand]" appearing directly in search results.

---

## Category page schema (category-schema.md)

### Authority: schema.org, ItemList type
URL: https://schema.org/ItemList

The `ItemList` type is the standard for expressing ordered or unordered lists of
items in structured data. Google uses it for carousel results and catalog
traversal. Documented by Google at:
https://developers.google.com/search/docs/appearance/structured-data/carousel

### Authority: Google Search Central, Breadcrumb structured data
URL: https://developers.google.com/search/docs/appearance/structured-data/breadcrumb

Google recommends `BreadcrumbList` on product and category pages to help engines
understand site structure and category context. It directly affects how product
pages appear in search results (with the breadcrumb trail shown below the URL).

---

## AI guide files, llms.txt, llms-full.txt, agents.md

### Authority: llmstxt.org, The /llms.txt specification
URL: https://llmstxt.org
Author: Jeremy Howard. Published September 3, 2024.

The original proposal for the `/llms.txt` standard. Direct quote from the
specification:

> "Large language models increasingly rely on website information, but face a
> critical limitation: context windows are too small to handle most websites in
> their entirety. Converting complex HTML pages with navigation, ads, and JavaScript
> into LLM-friendly plain text is both difficult and imprecise. While websites serve
> both human readers and LLMs, the latter benefit from more concise, expert-level
> information gathered in a single, accessible location."

The proposal explicitly addresses why HTML pages are poor inputs for LLMs and why
a dedicated plain-text file at a predictable URL is the recommended solution.
`llms-full.txt` is the extended variant described in the same specification.
FastHTML's own implementation uses `llms-ctx.txt` and `llms-ctx-full.txt` as the
expanded versions, following the same pattern we are proposing for Good Molecules.

### Note on adoption
As of June 2026, `llms.txt` has been adopted by Anthropic (anthropic.com/llms.txt),
Perplexity, Cloudflare, and hundreds of software and e-commerce sites. It is
supported as a crawl target by Claude, Perplexity, and other AI assistants that
accept URL context. Good Molecules already has a strong `llms.txt`, we are
proposing the deeper companion files the specification describes.

---

## WAF and crawler access

### Authority: OpenAI, GPTBot documentation
URL: https://platform.openai.com/docs/bots

OpenAI's official documentation for GPTBot and OAI-SearchBot, including the
user-agent strings and the statement that sites can allow or block them via
robots.txt or WAF rules.

### Authority: Anthropic, ClaudeBot documentation
URL: https://support.anthropic.com/en/articles/8896518-does-anthropic-crawl-data-from-the-web

Anthropic's documentation on ClaudeBot (training) and Claude-User (live fetch),
including user-agent strings.

### Authority: Perplexity, PerplexityBot documentation
URL: https://docs.perplexity.ai/docs/perplexitybot

Perplexity's documentation on PerplexityBot user-agent and crawl behavior.

---

## Summary: which recommendations are Google-specified vs. best practice

| Recommendation | Google-specified | Schema.org standard | Industry best practice |
|---|---|---|---|
| `gtin13` on Product | Recommended (Merchant Listing) | Yes | Yes |
| `sku` on Product | Recommended (Merchant Listing) | Yes | Yes |
| `shippingDetails` on Offer | Recommended (Merchant Listing) | Yes | Yes |
| `hasMerchantReturnPolicy` | Recommended (Merchant Listing) | Yes | Yes |
| `priceValidUntil` on Offer | Recommended | Yes | Yes |
| `Review` objects | Recommended (Product Snippet) | Yes | Yes |
| Plain text in `description` | Required | Yes | Yes |
| `ProductGroup` + `hasVariant` | Recommended (Variants) | Yes | Yes |
| `Organization` + `sameAs` | Recommended | Yes | Yes |
| `BreadcrumbList` | Recommended | Yes | Yes |
| `ItemList` on category pages | Recommended (Carousel) | Yes | Yes |
| `llms.txt` / `llms-full.txt` | Not a Google spec | No | Emerging standard |
| `agents.md` | Not a Google spec | No | Emerging standard |
