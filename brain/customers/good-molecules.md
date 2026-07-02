# Good Molecules

goodmolecules.com — skincare, ~$100M brand.
Last updated June 10, 2026. Source: founder-provided canonical context.

## Documents

- Audit deck: [documents/good-molecules-audit.pdf](documents/good-molecules-audit.pdf)
- Engagement letter ("AI visibility remediation", June 2026 — WAF
  reconfiguration for AI crawlers, server-side Product/Offer structured data,
  schema correction, llms.txt/agents.md guide files, before/after measurement,
  plus the no-cost AI assistant pilot):
  [documents/good-molecules-engagement-letter.pdf](documents/good-molecules-engagement-letter.pdf)

## Delivered

- Full AI visibility audit, composite D/61, eight findings (two Critical, two
  High, three Medium, one Strength)
- **Key discovery: the dividing line for AI visibility is crawler access, not
  model quality.** Search-index-fed surfaces (Gemini, Google AI Mode, AI
  Overviews, Bing) allow Googlebot/Bingbot through and show the brand.
  Standalone assistants (ChatGPT, Claude, Perplexity, Copilot) are blocked at
  the WAF and answer from retailers and Reddit instead
- Live AI search testing executed via Claude Code browser automation overturned
  a draft finding (Gemini was assumed blocked; testing showed it cites
  goodmolecules.com as its primary source)
- Claude's verbatim admission that it could not pull prices from the site and
  fell back to Amazon and third-party retailers became the evidence centerpiece
  of Finding 02
- Bing reached the brand but reported the shipping policy as the product price,
  which became its own finding

## Before-benchmark recon, June 17, 2026 (first weekly check-in)

Source: passive recon (curl with crawler user-agents) the morning of the first
weekly call, after the customer reported two changes: initial WAF rule edits and
server-side structured data. Memo:
[../../agents/geo/good-molecules/before-benchmark-recon-2026-06-17.md](../../agents/geo/good-molecules/before-benchmark-recon-2026-06-17.md).

Both changes verified live:

- **WAF, fixed for the major assistants.** GPTBot, OAI-SearchBot, ChatGPT-User,
  ClaudeBot, Claude-User, and PerplexityBot now return 200 (all blocked at audit).
  This is the audit's headline Critical finding, now remediated. Caveats:
  Perplexity-User (live fetch) still 405; spoofed Googlebot/Bingbot return 405
  (likely correct WAF behavior against unverified strings, but confirm the
  *verified* search crawlers still pass, since search-index surfaces were the
  brand's one working channel at audit).
- **Server-side structured data, present.** PDPs now serve JSON-LD in raw HTML:
  Product + Brand, Offer (price, priceCurrency USD, availability InStock),
  AggregateRating. Fixes Critical Finding 02 (Claude could not pull prices, fell
  back to Amazon). Canonical PDP resolves to a size-specific URL (niacinamide
  serum -> 30ml at $6.00), which also addresses the 12ml/30ml price-confusion
  finding.
- **Bonus, not reported by customer:** a rich llms.txt is now live (overview, best
  sellers, shipping, category map, full catalog with prices).

Still open: llms-full.txt (404), agents.md (404), /.well-known/ agentic endpoints
(404), sitemap.xml (404), plus the off-site/recommendability work. The customer
pre-remediated the two heaviest findings before a clean baseline, so the useful
"before" to measure our remaining work against is the live state today. The real
before benchmark is still the live engine battery (headed browser, by hand) against
the frozen truth table, not yet run.

### Server-side structured-data evaluation (same day, kickoff prep)

Full teardown across 10 PDPs + homepage + a category page (curl, allowlisted UA,
raw HTML). Kickoff brief:
[../../agents/geo/good-molecules/kickoff-week1-2026-06-17.md](../../agents/geo/good-molecules/kickoff-week1-2026-06-17.md).
Schema is real and server-rendered (claim confirmed) but minimum-viable and uniform
catalog-wide, so fixes are template-level.

Live and correct: Product (name with size, image, description, brand), Offer (price,
priceCurrency USD, availability InStock, itemCondition NewCondition), AggregateRating
(real ratingValue + reviewCount), an OnlineStore node on every page.

Gaps (ranked): (1) no product identifiers (sku/gtin/mpn), the join key engines use
to reconcile the brand page with Amazon/Ulta/Target, the root of the audit's
price-substitution finding; (2) no variant/ProductGroup modeling of sizes (residual
price-confusion); (3) Offer missing shippingDetails, hasMerchantReturnPolicy,
priceValidUntil, url, despite the data existing in llms.txt; (4) no Review objects,
only AggregateRating; (5) homepage entity schema thin (no sameAs/contactPoint/WebSite
SearchAction); (6) no BreadcrumbList, no collection ItemList, only og:site_name meta;
(7) sitemap.xml 404, llms-full/agents.md/.well-known still 404, no FAQPage. Week-one
plan and a before/after worked example (niacinamide serum) are in the kickoff brief.

Dependencies on the customer: GTIN/UPC + SKU per product, return-policy text, review
feed access, platform deploy + sitemap generation.

## Initial pitch call — May 21, 2026 ("Website structure review")

Source: Granola notes, filed June 10, 2026. **Caveat: Granola's speaker labels
on this call are scrambled** (it attributes the Blackwell side to "two Berkeley
freshmen" and places Armaan on the customer side). Reconstruction, to be
confirmed by Armaan:

- Blackwell pitched the Good Molecules/Beautylish contact on AI visibility
- Evidence used live: ChatGPT asked for "smaller specialty online beauty
  stores" suggests competitors (Credo Beauty, Violet Grey, etc.) but not Good
  Molecules; site lacks FAQ sections and LLM-readable structure
- Pitched a 30-day pilot at **$250** with full refund if baseline thresholds
  not met (pricing later evolved — see engagement letter)
- The contact agreed to review a one-pager and share it with a colleague —
  confirmed from the Dartmouth inbox (June 10): the contact is **Nils Johnson**
  (nils@beautylish.com, Beautylish co-founder, angel-invests in YC companies)
  and the colleague is **Sameer Iyengar** (sameer@beautylish.com), who Granola
  had transcribed as "Samir"
- Next step from the call: send one-pager; follow-up the next week. The email
  thread started as a May 21 cold email and stayed active through May 27+
  (subject: "Stanford Student Question - thoughts on AI retail tools")

## Engagement

- One-page engagement letter delivered at $1,000 upfront with full refund if
  benchmarks are not met, including a no-cost AI assistant pilot where the team
  texts an assistant to manage products, prices, stock, and orders on the live
  site

## Re-audit, June 30, 2026

The live after-benchmark against the June 1 audit (D/61). Full evidence in
`agents/geo/good-molecules-reaudit/` (battery-log.md, reputation-2026-06-30.md,
recon-2026-06-30.md, competitors-2026-06-30.md, assets/). Deck:
`brain/customers/documents/good-molecules-reaudit.pdf`. Evidence gate PASS.

- **Composite moved D (61) to C (67).** Both June 1 Critical findings are closed,
  verified live.
- **Recommendability recovered.** Six-engine two-pass browser battery on "best
  affordable dark spot serum for 2026": named in 6 of 9 passes. ChatGPT names it #1
  from memory and in live retrieval; Google AI Overview calls it the top overall pick;
  Gemini (#2) and Copilot (#2) name it in retrieval. The from-memory reads (ChatGPT,
  Claude) are the notable part: the brand now sits in the models' priors, not just
  their search results. At the June 1 audit no standalone assistant named it.
- **Quotability fixed.** Hero PDP serves Product + Offer (price $12, USD, InStock) +
  AggregateRating (4.3 / 7,631), confirmed in the headed browser (the storefront
  serves a 202 WAF challenge to curl, so this needs an in-browser read). The June 1
  "Claude could not read the price, fell back to Amazon" centerpiece no longer
  reproduces.
- **Open gap 1, retrieval holdouts.** Claude and Perplexity still do not surface the
  brand in live retrieval; they answer from affiliate and derm roundups (Forbes, Yahoo,
  e.l.f., Goodal, Curology) that do not list it. This is off-site presence, not crawler
  access. The brand it loses to, The Ordinary, has thinner product schema than Good
  Molecules and wins purely on being in every roundup.
- **Open gap 2, reputation stranded.** Amazon hero serum 4.4 / ~15.2K ratings, Amazon
  "Overall Pick," active Reddit and YouTube. But no sameAs from the entity, and weak
  aggregators (Trustpilot 2.8 on 4 unclaimed reviews, no BBB or ConsumerAffairs
  profile). Strong sentiment, no machine linkage.
- **Open gap 3, agent layer half open.** agents.md now serves 200 (was 404 at audit),
  but /.well-known/ucp, /api/ucp/mcp, llms-full.txt, and the agentic sitemap return a
  202 WAF challenge, not a confirmed handler. AXIS-Y serves all of these with clean
  200s.
- **Crawler state (WAF fix holds):** GPTBot, OAI-SearchBot, ClaudeBot, PerplexityBot
  all 200. Google-Extended 202, Amazonbot and Bingbot 405 (confirm the verified search
  crawlers still pass, since search-index surfaces were the one working channel at
  audit).
- **The Phase 2 lever is off-site.** On-site work has done what it can; the remaining
  points are getting into the lists Claude and Perplexity cite and linking the
  reputation to the entity. This is where the reviewer/UGC panel fits.
