# Skill registry

One line per registered skill. `report.write` updates the last-run column.

| Skill | Purpose | Primitives used | Last run |
|---|---|---|---|
| clay-cold-email | Clay leads → verify → personalize → send (the canonical cold-email flow) | verify, compose, gmail | — |
| autonomous-outreach | Headless cold-send loop: claim → hook → send (token-cheap volume) | (script; gog+claude -p+supabase) | 2026-06-10 |
| handle-replies | Triage outreach replies; propose slots + book Google Meet calls | (script; gog cal+gmail+claude -p) | — |
| researcher-watchlist-sweep | Watchlist sweep: fetch sources → LLM filter → file inbox tasks (non-outreach breadth proof) | fetch, llm, inbox | — |
| humanizer | Writing standard for all repo prose; remove AI tells (binding via CLAUDE.md "Writing") | (none; style guide) | — |
| token-leaderboard | Per-person Claude Code token usage via ccusage to Supabase, ranked board plus committed snapshot | (script; ccusage+supabase) | — |
| researcher-daily-digest | Weekday external-signal radar: fetch Reddit + HN → per-post items → filter → synthesize a brain digest + inbox tasks (cron via cron.sh) | fetch, extract, llm, inbox | 2026-06-16 (`researcher-daily-digest-20260616T150016Z-a9dc51`) |
| granola-export | Export Granola meeting notes to context/samarjit-granola/ (keychain decrypt + Granola API) | (script; node + macOS keychain + granola API) | 2026-06-16 |
