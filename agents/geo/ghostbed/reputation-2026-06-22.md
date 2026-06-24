# GhostBed reputation corpus (phase 3)

Run 2026-06-22 via `/browse` headed + stealth. Captures in `assets/reputation-*`.

## Live-confirmed this run

- **Trustpilot**: 3.5 / 5 over 172 reviews. Profile claimed September 2025, paid
  Trustpilot subscription. Capture: `assets/reputation-trustpilot-2026-06-22.png`.
  Matches prior recon.
- **BBB (GhostBed entity)**: B+ rating, 87 complaints in 3 years. Capture:
  `assets/reputation-bbb-2026-06-22.png`. The customer-review star average
  (prior recon: 1.61 / 5 over 36) sits behind the Reviews sub-tab and was not
  re-extracted this run; cite as prior recon, not re-confirmed.
- **BBB entity split confirmed**: search returned two separate profiles, GhostBed
  (`/profile/mattress/ghostbed-0633-90577536`, B+) and the parent Nature's Sleep
  LLC (`/profile/mattress/natures-sleep-llc-0633-90012011`). This is the
  unlinked-entity finding, confirmed live.

## Reddit (live-confirmed after login)

- **Reddit**: search now returns real threads ("Did anyone purchase the
  ghostbed?", "Ghostbed on sale - anyone bought it?"). Sentiment is mixed:
  positive owner reports ("the mattresses are very nice. Sleep has noticeably
  improved since the purchase", twin XL + adjustable base set) alongside generic
  foam-mattress skepticism. Capture: `assets/reputation-reddit-2026-06-22.png`.
  Consistent with prior recon's split read.

## Bot-walled this run (documented limitation, not a skipped phase)

- **ConsumerAffairs**: blocked, snippet only. The profile at
  `/mattresses/ghostbed.html` returns "Access to this page has been denied"
  (PerimeterX bot detection, not an account gate, so login does not clear it)
  under both curl and headed stealth. Prior recon figure (1.5 / 5 over 120,
  unclaimed) is NOT re-confirmed live. Capture shows the denial page.

## Entity linkage

`Organization` schema on GhostBed's own pages carries `sameAs: none` (see
`recon-2026-06-22.md`), so none of the above is linked to the brand entity. The
on-site first-party widget (4.8 / 10,223 on the Luxe Hybrid PDP) diverges sharply
from the off-site corpus above.

## Retry note

ConsumerAffairs and Reddit walls may clear from a logged-in browser session. If
re-run with login, replace the two "blocked" lines with live captures and figures.

## YouTube and retailer (added to complete the corpus)

- **YouTube**: active independent reviewer ecosystem. Titles include "GhostBed
  Mattress Reviews | Classic vs Luxe vs Flex (FULL GUIDE)", "GhostBed Mattresses
  EXPLAINED by GoodBed", "GhostBed Mattress One Year Follow Up Review", and "GhostBed
  Costco vs Most Expensive Tempur-Pedic Honest 6 Month Review". Capture:
  `assets/reputation-youtube-2026-06-22.png`. Sentiment skews evaluative/positive;
  none of this video reputation is linked to the brand entity.
- **Retailer (Amazon)**: GhostBed Luxe and related models rate 4.4 / 5 over 7,669
  reviews and 4.2 / 5 on another model. Capture:
  `assets/reputation-retailer-amazon-2026-06-22.png`. Matches prior recon's
  "Amazon per-model 3.9 to 4.4". This is the strongest off-site rating and, like
  the rest, is not linked to the site entity via sameAs.
