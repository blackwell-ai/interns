# Good Molecules: post week-one review

Internal prep for the weekly working session. June 25, 2026.

## Where the engagement stands

The model is recommendations, not implementation. Good Molecules did not give us
codebase access, and that is fine by agreement: they own the deploy, we own the
artifacts. Our kickoff set this out plainly. So the right question for this meeting
is whether we delivered the recommendation pack we committed to for week one, and the
answer is yes, all of it, plus the source citations.

A note for ourselves before the call: the site's technical state is essentially
unchanged since kickoff, which is expected since the schema deploys are theirs to
run. The one real change is Perplexity-User now passing the WAF. Do not credit them
with shipping homepage schema or URL redirects in the meeting; those were already
live at kickoff. Lead with what is genuinely new (Perplexity-User) and with our
delivered pack.

## Week-one commitments vs. delivered

| Week-one deliverable | Status | File |
|---|---|---|
| Enriched Product/Offer JSON-LD + niacinamide worked example + ProductGroup | Delivered | proposals/pdp-schema.md |
| Homepage Organization/WebSite schema (sameAs, contactPoint, SearchAction) | Delivered | proposals/homepage-schema.md |
| OfferShippingDetails + MerchantReturnPolicy blocks | Delivered | proposals/pdp-schema.md |
| BreadcrumbList (product) + ItemList (category) | Delivered | proposals/category-schema.md, pdp-schema.md |
| OpenGraph + product meta tag spec, plus sitemap | Delivered | proposals/opengraph-meta.md |
| llms-full.txt and agents.md drafts | Delivered | proposals/llms-full.txt, agents.md |
| First FAQ set with FAQPage markup | Delivered | proposals/faq-schema.md |
| Source and authority citations (extra) | Delivered | proposals/sources.md |

Every recommendation maps to a Google Search Central or schema.org authority in
sources.md, so they can verify each one independently.

## Live site state today (verified June 25)

What is live and working:

- Crawler access is fully open. GPTBot, ClaudeBot, PerplexityBot, and now
  Perplexity-User all return 200. This was the heaviest audit finding and it is done.
- Product `Product`/`Offer` JSON-LD on `/s/` size pages, server-rendered.
- Homepage `OnlineStore` block with name, url, logo.
- A strong `llms.txt`.

What is waiting on their deploy and their data:

- Product identifiers `sku` and `gtin13`, the highest-value gap.
- `priceValidUntil`, `shippingDetails`, `hasMerchantReturnPolicy`, `Review` on the
  Offer.
- Homepage `sameAs`, `contactPoint`, and a `WebSite` SearchAction block.
- Category `ItemList`, product and category `BreadcrumbList`.
- OpenGraph and product meta, and a `sitemap.xml`.
- `llms-full.txt`, `agents.md`, and the FAQ page.

## The one ask that matters most

GTIN/UPC and internal SKU per product per size variant. This is the field that lets
an engine match your page to the Amazon, Ulta, and Target listings, which is the root
cause of the price-substitution finding from the audit. Everything else is additive.
This one fixes the specific problem they hired us for. Push for it.

## Everything we need from them, in one list

1. GTIN/UPC and SKU per product per size variant.
2. Return policy: window in days, free return shipping or not, returns page URL.
3. Social and retailer URLs for `sameAs` (Instagram, TikTok, Beautylish, Ulta,
   Target).
4. A review feed sample, 3 to 5 reviews per product, or API access.
5. A homepage share image (1200x630).
6. Confirmation that `/shop/browse?q=` is the search URL format, and which platform
   they run so we can give exact sitemap steps.

## Next step

Schedule the live engine battery as the real before/after proof. We have the
technical before captured. Once they deploy, we re-run ChatGPT, Claude, Perplexity,
Gemini, and Google against the frozen truth table and produce the comparison report.
That is the deliverable that shows the engagement worked.

## Suggested agenda

1. Win: WAF fully open, including the Perplexity-User follow-up from last week.
2. Walk the delivered pack, schema by schema, framed as ready to paste in.
3. The GTIN/SKU ask, with the price-substitution problem as the reason.
4. The shorter list of other inputs we need.
5. Book the live engine battery for after their deploy.
