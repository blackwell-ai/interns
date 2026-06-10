# llm — generic LLM filter/transform over JSONL

Connection: ANTHROPIC_API_KEY (or anthropic connection).

## llm.filter
- in: JSONL records → out: JSONL of records that pass, each + `reason`/`summary`
- flags: `--criteria "<plain-English bar>"`, `--field text`, `--model`
- strict by design: the researcher's "would a human act on this?" bar
