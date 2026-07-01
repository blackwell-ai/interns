# Reply triage: report and guide

What it does, what we learned validating it, and how to run it. Covers
`reply_triage_probe.py`. Status as of June 25, 2026: working probe, read only,
writes nothing. Not yet a scheduled production scanner.

## What it answers

One question: of all the people we cold emailed, who has replied in a way that we
still owe a response to, and who should send it. It reads each reply thread, decides
whether a real person is waiting on us, throws out the noise (bounces, out of office,
"please remove me", and dead ends where the contact has left with no one to pursue),
skips threads we have already answered, and groups the rest by what to actually do.

It does not find people who went silent. That is the opposite query (the `contacted`
ledger minus the `replies` table) and a different tool.

## How it works

The pipeline is four steps.

1. Scope to real prospect replies. It pulls every recipient from the Supabase
   `contacted` ledger and asks Gmail for inbound only from those addresses
   (`in:inbox newer_than:Nd from:(...)`, batched 50 addresses per query, paginated
   past Gmail's 500 per page limit). This fetches only prospect replies instead of
   scanning the whole inbox, so coverage is complete within the window and internal
   mail never enters the picture.
2. Read the whole thread. For each candidate it fetches the full Gmail thread, both
   directions, and renders it with every message labelled US or THEM. Teammates who
   are CC'd on sends count as US, so a teammate is never mistaken for the prospect.
3. Triage with one LLM call per thread. The model returns a single `action`, plus a
   `confidence` and, for reroutes, the named contact to pursue. Calls run concurrently
   against the Anthropic API.
4. Bucket, dedupe, attribute. Because all four teammates are CC'd, the same reply
   lands in several inboxes. Results dedupe by thread, and each one is attributed to
   an owner (the first US sender in the thread, which is whoever originally emailed
   the prospect).

## The four buckets

The model sorts every reply into the action a human would take.

| Bucket | Meaning | What to do |
|---|---|---|
| reply | A real person is waiting on us (question, interest, scheduling, objection) | Reply to them |
| reroute | They handed us a different named contact (referral, handoff, "X has left, reach Y") | Pursue the named contact |
| gray | Genuinely ambiguous, the model is unsure | Human glance |
| skip | Dead end: flat decline, out of office, bounce, or "left, no contact given" | Nothing |

The reroute and skip split matters. A "left the company" note that names a successor
is a warm internal referral and goes to reroute. A bare "no longer works here" with no
one to pursue is a dead end and goes to skip. We do not surface dead ends.

## What we found validating it

Run on June 25, 2026 across the three sender inboxes (Armaan, Samarjit, Ethan), 60 day
window, no cap, against 7,186 contacted addresses.

Coverage was the headline. An earlier version sampled the 100 most recent inbox
messages and found 16 prospect threads in Samarjit's inbox. Querying the full ledger
found 114 in the same inbox. The sample was showing roughly one in seven of the
threads that needed attention.

Consolidated across the team after dedupe: 90 unique prospects worth an action, split
18 reply, 67 reroute, 5 gray. Around 150 more were dead ends and dropped.

The reroute bucket was the hidden value. Sixty seven companies told us exactly who to
talk to instead (for example `dalton@whogivesacrap.org` to `katie.s@whogivesacrap.org`,
`t.kreitz@zwilling.com` to `A.Jonaskovic@zwilling.com`). Before the bucket existed
these were buried as borderline noise.

The gray zone shrank from 66 to 5 once reroutes and dead ends were pulled out. The five
that remain are actually ambiguous, which is the point.

The clear replies were stable. The ones seen in all three inboxes (NEOM's EA proposing
a meeting time, Jenna at Made In, Seth at Save The Duck, and others) were classified
identically every time, so there is no run to run wobble on the real ones. Borderline
cases were where earlier versions flipped between runs, which is exactly why the model
now flags its own uncertainty instead of being forced into a binary.

## How to run it

From the repo root. Requires a valid `gog` token for the account
(`gog auth list` to check) and `ANTHROPIC_API_KEY` set for the fast path.

```bash
# one account, full ledger scope, parallel API triage
python3 skills/campaign/reply_triage_probe.py --account you@blackwell.com --ledger --concurrency 20

# scope to one campaign's contacts instead of the whole ledger
python3 skills/campaign/reply_triage_probe.py --log /tmp/campaign_abc12345.jsonl
```

Flags that matter:

- `--ledger` scopes to prospect replies via the contacted ledger. This is the
  recommended mode and the one validated above.
- `--since-days` is the lookback window, default 60. Set it to cover all your sends.
- `--concurrency` is parallel requests in flight, default 8. 20 is comfortable.
- `--max` caps threads triaged, default 0 meaning no cap (triage every prospect reply).
- `--recent` caps inbox messages pulled, default 0 meaning the whole window.
- `TRIAGE_MODEL` env var overrides the model (default `claude-sonnet-4-6`). Set it to
  `claude-opus-4-8` for sharper judgement on the gray zone at higher cost.

Speed. With the API key set, triage runs concurrently and each account finishes in
roughly 20 to 30 seconds (fetch about 5s, triage the rest). Without the key it falls
back to a `claude -p` subprocess per call, which is correct but far slower (minutes).
Each run prints its own fetch and triage timings.

## Known limits

It only sees replies sent from the address we emailed. If a prospect replies from a
different address (an assistant, an alias), the `from:(ledger)` query misses it. The
airtight fix is to match on any thread participant rather than the reply sender, at the
cost of scanning more threads. Not implemented.

The same thread in several inboxes gives several independent reads. We dedupe by
thread, but on a borderline thread two inboxes can disagree. The gray bucket absorbs
most of this; a majority vote across the CC'd copies would stabilize the rest.

It is a probe, not a service. It writes nothing and re-triages every thread on each
run. Productionizing means an hourly schedule, a Supabase table keyed on thread id so
verdicts persist, and re-triaging only threads whose last message changed.

## Dismissing people (Slack wizard)

After a triage runs in the Slack wizard, a teammate can remove someone who is not
relevant to our goals, both from the current result and from every future run.
Reply in the triage thread (no @mention needed) or @mention the wizard anywhere:

- `drop jane@acme.com, bob@foo.io — not our market` records a dismissal.
- `undo jane@acme.com` restores them.
- `show dismissed` lists who is currently hidden.

A dismissal hides the person from all three buckets (awaiting reply, reroute,
worth a glance) on future runs. It is keyed on the prospect email (`who` in each
row). This is NOT contacted-ledger suppression: it only hides them from triage,
campaign sending is untouched. The list is a Supabase table read with the
service-role key, so it is team-wide and survives restarts. The handler requires
a real email for dismiss/undo, so a normal question or send is never hijacked.

The table is created by `wizard/migrations/2026-06-29_triage_dismissed.sql` (run
once against prod). Until then, dismissing reports that the store is not set up
and triage runs unfiltered, since `load_dismissed` fails open to an empty set.

## Feeding the /respond review queue

The `reply` bucket (people awaiting a real answer) is also the source for the
Slack `/respond` review queue. `wizard/triage.py` `needs_for_founder(email)` runs
this same probe scoped to one founder's inbox, applies the dismiss list, and
returns the structured `needs` rows (thread id, prospect, subject, priority) so
the queue can draft and send a reply per row. See the wizard architecture doc.

That queue does NOT mark a handled email via the dismiss store. A reply sent from
it lands in-thread, so on the next run this probe sees us as the last sender and
drops the thread into `skip` on its own, while a genuine new reply from the same
prospect re-surfaces as `reply`. Dismissal stays what it is: hiding people who are
not relevant, keyed on the prospect email, forever until undone.

## Files

- `reply_triage_probe.py` is the probe.
- It reuses `gog_auth`, `toolbox.primitives.gmail.lib`, and the `contacted` ledger
  that `run.py` and `reply_scan.py` already use.
- `wizard/triage_dismiss.py` is the dismiss list (parsing + the Supabase store);
  `wizard/triage.py` applies it via `apply_dismissals`; `wizard/slack_bot.py`
  routes the thread commands through `_handle_triage_edit`.
