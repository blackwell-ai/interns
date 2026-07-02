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

## How to run it: the same program every time

This is a fixed nine-phase program, not a menu. Run every phase, in order, for
every audit. Each phase writes an artifact to `agents/geo/<client>/`, and
`./verify-evidence.sh agents/geo/<client>` must print PASS before the deck ships.
The gate exists because past runs skipped the live battery and wrote prose
instead. Do not narrate a phase you did not run.

**Hard prohibition.** The `WebSearch` tool, `web_search`, and "web-search-backed
retrieval" are NOT the AI engine battery and never substitute for it. Phase 5 is
real browser sessions against the six named engines through `/browse`, captured to
PNGs. An audit whose recommendability rests on WebSearch output is invalid, full
stop. If `/browse` cannot reach an engine, that is a documented limitation in
`battery-log.md`, not a reason to fall back to WebSearch.

### Phase 1+2. Truth table and crawlability (frozen first)

Run recon for the target and EACH competitor, before any engine query:

```
./recon.sh <domain> [product-handle] | tee agents/geo/<client>/recon-<YYYY-MM-DD>.md
```

`recon.sh` now covers phase 1 (title/meta/h1/og, homepage and product JSON-LD
`@type`s, robots/llms.txt, sitemap counts, pixel stack) and phase 2 (the agentic
layer probe over `/agents.md`, `/.well-known/ucp`, `/api/ucp/mcp`,
`sitemap_agentic_discovery.xml`, and the AI bot-UA crawlability matrix: GPTBot,
OAI-SearchBot, ClaudeBot, PerplexityBot, Google-Extended, Amazonbot, Bingbot).
Every technical claim in the deck traces back to a line in this file.

### Phase 3. Reputation corpus (live, captured)

Drive `/browse` through this FIXED source list and screenshot each to
`agents/geo/<client>/assets/reputation-<source>-<YYYY-MM-DD>.png`. The gate
requires all six: **Trustpilot, BBB, ConsumerAffairs, Reddit, YouTube, and
retailer** (the retailer the brand actually sells through: Amazon, Sephora, Ulta,
Sally Beauty, and so on; name it in the filename, for example
`reputation-retailer-amazon-...`). Record each rating, review count,
claimed/unclaimed status, and the sentiment split in `reputation-<YYYY-MM-DD>.md`.
A source with no profile gets an explicit `N/A` line naming the source in that file
(the gate accepts a documented N/A; it does not accept silence). Then check whether
the site entity links to any of it via `sameAs` in the recon output. Cloudflare or a
login wall is handled with headed stealth or an in-app view, not skipped.

### Phase 5. Two-pass AI engine battery (the flagship evidence)

Six engines, two passes each, through `/browse` in headed mode (`--headed`, which
clears most Cloudflare walls with stealth). Engines: ChatGPT, Perplexity, Gemini,
Claude, Google AI Overview, Microsoft Copilot.

- **Pass A, browsing OFF** (parametric / from-memory): the engine answers from
  training, web tool disabled. Shows whether the brand exists in the model's
  priors.
- **Pass B, browsing ON** (forced web retrieval): the live category answer.

**Incognito / clean profile is mandatory where the profile is logged in.** A
logged-in account carries Memory and search history that biases the engine toward
brands you searched before, which silently inflates recommendability. Before each
engine, use its in-app private mode: ChatGPT Temporary Chat, Perplexity Incognito
(account menu), Copilot/Gemini a fresh chat with personalization/memory off. If an
engine has no private mode and is logged in, note it in `battery-log.md` and read
the result as contaminated.

Queries are fixed per audit and written down: the category query ("best <category>
for <use case> <year>"), one or two adjacent category queries, and a brand-defense
query ("<brand> vs <competitor>"). Run the SAME query string on every engine.

Capture every engine and pass to
`assets/<engine>-<query-slug>-<pass>-<YYYY-MM-DD>.png`, where `<engine>` is one of
`chatgpt perplexity gemini claude googleaio copilot` and `<pass>` is `on` or
`off`. Log each row in `battery-log.md`: engine, pass, incognito yes/no, query,
whether the client and each competitor was named, sources cited, timestamp. Where
an engine refuses a pass (for example a logged-out engine that will not disable
browsing), write the limitation in `battery-log.md`; the gate accepts a documented
limitation but not a missing row.

Saving the captures (learned 2026-06-30). The browser tool's in-app screenshot
`save_to_disk` does not reliably persist a file you can reach from the shell, so drive
the engine through `/browse` to read and verify the answer, then save the PNG with
macOS `screencapture`. The working recipe: an AppleScript that makes the driven tab
active in its Chrome window and raises that window (`set active tab index`, then `set
index ... to 1`), read the window bounds, and `screencapture -x -R x,y,w,h out.png`.
Two gotchas: coercing bounds with `as string` concatenates the numbers with no
separators (build the comma list by item instead), and if the Chrome window is on a
different macOS Space than the one on screen, `screencapture` returns "could not create
image from rect" (bring that window to the front first). A guest engine can throw a
"verify you are human" check; completing bot-detection is off limits, so have the
operator clear it, then capture.

What each engine actually supports (learned, keep current):

- **ChatGPT**: Temporary Chat (`chatgpt.com/?temporary-chat=true`) is a true clean
  session. Both passes work; tell it "without searching the web" for the off pass
  and "search the web" for the on pass.
- **Perplexity**: Incognito lives in the account menu (button label starts "Use
  incognito"). It still always retrieves, so treat it as ON-only and document the
  OFF pass as N/A.
- **Claude**: no incognito mode exists. A fresh `claude.ai/new` chat is the cleanest
  available; both passes work via the "without searching" / "search the web" prompt.
- **Gemini**: no clean private mode in practice. If the profile is logged in and has
  prior searches for the brand, the read is contaminated; report it as unmeasured
  rather than counting it.
- **Copilot**: runs as a guest (no login), so it is clean by default but ON-only.
- **Google AI Overview**: always web-grounded (ON-only), and **non-deterministic**.
  The same query the same day can return the brand in one render and omit it in
  another. Capture it, and if the brand's presence varies, say "in some renders"
  rather than asserting a stable win or loss.

Note that absence is robust to contamination but presence is not: a logged-in
profile biases toward naming brands it has seen, so "absent despite a logged-in
profile" is conservative, while "named on a logged-in profile" must be re-checked
clean before you trust it.

### Phase 6. Competitor recon and scorecard

Run `recon.sh` on each competitor the same day and save the combined output to
`agents/geo/<client>/competitors-<YYYY-MM-DD>.md` (the gate requires at least two
competitor recon blocks in that file). Grade all five dimensions against the FROZEN
truth table from phase 1, never against anything an engine said. Competitor cells
are estimates from the same public signals, labeled as estimates.

### Phase 7-8. Deck and PDF

Adapt `template.html` (sans-serif black-on-white cover, AI Visibility Scorecard
with competitor columns and a red grade card, "the short version" with numbered
findings and a dark callout, findings worst-first with real AI-output boxes and
review quotes, optional paid-readiness section, competitive position, two-phase
$1,000 close, methodology section, repeated footer). `template.html` is the single
canonical format; do not fork a second house style.

The Recommendability finding (finding 1) is built around the **engine-results
table** the template now ships: one row per engine, two columns (from-memory and
live-retrieval), `pill no` (red) for not named and `pill yes` (green) for named,
filled directly from `battery-log.md`. Below it, embed the matching capture with
`<img class="eviv" src="assets/<engine>-<query-slug>-<pass>-<date>.png">` plus a
`<p class="cap-img">` caption, and quote the live answer in an `.ai`/`.resp` box.
Every AI-output box and review quote embeds or links its capture from phases 3 and
5; a claim with no screenshot does not ship. Replace all copy, numbers, and
evidence with this client's verified recon, and write the methodology section to
describe the real six-engine two-pass battery, never "web-search-backed retrieval".

**Standard Phase 2 service to include in every deck.** The "The work" / Phase 2
section names Blackwell's creator panel as one of the ongoing services: a vetted
panel of independent reviewers and UGC creators, scored for neutrality (built from
the `platform/` social-proof pipeline), that seeds genuine third-party reviews of
the client's product across YouTube, Reddit, and short-form video. Frame it as a
capability we are standing up for Phase 2 design partners, not a finished network,
and tie it to why it matters: off-site mentions are the strongest correlate of AI
visibility and are the part of reputation that on-site schema fixes cannot move.
Keep the wording honest to the current state (see [[reviewer-ugc-panel]]); do not
claim a guaranteed product send or a specific headcount the panel cannot yet back.

Render with headless Chrome or Chromium (WeasyPrint is the documented renderer but
needs pango/cairo native libs that are often missing, so Chrome/Chromium is the
working path; the binary is `google-chrome` on macOS and often `chromium` on
Linux):
`chromium --headless --disable-gpu --no-pdf-header-footer
--run-all-compositor-stages-before-draw --virtual-time-budget=8000
--print-to-pdf=out.pdf file://$PWD/audit.html` (the GPU/vaInitialize warnings are
harmless). Relative `assets/...` image paths resolve against the HTML file's own
directory, so render in place. The cover needs `break-after:page`; the footer is a
`position:fixed` element repeated on every page; use `print-color-adjust: exact` so
backgrounds and pills print. A full-width embedded capture often flows to the next
page, which is fine.

### Phase 9. Verify, place, record

Three hard gates, all must pass:

1. **Evidence gate:** `./verify-evidence.sh agents/geo/<client>` prints PASS. This
   is the anti-shortcut gate; a FAIL lists the exact artifact missing.
2. **Dash scan:** the HTML source and the extracted PDF text each contain zero em
   or en dashes.
   `python3 -c "t=open('audit.html').read();print(sum(t.count(c) for c in [chr(0x2014),chr(0x2013)]))"`
   and the same over `pdftotext out.pdf -`; both print 0.
3. **Visual QA:** rasterize with `pdftoppm -png -r 100 out.pdf qa` and read every
   page for overflow, collisions, broken fills, and bad page breaks.

Then place: PDF to `brain/customers/documents/<client>-audit.pdf`, working HTML and
`assets/` under `agents/geo/<client>/`, durable findings to
`brain/customers/<client>.md`, and post the draft location to `inbox/queue/` for
human sign-off (no deck reaches a customer without it). Mirror state into Notion
Tasks if interactive.

## Acceptance checks

- `./verify-evidence.sh agents/geo/<client>` prints PASS (recon, reputation
  captures, and all six engines with an ON capture plus an OFF capture or a
  documented limitation).
- Recommendability rests on phase-5 browser captures, never on the WebSearch tool.
- Engine sessions used in-app incognito where the profile was logged in, or the
  contamination is disclosed in `battery-log.md` and the deck.
- Zero em or en dashes in the HTML source and the extracted PDF text.
- Every technical claim traces to a same-day recon line; every competitor cell is
  verified the same day, not asserted from memory or a prior deck.
- The deck renders with nothing overflowing or colliding.

## Worked example

Atlas Skateboarding, June 16, 2026: see [[atlas]] and `agents/geo/atlas/`.
Composite 44 (F) against a competitive set averaging ~79. Flagship finding:
asked for the best Bay Area skate shops, AI answer engines named the sibling shop
DLX, FTC, SF Skate Club, and others, but never Atlas. Reputation is the top
dimension (4.8 stars, 115 reviews) yet stranded off any machine-readable entity.
The heavy deck is `atlas-ai-visibility-audit.html`; a condensed four-page variant
of the same findings is `atlas-audit.html`.
