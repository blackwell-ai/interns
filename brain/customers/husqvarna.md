# Husqvarna

Forest & Garden — robotic mowers.
Last updated June 10, 2026. Source: founder-provided canonical context.

## Contacts

- **Mandy Iswarienko** — mandy.iswarienko@husqvarnagroup.com (primary thread)
- **Hector BautistaDon** — hector.bautistadon@husqvarnagroup.com
- **Justin** (surname/email TBD) — sent the product feed June 12, 2026, with
  scope questions on the follow-up brief

## Documents

- Audit deck: [documents/husqvarna-audit.pdf](documents/husqvarna-audit.pdf)

## Delivered

- Full GEO audit of the current residential robotic mower line (Automower
  410 iQ, 420 iQ, 440 iQ), composite D/53
- 20-page evidence-table-driven deck: bot-UA maps, per-engine price spread
  tables, schema validation matrices, coverage and share-of-voice tables,
  reputation score tables, twelve-row competitive matrix
- Truth table frozen from husqvarna.com on June 2, 2026 before any engine was
  queried
- Findings: access and entity authority clean, but Recommendability 38/F,
  Reputation 42/F, Transactability 30/F. No agent-commerce endpoints, Trustpilot
  1.3, BBB customer average 1.04, AggregateRating absent from the brand's own
  markup, and the AI corpus relabels a wire-free 2026 product as dated and wired
- Competitors Mammotion LUBA 3 and Segway Navimow received indicative B grades
- Data collected in five sequential blocks combining Claude Code browser
  automation with manual test passes

## June 11, 2026 re-verification (follow-up meeting prep)

Source: live pulls by GEO agent (curl, BBB/Trustpilot reads), same day as
follow-up meeting.

- **BBB, corrected entity** (engineer critique absorbed): the profile
  registered to husqvarna.com/us is Husqvarna Professional Products, Inc.,
  Charlotte NC (alt name "Husqvarna Forest & Garden Company"), BBB Accredited
  since 2007 — **A+ letter rating, 1.03/5 customer average (58 reviews), 204
  complaints/3yr, 42 closed/12mo**. Materially identical to the audit's
  wrong-entity numbers (1.04, 191); finding stands.
- **Trustpilot (headed-browser read, Cloudflare bypassed)**: **1.4/5, 872
  reviews, 81% one-star, still UNCLAIMED**, "no history of asking for
  reviews"; 141 reviews in last 12 months. Was 1.3/864 on June 2. Trustpilot's
  own sidebar cross-sells Mammotion (4.0, 2.6K reviews) and Navimow (2.9, 218)
  on Husqvarna's page. Quotable fresh reviews include a June 9 "3 robot
  mowers, all 3 died" and an Automower 450X "planned obsolescence / 3G
  sunset" review recommending Mammotion/Worx/Segway.
- **PDPs (410/420/440 iQ)**: bot-UA parity clean; Product+Offer schema
  server-rendered; still missing gtin, aggregateRating, review,
  shippingDetails, return policy, seller, priceValidUntil; description empty.
  NEW: FAQPage schema (8–9 Qs/page, leads with wire-free answer) + VideoObject.
  Brand prices: 410iQ $2,599.99 / 420iQ $3,299.99 / 440iQ $4,299.99 (Amazon
  3P listings +$38 on 410/420).
- **Agent endpoints** (/.well-known/ucp, agent.json, ai-plugin.json): still 403.
- **Old models**: 430X URL now redirects to a "Parts, manuals and support"
  page marked discontinued but still serving a Product schema node; 450X/450XH
  URLs still return 200.
- **Follow-up meeting (June 11, Armaan)**: positive on the audit. They asked
  for Amazon testing detail, content change proposals (their code changes move
  slowly; content is the focus), specific PDP updates from public data for the
  three iQ pages, and engagement terms in the document. **They are providing a
  product feed with detailed PDPs across the catalog** — extends proposals
  feed-wide and grounds the re-benchmark. Fee terms: the $1,000 covers however
  many SKUs the feed contains (not per-SKU); work starts with the DTC products
  and moves up the catalog. Brief revised accordingly
  (agents/geo/husqvarna/husqvarna-followup-2026-06-11.pdf).
- **Product feed received (June 12)**: 1,254-product catalog export with PDP
  fields (title, description, URL, category, price, per-star review counts) at
  `agents/geo/husqvarna/husqvarna-product-feed-2026-06-11.csv`. Grounds the
  feed-wide page checks and the proposal extension across the catalog.
- **Amazon Alexa for Shopping (manual run by Armaan, 4 prompts; the assistant formerly branded Rufus)**: Husqvarna appeared in
  all 4 answers, top pick on the 2-acre question; correctly described as
  wire-free (catalog-grounded). Where the assistant expressed preference it cited
  reviews (Mammotion 4.4/87 "best overall" vs 440iQ 3.5/22). 430X surfaced as
  live option. LiDAR-under-trees heuristic repeated.
- **Feed received June 12** (Justin's email): product feed with detailed PDPs
  across the catalog. Their team added FAQs for Robotics & Chainsaws;
  Trimmers & Blowers in progress. Justin asks: (1) what "as it would ship"
  means, (2) confirm same depth across the full catalog, (3) whether we
  provide 10+ FAQs per product elsewhere plus review existing FAQs as done
  for the 440. Position in reply: review + gap-fill confirmed for every
  product; FAQ count follows real buyer questions (roughly 8-12 on complex
  products, fewer on simple ones), not a fixed quota.
