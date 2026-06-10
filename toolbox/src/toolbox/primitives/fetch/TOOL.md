# fetch — pull web sources into the run folder (read-only)

No connection needed. Reddit subreddit URLs are fetched via their public .json endpoints.

## fetch.urls
- in: CSV with a `url` column → out: pages.jsonl ({url,status,text[,error]})
- flags: `--concurrency 8`, `--max-chars 20000`
- failures are recorded per-row (status 0 + error), never crash the sweep
