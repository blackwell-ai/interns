# ai-visibility-audit

**Purpose:** produce the house AI Visibility Audit, the format delivered to Public
Goods, Good Molecules, Husqvarna, and Atlas. It grades a storefront on five
AI-behavior dimensions, benchmarks it against named competitors, shows real
evidence (AI-engine outputs, review quotes, schema snippets), and ships as a
branded PDF. Canonical length is 10 to 19 pages in the repo's sans-serif,
black-on-white house style. See [[audit-methodology]] for the underlying nine-phase
method. A condensed four to five page variant exists for fast leave-behinds
(`agents/geo/atlas/atlas-audit.html`), but the heavy format is canonical.

**When to use:** a warm prospect or discovery conversation with an e-commerce
storefront (Shopify especially). Every finding must be externally reproducible
with public tools, which is what makes it safe to send.

**Inputs:** target domain, two or three competitor domains, contact email, and any
owner context (stated concerns, paid-ads plans, named competitors). Fold the
context in; the Atlas run added a paid-readiness section because the owner asked
about Meta ads.

**No secrets needed.** Everything is public-surface recon over HTTPS.

## The five dimensions (score 0 to 100, simple-average composite)

- **Discoverability**: entity presence, agent discovery files, crawler access, third-party listings
- **Quotability**: schema depth, structured product and policy data, accuracy in machine-readable form
- **Recommendability**: inclusion in AI category answers and the listicles engines cite
- **Transactability**: UCP and MCP endpoints, payment handlers, agent-readable pricing
- **Reputation**: review-aggregator presence and rating, sentiment, links from the entity to that reputation

Grading scale: A 90+, B 75 to 89, C 60 to 74, D 50 to 59, F below 50. Estimate
competitor scores from the same public signals and label them as estimates.

## Steps

1. **Technical truth table.** Run `./recon.sh <domain>` for the target and each
   competitor: title/meta/h1/og, homepage and product JSON-LD `@type`s, robots and
   llms.txt state, product/collection/blog counts from the sitemaps, the pixel
   stack, and the UCP endpoint. Capture raw numbers; every technical claim traces
   back to one.
2. **AI behavior and recommendability.** Run web-search-backed category and brand
   queries ("best <category> shops <region>", "best online <category> shops",
   "where to buy <brand>"). Record which shops are named, which sources are cited,
   and whether the client appears in the listicles those engines pull from. This
   is the flagship evidence and what the WebSearch tool returns is itself a
   retrieval-AI answer, so quote it honestly.
3. **Reputation corpus.** Pull the client's Yelp, Birdeye, and Google ratings and
   review counts, official-dealer or directory listings, and sentiment, then check
   whether any of it is linked to the site entity via `sameAs`. Yelp and Trustpilot
   often 403 a bot; the rating usually still comes back through search snippets.
4. **Adapt `template.html`** (the heavy house style: sans-serif black-on-white
   cover, AI Visibility Scorecard with competitor columns and a red grade card,
   "the short version" with numbered findings and a dark callout, findings
   worst-first with real AI-output boxes and review quotes, optional
   paid-readiness section, competitive position, two-phase $1,000 close with
   benchmarks, methodology section, repeated page footer). Replace all copy,
   numbers, and evidence with this client's verified recon.
5. **Render to PDF** with headless Chrome:
   `"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless \
   --disable-gpu --no-pdf-header-footer --run-all-compositor-stages-before-draw \
   --virtual-time-budget=8000 --print-to-pdf=out.pdf file://$PWD/audit.html`.
   WeasyPrint is the documented renderer but needs pango/cairo native libs and
   failed to import here even after `brew install pango cairo gdk-pixbuf`, so Chrome
   is used. The cover needs `break-after:page`; the footer is a `position:fixed`
   element Chrome repeats on every page.
6. **Verify before shipping.** Two hard gates:
   - Dash scan (CLAUDE.md Writing rule): the HTML source and the extracted PDF text
     must each contain zero em or en dashes. Scan with
     `python3 -c "t=open('audit.html').read();print(sum(t.count(c) for c in [chr(0x2014),chr(0x2013)]))"`
     (and the same over `pdftotext out.pdf -`); both must print 0.
   - Visual QA: rasterize with `pdftoppm -png -r 100 out.pdf qa` and read every page
     for overflow, collisions, broken color fills, and bad page breaks. Use
     `print-color-adjust: exact` so backgrounds print.
7. **Place and record.** PDF to `brain/customers/documents/<client>-audit.pdf`,
   working HTML under `agents/geo/<client>/`, durable findings to
   `brain/customers/<client>.md`. Mirror state into Notion Tasks if interactive.

## Acceptance checks

- Zero em or en dashes in the HTML source and the extracted PDF text.
- Every technical claim traces to a same-day recon command; every AI-behavior and
  reputation claim is reproducible by re-running the same public query.
- Competitor cells are verified the same day, not asserted from memory or a prior
  deck.
- The deck renders with nothing overflowing or colliding (the cover needs its own
  page break).

## Worked example

Atlas Skateboarding, June 16, 2026: see [[atlas]] and `agents/geo/atlas/`.
Composite 44 (F) against a competitive set averaging ~79. Flagship finding:
asked for the best Bay Area skate shops, AI answer engines named the sibling shop
DLX, FTC, SF Skate Club, and others, but never Atlas. Reputation is the top
dimension (4.8 stars, 115 reviews) yet stranded off any machine-readable entity.
The heavy deck is `atlas-ai-visibility-audit.html`; a condensed four-page variant
of the same findings is `atlas-audit.html`.
