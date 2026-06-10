# skills/

Reusable, named procedures that any agent (or human) can invoke. A skill is a
flow that worked once and was worth keeping — e.g. an outreach sequence shown to
the agent once, or the new-company pipeline (idea → overview → plan → code →
GitHub → Vercel).

## Format

One folder per skill, containing a `SKILL.md`:

```markdown
# <skill name>

**Purpose:** one line — when to reach for this skill.
**Inputs:** what the caller must provide.
**Credentials:** which entries from credentials/.env it needs.

## Steps
1. ...numbered, concrete, executable by a fresh agent with no other context...

## Output
What "done" looks like and where results are written.
```

## Conventions

- Skills must be self-contained: a fresh agent reading only /CLAUDE.md and the
  SKILL.md should be able to execute it.
- When an agent performs a flow that will plausibly recur, codifying it here is
  part of finishing the job.
- Update a skill in place when the flow improves; the file history is the
  changelog.
