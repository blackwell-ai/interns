# ANNEAL

A direct-to-consumer apparel label designed and operated end to end by an autonomous agent. Print on demand, zero inventory, premium and restrained. This folder is the brand. Everything here is ready to load into a live store the moment the accounts exist.

The name is a variable. If you want a different one, it is a find-and-replace away and I will swap it. Reasoning for ANNEAL is in `brand/brand-book.md`.

## Status

Built and ready to ship, blocked only at the accounts gate.

| Layer | State |
|---|---|
| Niche and positioning | Done. Design-forward apparel, "made by a machine" as the wedge. |
| Brand (name, voice, identity, palette, type) | Done. `brand/brand-book.md` |
| Logo and design assets | Done. `brand/logo.svg`, `product/designs/` (curve back print + chest mark) |
| First drop product line + unit economics | Done. `product/line-plan.md`, `ops/financials.md` |
| Printify build sheet + size guide | Done. `product/printify-spec.md`, `product/sizing.md` |
| Store copy, policies, SEO | Done. `store/` |
| Marketing: launch plan, email flows, launch post | Done. `marketing/` |
| Operating runbook (the autonomous loop) | Done. `ops/operating-runbook.md` |
| Working storefront (real HTML/CSS, waitlist) | Done. `site/index.html` |
| Public hosting for the waitlist | Small step. A free host, or point me at infra you control. |
| Taking live payment + fulfillment | Blocked. The one hard gate. `ops/setup-gate.md` |

## Where I am actually blocked (corrected, smaller than I first said)

I over-gated this. Two corrections: you do not need to pick sole-prop vs LLC to launch (sole prop is the default, zero paperwork), and you do not need Shopify (the store is just software, I built a real one in `site/`).

So the gate is now staged (`ops/setup-gate.md`):
- Validating demand needs nothing from you. The waitlist site is built and captures emails with no money involved. Putting it on the public internet just needs a free host.
- The only hard gate is taking real money: a payment processor's identity check (KYC), a bank account, and a funding card. That is irreducible and yours, and it only matters once we sell, not to collect signups.

Once that one gate is cleared and I have API keys, the operation is mine: products live, orders routing to the printer, support, marketing, analytics, restocks, new drops.

## How it runs once live

Order comes in on Shopify, gets routed automatically to the print-on-demand vendor, vendor prints and ships direct to the customer, tracking flows back to the customer, support is handled from the shared inbox. No one touches a garment. I operate inside the guardrails in `ops/setup-gate.md` (spend ceiling, margin floor, refund authority).
