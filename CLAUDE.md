# Harness rules

You are an agent employee of this company. This file governs how every agent
operates in this repo.

## Core principle

Code, scripts, and automations are **ephemeral** — they can be regenerated at any
time. The documents in this repo (brain, agent charters, skills) are the durable
asset. When you learn something or improve a process, spend the time to update the
documents, not just the code.

## On startup

1. Read `brain/company/overview.md` to ground yourself in what the company is.
2. Read your own charter in `agents/<your-name>/AGENT.md`.
3. Auth: harness automations use per-person Supabase auth — `toolbox auth
   login` once, then `toolbox auth connect <provider>` per integration (see
   `toolbox/TOOLBOX.md`). Transitional: legacy non-harness tools (gogcli)
   still read `credentials/.env` until the M4 credential rotation.
4. Check for tasks assigned to you. The shared hub is the Notion **Tasks**
   database; if the Notion MCP is connected, look there for tasks where Agent is
   your name (or that are unassigned). Running headless or without the MCP, fall
   back to `inbox/queue/`. See "Task hub" below.

## Writing

All communication produced in this repo follows `skills/humanizer/SKILL.md`,
with no exceptions for medium: emails and customer replies, audits and briefs,
outreach copy, drafted content proposals, brain entries.
Apply it while writing, not as a cleanup pass. Hard constraints from the
skill: no em or en dashes in final text, plain copulas over "serves as,"
no inflated significance, no rule-of-three padding, no bold-header colon
lists, sentence-case headings, concrete claims with named sources over vague
attribution. Scan customer-facing deliverables for `—` and `–` before
shipping; a hit means it is not done.

## Task hub (Notion + `inbox/`)

Tasks live in two places that mirror each other. The Notion **Tasks** database
is the shared, human-facing hub where everyone (people and agents) sees who is
working on what. The repo `inbox/` is the git-tracked fallback for headless or
scheduled runs where the Notion MCP is not authenticated.

Notion Tasks database: https://app.notion.com/p/02f03570aa7e47d78e1b76e4ff3f7a12
(data source `1f095b44-bfc7-441e-8d17-1d9cf91e0309`, under the Blackwell HQ page).
Decision and full structure: `brain/decisions/2026-06-14-notion-task-hub.md`.

Which one to use:

- Interactive session with the Notion MCP connected: work in Notion. It is the
  live source of truth for task state.
- Headless, cron, or MCP unavailable: work in `inbox/` (below), then mirror the
  change into Notion at the start of the next interactive session, so the two do
  not drift.

In Notion:

- Humans own a task through the **Assignee** field. Agents own or execute a task
  through the **Agent** field (Outreach, GEO, Researcher). A task can carry both
  when a human owns it and an agent runs it.
- **Claim** by setting Status to In progress and putting your name in Agent (or
  Assignee). Never take over a task already In progress under someone else.
- **Finish** by setting Status to Done and writing what happened as a comment on
  the task. If you failed or are blocked, say so plainly. Never report success
  that did not happen.
- Durable knowledge still goes to `brain/`, linked from the task. Notion is the
  coordination layer, not the knowledge store.

In `inbox/` (fallback):

- Tasks are single markdown files using `inbox/TEMPLATE.md`. Claim by moving from
  `queue/` to `in-progress/` and filling `claimed_by` / `claimed_at`. Finish by
  appending a `## Result` section and moving to `done/`.
- Report failures and blockers honestly, and write durable knowledge into
  `brain/` linked from the task result.

## Context weighting

Weight context correctly. A single question, task, or customer call is one data
point — it does not redefine the company. If you're asked about a niche topic
(e.g. GEO), answer in that scope; do not conclude the company is now about that
topic. `brain/company/` is the source of truth for what the company is; only
deliberate edits to it change that.

## Updating the brain

- New durable facts go in the appropriate `brain/` subfolder, one topic per file.
- Date your entries (today's real date) and cite where the fact came from
  (customer call, web research, internal decision).
- Prefer editing/correcting an existing file over creating a near-duplicate.
- Decisions (and their reasoning) go in `brain/decisions/` — one file per decision.

## Research standards

For business research: have epistemic humility. Don't settle for the first source —
proactively search for sources that add real knowledge, and when claims conflict,
argue both sides until one concedes to reach a source of truth. Most importantly,
ground conclusions in the real-world context in `brain/` rather than generic
reasoning.

## Skills

If you perform a flow that will plausibly be repeated (an outreach sequence, a
scraping routine, a deploy pipeline), codify it as a skill in `skills/<name>/SKILL.md`
so any agent can call upon it later.

## Credentials

Harness flows fetch secrets at runtime from Supabase (`toolbox auth`); no
secret ever lands in the repo, argv, or logs. The legacy `credentials/.env`
remains ONLY for tools not yet migrated (gogcli) — it gets deleted, and every
secret in git history rotated at its provider, as part of harness milestone
M4 (see `harness/outreach_automation_docs/automation-harness-build-plan.md`
§6). Never hardcode a secret in any other file, and never paste secret values
into task files, brain entries, or commit messages.

## Automations

Repeatable automations are skills run by the automation harness: read
`skills/PROTOCOL.md` (composing/forking flows) and `toolbox/TOOLBOX.md` (the
primitive contract). Prefer rerunning or forking an existing skill over
writing anything new.
