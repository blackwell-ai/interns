# apollo-cold-email

The spec §10 worked example: *"fetch N domains related to X, find their emails
on Apollo, fill a template, send."* Full default chain (new skill touching the
world): clarify → source → enrich → verify → compose → smoke → dryrun → canary
→ send → report.

## Purpose

Cold outreach to a segment from `brain/company/targets.md`, end to end, same
day. Pure-parameter variations should **rerun** this skill with different
inputs (`-i segment=...`), not fork it. Fork when the step list itself changes.

## Inputs

See `inputs.yaml` — every field pre-filled; `clarify.ask` presents them once.
`from_account` must stay the Dartmouth cold-email account per
`brain/company/connections.md` (the gmail account is reserved for YC).

## Steps

1. `clarify.ask` — one review pass over inputs.
2. `domains.source` — web-search domain sourcing for `{{segment}}`.
3. `apollo.enrich` — people matching `{{contact_roles}}` + their emails.
4. `verify.check` — MX/DNS; undeliverables dropped.
5. `compose.render` — template + LLM `{{personalization_hook}}` per contact;
   rows with no concrete hook are dropped (no generic blasts — charter rule).
6. `test.smoke` — offline tests of every primitive used here.
7. `test.dryrun` — render 10, grade against the acceptance checks below.
8. `canary.run` — 10 live + seed copies to our own inbox, then a human gate.
9. `gmail.send` — the full send, `concurrency: 8`; the ledger guarantees
   no person is contacted twice, ever, across anyone's runs.
10. `report.write` — report + changelog + INDEX refresh.

## Acceptance checks

- Every rendered message has a non-empty subject and body.
- No unresolved `{{slot}}` placeholders survive rendering.
- Every `personalization_hook` names something concrete about the recipient
  (store, role, company) — empty hooks must have been dropped, not sent.
- From address is the Dartmouth account; never the gmail account.

## Changelog
