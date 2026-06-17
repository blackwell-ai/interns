# outreach-counter

Team-wide email send tracking: a daily, weekly, and total count of every email
the team sends as outreach.

## How it works

Counts are **derived from the ledger**, not maintained as a separate number.
Every outreach path in this repo records each recipient in Supabase before
sending: the volume senders (`send_fast.py`, `send_taste_data.py`) and the
interactive Clay sends write the `suppression` table with a reason that starts
with "contacted ", and the harness `gmail.send` primitive writes the `contacted`
table. So the real team send count is just those rows, bucketed by date. There is
no counter to increment and nothing that can drift, and it captures every team
member automatically (whoever sends, through whatever path, writes the ledger).

Excluded from the counts: pre-company Giftly-era imports, bounces, failed sends,
and claimed-but-unconfirmed rows. The Giftly historical figure is reported
separately at the bottom of the output file.

## Use

```
python skills/outreach-counter/counter.py
```

This prints today / this week / total and rewrites
`agents/outreach/send-counts.md` (the committed, human-readable scoreboard). It
reads Supabase credentials from the environment, falling back to
`credentials/.env`, so it runs with no setup.

## Automatic refresh

`send_fast.py` and `send_taste_data.py` call the counter at the end of every run
(and `campaign.sh` runs through `send_fast.py`), so any volume campaign refreshes
the scoreboard on finish. For sends made outside those scripts (for example an
interactive Clay session), run the command above, or set up a daily scheduled
refresh so the committed file never goes stale.

## Definitions

- Day and week are bucketed in US Pacific time. Change `TZ` in `counter.py` to
  adjust.
- "This week" is a rolling 7 days (today and the previous six).
- "Total" is all sends through this system. Pre-company Giftly imports are listed
  separately, so the all-time-including-history figure is also visible.
