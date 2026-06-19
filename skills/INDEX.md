# Skill registry

One line per registered skill. `report.write` updates the last-run column.

| Skill | Purpose | Primitives used | Last run |
|---|---|---|---|
| researcher-watchlist-sweep | Watchlist sweep: fetch sources → LLM filter → file inbox tasks (non-outreach breadth proof) | fetch, llm, inbox | — |
| humanizer | Writing standard for all repo prose; remove AI tells (binding via CLAUDE.md "Writing") | (none; style guide) | — |
| token-leaderboard | Per-person Claude Code token usage via ccusage to Supabase, ranked board plus committed snapshot | (script; ccusage+supabase) | — |
| researcher-daily-digest | Weekday external-signal radar: fetch Reddit + HN → per-post items → filter → synthesize a brain digest + inbox tasks (cron via cron.sh) | fetch, extract, llm, inbox | 2026-06-18 (`researcher-daily-digest-20260618T170830Z-554acd`) |
| granola-export | Export Granola meeting notes to context/samarjit-granola/ (keychain decrypt + Granola API) | (script; node + macOS keychain + granola API) | 2026-06-16 |
| ai-visibility-audit | House AI Visibility Audit to a branded PDF (Public Goods/Atlas format): recon + AI-behavior + reputation → 5-dim scorecard → findings → two-phase $1,000 close | (script; curl recon + web queries + Chrome render) | 2026-06-16 |
