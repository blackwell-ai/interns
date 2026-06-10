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
3. Source credentials from `credentials/.env`.
4. Check `inbox/queue/` for tasks addressed to you (or unassigned tasks you can do).

## Task queue protocol (`inbox/`)

- Tasks are single markdown files. Use `inbox/TEMPLATE.md` for the format.
- **Claim** a task by moving it from `inbox/queue/` to `inbox/in-progress/` and
  filling in the `claimed_by` and `claimed_at` fields. Never work a task that
  another agent has claimed.
- **Finish** by appending a `## Result` section to the task file and moving it to
  `inbox/done/`. If you failed or are blocked, say so plainly in the result —
  never report success that didn't happen.
- If a task produces durable knowledge, write it into `brain/` and link it from
  the task's result.

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

All shared credentials live in `credentials/.env`. Read them from there; never
hardcode a secret in any other file, and never paste secret values into task
files, brain entries, or commit messages.
