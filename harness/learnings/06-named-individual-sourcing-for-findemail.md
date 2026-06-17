# Sourcing named individuals (researchers, big-tech staff) for findemail

The 2026-06-10 DTC flow sources *domains* and lets `findemail.find-exec` pick the
top exec. Some campaigns instead need *named people* (academics, employees at a
specific company) where you already know who you want. The path there:

1. **Fan out web-research agents, one per sub-segment**, each returning real
   people as `first_name|last_name|org|title|email_domain|subarea|why|source_url`.
   Require a real source URL per person — it doubles as a hallucination check.
2. **Dedup globally** (by name, and by name+domain) before enriching — the same
   person shows up in adjacent lanes (e.g. Google Research scientists land in
   both a "researchers" lane and a "Google" lane).
3. **`findemail.find` (name+domain → verified email)** at `--min-score 0` so you
   capture every score, then choose the floor by filtering the output CSV — no
   re-spend. Hunter verification is the real filter: a wrong name+domain returns
   nothing, so a fake person silently drops out.

## The verify rate is set by domain hygiene, not by the people

Measured on this run (200-contact agentic-ads campaign, 2026-06-14):

| Pool | Verify rate (emails found / candidates) |
|---|---|
| Researchers, round 1 (no domain guidance) | 60/85 = **71%** |
| Researchers, round 2 (told to prefer clean firstname.lastname domains, get the domain exactly right) | 43/47 = **91%** |
| Big-tech employees | 88/127 = **69%** |

Two levers moved the round-2 rate up 20 points:
- **Tell the sourcing agent the email domain gets verified against the mail
  server**, so it should give the address the person's real email actually uses
  (business schools and CS departments use subdomains: `gsb.columbia.edu`,
  `chicagobooth.edu`, `cs.princeton.edu`, `haas.berkeley.edu`, not the bare
  university domain).
- **Prefer institutions with clean `firstname.lastname@` patterns.** Schools that
  use opaque patterns (Ohio State's `lastname.number@osu.edu`) produce
  low-confidence guesses Hunter scores in the 40s-50s.

## Score floor: 70 is the deliverability line here

Below ~60, the "found" email is usually a pattern guess on an `accept_all`
domain (the server accepts anything, so Hunter can't truly verify) — e.g.
`su@osu.edu`, `sun@osu.edu` — and will bounce, hurting the sending domain.
At score ≥70 the addresses were correct `firstname.lastname` forms. This run
shipped at **score ≥70**; final 200 had median 98, floor 81 after taking the
best N per segment.

## Over-source, because corp emails verify lower

Big-tech corporate emails verify ~10 points lower than academic ones and far
lower than DTC founder addresses (which were ~100% via find-exec). Source
~2× the target for corporate segments so the score floor doesn't force you below
quota. Keep the research agents' IDs — re-message them for a second round
instead of re-sourcing from scratch.

## Cost

~260 Hunter credits for 200 verified contacts (1 credit per successful
email-finder call; misses are cheap). Well inside Starter's 2,000/mo. NOTE: the
`find` subcommand has no `--cache` flag (only `find-exec` does), so a re-run
re-spends — enrich once, filter the output CSV repeatedly.
