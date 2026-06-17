# Operating runbook: how Anneal runs once the keys exist

This is the autonomous loop. Everything here is mine to run after the accounts gate (`setup-gate.md`) is done and I have the API tokens. It is written so any agent picking this up can run the brand without re-deriving it.

## Daily

- Pull new Shopify orders. Print on demand auto-routes fulfillment, so the job is to watch for anything stuck: failed payments, address errors, fulfillment holds. Resolve or flag.
- Read the support inbox. Reply in brand voice. Authority: refund or reprint up to the per-order cap without asking (default $120), anything larger gets flagged to you.
- Scan for misprint or damage reports. Reprint or refund per the returns policy, no return shipping required.

## Weekly

- Pull the numbers: sessions, conversion rate, orders, revenue, contribution, blended customer acquisition cost if paid is running. Write a short log entry in `ops/log.md` (create on first run).
- Check margin on every live variant against the $15 floor. Blanks change price, so re-confirm.
- If paid is running, check it against the thresholds in `financials.md` and cut or scale.
- Decide content for the week from the formats in `marketing/launch-post.md`. Draft, post the ones inside standing authority, hold the "show me first" ones for you.

## Monthly

- Full review: what sold, what did not, what the data says about the next drop.
- Restock decision is automatic since made-on-order, but pricing and the live SKU set are not. Promote the one or two SKUs that sell into the standing line, retire the rest.
- Only build drop 02 designs if drop 01 cleared a real conversion bar (set the bar with you on first monthly review).

## Standing guardrails

These never change without you saying so:
- Monthly spend ceiling: the number you set at handover. I stop at it.
- Margin floor: no variant below the set contribution.
- Refund authority: up to the per-order cap without asking.
- Show-me-first list: first public launch post, any new claim about the brand, any use of a person's likeness, any spend above the ceiling.

## What I escalate to you, always

- Anything needing a fresh KYC or ID check (new processor, new bank, ad-platform business verification).
- A binding contract or its signature.
- Tax thresholds: once sales create nexus in a state, sales-tax registration and remittance is yours. I will flag when volume approaches a threshold, I cannot file it.
- A legal or safety complaint about a product.

## State of the world this runbook assumes

- Store: Shopify Basic, theme set to the brand palette and type in `brand/brand-book.md`.
- Fulfillment: Printify connected, lowest-base provider per blank.
- Email and SMS: Klaviyo, the three flows in `marketing/email-flows.md` live.
- Products: the three SKUs in `product/printify-spec.md`.
- Access I hold: Shopify Admin API token, Printify API token, Klaviyo API key, support inbox.

If any of those is missing, the gap is in `setup-gate.md`, not here.
