# Finding gaps by studying laggards, not the frontier

Started June 15, 2026. Source: founder direction from Armaan (this session).
Builds on [[cpg-ecommerce-value-chain]] and [[2026-06-14-company-is-in-exploration-phase]].

## The method

Do not study the big players to find the gap. Study the laggards: the long-tail
merchants who are behind on adoption. The gap is the negative space, meaning what
they still do by hand or cannot do at all, and the trailing edge is where that
negative space is most visible.

Why laggards beat the frontier as a detector: the frontier shows solved problems
(what has already been built), while laggards show unsolved problems (what they
still struggle with). The majors also close gaps from the top down, enterprise
first, so the laggards reveal what is still open at the bottom of the market, which
is where the volume is and where the majors have the weakest incentive to serve.

This is the sharpened form of the June 10 YC advisor advice: shadow customers,
watch what they do, do not lead with AI, find the real problems
(`context/samarjit-granola/2026-06-10-smb-outreach-and-customer-discovery-strategy-with-ai-solutions.md`).

## What to log when observing a laggard

Walk the value chain ([[cpg-ecommerce-value-chain]]) and for each merchant record:

- Every manual task, meaning anything done in a spreadsheet or by hand.
- Every workaround or piece of duct tape.
- Every separate app or tool bolted on, and what it costs.
- Every "we cannot do X because we have no developer."
- Every piece of legacy or on-prem software.
- Every moment of confusion, or "I had to dig to find this."

Tag each to a value-chain node. A gap candidate is a pain that recurs across
laggards and that no affordable platform has closed for them.

## Durability test

Would a big player close this gap for this merchant directly? If the work is
long-tail, bespoke, low-margin, trust-heavy, or integration-heavy, the answer is
no, and the gap is durable, because platforms leave that work to an ecosystem.

## Gap candidates from the calls we already have

Grounded in `context/samarjit-granola/`. These are candidates from current
evidence, not settled conclusions. Validate by recurrence across more merchants.

1. Affordable demand and cash-flow planning (nodes 2 and 9). JD Sports forecasts
   replenishment by hand in Excel; the fashionology merchant plans seasonal buys
   across spreadsheets, QuickBooks, and Settle plus a bookkeeper. Even a 5,500-store
   enterprise could not buy its way out for under 15M pounds (Oracle or SAP plus
   system-integrator and build cost), so it hired data scientists to build its own.
   Strongest signal in the set: if an enterprise still does this by hand, the long
   tail has an expensive unmet problem.

2. The app-sprawl tax (node 5). The fashionology merchant pays separate
   subscriptions for self-serve returns, product filtering, and a lead-gen quiz, and
   had to dig hard to find a quiz with a shoppable results page. Small features each
   cost a separate app, and assembling them is manual and confusing.

3. DIY AI-readiness done badly (nodes 3, 4, 10). Good Molecules generated its own
   llms.txt with Claude but crudely, and had no idea what queries customers actually
   use. A merchant trying to keep up with the AI shift and doing it poorly is a
   clearer buyer than one who has not started.

4. The disconnected-systems glue (nodes 6, 7, 12). GNM Liquors runs decade-old
   inventory software plus DoorDash and no website; Loontogs runs headless Sanity
   into Omnium; the fashionology merchant runs Shopify plus QuickBooks plus Settle
   plus spreadsheets. No platform connects one merchant's specific mess, and AI now
   makes that per-merchant integration cheap enough to deliver as a service.

5. The no-developer wall (cross-node). Loontogs cannot add features without
   developers it does not have; the fashionology merchant has basic coding knowledge
   and pieced the site together with a contractor and volunteer friends; Public
   Goods runs storefront operations with one engineer. Every laggard hits this wall,
   and it is the single most common constraint in the calls.

6. Non-standard workflows platforms do not cover (node 7). Loontogs' B2B preorder
   flow (sell to retailers before the goods are bought, confirm orders later) is the
   reason its Shopify migration is blocked; liquor-specific operations at GNM are
   similar. Too niche for a platform feature, too common to ignore.

## How this feeds the exploration

Every customer conversation should produce gap-log entries here, not just a yes or
no on the current pitch. The recurring, durable, payable gap across many laggards
is the one to build the service around. Pair this with the value-chain map so each
gap is tied to a node and we can see which node accumulates the most pain.
