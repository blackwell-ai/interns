# Hunter find-exec yield: curated brands ~75-100%, web-sourced long-tail ~18%

The `findemail.find-exec` (domain -> top exec) yield is set by how well Hunter's
Domain Search covers the domain, which tracks brand size, not the sourcing method.

Two runs, same pipeline, very different yields:

| Run | Domains | Execs found | Net sendable | Yield |
|---|---|---|---|---|
| 2026-06-10 curated (hand-picked known DTC brands) | 224 | ~180 | 169 | ~80%, founder addresses ~100% |
| 2026-06-16 web-sourced (`domains.source` long tail) | 800 | 149 | 140 | 18.6% |

Why the gap: `domains.source` surfaces a long tail of small and new brands.
Hunter has no executive on file for most tiny brands, so find-exec returns
nothing. A miss still costs 1 credit. The curated list was implicitly
pre-filtered to brands big enough to be in Hunter's database; the well-known
names in the web-sourced batch (Manscaped, Olaplex, SKIMS, Le Creuset) are
exactly the ones that hit.

## Planning a target send count N

- From curated/known brands: budget ~1.3-1.5 domains (and credits) per send.
- From raw web-sourced domains: budget ~5-6 domains (and credits) per send.
- A real 500 from cold web-sourced domains needs ~2,800 credits at this yield,
  which is more than a Hunter Starter month (2,000). To actually hit a high target:
  (a) bias sourcing toward larger/funded brands (Series A+, Shopify Plus, Inc
  5000) so coverage is high, (b) spread the send across Hunter billing cycles, or
  (c) upgrade the plan. Decide this before sourcing, not after spending credits.

## Operational notes

- The Hunter budget, not the domain supply, is the binding constraint on volume.
  `domains.source` is free (claude-CLI web search) and produced 1,068 fresh
  domains in one pass; enrichment is what costs.
- `find-exec --cache enrichment_cache.jsonl` caches both hits and misses, so the
  651 no-exec domains from this run are free to re-query. Only new domains cost.
- Always run a small canary (3 sends) before releasing the full queue. send_fast.py
  claims each recipient in suppression before sending, so a systemic send failure
  would otherwise claim-and-burn the whole queue without a single delivery.

See also `06-named-individual-sourcing-for-findemail.md` (verify rates by domain
hygiene) and `brain/decisions/2026-06-10-clay-not-headless-findemail-primitive.md`.
