# BeautyStat reputation corpus (phase 3)

Run 2026-06-22 via `/browse` headed + stealth. Captures in `assets/reputation-*`.

The pattern: BeautyStat has genuine, strong human reputation and almost no
machine-readable third-party aggregator presence. This is the audit's "reputation
real but not machine-readable" finding, confirmed live.

## Live-confirmed this run

- **Trustpilot**: 0 reviews, **0.0**, **unclaimed profile**. BeautyStat has no
  Trustpilot footprint at all. Capture:
  `assets/reputation-trustpilot-2026-06-22.png`.
- **Reddit**: live, and notably positive. Threads include "Has anyone tried
  beautystat vitamin c? Is it good?" with replies like "10/10! licensed esthetician
  here and it's honestly the best vitamin c i've ever used" and "Couldn't tolerate
  10% liquid L-ascorbic acid but my skin loves the BeautyStat 20%." Confirms the
  esthetician-praise and tolerability story in the brain. Capture:
  `assets/reputation-reddit-2026-06-22.png`.

## No profile (documented N/A)

- **BBB**: no BeautyStat profile. Search returned no results. Capture of the empty
  search: `assets/reputation-bbb-2026-06-22.png`. N/A.
- **ConsumerAffairs**: no profile (N/A). BeautyStat is a DTC skincare brand with no
  ConsumerAffairs listing; not applicable to this category the way it is for a
  mattress brand.

## Where the reputation actually lives

On-site Yotpo widget (loads in JavaScript, no `AggregateRating`/`Review` schema, so
invisible to non-JS crawlers, see `recon-2026-06-22.md`), plus retail ratings on
Sephora and Amazon, plus founder/chemist authority (Ron Robinson) and press. None
of it is structured for an AI engine to quote. That is the central reputation gap:
the sentiment is strong and the machine-readable signal is near zero.

## YouTube and retailer (added to complete the corpus)

- **YouTube**: real independent reviews of the hero product. Titles include "Is
  BeautyStat Universal C Refiner Really That Good?" and "BeautyStat Universal
  Vitamin C Skin Refiner Review & How to (Non-Sponsored)". Capture:
  `assets/reputation-youtube-2026-06-22.png`.
- **Retailer (Sephora)**: BeautyStat products carry roughly 4.5-star ratings on
  Sephora. Capture: `assets/reputation-retailer-sephora-2026-06-22.png`. This is
  exactly the gap: strong retail and video reputation that an AI engine cannot read
  off beautystat.com, because the on-site Yotpo widget has no AggregateRating schema.
