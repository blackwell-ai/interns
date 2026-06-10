# clay-cold-email

**Purpose:** the canonical cold-email flow. Take a Clay lead list, verify
deliverability, personalize from enrichment data, and send from the
cold-email account — with the full trust chain (clarify → dryrun → canary)
until proven.

**Inputs:** see `inputs.yaml`. The one that matters: `leads_csv`, a Clay
export with at least `email,name,company` — richer enrichment columns make
better hooks. Sourcing/enrichment happens **in Clay** (the lead workbench,
decision 2026-06-10); this skill starts where Clay ends.

**Credentials:** gmail via `toolbox auth connect gmail` (must be the
Dartmouth account — see `brain/company/connections.md`). Personalization runs
on headless Claude Code (no key needed).

## Steps

1. `clarify.ask` — one review pass over the pre-filled inputs.
2. `verify.check` — MX/DNS checks; unverified rows are dropped.
3. `compose.render --personalize` — renders `template.md`; the LLM fills
   `{{personalization_hook}}` from the row's enrichment columns and drops any
   row with no concrete hook (never force a generic blast).
4. `test.smoke` / `test.dryrun` — offline tests, then a 10-row dry run graded
   against the acceptance checks below.
5. `canary.run` — 10 real recipients + seed inboxes, then a human go/no-go.
6. `gmail.send` — the ledger claim lives inside this step: already-contacted
   recipients are skipped, suppressed ones never sent.
7. `report.write` — run report + changelog + INDEX refresh.

## Acceptance checks (graded by test.dryrun)

- Every outbox row has a non-empty, lead-specific `{{personalization_hook}}`
  that references something real about that store/person.
- No placeholder text (`{{`, "Hi ,", empty company) survives rendering.
- `from` is armaan.priyadarshan.29@dartmouth.edu — never the gmail account.

## Template note

`template.md` is the "Stanford Student Question" email — the exact template
that opened Beautylish, Public Goods, and Husqvarna in May 2026
(`brain/research/outreach-learnings.md`), with a personalization-hook slot
added. Caveat from the learnings file: the student framing may age out now
that the team is a YC company — revisit before large-scale reuse. One reply
also landed in spam ("[ AREA1 SPAM ]"), so watch deliverability in replies.

## Changelog

- 2026-06-10: created (replaces apollo-cold-email per the Clay decision;
  never yet run live — first run must keep the full default chain).
