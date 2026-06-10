# agents/

One folder per agent employee. Each agent's `AGENT.md` is its charter: what it's
for, what tools it uses, how it operates, and how it reports back. The charter is
the durable artifact — an agent session can be killed and restarted from its
charter at any time.

## Current roster

- `outreach/` — autonomous outbound: finds and enriches leads in Clay,
  runs outreach via gogcli.
- `researcher/` — monitors Discord servers, subreddits, researchers, and
  conferences; surfaces anything relevant to us.

## Adding an agent

1. Create `agents/<name>/AGENT.md` (copy the structure of an existing charter).
2. Add the agent to `brain/people/` as an employee.
3. List any new credentials it needs in `credentials/.env`.
4. Launch it with Claude Code from the repo root: it will read `/CLAUDE.md`,
   then its own charter, then check `inbox/queue/`.
