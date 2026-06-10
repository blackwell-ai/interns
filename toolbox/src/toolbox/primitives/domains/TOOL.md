# domains — web-search domain sourcing (Anthropic web_search tool)

Connection: ANTHROPIC_API_KEY (or anthropic connection). Two-stage: LLM drafts
search queries, each query web-searches + structured-extracts company domains.

## domains.source
- out: domains.csv (`domain,company,source,segment`); dedup + canonicalization here,
  deliverability is verify.check's job
- flags: `--query "<segment>"`, `--count`, `--exclude "amazon,etsy"`, `--concurrency 4`, `--model`
