# Good Molecules: AI visibility remediation — delivery status

Prepared by Blackwell Enterprises for the Good Molecules engineering team.
June 18, 2026.

This folder contains our proposals and ready-to-deploy files for each item in the
engagement letter. Every finding below was verified by fetching goodmolecules.com
live on June 18 using AI crawler user-agents (GPTBot, ClaudeBot). We are not
guessing — the before states are what your site returns right now.

---

## Engagement deliverables

### 1. AI crawler access
Status: complete.

Your WAF now returns 200 for GPTBot, ClaudeBot, and PerplexityBot. We confirmed
this on June 18. At the original audit all three were blocked. This was the
highest-impact fix and it is done.

One edge case still open: Perplexity-User (the live-fetch variant, distinct from
PerplexityBot) was returning 405 as of the June 17 recon. Worth confirming whether
this has been addressed, as Perplexity uses both user-agents.

### 2. Machine-readable product pages
Status: partial.

You added server-side JSON-LD to your `/s/` size-specific pages after the audit.
That is confirmed live and is a meaningful improvement. Two gaps remain:

- The `/p/` family pages (the URLs your llms.txt links to) still have no JSON-LD.
  We confirmed this on June 18 across multiple products including the Vitamin C
  Serum and Discoloration Correcting Serum.
- The schema on `/s/` pages is missing the fields engines need to confidently answer
  price, shipping, and return questions: `sku`, `gtin13`, `shippingDetails`,
  `hasMerchantReturnPolicy`, `priceValidUntil`, and `Review` objects.

Proposals and before/after code: see `pdp-schema.md`.

### 3. Schema correction
Status: not started.

The homepage has no JSON-LD at all. Category pages have no JSON-LD at all. Neither
was in scope of the structured data you added post-audit. These are the pages that
establish the brand as a recognizable entity and make the catalog traversable.

Proposals and before/after: see `homepage-schema.md` and `category-schema.md`.

### 4. AI guide files
Status: one of three complete.

- `llms.txt`: live and good. Well-structured with products, prices, shipping, and
  skin concern mappings. No changes needed.
- `llms-full.txt`: returns 404. Draft ready to upload — see `llms-full.txt` in
  this folder. Needs your team to fill in the returns policy and upload.
- `agents.md`: returns 404. Draft ready to upload — see `agents.md` in this folder.
  Needs your team to fill in the returns policy and upload.

### 5. Before-and-after measurement
Status: before complete, after pending your deployment.

We ran a full before-benchmark on June 17 (WAF, crawler access, schema validation,
AI engine citation testing). We re-verified the technical layer on June 18. The
after-benchmark runs once you have deployed the changes above. We will re-run the
full engine battery (ChatGPT, Claude, Perplexity, Gemini, Google) and produce the
comparison report.

---

## What we need from you to complete the open items

These are the only blockers on our end. Everything else in the proposals below is
ready to deploy once your team pastes in the code.

1. GTIN/UPC and internal SKU per product per size variant. This is the single
   highest-impact open field. Without it, engines cannot match your product pages
   to your Amazon, Ulta, or Target listings — the root cause of the price-
   substitution finding at audit.
2. Return policy: window in days, whether return shipping is free, and the URL of
   your returns page.
3. Logo image CDN path for the homepage Organization schema.
4. Social profile URLs (Instagram, TikTok, and others) and retail partner URLs
   (Beautylish, Ulta, Target — whichever apply).
5. Confirmation that `/shop/browse?q=` is your search URL format.
6. Review feed: a sample export of 3 to 5 reviews per product, or API access.

---

## Files in this folder

| File | What it is | Status |
|---|---|---|
| pdp-schema.md | Enriched JSON-LD for /s/ pages + ProductGroup for /p/ pages | Needs GTIN/SKU from you |
| homepage-schema.md | Organization + WebSite schema for the homepage | Needs logo + social URLs from you |
| category-schema.md | ItemList schema for category browse pages | Ready, needs developer templating |
| llms-full.txt | Full AI guide file, ready to upload | Needs returns policy from you |
| agents.md | Agentic interaction guide, ready to upload | Needs returns policy from you |
