---
description: Send N cold emails across the ICP mix (icp_mix.toml), fully non-interactive
argument-hint: <number-of-emails> [sender-key] [provider]
allowed-tools: Bash(bash skills/campaign/send.sh:*)
---

You are running the `campaign` skill in fully non-interactive mode. Send
`$ARGUMENTS` total cold emails, distributed across the ICPs defined in
`skills/campaign/icp_mix.toml` (each segment uses its own template), CC'ing the
cofounders per `skills/campaign/FOUNDERS.md`.

Rules:

- Do NOT ask any questions. Sender, CC list, ICP distribution, and templates are
  all predetermined. Just run it.
- Run exactly this, using the Bash tool with a timeout of 1800000 ms because a
  large send can take many minutes:

  `bash skills/campaign/send.sh $ARGUMENTS`

  `$ARGUMENTS` is the email count, optionally followed by a sender key
  (`samarjit` | `armaan` | `ethan` | `shamit`; default `samarjit`) and an email
  provider (`hunter` | `apollo`; default `hunter`) that finds and verifies the
  contacts. The provider may also be given alone in the sender slot, e.g.
  `1000 apollo`. Apollo needs `TOOLBOX_TOKEN_APOLLO` in `credentials/.env`.
- The script loads credentials, derives the sender and CC, and calls `run.py` in
  ICP-mix mode. `run.py` runs its own preflight, so do not pre-check auth.
- When it finishes, report the per-segment sourced counts and the final
  `Result: sent=N` line. Nothing else.
- If preflight fails (not signed in, missing key), surface the single fix line it
  printed and stop. Do not improvise or retry destructively.
