# Reuzel reputation corpus (phase 3)

Run 2026-06-22 via `/browse` headed + stealth. Captures in `assets/reputation-*`.
Reuzel's reputation lives in retail (Amazon, Ulta, Sally Beauty) and the
barbershop/grooming community, not on consumer aggregators.

## Live-confirmed this run

- **Reddit**: live and positive. Threads include "My favorite Reuzel" and "Reuzel
  Blue Pomade, Strong Hold, High Shine $24 ~ REVIEW," with replies like "amazing
  scent, applies easily, and washes out without any effort" and "a strong hold
  pomade, it stays malleable throughout the day and doesn't flake or dry out."
  Confirms the strong grooming-community sentiment and the Schorem heritage appeal.
  Capture: `assets/reputation-reddit-2026-06-22.png`.
- **Trustpilot**: 1 review, 3.7, **unclaimed**. Effectively no Trustpilot footprint.
  Capture: `assets/reputation-trustpilot-2026-06-22.png`.

## No profile (documented N/A)

- **BBB**: no Reuzel profile (search returned no results). Capture:
  `assets/reputation-bbb-2026-06-22.png`. N/A.
- **ConsumerAffairs**: no profile (N/A). Reuzel is a grooming brand with no
  ConsumerAffairs listing.

## Machine-readability gap

Per `recon-2026-06-22.md`, the Reuzel PDP carries no server-rendered
`aggregateRating` despite four review apps (Okendo, Yotpo, Loox, Judge.me) loaded
client-side. So the genuine community sentiment above is invisible to non-JS
crawlers. Same core gap as the other two audits: real reputation, near-zero
machine-readable signal.

## YouTube and retailer (added to complete the corpus)

- **YouTube**: strong grooming-creator coverage. Titles include "Which of these 4
  Hollands finest Reuzel Pomades is best for you?" and "Wow, the Difference is Huge:
  Reuzel Matte Clay VS Fiber". Capture: `assets/reputation-youtube-2026-06-22.png`.
- **Retailer (Amazon)**: Reuzel pomades rate 4.2 to 4.6 / 5, with review counts from
  356 up to 5,452 on the flagship. Capture:
  `assets/reputation-retailer-amazon-2026-06-22.png`. Genuine retail reputation that
  the PDP does not expose as server-rendered aggregateRating (the central Reuzel
  finding).
