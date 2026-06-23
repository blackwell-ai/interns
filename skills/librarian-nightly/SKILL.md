# librarian-nightly

Autonomous nightly repo-cleanup pass. Deletes the cruft that builds up (stale
run dirs, caches, finished inbox tasks), keeps the file structure and indexes
tidy, repairs cross-links, flags the judgment calls for a human, and lands one
scoped commit on `main`. The librarian agent's charter is
`agents/librarian/AGENT.md`; this skill is how it runs each night.

This is not a deterministic toolbox flow. Cleanup needs judgment (is this brain
entry a duplicate, is this file junk or load-bearing), so `cron.sh` drives
headless Claude Code (`claude -p`) with the checklist in `PROMPT.md`, then
enforces a deterministic safety gate in bash before committing. See
`brain/decisions/2026-06-22-librarian-nightly-agent.md` for why it is built this
way.

## Files

```
skills/librarian-nightly/
  SKILL.md   # this file
  PROMPT.md  # the nightly checklist handed to claude -p (the durable "what")
  cron.sh    # the runner: dirty-tree guard -> claude -p -> safety gate -> commit/push
```

## How a run works

1. `cron.sh` refuses to run if the working tree is dirty (a human is mid-edit).
2. It runs `claude -p` with `PROMPT.md`. The agent deletes cruft, repairs
   indexes and links, files flags as a single `inbox/queue/` task, writes its
   report to `agents/librarian/LOG.md`, stages everything with `git add -A`, and
   writes a commit message to `runs/librarian-commit-msg.txt`. The agent does
   not commit or push.
3. `cron.sh` runs the safety gate on the staged diff:
   - **Protected paths** (`credentials/`, `CLAUDE.md`, `.mcp.json`,
     `toolbox/src|tests/`, `agents/*/AGENT.md`, `brain/company/overview.md`,
     `brain/decisions/`, `.claude/`, `.agents/`, its own
     `skills/librarian-nightly/*`): any staged change here aborts the run.
   - **Runaway cap**: deleting more than `LIBRARIAN_MAX_DELETE` (15) tracked
     files or changing more than `LIBRARIAN_MAX_CHANGE` (40) aborts the run.
   On abort it hard-reverts the tree, files an `inbox/queue/<date>-librarian-alert.md`
   task, and lands nothing.
4. Otherwise it makes one commit on `main` (the agent's message + the
   `Co-Authored-By` trailer) and pushes.

Recovery for anything deleted is `git revert` / `git log`. There is no archive;
that is a deliberate choice (see the decision doc), which is why the protected
set and the runaway cap carry the safety.

## Inputs and flags

```bash
skills/librarian-nightly/cron.sh            # full run: clean, gate, commit, push
skills/librarian-nightly/cron.sh --dry      # run the pass, print what it would commit, revert
skills/librarian-nightly/cron.sh --no-push  # commit locally, do not push
```

Env overrides: `LIBRARIAN_MAX_DELETE`, `LIBRARIAN_MAX_CHANGE`.

## Acceptance checks

- `bash -n cron.sh` parses clean.
- `--dry` on a clean tree completes, prints a `git diff --cached --stat`, and
  leaves the working tree clean (no leftover changes, no commit).
- A run never modifies a protected path; if the agent tries, the run aborts with
  an inbox alert and no commit.
- A run never commits when the tree was dirty at start.
- Each landed commit has a matching newest entry in `agents/librarian/LOG.md`.

## Operations (machine-local; not reproducible from the repo alone)

The schedule and the `claude` subscription auth live on Armaan's machine, not in
git.

- **Schedule**: a systemd user timer,
  `~/.config/systemd/user/librarian-nightly.{service,timer}` (OnCalendar
  `*-*-* 03:00`, `Persistent=true`), `ExecStart=` this folder's `cron.sh`, plus
  `loginctl enable-linger armaan` so it runs while logged out. Rebuild: write the
  two unit files, `systemctl --user daemon-reload`, `systemctl --user enable
  --now librarian-nightly.timer`. Logs: `runs/cron-librarian.log` and
  `journalctl --user -u librarian-nightly.service`.
- **Auth**: needs a logged-in `claude` CLI (subscription, not API key); see
  `brain/decisions/2026-06-10-llm-via-claude-code.md`. If `claude` is logged
  out, the run fails and reverts cleanly, landing nothing.
- **No secrets of its own.** It sources `credentials/.env` only so any sub-step
  that needs it works; the cleanup itself uses none.

## Changelog

- 2026-06-22: created. Charter `agents/librarian/AGENT.md`, decision
  `brain/decisions/2026-06-22-librarian-nightly-agent.md`.
