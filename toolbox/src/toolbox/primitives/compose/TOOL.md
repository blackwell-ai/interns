# compose — template render + LLM personalization

Template file = subject frontmatter + body; slots are {{column_name}}:

    ---
    subject: Quick question about {{company}}
    ---
    Hi {{first_name}}, …

## compose.render
- in: contacts CSV (any columns) → out: outbox.csv (`email,subject,body,…`)
- flags: `--template <file>`, `--personalize` (LLM fills {{personalization_hook}} +
  resolves ambiguous first names), `--model`, `--on-missing drop|fail`
- derives first_name from name via deterministic rules; LLM only for ambiguous names
- a row with an empty slot is dropped (and logged) by default — test.dryrun catches
  systematic emptiness before any send
