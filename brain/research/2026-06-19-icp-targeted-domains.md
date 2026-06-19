# ICP-targeted domain pool for /campaign (2026-06-19)

Source: Armaan asked for a properly-targeted domain list to the icp_mix ratio,
replacing the campaign's LLM domain generation, which had been producing generic
household brands the ICP explicitly excludes (Glossier, Skims, Allbirds, etc.).

## What was built

193 web-verified, ICP-filtered company domains across the six icp_mix segments,
saved to `skills/campaign/target_domains.csv` (columns: domain, segment). Built
by six parallel research agents, each running web searches across funding press,
category directories, and accelerator cohorts, then verifying each live domain
before inclusion.

| Segment | Domains |
|---|---|
| DTC brands and retailers | 83 |
| 3PL and warehouses | 35 |
| Manufacturing | 35 |
| Agent transaction companies | 16 |
| Shopping agent companies | 12 |
| Inventory management systems | 12 |

ICP adherence: US-based, physical-product for DTC, founder-led or reachable,
roughly $1M to $200M, and deliberately not the household names. DTC spans
apparel, food and CPG, beauty, outdoor, and home.

## How it is wired

The mix mode in `skills/campaign/run.py` (`_source_from_mix`) now reads the
curated pool per segment from `target_domains.csv` instead of generating domains
with `claude -p`. Domains are shuffled per segment for category diversity, then
enriched by `apollo_source` until the segment's contact quota is hit or the pool
runs out. A segment with no curated domains falls back to LLM generation.

## Caveats

- The niche segments (agentic commerce, shopping agents, inventory) are emerging
  spaces with few companies and small teams, so they cannot fully fill their
  icp_mix quotas. A 1000-contact run at the strict ratio realistically yields
  about 750 to 850 quality contacts rather than a padded 1000.
- `basistheory.com` was pulled from the agentic list: Armaan is already in their
  Agentic Commerce Consortium, so it is a warm relationship, not cold outreach.
- The researchers flagged a couple of transitional storefronts to spot-check
  before sending; the campaign's bounce suppression covers the rest.

## Refresh

Re-run the six per-segment research agents to top up or refresh the pool. The
contact ledger dedupes per person, so re-running the campaign against the same
pool skips anyone already contacted.
