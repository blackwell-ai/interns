# Lead enrichment: Clay isn't headless; Hunter is

## Clay cannot be driven fully headlessly — it's architecture, not a key

Confirmed across Clay's own docs: **"Clay doesn't have a traditional API."** Its
programmatic surface is a per-table **webhook in** + an **HTTP action out**; the
enrichment *recipe* (the find-work-email waterfall) is configured **in the Clay
UI, per table**, and there is **no API to create a table or its enrichment
columns**. The Enterprise People/Company API exists but "doesn't include
verified emails." The claude.ai Clay connector is interactive-only and is not
exposed to headless Claude Code / cron runs.

→ A `clay` primitive would still need a one-time ~10-min manual table setup in
the Clay UI. So for headless/autonomous flows, **don't use Clay** — call the
providers Clay waterfalls across (Hunter, Findymail) directly. Full detail:
`brain/decisions/2026-06-10-clay-not-headless-findemail-primitive.md`.

## Hunter `domain-search` is the unlock: domain → decision-maker → verified email

The `findemail.find-exec` primitive wraps Hunter's Domain Search: give it a bare
domain, it returns the most senior person (ranked founder > owner > CEO >
president > … by job title) **and** their email with a 0–100 deliverability
score and a `valid`/`accept_all`/`unknown`/`invalid` status. This removes the
need to source founder *names* first — the slowest part of the old plan.

Result on this run: **224 domains → 180 verified decision-makers** (median
score **98**), and after dropping `invalid`/generic/no-name rows, a 169-lead
send queue. Quality was excellent — real CEOs/founders, not generic inboxes.

## Verified beats inferred, and it's cheap

- Web search readily gives a founder's **name** and the **company domain**, but
  the **full personal email is paywalled** in the aggregators — so web-search
  alone only yields `firstname@domain` *guesses*. Guesses bounce and burn domain
  reputation. **Don't ship them.**
- Hunter returns the **verified** address. Cost: **362 credits for ~180 results
  over ~520 attempts** — Hunter only charges on a successful find, and the
  Starter plan has 2,000/mo. Getting it right was effectively free.

## Concurrency is the hidden yield lever (see file 03 for the rate-limit lesson)

Same 160 domains: **concurrency 12 → 50 found (~31%)**; **concurrency 5 → 80%
found.** The high-concurrency run wasn't finding fewer real people — it was
getting rate-limited, and the retries exhausted into what *looked* like
"not found." `findemail`'s default concurrency is now **5** for this reason.

## Reuse

`findemail.find` (name+domain → email) and `findemail.find-exec` (domain →
decision-maker+email) are general primitives — any future flow (sales, research,
partnerships) can use them. Swap `--provider findymail` if Hunter coverage is
thin for a segment.
