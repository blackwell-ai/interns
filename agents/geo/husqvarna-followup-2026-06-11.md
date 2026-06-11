# Husqvarna follow-up, June 11, 2026: internal meeting notes

Customer-facing deck: husqvarna-followup-2026-06-11.pdf. These notes stay
internal. Goal: close a $1,000 Phase 1.

## Updated facts (all re-checked June 11)

- BBB on the husqvarna.com/us entity (Husqvarna Professional Products, Inc.,
  Charlotte NC): A+, 1.03/5 over 58 reviews, 204 complaints in 3 years. The
  re-pull reads slightly worse than the June 2 figures.
- Trustpilot, live read: 1.4/5, 872 reviews, 81% one-star, still unclaimed.
  The sidebar on that page advertises Mammotion and Navimow.
- Agent endpoints still 403. No checkout. Price exists only in JSON-LD.
- Nothing on the product pages answers the under-trees objection.
- 430X support page still serves Product schema; 450X/450XH still return 200.
- Rufus (4 prompts, manual): iQ described correctly as wire-free, top pick on
  the two-acre question, present in all four answers. Lost "best overall" to
  Mammotion on reviews (4.4/87 vs 3.5/22). Rufus rarely recommends anything
  under 4.0 stars; its median pick has ~3,000 reviews (Amalytix).
- Corpus sweep: PCWorld, Reviewed, SlashGear, Lawn Love and BBC Gardeners'
  World all still test wired models or omit the brand. Mammotion's own blog
  ranks #1 in Google for "best robot lawn mower 2026". Only 4 of 18 ranking
  pages mention the iQ, all small blogs. The one dedicated iQ YouTube video
  has 11K views against 40-135K for the big roundups.

## Talking points

- Lead with the re-checks: every critical finding reproduced this morning,
  and the corrected BBB entity made the number worse, not better.
- Rufus is the useful contrast: it reads their catalog and gets the product
  right. The open-web engines read PCWorld and Reddit and get it wrong. The
  product data is fine. The corpus is the problem, and the corpus is the
  scope.
- llms.txt only if they raise it: agree, it doesn't drive rankings, it's
  downgraded in our methodology. One sentence, move on.
- Do not re-mention the audit being "automated."

## Objections

- "We can do this ourselves." The schema work, yes, and the spec hands it to
  your team. The measurement harness is the part you can't reproduce: six
  engines, two passes, frozen baseline, plus Rufus. Take the specs; we still
  measure.
- "$1k for what?" Point at the scope page. Fixed fee, fixed deliverables,
  named re-test date.
- "Rufus already ranks us fine." Because it reads your catalog. Buyers start
  in ChatGPT and Google, which read the corpus. We close that gap.

## The ask

"Same structure as our other Phase 1 engagements: $1,000 fixed, scope on this
page, re-benchmark by [date]. Can we start this week?" Then stop talking.
