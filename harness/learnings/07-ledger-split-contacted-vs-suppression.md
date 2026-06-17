# The ledger is split across two tables — check both, or you'll think a contacted list is fresh

## What happened (2026-06-15 advertising campaign)

I built a 200-contact list, presented it as "200 fresh emails," and only at
**send time** discovered that **71 of them (all 70 DTC founders + 1 big-tech
contact) had already been cold-emailed** in the 2026-06-10 campaign. The
no-double-contact guarantee held — the send-time claim skipped them — but the
*planning* was wrong: the user asked for 200 and the real number of contactable
people was 129. The failure surfaced five steps too late.

## Root cause: two senders, two different ledger tables

There are two send paths in this repo and they record "we contacted X" in
**different tables**:

| Sender | Mechanism | Writes to |
|---|---|---|
| `gmail.send` primitive (harness) | `claim_contact` RPC, `sent_by = auth.uid()` | **`contacted`** |
| `send_fast.py` / `campaign.sh` (autonomous-outreach) | service key inserts directly into the PK | **`suppression`** |

Why the split exists: `contacted.sent_by` is `NOT NULL references auth.users(id)`,
so an insert needs a real user JWT (`auth.uid()`). The headless volume sender
runs on the **service key**, which has no `auth.uid()`, so it can't write
`contacted`. It uses `suppression`'s `PRIMARY KEY (channel, recipient)` as its
atomic dedup instead — overloading the opt-out list as the contact ledger.

The 2026-06-10 campaign ran through `send_fast.py`. So all ~166 of its
recipients landed in **`suppression`**, and `contacted` stayed **empty**.

## Why I didn't catch it during sourcing

Honestly: I checked the wrong table and trusted one query.

1. **I queried `contacted`, got 0 rows, and concluded "ledger empty, all fresh."**
   `contacted` is what the schema and `PROTOCOL.md` call "THE invariant"
   (`UNIQUE (channel, recipient)`), so I treated it as authoritative and never
   queried `suppression` (2,808 rows, where the real send history lived).

2. **I reused a prior campaign's OUTPUT as fresh INPUT without checking
   provenance.** The DTC 70 came from `samarjit_enriched.csv` /
   `samarjit_final_queue.csv` — literally the enriched results and send queue of
   the 2026-06-10 run. I described them as "ready now, free." They were "ready"
   *because they had already been emailed.* The clues were all there and I read
   past them: `INDEX.md` says autonomous-outreach "Last run 2026-06-10";
   `SKILL.md` says "166 sends" and "re-running the same bank sends to nobody
   new." Pre-enriched data should trigger the question "who made this, and did
   they then contact these people?"

3. **I deduped at send time instead of sourcing time.** The right moment to
   check the ledger is *before* building the list (and before spending Hunter
   credits), not at the send boundary. `learnings/05` even documents this exact
   lever as a known TODO: "Pre-filter domains against the suppression ledger
   before enriching." I didn't apply it.

## The fix

**Use `check_contact` as the dedup oracle, not a raw table query.** The
`check_contact(channel, recipient)` RPC already unions both tables — it returns
`'suppressed'` if the recipient is in `suppression`, `'contacted'` if in
`contacted`, else `'new'`. It's `security definer` and doesn't depend on
`auth.uid()`, so the service key can call it. Had I called `check_contact`
instead of hand-rolling `GET /contacted`, I'd have caught all 71 immediately.

Concretely, for any future list build:

1. **Dedup at sourcing time.** As soon as you have candidate emails (before
   enrichment spend, before presenting a list), run each through `check_contact`
   (or query BOTH `contacted` AND `suppression`). Drop or flag the hits, and
   over-source to backfill.
2. **Never trust one table.** "Is the ledger empty?" must check `contacted` +
   `suppression`. A single-table query is how a 2,808-row history reads as zero.
3. **Treat reused data as contacted until proven otherwise.** If a leads/
   enriched CSV is the output of a prior run (check `INDEX.md` last-run +
   `SKILL.md` changelog), assume its people were emailed and verify before reuse.

## The deeper architectural debt (worth fixing)

The split itself is the trap. Two recommendations, in order of preference:

- **Give the volume sender a service-role path into `contacted`** (e.g. a
  `claim_contact_service(channel, recipient, sent_by_label)` RPC that doesn't
  require `auth.uid()`), so *one* table is the contact ledger and `suppression`
  goes back to meaning only opt-outs/bounces. Then `check_contact` and a plain
  `contacted` query agree.
- **At minimum, document the split loudly** in `TOOLBOX.md` and the
  autonomous-outreach `SKILL.md`: "the volume sender records contacts in
  `suppression`, not `contacted` — dedup must check both / use `check_contact`."

Conflating "we emailed them" with "they opted out" also has a quieter cost: a
cold-emailed person can never be deliberately re-contacted via `allow_recontact`,
because suppression always wins over `force_claim`. That's fine for one-shot cold
outreach but wrong if a follow-up sequence is ever intended.

## One-line takeaway

The contact history is split across `contacted` (harness sender) and
`suppression` (volume sender). Dedup with `check_contact` (it unions both) at
**sourcing** time, and never read pre-enriched data as fresh without checking
who already sent to it.
