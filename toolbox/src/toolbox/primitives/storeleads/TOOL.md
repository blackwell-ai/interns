# storeleads — e-commerce store search (storeleads.app)

Connection: `toolbox auth connect storeleads` (API key).

## storeleads.search
- out: domains.csv (`domain,company,source,segment`) compatible with apollo.enrich
- flags: `--platform shopify`, `--category`, `--country US`, `--count`, `--segment <label>`
- failure modes: 429/5xx → backoff retry
