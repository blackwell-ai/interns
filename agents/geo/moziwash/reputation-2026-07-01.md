# Mozi Wash reputation corpus (phase 3)

Captured 2026-07-01 via headed /browse (stealth). Captures in
`assets/reputation-<source>-2026-07-01.png`. Fixed six-source list per the
methodology. Session notes: Amazon read on a logged-in profile (delivery address
visible); ratings and counts are not personalized so the read stands, disclosed
here. All other sources logged out.

## Source-by-source

- **Trustpilot: N/A, no profile.** trustpilot.com/review/moziwash.com returns
  404 ("page could not be found"); a Trustpilot search for "mozi wash" returns
  only car washes and unrelated companies. The brand has never claimed or
  accumulated a Trustpilot presence. Capture: reputation-trustpilot (404 page).
- **BBB: N/A, no profile.** bbb.org search for "Mozi Wash" (USA) returns "No
  results". No profile, no complaints, no accreditation. Capture: reputation-bbb.
- **ConsumerAffairs: N/A, no profile.** On-site search for "mozi wash" returns
  only unrelated washer-brand pages (Whirlpool, Midea, Panda). Capture:
  reputation-consumeraffairs.
- **Reddit: present and MIXED-NEGATIVE, the live sentiment surface.** Six-plus
  threads in r/laundry (739K weekly visitors), organic and substantive:
  - "Mozi Wash" (7mo, 7 votes, 53 comments): scent praised, but two users report
    tins RUSTING and leaking from the seam, replacements also leaking ("a
    recurring packaging issue rather than an isolated defect"); one user
    "not even close to Tyler wash... 2 washes per trial bottle"; another "Not a
    fan. Mozzi gave poor cleaning performance and really no lasting scent...
    Hard pass"; a top-1% commenter is cautiously positive on formula 3.0
    ("surprisingly legit"). Capture: reputation-reddit-thread.
  - "Mozi Wash cleaning power?" (1mo, current sentiment): OP asks if the rust /
    leak / formula-consistency issues are fixed; top-1% commenter jtfolden
    replies "Mozi wash is pretty horrible. In fact Jeeves NY rated it as one of
    the worst detergents of 2025. It's way too expensive considering the lousy
    performance and the only nice thing about it is the fragrance." (Jeeves
    claim not independently verified; attributed to this comment.) Capture:
    reputation-reddit-thread2.
  - Also: "My husband went out of town so I got a folding bone and Mozi wash.
    AMA" (57 votes, 36 comments, tone playful), "Best premium laundry
    detergent" (2y), two smaller threads. Search capture: reputation-reddit.
- **YouTube: thin and paid-skewed.** Search "mozi wash review": the first
  render showed Mozi's own sponsored shopping shelf plus a moziwash.com search
  ad above the results; the captured render shows a competitor's sponsored slot
  (Charlie's Soap), i.e. the ad shelf rotates. Organic in both renders is
  shorts (53K-view review short, one disclosing "free product", one asking
  "why the hell is...") and two 1-year-old small reviews ("Tech Reviews with
  phil" 1.6K views; Isabel Pizarro 846 views with an Amazon affiliate link).
  No major reviewer coverage. Capture: reputation-youtube.
- **Retailer (Amazon): PRESENT, active storefront, ratings well below the
  on-site claim.** Brand storefront with heavy sponsored placement ("5K+ bought
  from this brand in past month", Small Business badge). Per-scent ratings in
  this render: Cozy Cashmere 3.9 (491 ratings), Alpine Woods 3.8 (339), Central
  Coast 4.1 (319), Sugar Dew 4.2 (200), Vanilla Moon 4.2 (104), Free and Clear
  4.2 (29), Golden Hour 3.9 (16). Roughly 1,500 visible ratings averaging about
  4.0. Category neighbors on the same results page: Tyler Glamorous Wash 4.7
  (10K), Tyler Glam Wash 4.6 (8.5K), Dirty Labs 4.3 (5.1K, EPA Safer Choice +
  EWG Verified badges), Molly's Suds 4.6 (22.9K), Zum 4.6 (13.1K), The
  Laundress Signature Isle 4.2 (1.6K). Capture: reputation-retailer-amazon.

## The headline split

The site's own llms.txt claims "4.8 stars across 40,000+ reviews. Trusted by
100,000+ customers" (first-party Okendo corpus, on-site only). The open web an
AI engine can retrieve tells a different story: ~4.0 average across ~1,500
Amazon ratings, r/laundry threads led by packaging-failure and
weak-cleaning complaints, zero presence on all three review aggregators, and
YouTube coverage that is mostly the brand's own ads. Nothing links the entity to
any of it: homepage Organization sameAs carries only social links (plus six
empty strings) and no AggregateRating markup exists on any PDP, so even the
favorable first-party corpus is invisible to machines.

## Claimed/unclaimed status

- Trustpilot / BBB / ConsumerAffairs: no profile to claim; all unclaimed.
- Amazon: brand-operated storefront (claimed, actively advertised).
- Reddit / YouTube: organic third-party surfaces; no observed brand replies in
  the threads read.
