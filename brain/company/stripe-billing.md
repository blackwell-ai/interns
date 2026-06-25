# Stripe billing and the YC Stripe perk

Filed 2026-06-25. Source: Granola notes from the June 25, 2026 Stripe onboarding
call ("Client onboarding with Lindsey"; Lindsey is the Stripe contact via the YC
perk). Billing context for Blackwell as it moves from manual pilot invoices toward
recurring revenue.

## How billing works today

- Pilots are invoiced manually from the Stripe dashboard. Pricing is the $1,000
  30-day pilot (see [[overview]]). 2 paying customers so far, a couple more being
  finalized. All sales-led; no self-serve checkout is planned.
- The team is exploring a move from one-off pilot invoices to a monthly recurring
  model as pilots convert.

## Recurring-billing options Stripe laid out (for when we are ready)

- Automated billing via the API, charged on a set date each month.
- A customer portal so clients manage their own subscription.
- A consumption-based model is possible (for example, vary the charge by the LLM
  visibility delivered that month), which fits the GEO re-benchmark cadence.
- Stripe-hosted checkout, embeddable on the site, only if self-serve is ever wanted.
- A sandbox is available to test billing logic before going live. Lindsey will send
  the Stripe API docs.

## YC perks on the account

- **$15,000 in free Stripe credits.** One year to accept, then one year from the
  acceptance date to use. Credits should be visible by Friday, June 26, 2026.
  Lindsey's follow-up email will include the account ID.
- **Accelerate on Demand**: a dedicated Stripe technical integration expert assigned
  to the account, CC'd on Lindsey's follow-up email.

## Open action items (Armaan)

- **Accept the $15,000 Stripe credits.** Account ID arrives in Lindsey's follow-up;
  credits appear by June 26. Note the one-year acceptance window.
- **Review the Stripe API docs and test recurring billing in the sandbox**, ahead of
  moving customers to monthly agreements.
