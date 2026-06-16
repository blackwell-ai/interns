# fetch: pull web sources into the run folder (read-only)

No connection required. Reddit is read via its public Atom feed; everything else
(e.g. the HN Algolia API) is fetched plainly.

## fetch.urls
- in: CSV with `url` (and optional `label`) columns → out: pages.jsonl
  ({url, label, status, text[, error]})
- flags: `--concurrency`, `--max-chars`, `--limit 25` (items per Reddit listing)
- Reddit: read the public `.rss` Atom feed (no key). Reddit IP-blocks `.json`
  and its API now needs pre-approval (Responsible Builder Policy, Nov 2025), but
  the Atom feed is not gated. It works from a **residential IP only**; cloud IPs
  get 403/429, so run the cron on a residential machine. Reddit rate-limits
  anonymous reads hard, so fetch Reddit with `--concurrency 1` and a high
  `--max-chars` (feeds are 60-150KB; truncated XML will not parse).
- failures are recorded per-row (status 0 + error), never crash the sweep.

## Optional: authenticated Reddit (if you get API approval)
If Reddit grants API access, store the app secret and `fetch` will switch to
`oauth.reddit.com` (app-only, ~100 req/min, works from any IP):
- interactive: `toolbox auth connect reddit`, secret = `client_id:client_secret`
- cron: `TOOLBOX_TOKEN_REDDIT=client_id:client_secret` in `credentials/.env`
  (a non-interactive session cannot reliably read the keychain).
