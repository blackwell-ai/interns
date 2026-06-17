# The real gate, in stages

I over-gated this earlier. Corrected. Most of what I called a blocker either is not needed yet or is not needed at all. Here is the honest version, smallest first.

## Stage A: validate demand. Needs nothing from you.

The store is built as a real, working site in `site/` (open `site/index.html` in a browser). It is a waitlist landing page: it shows the brand, the drop, and the story, and it captures emails. It takes no money, so it needs no entity, no payment processor, no Shopify. This is the cheapest way to learn whether anyone outside our network wants this before a cent is spent.

The one small thing to put it on the public internet is a place to host it. A free tier (a static host on a free subdomain) costs nothing and needs no card. Creating that host account is the only "you" step here, and it is small. If you would rather, point me at any hosting you already control and I deploy there. Until then it runs locally and is ready.

## Stage B: take real money and ship products. The one hard gate.

This is the only genuinely irreducible blocker, and it only matters once you want to sell, not just collect waitlist signups.

To accept a payment and pay a printer, you need a payment processor (Stripe or Shopify Payments). It is legally required to verify a real human or entity, and it needs a bank account for payouts and a card to fund per-order printing. I cannot pass that verification and I will not impersonate you to it. That is the gate. Everything else routes around it.

What this stage actually requires from you, once you choose to flip it on:
- A payment processor account, verified (the KYC step, ~20 minutes).
- A bank account for payouts and one funding card.
- An "I agree" on the processor's and printer's terms, as a person.

Entity is optional here. Selling under your own name is a sole proprietorship by default, no paperwork. Form an LLC later for liability separation only if it sells. Do not let it block launch.

## After Stage B, hand me the keys

These turn it autonomous and are the last thing I need:
- The store platform's admin API token (whatever we sell on).
- The print-on-demand API token (Printify to start).
- The Klaviyo API key for the email flows in `marketing/email-flows.md`.
- The support inbox.

## Guardrails to set at handover

Pick the numbers, I operate strictly inside them and never raise them without asking:
- Monthly spend ceiling (tools plus any ads). Suggested start: $300.
- Margin floor: no SKU below a set contribution. Suggested: $15.
- Refund authority without asking, per order. Suggested: $120.
- A short "show me first" list: the first public launch post, any new claim about the brand, any use of a person's likeness.

## What stays yours forever

- Being the legal and tax person of record (entity if you form one, sales tax once there is nexus).
- Anything needing a fresh ID or KYC check.
- The signature on any binding contract.

That is the whole gate. Stage A is unblocked right now.
