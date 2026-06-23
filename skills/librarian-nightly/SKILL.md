# librarian-nightly

Autonomous nightly repo-cleanup pass. Deletes the cruft that builds up (stale
run dirs, caches, finished inbox tasks), keeps the file structure and indexes
tidy, repairs cross-links, flags the judgment calls for a human, and lands one
scoped commit on `main`. The librarian agent's charter is
`agents/librarian/AGENT.md`; this skill is how it runs each night.

Cleanup needs judgment (is this brain entry a duplicate, is this file junk or
load-bearing), so the tracked-content phase drives headless Claude Code
(`claude -p`) with the checklist in `PROMPT.md`. It runs in two phases so it can
never touch concurrent uncommitted work, and `cron.sh` enforces a deterministic
safety gate in bash before committing. See
`brain/decisions/2026-06-22-librarian-nightly-agent.md` for why it is built this
way.

## Files

```
skills/librarian-nightly/
  SKILL.md   # this file
  PROMPT.md  # the nightly checklist for the worktree pass (the durable "what")
  cron.sh    # the runner: disk hygiene -> isolated worktree -> safety gate -> commit/push
```

## How a run works

1. **Phase A, disk hygiene on the main checkout** (bash, no agent). Deletes only
   gitignored regenerable junk: `__pycache__`, `.ruff_cache`, `.pytest_cache`,
   `*.pyc`, `.DS_Store`, editor backups, and `runs/` dirs past
   `LIBRARIAN_RUNS_KEEP` (7). Never stages, never commits, only touches files git
   already ignores, so it is safe alongside any concurrent work.
2. **Phase B, tracked-content cleanup in an isolated worktree.** `cron.sh`
   fetches and adds a detached worktree at `origin/main`, then runs `claude -p`
   with its cwd inside that worktree. The agent prunes finished inbox tasks,
   repairs indexes and links, files flags as a single `inbox/queue/` task, writes
   its report to `agents/librarian/LOG.md`, stages with `git add -A`, and writes
   a commit message to `runs/librarian-commit-msg.txt` (gitignored). It does not
   commit or push. The worktree holds only committed content, so the agent cannot
   see or delete the main checkout's uncommitted files.
3. `cron.sh` runs the safety gate on the worktree's staged diff:
   - **Protected paths** (`credentials/`, `CLAUDE.md`, `.mcp.json`,
     `toolbox/src|tests/`, `agents/*/AGENT.md`, `brain/company/overview.md`,
     `brain/decisions/`, `.claude/`, `.agents/`, its own
     `skills/librarian-nightly/*`): any staged change here aborts.
   - **Runaway cap**: deleting more than `LIBRARIAN_MAX_DELETE` (15) tracked
     files or changing more than `LIBRARIAN_MAX_CHANGE` (40) aborts.
4. Otherwise it commits in the worktree (the agent's message + the
   `Co-Authored-By` trailer) and pushes the detached HEAD to `origin/main`.
5. On any abort, a rejected push (`origin/main` moved), or a clean night, the
   whole worktree is removed and nothing lands on the main checkout. The next run
   retries on fresh `origin/main`.

The main checkout is never `reset`/`clean`'d, so the librarian cannot destroy
in-progress work. Recovery for anything it deletes is `git revert` / `git log`;
there is no archive, which is why the protected set and runaway cap carry the
safety. After a push, the main checkout's local `main` is one commit behind and
fast-forwards on the next `git pull`.

## Inputs and flags

```bash
skills/librarian-nightly/cron.sh            # full run: hygiene, worktree pass, gate, commit, push
skills/librarian-nightly/cron.sh --dry      # both phases read-only: report junk, build worktree, print staged diff, commit nothing
skills/librarian-nightly/cron.sh --no-push  # commit in the worktree but do not push (discarded on cleanup)
```

Env overrides: `LIBRARIAN_MAX_DELETE`, `LIBRARIAN_MAX_CHANGE`, `LIBRARIAN_RUNS_KEEP`.

## Acceptance checks

- `bash -n cron.sh` parses clean.
- `--dry` completes even with a dirty main checkout, prints a
  `git diff --cached --stat` from the worktree, commits nothing, and leaves the
  main checkout's tracked files and uncommitted work untouched.
- No `git worktree` entries leak after a run (`git worktree list` shows only the
  main checkout).
- A run never modifies a protected path; if the agent stages one, the run aborts
  and lands nothing.
- The main checkout is never `git reset`/`clean`'d by a run; concurrent
  uncommitted work survives.
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
- **Auth**: needs a logged-in `claude` CLI (subscription, not API key; see
  `brain/decisions/2026-06-10-llm-via-claude-code.md`) and push access to
  `origin`. If `claude` is logged out or the push fails, the worktree is
  discarded and nothing lands.
- **No secrets of its own.** It sources `credentials/.env` only so any sub-step
  that needs it works; the cleanup itself uses none.

## Changelog

- 2026-06-23: reworked to worktree isolation. Split into disk hygiene (main
  checkout, bash) + tracked-content cleanup (isolated worktree off `origin/main`,
  `claude -p`). Dropped the dirty-tree skip and the repo-wide
  `reset --hard`/`clean` revert, which could refuse to run or delete concurrent
  work. See the decision doc's 2026-06-23 update.
- 2026-06-22: created. Charter `agents/librarian/AGENT.md`, decision
  `brain/decisions/2026-06-22-librarian-nightly-agent.md`.
