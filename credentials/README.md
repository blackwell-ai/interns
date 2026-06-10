# credentials/

Shared credentials for all human and agent employees, stored as a plain `.env`
in this **private** repo.

## Usage

- Agents and scripts read from `credentials/.env` (e.g. `source credentials/.env`
  or a dotenv loader pointed at it).
- One entry per credential, `UPPER_SNAKE_CASE`, with a comment saying what it's
  for and who owns the account.
- Never copy secret values anywhere else in the repo — not into brain files,
  task files, code, or commit messages.

## Known tradeoff

This is the simplest possible setup and it was chosen deliberately as a stopgap:
anyone with repo read access sees every secret in plaintext, and git history
keeps old values forever. Consequences to respect:

- This repo must stay **private**, and access to it is access to everything.
- **Rotating** a secret means changing it at the provider too — deleting it from
  the file does not un-leak it from history.
- If the repo is ever exposed, rotate *all* credentials immediately.

When the team grows, migrate to SOPS+age or 1Password; the rest of the repo
already reads through this folder, so only this folder changes.
