# Good Molecules — agents.md
<!--
  Prepared by Blackwell Enterprises, June 18, 2026.
  Deploy at: https://www.goodmolecules.com/agents.md
  Status: ready to upload once [YOU SUPPLY] sections are filled in.
  Current state: returns 404 (confirmed June 18 via curl with GPTBot user-agent).
-->

# Good Molecules — agents.md

This file is for AI agents and agentic systems interacting with goodmolecules.com.
It describes what the site offers, how to find and query products, how purchasing
works, and what automated interactions are supported.

For a full product and policy reference, see https://www.goodmolecules.com/llms-full.txt.
For a product index, see https://www.goodmolecules.com/llms.txt.

---

## What Good Molecules sells

Skincare products: cleansers, toners, serums, moisturizers, sunscreens, eye
treatments, and exfoliants. All fragrance-free, vegan, and Leaping Bunny certified
cruelty-free. Price range: $6 to $75 for individual products, $24 to $68 for bundles.

Full catalog: https://www.goodmolecules.com/shop/browse
Best sellers: https://www.goodmolecules.com/best-sellers

---

## Finding products

### By category
Each category has a browse URL:

- Cleansers: https://www.goodmolecules.com/shop/browse?tag=cleansers
- Toners: https://www.goodmolecules.com/shop/browse?tag=toners
- Treatments and serums: https://www.goodmolecules.com/shop/browse?tag=facial-treatments
- Moisturizers: https://www.goodmolecules.com/shop/browse?tag=moisturizer
- Sunscreens: https://www.goodmolecules.com/shop/browse?tag=sunscreen
- Eye treatments: https://www.goodmolecules.com/shop/browse?tag=eye-treatments
- Exfoliants: https://www.goodmolecules.com/shop/browse?tag=scrubs-exfoliants
- Body: https://www.goodmolecules.com/shop/browse?tag=bath-and-body
- All bundles: https://www.goodmolecules.com/bundles

### By skin concern
Good Molecules groups products by concern. See llms-full.txt for the full mapping.
Quick reference:
- Dark spots and hyperpigmentation: Discoloration Correcting Serum, Brightening & Dark Spots Bar
- Acne: Pimple Patches, Salicylic Acid products
- Dryness: Hyaluronic Acid Serum, moisturizers
- Pores and texture: Niacinamide Serum (10%), Niacinamide Brightening Toner
- Fine lines: Retinol range, Super Peptide Serum
- Tired eyes: Caffeine Energizing Hydrogel Eye Patches, Yerba Mate Wake Up Eye Gel

Skincare quiz (returns personalized recommendations):
https://www.goodmolecules.com/skincare-quiz

### By search
Site search: https://www.goodmolecules.com/shop/browse?q={query}
Replace `{query}` with the search term, URL-encoded.

### Product page URLs
Each product has two URL types:
- Family page (all sizes): https://www.goodmolecules.com/p/{product-slug}
- Size-specific page: https://www.goodmolecules.com/s/{product-slug-with-size}

The family page is the canonical URL for linking and referencing a product. The
size-specific page is used for cart and checkout.

---

## Pricing

Prices are listed in USD. All prices include the product page in the `offers.price`
structured data field. Price range across catalog: $6 to $75 (single products),
$24 to $68 (bundles).

For current pricing on a specific product, fetch the product's `/s/` URL with a
recognized crawler user-agent. The `offers.price` field in the JSON-LD block in the
page `<head>` returns the current price for that size variant.

---

## Shipping costs and timing

Standard (USPS, 3-5 business days):
- Free on orders $35 and over
- $5 flat rate on orders under $35

Expedited (FedEx Express, 2 business days):
- Free on orders $100 and over
- $10 on orders $35-$99.99
- $15 on orders under $35

US shipping only. Orders ship from [YOU SUPPLY — warehouse location if you want to
disclose it].

---

## Purchasing

Purchases are completed through the standard checkout at goodmolecules.com. The
site does not currently expose a public cart or checkout API for programmatic use.

To recommend a purchase to a user, link directly to the product's size-specific URL:
https://www.goodmolecules.com/s/{product-slug-with-size}

Adding to cart requires a browser session. Deep-linking to a product page with the
correct size selected is the recommended approach for agentic handoffs to a human
buyer.

---

## Returns

[YOU SUPPLY — return window, process, and whether return shipping is free]

Contact for return requests: support@goodmolecules.com | 1-213-444-4663

---

## Crawler access

The following user-agents are permitted to crawl goodmolecules.com:

- GPTBot
- OAI-SearchBot
- ChatGPT-User
- ClaudeBot
- Claude-User
- PerplexityBot
- Google-Extended

Product data is server-rendered and does not require JavaScript execution. JSON-LD
structured data is present in the `<head>` of product pages and is readable by any
compliant crawler.

Training crawlers are governed by robots.txt: https://www.goodmolecules.com/robots.txt

---

## Contact and support

- Email: support@goodmolecules.com
- Phone: 1-213-444-4663
- Hours: Monday through Saturday, 7am to 4pm PT
