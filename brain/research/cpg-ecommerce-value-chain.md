# CPG and e-commerce value chain: the map we are exploring

Started June 15, 2026. Source: founder direction from Armaan (this session) plus
the June 10 YC advisor mandate to "map out the whole connected graph of
everything around DTC and be surgical about each node"
(`context/samarjit-granola/2026-06-10-smb-outreach-and-customer-discovery-strategy-with-ai-solutions.md`).
Grounds the exploration stance in [[2026-06-14-company-is-in-exploration-phase]].

## Why this file exists

The exploration is not "GEO" and it is not "inventory management." Those are two
nodes on a long chain that moves a physical product from a factory to a person.
At every node there is software, there are parties who hand work to each other,
and there is now a question of how AI changes that node. Blackwell's exploration
target is the whole chain: learn each node in and out, then find the recurring,
concrete, payable problems where a business needs a hand adapting to AI. The
service we sell can sit at any node, and over time at several.

This file is the index and the map. As we go deep on a node it gets its own file
(for example product feeds and POS already deserve their own); link them back
here. Treat the AI-opportunity notes as hypotheses to test with real merchants,
not settled conclusions.

A note on scope: "CPG" (consumer packaged goods, physically made and sold
products) is the spine, but most of this applies to any brand or retailer moving
physical goods, which is the customer base we have talked to so far (beauty,
apparel, outdoor, liquor, sporting goods).

## The chain, end to end

Read top to bottom as product and money flow. Each node lists what it is, the
systems that run it, the parties involved, and where AI is changing it (the
service opening for us). Nodes overlap and loop in real businesses; the linear
order is for learning, not literal sequence.

### 1. Product development and sourcing

What it is: deciding what to make, designing it, sourcing materials, and getting
it manufactured.

Systems: PLM (product lifecycle management) at larger brands, spreadsheets and
Tech Packs at small ones, supplier directories (Alibaba, Faire for wholesale
discovery), sampling and QA tracking.

Parties: the brand, raw-material and component suppliers, contract manufacturers
(in CPG these are co-manufacturers or "co-mans"; in apparel, cut-and-sew
factories), and sometimes a sourcing agent or broker who sits between brand and
factory. Key constraints that shape everything downstream: MOQs (minimum order
quantities) and manufacturing lead times (weeks to months).

AI opening: supplier and material discovery, spec and tech-pack drafting,
translating demand forecasts into production runs, compliance and certification
checks.

### 2. Demand planning and inventory

What it is: deciding how much to make or buy and when, then keeping the right
stock in the right place. This is the node JD Sports and the fashionology
merchant both named as their sharpest pain.

Systems: ERP modules at the top end, dedicated inventory planning tools
(Inventory Planner, Cogsy, Netstock, Cin7), purchase-order and PO-financing tools
(Settle), and at the small end spreadsheets plus QuickBooks plus Shopify history.

Parties: the brand's merchandiser or planner (often the owner at a small brand),
finance or a bookkeeper, and the manufacturer whose lead time sets how far ahead
you must commit cash.

AI opening: predictive demand forecasting (the most validated signal we have, see
JD Sports, the fashionology merchant, and the Upwork forecasting job in
`brain/research/lead-signal-sources.md`), reorder and safety-stock logic,
inter-location transfer recommendations, dead-stock flags, and cash-flow planning
tied to the buy. The cash-flow framing matters: for small brands the real pain is
money tied up for months, not just stockouts.

### 3. Master product data (PIM)

What it is: the single source of truth for what a product is. SKU structure,
GTIN/UPC barcodes, attributes (size, color, material, ingredients), variants,
descriptions, and the digital assets (photos, video) that go with them. Almost
everything downstream (storefronts, feeds, syndication, GEO, marketplaces) reads
from here, so bad master data poisons every channel at once.

Systems: PIM platforms (Akeneo, Salsify, inriver, Plytix, Pimcore), DAM (digital
asset management) for the images, and a product taxonomy. Small brands usually
have no PIM; the "PIM" is Shopify plus a spreadsheet, which is why their data is
inconsistent across channels.

Parties: whoever owns the catalog (a merchandiser, an ops person, or the founder),
plus anyone publishing to a channel that needs clean attributes.

AI opening: attribute enrichment and gap-filling, taxonomy and category mapping,
auto-generating descriptions and structured data, and normalizing a messy catalog
into something machines (search engines, marketplaces, and now AI agents) can
read. This is the node where GEO actually lives: GEO is "make the product data
legible to AI," which is a master-data and syndication problem wearing a
marketing hat.

### 4. Product syndication and structured feeds

What it is: taking the master product data and pushing it out to every channel in
that channel's required format. "Syndication" is the distribution; a "feed" is the
file or stream that carries it. Each destination wants a different shape, so this
node is mostly format translation and rule-keeping at scale. Deep dive below.

Systems: feed management platforms (Feedonomics, Channable, DataFeedWatch,
Productsup, GoDataFeed) and, for retail and grocery, GDSN data pools (1WorldSync)
built on GS1 standards.

Parties: the brand, the channels and retailers receiving the feed (Google,
Meta, Amazon, Walmart, TikTok Shop, and brick-and-mortar retail buyers), and the
data-pool or feed-tool vendor in between.

AI opening: auto-mapping a brand's attributes to each channel's schema, fixing
feed rejections, and the emerging job of making feeds agent-readable (see the
agentic-commerce layer below). llms.txt and on-site structured data are, in
effect, a feed aimed at AI answer engines rather than at Google Shopping.

### 5. Selling channels and storefront

What it is: where the product is actually sold. DTC website, online marketplaces,
physical retail, wholesale/B2B, and social commerce. Most brands are on several at
once and the hard part is keeping them consistent (price, stock, content).

Systems: Shopify and BigCommerce (hosted), headless setups (a CMS like Sanity in
front of a commerce engine, as Loontogs runs), marketplace seller accounts, and
the third-party app ecosystem that bolts on features (the fashionology merchant's
complaint: every small feature is a separate paid app).

Parties: the brand, the platform, app and theme developers, and agencies.

AI opening: GEO and AEO for discovery, on-site search and personalization, content
and merchandising, conversational shopping, and agentic checkout (below).

### 6. Point of sale and omnichannel

What it is: selling in the physical world and keeping it in sync with online. POS
is the system that rings up an in-person sale; omnichannel is the harder problem
of one inventory and one customer across store and web. Deep dive below.

Systems: POS platforms (Square, Clover, Toast for food, Lightspeed, Shopify POS,
and legacy or industry-specific systems like the decade-old inventory software GNM
Liquors runs). Omnichannel patterns: BOPIS (buy online, pick up in store),
ship-from-store, click-and-collect, endless aisle.

Parties: the POS vendor, the payment processor behind it, hardware, and the store
staff who are the real users.

AI opening: a single live view of inventory across channels (the thing that breaks
JD Sports' replenishment, since stock decrements through in-store, ship-from-store,
and click-and-collect at once), store-associate assistants, and the "AI store
manager" framing the team has pitched.

### 7. Order management (OMS) and the ordering parties

What it is: the orchestration layer between "an order exists" and "the order is
fulfilled," across every channel. The OMS captures orders, decides which location
or warehouse ships each one, sends fulfillment instructions, and tracks status and
returns. It is distinct from the storefront (which takes the order) and the WMS
(which runs the warehouse). Loontogs runs Omnium as its OMS. Deep dive below,
including the full list of parties in an order and the EDI messages they exchange.

Systems: OMS platforms (Manhattan, IBM Sterling, Fluent Commerce, Kibo for
enterprise; Brightpearl, Cin7, Linnworks, Extensiv, Omnium for mid-market and SMB),
and DOM (distributed order management) logic for sourcing decisions.

Parties: the merchant, the payment gateway and processor, the OMS, the WMS or 3PL,
carriers, and on the B2B side the retailers, distributors, and wholesalers who buy
in bulk. See the deep dive for the handoffs.

AI opening: order orchestration and exception handling, EDI mapping and onboarding
(a slow, manual, expensive job today), and returns processing.

### 8. Warehousing and logistics

What it is: physically receiving, storing, picking, packing, shipping, and taking
back goods.

Systems: WMS (warehouse management systems), 3PL platforms (ShipBob, ShipMonk),
Amazon Multi-Channel Fulfillment, and shipping software (ShipStation) plus rate
and carrier APIs.

Parties: 3PLs (third-party logistics) and 4PLs, freight forwarders and customs
brokers for imported goods, drayage, and carriers (parcel: UPS, FedEx, USPS,
regional; freight and LTL for pallets).

AI opening: warehouse slotting and labor, returns triage, shipment exception
handling, and landed-cost and delivery-date prediction.

### 9. Payments and finance

What it is: taking money, reconciling it, financing the gap, and keeping the books.

Systems: payment gateways and processors (Stripe, Shopify Payments, Adyen), fraud
and chargeback tools, accounting (QuickBooks, Xero), PO and inventory financing
(Settle), and for B2B the net-terms and invoicing stack (AR/AP).

Parties: the processor, the acquiring and issuing banks, fraud vendors, lenders,
and the bookkeeper or finance lead.

AI opening: reconciliation, cash-flow forecasting tied to the inventory buy
(connects back to node 2), fraud, and financing decisions.

### 10. Marketing, demand generation, and retention

What it is: getting discovered and bringing customers back.

Systems: paid ads, SEO, email and SMS (Klaviyo), loyalty, reviews and UGC
(Bazaarvoice, see `brain/research/review-platforms-bazaarvoice-influenster.md`),
influencer, attribution, and CDPs (customer data platforms).

Parties: the brand's marketing lead or owner, agencies, ad platforms, and review
and creator networks.

AI opening: this is where GEO and AEO sit on the demand side, because discovery is
shifting from Google's blue links to AI answer engines (see
`brain/research/answer-engine-citation-behavior.md`). Also creative generation and
personalization.

### 11. Customer service and post-purchase

What it is: support, order questions (WISMO, "where is my order"), and returns.

Systems: helpdesks (Gorgias, Zendesk) and returns platforms (Loop, Returnly).

Parties: the support team or owner, the helpdesk vendor, and the returns and
carrier stack.

AI opening: the fashionology merchant drew the line cleanly. Transactional contact
(order status, return policy) is fine to automate; relationship-building contact
(styling, fit advice, special orders) is a human differentiator versus Amazon and
should stay human. The opening is automating the transactional half well without
touching the relationship half.

### 12. Analytics and the data layer

What it is: turning all of the above into decisions. The Upwork forecasting job
showed the modern shape: Shopify to Fivetran to BigQuery to Cloud Run to GPT, run
daily, producing plain-English ops insights.

Systems: data warehouses (BigQuery, Snowflake), ELT (Fivetran), BI (Looker), and
increasingly an LLM at the end writing the narrative.

AI opening: the "analyst in a box" that watches the data and tells the owner what
to do in plain language. This is a horizontal that touches every node above.

## Deep dives on the nodes Armaan flagged

### Point-of-sale systems

A POS is the system of record for an in-person sale: it rings up the transaction,
takes payment, prints or emails the receipt, and decrements inventory. Modern POS
is rarely just the register. It bundles payments (the processor is often the POS
company itself, which is how Square and Toast make most of their money), inventory,
basic CRM and loyalty, staff management, and reporting.

The market splits by vertical because the workflows differ. Square and Clover
serve general retail and small business; Toast owns restaurants; Lightspeed serves
retail, restaurants, and golf; Shopify POS exists to unify a Shopify store's online
and offline selling; and legacy or industry-specific systems (liquor, grocery,
pharmacy) often run decade-old on-premise software, which is what GNM Liquors has
and why a rebuild was on the table.

The hard and valuable problem is not the register, it is unified commerce: making
the POS, the online store, and inventory agree in real time. When a customer buys
in store, returns online, and the next shopper checks stock on the website, all
three need one truth. Small merchants usually run a POS and an online store that do
not talk, so stock is wrong somewhere most of the time. This is the same root issue
that breaks JD Sports' replenishment (stock decrements through multiple channels at
once) just at a smaller scale.

AI angle: store-associate copilots (answer product and stock questions on the
floor), the unified-inventory truth as a prerequisite for any "AI store manager,"
and reading POS sales history as the demand signal for forecasting.

### Product syndication and structured product feeds

Syndication is publishing one product catalog to many destinations, each in its own
required format, and keeping them current as price, stock, and content change. A
feed is the artifact that carries it, usually a file (CSV, XML, or a Google Sheet)
or an API stream, regenerated on a schedule.

Two worlds use the word differently:

Digital marketing and marketplace feeds. To sell on Google Shopping you submit a
product feed to Google Merchant Center that follows Google's product feed spec
(required fields like id, title, description, link, image_link, price,
availability, gtin, brand). Meta, Amazon, Walmart, TikTok Shop, and Pinterest each
want their own variant. Feed management tools (Feedonomics, Channable,
DataFeedWatch, Productsup) exist because mapping one catalog to a dozen schemas,
applying rules, and fixing rejections by hand does not scale. A rejected or
malformed feed quietly kills a sales channel, so this is unglamorous but
high-stakes work.

Retail and grocery syndication. Selling through retailers (a grocery chain, a big
box) usually means GDSN, the Global Data Synchronization Network, built on GS1
standards (the people behind barcodes and GTINs). Brands publish product data into
a data pool (1WorldSync is the largest) and retailers subscribe, so a spec change
propagates to every retailer at once. This is how packaged-goods attributes,
dimensions, and images reach retail buyers in a trusted, standardized form.

On-site structured data. The same catalog also has to be legible to crawlers and
answer engines on the brand's own site, via Schema.org Product markup in JSON-LD
(price, availability, reviews, GTIN). This is the bridge to GEO: an llms.txt or
llms-full.txt file and clean Product schema are, functionally, a feed aimed at AI
answer engines instead of at Google Shopping. So syndication, master data, and GEO
are the same muscle pointed at different consumers (marketplaces, retailers,
crawlers, and now AI agents).

AI angle: auto-mapping attributes to each destination's schema, diagnosing and
fixing feed rejections, enriching thin product data so it qualifies for more
channels, and producing the agent-readable version of the catalog as the agentic
protocols below mature.

### Manufacturing and sourcing

Covered as node 1 above; the points worth holding onto for the chain. Two
constraints set downstream behavior: MOQs force brands to commit to large batches,
and lead times (weeks for domestic, months for overseas with freight and customs)
force them to commit cash long before revenue. That is the origin of the
fashionology merchant's pain (order wool gloves in July, sell in December) and it
ties manufacturing directly to demand planning (node 2) and cash flow (node 9).
Most small brands use contract manufacturers (co-mans or co-packers in CPG, cut-and-sew
factories in apparel) rather than owning production, often with a sourcing agent in
between. The AI openings are supplier and material discovery, spec and tech-pack
drafting, and turning a demand forecast into a production and PO plan.

### Order management systems and the parties in an order

An OMS is the orchestration brain between the channels that capture orders and the
operations that fulfill them. It is easy to confuse three systems that sound alike,
so the clean distinction:

- ERP runs the business and the money (finance, purchasing, the master records).
- OMS runs the order's lifecycle across channels (capture, sourcing, routing,
  status, returns).
- WMS runs the physical warehouse (receiving, putaway, pick, pack, ship).

A capable OMS does distributed order management (DOM): when an order comes in, it
decides which location or warehouse should fulfill it based on stock, distance, and
cost. That sourcing decision is exactly what JD Sports does manually and what
ship-from-store omnichannel depends on.

The parties in a DTC order, in sequence:

1. Customer places the order on the storefront.
2. Payment gateway authorizes and the processor captures funds; the acquiring bank
   and the customer's issuing bank settle behind it.
3. OMS receives the order and decides where it ships from.
4. WMS or 3PL picks, packs, and labels it.
5. Carrier (UPS, FedEx, USPS, regional) delivers; tracking flows back to the
   customer.
6. Returns and RMA (return merchandise authorization) run the same chain in
   reverse.

The parties in a B2B or wholesale order are different and run on EDI (Electronic
Data Interchange), the decades-old standardized messaging that retailers require
of their suppliers. The core X12 transaction sets are worth knowing by number
because vendors talk in them:

- 850 purchase order (the retailer orders).
- 855 PO acknowledgment (the supplier confirms).
- 856 ASN, advance ship notice (what is in the shipment, before it arrives).
- 810 invoice.
- 846 inventory advice, 832 price/catalog, 940/945 warehouse ship order and advice.

EDI typically moves through a VAN (value-added network) or modern API equivalent,
and onboarding each retailer's exact EDI requirements is slow, manual, and
error-prone, which is one of the clearer AI openings in the whole chain. Loontogs'
B2B preorder model (sell to retailers in advance, confirm orders after the goods
are bought) is exactly the kind of non-standard ordering flow that Shopify's
out-of-the-box B2B does not cover and that an OMS or custom integration has to
handle, which is why their Shopify migration is blocked.

AI angle: order orchestration and exception handling, automating EDI mapping and
retailer onboarding, and intelligent returns.

## The cross-cutting layer: the AI and agentic-commerce shift

This is the change Blackwell wants to help businesses adapt to, and it does not
live at one node, it cuts across the whole chain:

- Discovery is moving from search to AI answer engines, which is what GEO and AEO
  respond to (nodes 4, 5, 10).
- Product data has to become legible to AI agents, not just to humans and crawlers
  (nodes 3, 4).
- Agentic checkout is emerging: AI agents that buy on a person's behalf. The
  protocol layer here is real but moving fast and the specifics need a live
  verification pass before we advise a customer. What we have referenced so far:
  MCP (Model Context Protocol) endpoints, an "agentic commerce protocol" tied to
  ChatGPT checkout, Google's agent-payments work, and the UCP and agents.md
  conventions our own audits already check (see the Good Molecules audit). Confirm
  current names, owners, and adoption before quoting them.
- An AI copilot or "manager in a box" is plausible at almost every operational
  node (planning, store ops, support, analytics), which is the broad version of the
  "AI store manager" pitch.

The exploration question for each node is the same: where does a real business need
a hand adapting to this, concretely enough that they will pay? We answer it by
talking to merchants at each node, not by reasoning about it here.

External view worth noting: a May 2026 PwC article argues for entering this chain
at merchandising first and describes an "autonomous merchandising operating model"
that matches the "AI store manager" framing above. It is one consulting opinion,
filed and assessed in [[2026-06-19-pwc-merchant-ai-value-chain]].

## How we drill down from here

This map is breadth. Depth comes node by node, each becoming its own file with real
sourcing and, where possible, a merchant who has the problem:

- Verify the agentic-commerce protocol layer against current sources (it is the
  fastest-moving and least settled part of this file).
- Split POS/omnichannel, product feeds/syndication, and OMS/EDI into their own deep
  files as we work them.
- For each node, tie the abstract opening to a named lead or signal we already have
  before calling it a real opportunity.

Open questions worth holding: which node has the most acute, most common,
most-willing-to-pay problem for the small and mid brands we can actually reach; and
whether the long-term wedge is a single node done well or the horizontal "manager"
that reads across several.
