# Catalog — product data infrastructure notes

Filed June 10, 2026. Source: Granola notes from "Intro to catalog with Hamish",
May 19, 2026.

## Who they are

- Hamish: ex-Afterpay data scientist, Cash App Commerce founding team;
  co-founder is Harvard math, staff ML engineer
- $3M raised from investors behind Cursor, Coinbase, Robinhood
- Positioning: "Rails for AI to understand real-economy products"

## Technical approach

- Compound data sourcing — no single source suffices; SERP API (Google Shopping
  index) as the seed, then PDP scraping and cross-source entity resolution
- Core system is agentic: dynamic mapping of disparate unstructured /
  semi-structured datasets (pre-AI this was infeasible)

## Market insights (worth weighing)

- Dozens of agentic-commerce infrastructure companies (Rye, Lithic, Skyfire)
  but **no actual consumer use cases** — their monthly agentic-commerce
  consortium keeps confirming this; infra customers are developers, not
  consumers
- Open question: is the consumer gap due to competition with Amazon/ChatGPT or
  consumer behavior?
- Amazon Rufus recommends high-margin inventory Amazon wants to move; Shopify
  has ~20% of merchants and controls its agentic-commerce APIs
- Risk hanging over all infra players: absorption by Stripe/Shopify/Amazon

## Notes that touched Blackwell strategy (May 19 snapshot)

- At the time: YC had said "show more progress" pre-decision; a16z final-round
  rejection
- Discussed: keep customer-discovery outreach to e-commerce heads/VPs/CMOs;
  make shopping agents trendy/aesthetic vs. basic chat UI; consider shopping
  agents for brands/retailers before any universal platform
