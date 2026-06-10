# AI visibility audit methodology & delivery infrastructure

Last updated June 10, 2026. Source: founder-provided canonical context.

> This is Blackwell's core repeatable flow. Candidate for codifying as a
> step-by-step skill in `skills/ai-visibility-audit/` once an agent runs one
> end-to-end.

## The audit methodology

Blackwell developed a repeatable nine-phase AI visibility audit with a
five-dimension scorecard (Discoverability, Quotability, Recommendability,
Transactability, Reputation), delivered as professional 14 to 22 page
WeasyPrint-rendered PDF decks in a consistent house format.

In brief: freeze a truth table from the brand's own site before querying any
engine; run passive recon (crawlability, bot-UA testing via curl, schema
validation); analyze the entity and reputation corpus (Reddit, YouTube,
Trustpilot, BBB, retailer listings); run a two-pass AI prompt battery across six
engines (browsing off, then forced on), using headed Chromium with stealth mode
and imported session cookies where needed; probe agentic commerce readiness
(UCP endpoints, structured feeds); grade against the frozen truth table.

## Technical work and infrastructure built

- Audit production pipeline: HTML decks rendered to PDF with WeasyPrint,
  validated with pypdf, visually checked via pdftoppm rasterization
- Word document generation with docx (22-page validated documents with custom
  tables, score bars, embedded screenshots)
- Browser automation for live AI engine testing: headed Chromium with stealth
  mode, session cookie import, two-pass prompt batteries captured to
  spreadsheets with timestamps
- Engagement letter templating with embedded fonts and e-signatures

The G&M Liquor engagement letter is the house template for subsequent letters
(one-page format, embedded script signature, mechanism-focused AI assistant
pilot section) — see [[gm-liquor]].
