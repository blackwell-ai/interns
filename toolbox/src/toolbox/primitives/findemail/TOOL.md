# findemail — find + verify a work email from a name + domain

The headless equivalent of Clay's "find work email" enrichment. Clay exposes
no API to drive its enrichment recipe (the waterfall lives in a UI-configured
table), so this primitive calls the same underlying providers directly.

Connection: `toolbox auth connect hunter` (or `findymail`) — API key.
No key in argv or the repo; fetched at runtime via core/auth.

## findemail.find
- in: candidates CSV with `domain` + (`first_name`,`last_name`) or `name`
  (plus any passthrough columns, e.g. brand, title)
- out: contacts CSV (email, first_name, last_name, domain, email_score,
  email_status, + passthrough) — ready for verify.check / compose.render
- flags:
  - `--provider hunter|findymail` (default hunter)
  - `--min-score 80` — drop emails below this confidence (Hunter 0–100 score)
  - `--concurrency 10`
- Rows with no email found, or below `--min-score`, are dropped and logged —
  never guessed. Transient errors (429/5xx) back off and retry.

## Providers
- **hunter** — `GET api.hunter.io/v2/email-finder` → email + score + verification.status (1 credit/call)
- **findymail** — `POST app.findymail.com/api/search/name` → only returns verified/deliverable emails

## find-exec credit efficiency (Hunter bills per result returned)
- Default `--per-domain 10` + executive filter = **1 credit/domain**.
- `--thorough` = limit 25, no seniority filter = **3 credits/domain**, but a
  lower-confidence founder won't be cut off (founder-to-founder precision).
- `--cache file.jsonl` = every domain billed **once, ever** (hits + misses
  cached; re-runs and a growing lead bank are free). See harness/learnings/05.

## Composes with
`domains.source` / web-sourced brand lists → findemail.find → verify.check →
compose.render → gmail.send. This is the Clay-replacement sourcing path.
