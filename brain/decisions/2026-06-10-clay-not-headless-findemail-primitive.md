# Finding: Clay can't be driven fully headlessly — `findemail` is the headless path

**Date:** 2026-06-10 · **Source:** building the headless lead-sourcing pipeline
(Armaan: "control Clay headlessly, save as a primitive").

## What we learned

Clay **cannot** be driven end-to-end headlessly from a cold start. Confirmed
across Clay's own docs (university.clay.com) and multiple guides:

- "Clay doesn't have a traditional API." The programmatic surface is: a
  per-table **webhook URL** to POST rows in, and an **HTTP action** to push
  enriched rows out to your endpoint.
- The enrichment *recipe* — the "find work email" waterfall (Findymail/Enrow/
  etc.) — is **configured in the Clay UI, per table**. There is **no API** to
  create a table or add enrichment columns.
- The Enterprise People/Company API exists but explicitly **"doesn't include
  verified emails."**

So a `clay` primitive would still need an irreducible one-time ~10-min setup
**in the Clay UI** (create table → add a find-work-email column → add a
send-to-webhook output). The claude.ai Clay connector that's authed on
armaanp4423@gmail.com is interactive-only and is **not** exposed to headless
Claude Code / cron runs.

## Decision

The headless lead-enrichment step is the new **`findemail` primitive**, which
calls the same providers Clay waterfalls across (Hunter, Findymail) via their
REST APIs — one API key, zero manual setup, fully reusable:

- `findemail.find` — name + domain → verified work email (Hunter Email Finder
  / Findymail).
- `findemail.find-exec` — domain → the most senior decision-maker + their
  verified email (Hunter Domain Search; no founder name needed). This makes
  the whole pipeline domain-only: `domains.csv → findemail.find-exec →
  verify.check → compose.render → gmail.send`.

Confidence-gated (`--min-score`, default 80); rows without a found/verified
email are dropped and **never guessed**. Registered in `toolbox/TOOLBOX.md`;
5 offline smoke tests green.

## Implication for the Clay-only decision

`brain/decisions/2026-06-10-clay-is-the-lead-workbench.md` said Clay is the
sole sourcing/enrichment tool. That holds for *interactive* enrichment (a
human in claude.ai), but for **headless/autonomous** flows Clay is not usable;
`findemail` (Hunter/Findymail direct) is the headless equivalent and uses the
same underlying data. A Clay CSV export remains a valid manual input.

## To run a headless campaign

Needs two keys (neither in the repo): a **Hunter (or Findymail) API key**
(`toolbox auth connect hunter`, or `TOOLBOX_TOKEN_HUNTER`) for enrichment, and
the **Supabase secret key** for the no-double-contact ledger gate at send time.
gog/Dartmouth send accounts are already authed locally.
