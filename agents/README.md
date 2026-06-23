# agents/

One folder per agent employee. Each agent's `AGENT.md` is its charter: what it's
for, what tools it uses, how it operates, and how it reports back. The charter is
the durable artifact — an agent session can be killed and restarted from its
charter at any time.

## Current roster

- `outreach/` — autonomous outbound: sources and enriches leads in Apollo,
  runs outreach via gogcli.
- `researcher/` — monitors Discord servers, subreddits, researchers, and
  conferences; surfaces anything relevant to us.
- `geo/` — owns all GEO (AI visibility) work: audits, implementation,
  re-benchmarks, per `brain/company/audit-methodology.md`.
- `librarian/` — night-shift custodian: one autonomous cleanup pass per night
  (delete cruft, tidy structure, repair indexes and links, flag the judgment
  calls), one scoped commit on `main`. Runs the `librarian-nightly` skill.

## Adding an agent

1. Create `agents/<name>/AGENT.md` (copy the structure of an existing charter).
2. Add the agent to `brain/people/` as an employee.
3. List any new credentials it needs in `credentials/.env`.
4. Launch it with Claude Code from the repo root: it will read `/CLAUDE.md`,
   then its own charter, then check its tasks in the Notion **Tasks** hub (or
   `inbox/queue/` when running headless). Add the agent as an option in the
   Tasks database **Agent** field so work can be assigned to it.
