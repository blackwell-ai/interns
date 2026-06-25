# Homepage schema

> **At a glance**
> | | |
> |---|---|
> | **Priority** | P3 |
> | **Template** | homepage |
> | **Add to** | the existing `OnlineStore` block, plus one new `WebSite` block |
> | **You fill in** | social + retailer profile URLs, search URL format |
> | **Authority** | [sources.md](sources.md), Homepage schema section |

Prepared by Blackwell Enterprises, June 25, 2026.

Your homepage carries an `OnlineStore` block with `name`, `url`, and `logo`.
`OnlineStore` is a subtype of `Organization`, so it counts as your brand entity
block. What it lacks are the fields that consolidate brand authority and enable site
search.

This is the page an engine lands on when a user asks "what is Good Molecules" or
"tell me about Good Molecules skincare." The `sameAs` array is the field that grounds
the brand as a single entity across your retailer and social listings. Without it, an
engine leans on Reddit threads, Ulta product pages, and press mentions to describe
you.

---

## What your homepage serves today

```json
{
  "@context": "https://schema.org",
  "@type": "OnlineStore",
  "name": "Good Molecules",
  "url": "https://www.goodmolecules.com",
  "logo": "https://dy6g3i6a1660s.cloudfront.net/0VDrsDcpa9lworZ9fqkd8wH2AGQ/orig.jpg"
}
```

Present: `name`, `url`, `logo`. Missing: `sameAs`, `contactPoint`, `description`, and
a separate `WebSite` block with a `SearchAction`.

---

## Recommended: enrich the existing block and add a WebSite block

Keep your `OnlineStore` block and add the missing fields to it, then add the
`WebSite` block as a second tag. Both are `<script type="application/ld+json">` tags.
They do not affect page rendering, page speed, or existing SEO signals. You can keep
`@type` as `OnlineStore` rather than `Organization`, it is the more specific type and
engines accept the same fields on it.

### Block 1: enriched OnlineStore

```json
{
  "@context": "https://schema.org",
  "@type": "OnlineStore",
  "name": "Good Molecules",
  "url": "https://www.goodmolecules.com",
  "logo": "https://dy6g3i6a1660s.cloudfront.net/0VDrsDcpa9lworZ9fqkd8wH2AGQ/orig.jpg",
  "description": "Science-backed, affordable skincare with clinically-studied active ingredients. Fragrance-free, Leaping Bunny certified cruelty-free, and vegan. Formulated without PEGs, mineral oils, or ethoxylated ingredients.",
  "contactPoint": {
    "@type": "ContactPoint",
    "telephone": "1-213-444-4663",
    "email": "support@goodmolecules.com",
    "contactType": "customer service",
    "hoursAvailable": {
      "@type": "OpeningHoursSpecification",
      "dayOfWeek": ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday"],
      "opens": "07:00",
      "closes": "16:00"
    }
  },
  "sameAs": [
    "[YOU SUPPLY: Instagram URL]",
    "[YOU SUPPLY: TikTok URL]",
    "[YOU SUPPLY: YouTube URL if applicable]",
    "[YOU SUPPLY: Beautylish storefront URL]",
    "[YOU SUPPLY: Ulta URL if applicable]",
    "[YOU SUPPLY: Target URL if applicable]"
  ]
}
```

The `contactPoint` values (phone, email, hours) come directly from your live
`llms.txt`. The `sameAs` array is the most important field here: it tells engines
that your Instagram account, your Beautylish storefront, and your Ulta listing all
refer to the same brand. This consolidates your authority signal across platforms and
is how an engine learns to say "Good Molecules" confidently instead of hedging with
retailer references.

### Block 2: WebSite with SearchAction

```json
{
  "@context": "https://schema.org",
  "@type": "WebSite",
  "name": "Good Molecules",
  "url": "https://www.goodmolecules.com",
  "potentialAction": {
    "@type": "SearchAction",
    "target": {
      "@type": "EntryPoint",
      "urlTemplate": "https://www.goodmolecules.com/shop/browse?q={search_term_string}"
    },
    "query-input": "required name=search_term_string"
  }
}
```

This enables a sitelinks search box in Google results when someone searches for
Good Molecules directly, and signals to crawlers that the site has a functioning
search endpoint. The URL template uses `/shop/browse?q=`, confirm with your
platform that this is the correct search parameter.

---

## Comparison: what Paula's Choice does

Paula's Choice (the closest competitor with strong schema) has none of this on their
homepage either. You have the opportunity to implement the full entity layer before
any comparable brand does. This is the Reputation and Recommendability dimension
from the audit. It is what makes an engine treat Good Molecules as a definitive
source rather than one of many skincare brands.

---

## Data your team fills in

1. Social profile URLs: Instagram, TikTok, and any others you maintain.
2. Retail partner storefront URLs: Beautylish, Ulta, Target, whichever apply.
3. Your site search URL format (we have it as `/shop/browse?q=`; confirm in the
   template).

The logo is already live in your `OnlineStore` block
(`.../0VDrsDcpa9lworZ9fqkd8wH2AGQ/orig.jpg`), so no logo path is needed.
