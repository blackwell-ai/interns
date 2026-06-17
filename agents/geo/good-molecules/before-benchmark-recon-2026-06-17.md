# Good Molecules before-benchmark recon, June 17, 2026

Prepared for the first weekly check-in. This is a passive-recon re-check run today,
after the team told us they made two changes since the audit. It confirms what
landed and sets up a clean before/after for the remaining work. It is not yet the
live engine battery, which is the real before/after proof and comes next.

Reference: the June 1 audit (composite D, 61) with eight findings, two of them
Critical. The two Critical findings were (1) AI assistant crawlers blocked at the
WAF, so ChatGPT, Claude, Perplexity, and Copilot answered from Amazon, Ulta,
Target, and Reddit instead of the site, and (2) no server-side structured data, so
engines could not read prices from goodmolecules.com (Claude said verbatim it could
not pull prices and fell back to Amazon).

## What you told us, and what recon confirms

You noted two changes. Both are verifiably live as of this morning. Recon was run
with curl using each crawler's published user-agent against the production site.

### 1. WAF rules, confirmed live for the major assistants

The crawlers that were blocked at audit now return HTTP 200:

| Crawler (user-agent) | Audit | June 17 |
| --- | --- | --- |
| GPTBot | blocked | 200 |
| OAI-SearchBot | blocked | 200 |
| ChatGPT-User (live fetch) | blocked | 200 |
| ClaudeBot | blocked | 200 |
| Claude-User (live fetch) | blocked | 200 |
| PerplexityBot | blocked | 200 |

This is the single biggest finding from the audit, and the fix is in. The exact
agents that power ChatGPT and Claude browsing can now reach the site.

Two things still worth a look on your side:

- Perplexity-User, the agent Perplexity uses for live fetches, still returns 405.
  PerplexityBot (the indexer) is allowed, but the live-answer fetch is not. If
  Perplexity coverage matters, that one user-agent needs the same allowlist entry.
- Spoofed Googlebot and Bingbot user-agents return 405. That is likely the WAF
  correctly rejecting unverified search-bot strings, since anyone can spoof them,
  and the real verified crawlers may still pass. But search-index surfaces
  (Google AI Mode, AI Overviews, Bing) were your one working channel at audit, so
  we should confirm the verified Googlebot and Bingbot are not caught before we
  call the WAF settled.

### 2. Server-side structured data, confirmed live

Product pages now serve full JSON-LD in the raw server HTML, no JavaScript needed.
On the Niacinamide Serum and Discoloration Correcting Serum PDPs we see:

- `Product` with `Brand`
- `Offer` with `price`, `priceCurrency: USD`, `availability: InStock`
- `AggregateRating`

This is the direct fix for Critical Finding 02. Prices are now machine-readable on
your own page. The canonical PDP also resolves to a size-specific URL (for example
the niacinamide serum lands on the 30ml page at $6.00), which addresses the
12ml-versus-30ml price-confusion finding from the audit.

### Bonus: llms.txt is now live

Not on your list, but worth calling out. A real `llms.txt` is now served, with a
brand overview, best sellers, shipping terms, category map, and a full product
list with prices and descriptions. At audit this file was effectively absent. This
is a meaningful step on its own.

## What this means for the benchmark

You have already remediated the two heaviest findings before we captured a clean
baseline. That is good for the site and it changes how we should run the
before/after. The June 1 audit was a "fully blocked" before. The useful before to
measure our remaining work against is the live state today: crawlers open, schema
present, llms.txt live. We capture how the engines actually answer now, then re-run
after the remaining work and measure the delta.

The HTTP 200s and the JSON-LD prove the engines now *can* read the site. They do
not yet prove the engines *do* quote it correctly and recommend the brand in live
answers. That is the live engine battery against the frozen truth table, headed
browser, run by hand across the engines. That battery is the real before benchmark
and it is the next step.

## Remaining scope (still open as of today)

Confirmed absent by curl this morning (404 to an allowlisted crawler, so genuinely
missing, not a block):

- llms-full.txt (the deep version; the short llms.txt is live)
- agents.md
- /.well-known/ agentic-commerce endpoints (UCP, ai-plugin), all 404
- sitemap.xml, 404, no sitemap is served, which is a discoverability gap

Plus the off-site and recommendability work from the audit (absence from the
listicles, the comparison against The Ordinary), which is content and outreach, not
a file fix.

## Suggested talking points for the call

- Their two changes are in and we verified them this morning, with the WAF fix
  being the headline win. Show the crawler table.
- They also shipped a strong llms.txt, more than they flagged.
- Two small WAF follow-ups: Perplexity-User and confirming verified Googlebot and
  Bingbot still pass.
- Next step is the live engine battery as the real before benchmark, then the
  remaining files (llms-full.txt, agents.md, well-known endpoints, sitemap) and the
  off-site recommendability work.

Recon method: curl with each crawler's published user-agent against
www.goodmolecules.com, following redirects, June 17, 2026. Status codes and JSON-LD
read from raw server responses.
