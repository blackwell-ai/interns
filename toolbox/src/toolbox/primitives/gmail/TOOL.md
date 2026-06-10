# gmail — send mail, read replies/bounces

Send-class primitive: the ledger claim is **inside** `send` and cannot be
composed away. Connection: `toolbox auth connect gmail` (the SENDING account —
armaan.priyadarshan.29@dartmouth.edu per brain/company/connections.md).

## gmail.send
- in: outbox CSV — `email,subject,body[,body_html,…]` (extra columns ignored)
- flags: `--from` (required), `--from-name`, `--reply-to`, `--cc` (comma-separated,
  added to every send — the co-founder CC convention), `--concurrency` (8),
  `--limit N`, `--allow-recontact` (loud, deliberate follow-ups only), `--dry-run`
- per recipient: claim → send → mirror(`runs/<id>/ledger.jsonl`) → mark_sent.
  Already-contacted → skipped; suppressed → never sent, no override.
- dry-run: writes `dryrun/gmail.send.json` with each row + its ledger status; no claims, no sends.
- failure modes: hard quota (daily cap) → step fails cleanly (resume later);
  invalid recipient → marked failed + suppressed from retry; transient → backoff.
- resume: rows whose recipient is `sent` in the run's mirror are skipped.

## gmail.replies
- in: CSV of contacted people (`email` column); flags: `--since-days`, `--out`,
  `--classify/--no-classify`, `--file-inbox-tasks` (positive replies → inbox/queue/ tasks)

## gmail.bounces
- finds mailer-daemon failure notices, marks recipients failed + suppressed; out: bounces.csv
