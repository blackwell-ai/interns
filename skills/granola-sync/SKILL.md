---
name: granola-sync
version: 1.0.0
description: |
  One command to pull every Granola meeting not yet in the repo and publish it:
  export the new notes into context/samarjit-granola/, commit them, and push,
  rebasing automatically when the shared repo has moved on. Idempotent — a no-op
  when nothing is new. Wraps granola-export; does not touch Granola's store
  itself.
license: MIT
compatibility: claude-code
allowed-tools:
  - Bash
---

# granola-sync

Keeps `context/samarjit-granola/` caught up with Granola in a single step. It
exports any meeting note that is not already committed, commits the new ones,
and pushes them to the shared notes repo. Run it after a meeting, or any time
you want "upload the transcripts I do not have yet" without thinking about the
git dance.

## When to use

- A meeting just finished and you want it in the repo and pushed, now.
- Backfill: publish every Granola note that is not committed yet.
- You hit a non-fast-forward push because a teammate pushed first, and you want
  that handled for you instead of by hand.

For exporting to disk only (no git), use `granola-export` directly. This skill
is the publish layer on top of it.

## Run it

From anywhere in the repo:

```bash
skills/granola-sync/sync.sh            # export new notes, commit, push
skills/granola-sync/sync.sh --no-push  # export and commit, leave the push to you
skills/granola-sync/sync.sh --list     # show in-repo vs NEW, write nothing
```

The first export of a session shows one macOS Keychain prompt (see
`granola-export`). Click Allow.

## How it works (so the next agent can fix it)

Four steps, all in `sync.sh`:

1. Run `node skills/granola-export/export.js` in its default idempotent mode.
   That script reads the document id out of every existing `.md` in the folder
   and writes only the meetings that are missing. All the hard parts (keychain
   decrypt, Granola API, note formatting) live there, not here.
2. `git add context/samarjit-granola`, then check `git diff --cached --quiet`.
   If the folder is unchanged, print "nothing new to upload" and exit 0. This is
   what makes reruns safe.
3. Commit the staged notes with a message that counts how many were added.
4. `git push`. If the push is rejected because the remote moved (this repo gets
   frequent pushes), `git fetch` and `git rebase origin/<branch>`, then push
   again. New notes never collide with other people's files, so the rebase is
   clean; if it somehow conflicts, the script aborts the rebase and tells you to
   finish by hand rather than guessing.

## Design notes

- It reuses `granola-export` rather than re-implementing the export. Per
  `skills/PROTOCOL.md`, composing from an existing skill beats writing new code.
  No new primitive was added; this is a shell wrapper around an existing one
  plus git.
- It pushes straight to the working branch (`main` in practice), matching how
  the rest of the notes and audits land in this repo. Use `--no-push` when you
  want to eyeball the diff before it goes out.

## Known limits

- Inherits every limit of `granola-export`: stale token (open the Granola app
  to refresh, then rerun), share links only when the live cache has them,
  speaker attribution by audio source only. See that skill's SKILL.md.
- Rebase safety net assumes the only staged changes are new note files. If you
  have other staged edits in `context/samarjit-granola/`, commit or stash them
  first so the auto-commit stays scoped to the sync.
- Pushes to the current branch's `origin` remote. Run it on the branch you
  actually want the notes on.

## Acceptance checks

- On a fully synced repo it prints "nothing new to upload" and makes no commit.
- With one or more new meetings, it writes them, commits exactly those files,
  and pushes, surviving a non-fast-forward remote without manual steps.
- No secret value appears in stdout or in any written file (it never handles
  secrets; `export.js` keeps them in memory).

## Changelog

- 1.0.0 (2026-06-25): first version. Codified from the backfill of the
  2026-06-17/06-19 notes and the 2026-06-25 Public Goods note, where the push
  was rejected twice by remote moves and rebased through by hand.
