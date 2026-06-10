# apollo — people search + enrichment (api.apollo.io)

Connection: `toolbox auth connect apollo` (API key; use --org-shared for the team key).

## apollo.enrich
- in: domains.csv (`domain,company,…`) → out: contacts.csv (`email,first_name,last_name,name,title,company,domain`)
- flags: `--roles "founder,ceo,owner"`, `--per-company 2`, `--concurrency 20`
- locked/placeholder emails are dropped (Apollo returns fakes for unrevealed emails)
- failure modes: 429/5xx → backoff retry; other 4xx per domain → logged + skipped
