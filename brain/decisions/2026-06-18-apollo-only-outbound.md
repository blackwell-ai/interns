# Decision: Apollo is the only outbound tool, Clay/Prospeo/Hunter/Origami dropped

**Date:** 2026-06-18 · **Source:** internal decision (Armaan, in session).

## What was decided

All email-campaign sourcing, enrichment, and verified-email lookup run through
**Apollo**, and only Apollo. The previous outbound stack is retired in full:
Clay (the lead workbench), Prospeo (the volume email engine), Hunter and
Findymail (the findemail provider adapters), and Origami (list building and the
sequencer). No agent reaches for any of them again.

This reverses two earlier decisions, both now superseded:

- `2026-06-10-clay-is-the-lead-workbench.md`
- `2026-06-16-prospeo-email-engine.md`

## What changed in the repo (2026-06-18 cleanup)

- Outreach charter (`agents/outreach/AGENT.md`) rewritten so Apollo is the lead
  and email tool; Clay, Prospeo, and Hunter references removed.
- The `toolbox` `findemail` primitive is Apollo-only. The Hunter and Findymail
  provider adapters and their tests were removed.
- Scrubbed the dead tools from `credentials/.env.example`,
  `brain/company/connections.md`, `brain/company/targets.md`, `skills/INDEX.md`,
  `toolbox/TOOLBOX.md`, `agents/README.md`, and the toolbox auth/CLI strings.
- The Clay and Prospeo decision records are kept as history with a superseded
  banner pointing here.
- The old outreach skills (`clay-cold-email`, `autonomous-outreach`, `campaign`,
  `handle-replies`, `outreach-counter`) were deleted by Armaan in the same
  session.

## Still open, pending Armaan's Apollo directions

The Apollo API key is stored (gitignored `credentials/.env`,
`TOOLBOX_TOKEN_APOLLO`, which `findemail`'s `get_token("apollo")` reads) and was
validated June 18 against `auth/health` (200, is_logged_in). What is not yet
specified is how we drive Apollo: search filters, enrichment calls, sequencing,
the exact endpoints and credit model. The existing `findemail` Apollo adapter is
a starting point, not a confirmed integration, and the Apollo-based cold-email
skill is not rebuilt yet. Wire-up details land here once Armaan provides them.

## Outside the repo, manual, by Armaan

- Disconnect the Clay claude.ai MCP connector and the Prospeo MCP server in the
  claude.ai connector settings.
- Remove the Origami gstack plugin skills (`.claude/skills/origami-*`) through
  gstack if they should be gone for good. They are gitignored plugin content,
  not repo files, so they do not show up in git.
