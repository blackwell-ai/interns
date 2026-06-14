# Notion is the shared task hub for humans and agents

Date: 2026-06-14. Source: decision by Armaan in a working session, after trying
and dropping Todoist in favor of Notion.

## Decision

Blackwell uses a Notion workspace as the shared task hub where humans and agent
employees track who is working on what. It runs alongside the repo `inbox/`
queue rather than replacing it: Notion is the live, human-facing source of truth
for task state, and `inbox/` is the git-tracked fallback for headless or
scheduled agent runs where the Notion MCP is not authenticated. The agent boot
protocol in `/CLAUDE.md` now points agents at Notion first.

## Why

The four founders needed one place to see each other's work and the agents'
work. Markdown files in `inbox/` are good for git history and offline agent runs
but are poor for shared, at-a-glance visibility across people. Notion gives
boards grouped by person and by agent. We kept `inbox/` because the Notion MCP
may be absent in headless or cron runs, and losing the offline path would break
autonomous agents. The repo `brain/` stays the source of truth for company
knowledge; Notion is coordination only.

## Structure

Workspace: Armaan's Notion (`armaanp4423@gmail.com`). The four founders are real
Notion users (Armaan, Samarjit, Ethan, Shamit), so humans can be assigned
natively. The three agents (Outreach, GEO, Researcher) are not Notion users and
are tracked through a select field.

- Hub page: "Blackwell HQ" — https://app.notion.com/p/37fbea8c6fe78160af9ad1987ec39357
- Tasks database: https://app.notion.com/p/02f03570aa7e47d78e1b76e4ff3f7a12
  (data source `1f095b44-bfc7-441e-8d17-1d9cf91e0309`)
- Properties: Task (title), Status (Not started / In progress / Done), Assignee
  (people, for humans), Agent (Outreach / GEO / Researcher), Priority, Area,
  Customer, Due, Created.
- Views: default table, Board by status, By person, By agent.

Ownership model: humans own a task through Assignee; agents own or execute
through Agent; a task can carry both when a human owns it and an agent runs it.

MCP: the `notion` HTTP MCP (`https://mcp.notion.com/mcp`) is registered at local
scope for this repo in `/home/armaan/.claude.json`. Authenticated via OAuth as
Armaan, so it acts with his access.

## How the two systems relate

Interactive session with the MCP connected: work in Notion. Headless or MCP
unavailable: work in `inbox/`, then mirror the change into Notion at the start of
the next interactive session so the two do not drift. Full protocol is in
`/CLAUDE.md` under "Task hub".

## Open follow-ups

- Manual step for Armaan: drag "Blackwell HQ" into the shared teamspace so all
  four founders see it. The integration cannot place a page into a teamspace
  through the API, so it was created at the workspace root. Renaming the
  teamspace from the default personal name to "Blackwell" is worth doing at the
  same time.
- Proposed next builds, not yet decided: a customer and engagement tracker
  (related to Tasks) for pipeline and delivery state, a weekly batch tracker for
  the YC cadence, and an agent standup feed so humans see agent work without
  reading `agents/*/log.md`.
- Deliberately not built: a lead CRM (would duplicate Clay, see
  `brain/decisions/2026-06-10-clay-is-the-lead-workbench.md`) and a knowledge
  base (would duplicate the repo brain).
