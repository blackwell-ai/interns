# Skill registry

One line per registered skill. `report.write` updates the last-run column.

| Skill | Purpose | Primitives used | Last run |
|---|---|---|---|
| researcher-watchlist-sweep | Watchlist sweep: fetch sources → LLM filter → file inbox tasks (non-outreach breadth proof) | fetch, llm, inbox | — |
| humanizer | Writing standard for all repo prose; remove AI tells (binding via CLAUDE.md "Writing") | (none; style guide) | — |
| token-leaderboard | Per-person Claude Code token usage via ccusage to Supabase, ranked board plus committed snapshot | (script; ccusage+supabase) | — |
| researcher-daily-digest | Weekday external-signal radar: fetch Reddit + HN → per-post items → filter → synthesize a brain digest + inbox tasks (cron via cron.sh) | fetch, extract, llm, inbox | 2026-06-30 (`researcher-daily-digest-20260630T155222Z-b771fe`) |
| granola-export | Export Granola meeting notes to context/samarjit-granola/ (keychain decrypt + Granola API) | (script; node + macOS keychain + granola API) | 2026-06-16 |
| granola-sync | Publish layer over granola-export: export new meeting notes, commit, push (auto-rebase on remote move); idempotent no-op when nothing is new | (script; granola-export + git) | 2026-06-25 |
| ai-visibility-audit | House AI Visibility Audit to a branded PDF (Public Goods/Atlas format): recon + AI-behavior + reputation → 5-dim scorecard → findings → two-phase $1,000 close | (script; curl recon + web queries + Chrome render) | 2026-06-16 |
| librarian-nightly | Autonomous nightly repo cleanup: delete cruft, tidy structure, repair indexes + links, flag judgment calls, one gated commit on main (cron via cron.sh, drives claude -p) | (script; claude -p + git) | — |
