# Homepage schema

Prepared by Blackwell Enterprises for the Good Molecules engineering team.
June 18, 2026.

We fetched goodmolecules.com on June 18 using a GPTBot user-agent. The homepage
loaded correctly (title: "See a difference in your skin | Good Molecules") but
contains no JSON-LD at all.

This is the page an engine lands on when a user asks "what is Good Molecules" or
"tell me about Good Molecules skincare." Without entity schema here, an engine has
no structured signal to ground the brand as a single entity distinct from retailer
listings. It falls back to Reddit threads, Ulta product pages, and press mentions
instead.

---

## Before (what a bot sees today — confirmed June 18)

```
(no JSON-LD block in page source)
```

---

## After: two blocks to add to the homepage head

Add both as `<script type="application/ld+json">` tags. They do not affect page
rendering, page speed, or existing SEO signals.

### Block 1: Organization

```json
{
  "@context": "https://schema.org",
  "@type": "Organization",
  "name": "Good Molecules",
  "url": "https://www.goodmolecules.com",
  "logo": "[YOU SUPPLY — your CDN path to the logo image]",
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
    "[YOU SUPPLY — Instagram URL]",
    "[YOU SUPPLY — TikTok URL]",
    "[YOU SUPPLY — YouTube URL if applicable]",
    "[YOU SUPPLY — Beautylish storefront URL]",
    "[YOU SUPPLY — Ulta URL if applicable]",
    "[YOU SUPPLY — Target URL if applicable]"
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
search endpoint. The URL template uses `/shop/browse?q=` — confirm with your
platform that this is the correct search parameter.

---

## Comparison: what Paula's Choice does

Paula's Choice (the closest competitor with strong schema) has none of this on their
homepage either. You have the opportunity to implement the full entity layer before
any comparable brand does. This is the Reputation and Recommendability dimension
from the audit — it is what makes an engine treat Good Molecules as a definitive
source rather than one of many skincare brands.

---

## What we need from you

1. Logo image URL (your CDN path).
2. Social profile URLs: Instagram, TikTok, and any others you maintain.
3. Retail partner storefront URLs: Beautylish, Ulta, Target — whichever apply.
4. Confirmation that `/shop/browse?q=` is your site search URL format.
