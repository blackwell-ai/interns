# findemail — find + verify a work email from a name + domain

Apollo-backed lead enrichment: name + domain → verified work email, or domain →
decision-maker + email. Apollo is the only provider as of 2026-06-18 (see
`brain/decisions/2026-06-18-apollo-only-outbound.md`); the Hunter and Findymail
adapters were removed.

Connection: `toolbox auth connect apollo` — API key. No key in argv or the
repo; fetched at runtime via core/auth.

## findemail.find
- in: candidates CSV with `domain` + (`first_name`,`last_name`) or `name`
  (plus any passthrough columns, e.g. brand, title)
- out: contacts CSV (email, first_name, last_name, domain, email_score,
  email_status, + passthrough) — ready for verify.check / compose.render
- flags:
  - `--min-score 80` — drop emails below this confidence
  - `--concurrency 10`
- Rows with no email found, or below `--min-score`, are dropped and logged —
  never guessed. Transient errors (429/5xx) back off and retry.

## findemail.find-exec
- in: domains CSV → out: one decision-maker contact per domain (Apollo people
  search, ranked by seniority), with the same verified-email guarantee.
- `--cache file.jsonl` = every domain billed once, ever (hits and misses
  cached; re-runs and a growing lead bank are free).

## Provider
- **apollo** — `api.apollo.io` people match + search → email + confidence +
  verification status. Exact filters and credit model are pending Armaan's
  Apollo directions.

## Composes with
`domains.source` / web-sourced brand lists → findemail.find → verify.check →
compose.render → gmail.send.
