# llm: generic LLM filter/transform over JSONL

Connection: ANTHROPIC_API_KEY (or anthropic connection).

## llm.filter
- in: JSONL records → out: JSONL of records that pass, each + `reason`/`summary`
- flags: `--criteria "<plain-English bar>"`, `--field text`, `--model`, `--batch N`
- strict by design: the researcher's "would a human act on this?" bar
- `--batch N` judges N items per LLM call (default 1). Use it for volume: 170
  items at `--batch 25` is about 7 calls instead of 170, which is the
  difference between ~1 minute and 20+.

## llm.digest
- in: JSONL items that cleared the filter → out: a markdown digest
- flags: `--out digest.md`, `--brain-dir <dir>` (also writes `<dir>/<YYYY-MM-DD>.md`),
  `--reviewed N`, `--reviewed-from <jsonl>`, `--date YYYY-MM-DD`, `--model`
- synthesizes a themed digest (problems / ideas / competitor moves); every item
  says why it matters to Blackwell and links its source.
- humanizer-compliant: the system prompt forbids em/en dashes and a defensive
  pass strips any that slip through (the skill runs unattended).
- appends a deterministic `## Sources indexed` section (source -> item count)
  from `--reviewed-from`, so the digest shows full coverage, not just what passed.
- empty input writes a one-line "nothing cleared the bar" digest, never a crash.
