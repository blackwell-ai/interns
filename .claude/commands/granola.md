---
description: Upload recent Granola meeting notes to context/samarjit-granola, then commit and push
argument-hint: "[--list] [--no-push]"
allowed-tools: Bash(skills/granola-sync/sync.sh:*)
---

You are running the `granola` command. It publishes every Granola meeting note
that is not already in the repo: export the new ones into
`context/samarjit-granola/` in the same format as the notes already there,
commit exactly those files, and push. It is idempotent, so a repo that is
already caught up makes no commit.

This command is a thin front door over the `granola-sync` skill. All of the real
work (keychain decrypt, Granola API, note formatting, the commit-and-push with
auto-rebase on a moved remote) lives in `skills/granola-sync/` and
`skills/granola-export/`. Do not reimplement any of it here.

Run exactly this with the Bash tool:

`skills/granola-sync/sync.sh $ARGUMENTS`

`$ARGUMENTS` is optional and passes straight through to the skill:

- no argument: export new notes, commit, and push.
- `--list`: show which meetings are in the repo versus new, write nothing.
- `--no-push`: export and commit, but leave the push to the user.

Rules:

- Do not ask questions first. Just run it.
- The first export in a session shows one macOS Keychain prompt ("security wants
  to use the Granola Safe Storage key"). That is expected. The user clicks Allow.
  If the run stalls waiting on it, tell the user to approve the prompt.
- When it finishes, report the outcome from the script's own output: the notes it
  published (or "nothing new to upload"), and whether the push landed. Do not
  invent counts; read them from the output.
- If the script says the token is stale, tell the user to open the Granola app
  once so it refreshes, then rerun. Do not try to work around it.
- If the push is rejected and the auto-rebase hits a real conflict (your
  uncommitted work touches a file that also moved on the remote), the script
  stops and asks for a hand resolution. Resolve that file by keeping both sides
  when it is an append-only log, then run `git push`. The notes commit itself is
  independent and safe to push once the tree is clean.
