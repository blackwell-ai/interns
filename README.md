# interns

The company brain and a fleet of Claude Code agents.

This repo is the harness: the documents in it define what the company knows, what
agents exist, what they can do, and what work is queued. Per the founding notes —
**code and automations are ephemeral; the documents are the product.** Most effort
should go into editing and improving these documents.

## Layout

| Folder | Purpose |
|---|---|
| `brain/` | Durable company knowledge: who we are, customers, research, decisions |
| `agents/` | One folder per agent — its charter, tools, and operating instructions |
| `skills/` | Remembered flows (SKILL.md + flow.yaml + inputs.yaml) — see `skills/PROTOCOL.md` |
| `inbox/` | Task queue: `queue/` → `in-progress/` → `done/` |
| `toolbox/` | The automation harness: primitives + runner — the only maintained code |
| `runs/` | One folder per flow execution: artifacts, events, report (gitignored) |
| `supabase/` | Backbone: per-person auth, provider connections, the contact ledger |
| `harness/` | The harness spec + build plan |
| `credentials/` | Legacy `.env` (gogcli only) — retired at harness milestone M4 |

## How it works

1. Humans (or agents) drop task files into `inbox/queue/`.
2. An agent claims a task by moving it to `inbox/in-progress/`, does the work,
   writes results into the task file, and moves it to `inbox/done/`.
3. Anything learned that outlives the task gets written into `brain/`.
4. Anything that worked and is repeatable gets codified into `skills/`.

See `CLAUDE.md` for the rules every agent operates under.
