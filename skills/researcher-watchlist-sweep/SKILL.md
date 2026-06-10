# researcher-watchlist-sweep

The spec §11 M4 breadth proof: the researcher's watchlist sweep as a flow —
`fetch sources → llm filter → file inbox tasks` — running on the exact same
runner and primitives as outreach. This is brain infrastructure, not an
outreach feature.

## Purpose

Sweep the researcher watchlist sources, filter hard ("would a human act on
this?"), and file what clears the bar as `inbox/queue/` tasks addressed to a
human. Read-only in the outside world (researcher charter guardrail) — no
send-class steps, so no clarify/canary in the chain.

## Inputs

- `sources_csv` — CSV with a `url` column. `sources.csv` here is a snapshot of
  `agents/researcher/watchlist.md`; update both together.
- `relevance_bar` — the plain-English filter criteria handed to `llm.filter`.

## Steps

1. `fetch.urls` — pull each source (Reddit via public .json endpoints).
2. `llm.filter` — strict relevance judgment + 1–2 sentence summary each.
3. `inbox.file` — one task per finding, per the inbox/TEMPLATE.md shape.
4. `report.write` — run report + changelog.

## Acceptance checks

- Every filed task names why it matters to Blackwell specifically (the
  `reason` field), not a generic summary.
- Sources that fail to fetch are recorded in pages.jsonl with an error, never
  silently dropped.

## Changelog
