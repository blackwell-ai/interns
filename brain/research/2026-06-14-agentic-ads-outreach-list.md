# Agentic-ads outreach list: 200 contacts on the future of advertising under agentic commerce

Date: 2026-06-14. Source: internal request (Armaan) to build a contact list for
a campaign on "how advertising evolves as AI agents increasingly buy products
instead of people."

## What was built

200 unique, Hunter-verified work emails, segmented:

- **70 DTC founders/CEOs** — reused the 2026-06-10 enriched lead bank
  (`samarjit_enriched.csv`), top 70 by score (all `valid`, 98-99).
- **65 researchers** — academics studying ad auctions/market design, marketing
  science, recommender systems / LLM agents, agentic commerce, consumer behavior,
  and AI policy. Web-sourced by name, then `findemail.find` verified.
- **65 big-tech advertising people** — Google, Meta, Amazon (Rufus/Ads),
  Microsoft, OpenAI, Perplexity, Anthropic, Shopify, Stripe, TikTok, Pinterest,
  Reddit, Snap, Trade Desk, Criteo, Instacart, Klaviyo, Walmart Connect,
  Comcast, Visa, Mastercard — people on ads products, agentic commerce, and
  payments-for-agents.

Deliverable: `skills/autonomous-outreach/agentic-ads/master_200.csv`
(columns: email, first_name, last_name, title, org, domain, segment, subarea,
why_relevant, source_url, email_score, email_status). Per-segment files and the
candidate/enriched provenance CSVs sit alongside it.

## Status / important

- **Nothing sent.** The user is supplying the email template later. The contact
  ledger (`contacted`) is untouched, so all 200 remain contactable — the
  no-double-contact claim only fires inside `gmail.send`.
- When the template arrives, this is a `clay-cold-email` rerun (or
  `autonomous-outreach`): feed `master_200.csv` as the leads CSV. The
  `why_relevant` column is a ready-made personalization hook per contact.
- Method + verify-rate lessons: `harness/learnings/06-named-individual-sourcing-for-findemail.md`.

## Why this is company-relevant

Blackwell works in agentic commerce ([[overview]]). This list is a campaign
asset, but the segmentation also maps the people actively shaping how ads and
agent-driven buying collide — useful primary-source reach for that thesis.
