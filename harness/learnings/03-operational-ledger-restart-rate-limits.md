# Operational: the ledger is truth, restart-safety, and rate limits

## 1. The ledger is the source of truth for send progress — never Gmail search

Mid-run I checked "did the sends go out?" with a Gmail **search**
(`in:sent subject:...`) and it returned the *old* count. I concluded sends were
failing and **killed a healthy run**. They weren't failing — Gmail's search
index lags **minutes** behind actual sends. The Supabase `suppression` ledger,
written synchronously as each send completes, showed the truth: 40 sent, 0
failed.

**Rule:** for live send progress, count rows in the ledger
(`suppression` / `contacted`), not the Sent folder via search. The provided
poll pattern:

```bash
curl -s -H "apikey: $KEY" -H "Authorization: Bearer $KEY" \
  -H "Prefer: count=exact" -H "Range: 0-0" \
  "$SUPABASE_URL/rest/v1/suppression?reason=ilike.*blackwell%20volume*&select=recipient"
# read the Content-Range header: 0-0/<total>
```

Corollary gotcha: `send_fast.py`'s CSV log is **buffered** (no per-row flush),
so the on-disk log looks empty mid-run too. Don't use it as a liveness signal;
use the ledger. (A per-row `flush()` would fix the log, but the ledger is the
better signal regardless.)

## 2. Claim-before-send + a UNIQUE constraint makes runs safely restartable

The one genuinely great property: every recipient is `claim`ed in the ledger
(insert; `UNIQUE(channel, recipient)`; conflict → skip) **before** the send. So
when I killed and relaunched the run, the already-sent 40 simply skipped on the
re-scan — **zero double-sends**, no manual state to reconcile. The final ledger
proved it: 242 unique rows, 0 duplicates. This invariant is what turned my
misread from a disaster into a non-event. Preserve it in every send-class flow.

## 3. "Parallel by default" has an exception: rate-limited provider APIs

The harness ethos is speed/parallel-by-default, no throttling (spec §9). That's
right for *our* sends (Gmail took the volume fine), but **wrong for metered
third-party enrichment APIs**. Hunter rate-limited at concurrency 12 and the
tenacity retries **silently exhausted into "not found"** — a dangerous failure
mode, because a rate-limited give-up is indistinguishable from a genuine miss in
the output. Two takeaways:

- Default enrichment primitives to **conservative concurrency** (findemail is
  now 5).
- A rate-limited-exhaustion should be **logged distinctly** from a true miss, so
  low yield is diagnosable instead of looking like "this segment has no
  contacts." (Open improvement for `findemail`.)

## 4. Known debt: two dedup ledgers that don't talk to each other

There are **two** no-double-contact systems and they use **different tables**:

- The autonomous sender (`send_fast.py`) claims in **`suppression`** — this is
  where all ~2,800 real contacts live (Giftly seeds + every send so far).
- The harness primitive `gmail.send` claims in **`contacted`** (via the
  `claim_contact` RPC).

A harness-native cold-email flow built on `gmail.send` would therefore **not**
dedup against the suppression history and could re-email everyone. Until these
are reconciled, **any cold-email flow must use the suppression-based path**
(`send_fast.py`), which is why `campaign.sh` (file 04) wraps that and not
`gmail.send`. Reconciling the two ledgers (or pointing `claim_contact` at the
same table the campaign uses) is the cleanest fix and is worth doing before the
next agent builds on `gmail.send`.
