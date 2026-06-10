# inbox/

The task queue. Humans and agents drop work here; agents (and humans) pick it up.

## Lifecycle

```
queue/  →  in-progress/  →  done/
```

1. **File** a task: copy `TEMPLATE.md` into `queue/` as
   `YYYY-MM-DD-short-slug.md` and fill it in.
2. **Claim** it: move the file to `in-progress/` and set `claimed_by` /
   `claimed_at`. A task in `in-progress/` belongs to its claimant — never
   double-work it.
3. **Finish** it: append a `## Result` section (honest — failures and blockers
   included), then move the file to `done/`.

## Rules

- One task per file. Big tasks get split into multiple files.
- Tasks addressed to a specific agent/human name them in the `assignee` field;
  unassigned tasks may be claimed by anyone capable.
- Durable knowledge produced by a task goes into `brain/`, linked from the
  task's result — `done/` is an archive, not the brain.
