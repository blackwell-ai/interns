# Outreach learnings

What has actually worked. The outreach agent reads and extends this file.

## Giftly-era contacts are suppressed (2026-06-10)

All prior outreach was extracted from `~/Documents/Giftly` (send logs:
`outreach/outreach-log.csv` — the April Throne-merchant campaign, 1,693 sends
incl. 159 bounces, sent from the retired trygiftly account; and
`outreach-retailers/outreach-log.csv` — the May retailer campaign, 876 sends
incl. 120 bounces, from the Dartmouth account), deduped, and cross-checked
against 1,275 sent messages in the Dartmouth mailbox (sweep found **zero**
recipients missing from the logs — the logs are complete).

**2,561 unique addresses now sit in the Supabase `suppression` table**
(reason-tagged `giftly-era outreach (...)`), which `gmail.send` checks before
every send with no override — no one from the Giftly era can ever be
cold-emailed again by any harness flow. This includes current customer
contacts (e.g. nils@beautylish.com, the husqvarnagroup.com contacts): correct
for cold sends; replies and manual email are unaffected. To deliberately
re-approach someone suppressed, a human removes the row first.

## The cold email that landed the current customers (observed June 10, 2026)

Source: Armaan's Dartmouth sent mail. The same template opened the Beautylish/
Good Molecules, Public Goods, and Husqvarna threads in May 2026:

- **Subject:** "Stanford Student Question - thoughts on AI retail tools"
- **Body shape:** 3 short sentences — (1) "We're Stanford/Dartmouth students
  curious how {Company} is thinking about AI, given 50 million people now shop
  with ChatGPT daily." (2) ask for a quick 10-minute call; (3) fallback ask:
  "even a one-sentence response" with their thoughts
- Sent from armaan.priyadarshan.29@dartmouth.edu, co-founders CC'd
- Replies came fast (Nils Johnson replied same day, May 21) and threads
  converted to pitch calls within hours

Why it works (hypothesis): student framing + tiny fallback ask lowers the
reply bar; the .edu sender domain supports the framing and survives filters
(one Beautylish reply did get tagged "[ AREA1 SPAM ]" — watch deliverability).

Caveat: the team is now a YC company, not just students — this framing may age
out; revisit before reusing at scale.
