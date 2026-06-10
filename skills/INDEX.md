# Skill registry

One line per registered skill. `report.write` updates the last-run column.

| Skill | Purpose | Primitives used | Last run |
|---|---|---|---|
| clay-cold-email | Clay leads → verify → personalize → send (the canonical cold-email flow) | verify, compose, gmail | — |
| autonomous-outreach | Headless cold-send loop: claim → hook → send (token-cheap volume) | (script; gog+claude -p+supabase) | 2026-06-10 |
| handle-replies | Triage outreach replies; propose slots + book Google Meet calls | (script; gog cal+gmail+claude -p) | — |
| researcher-watchlist-sweep | Watchlist sweep: fetch sources → LLM filter → file inbox tasks (non-outreach breadth proof) | fetch, llm, inbox | — |
