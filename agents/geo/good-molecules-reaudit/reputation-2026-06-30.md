# Good Molecules reputation corpus, 2026-06-30

Phase 3 of the re-audit. Live captures in `assets/reputation-*.png`, read the same day.
Hero product for context: Discoloration Correcting Serum (4.3 / 7,624 reviews at the
June 1 audit, on the brand's own PDP).

## Sources

- **trustpilot**: 2.8 / 5 across only 4 reviews. Profile is **unclaimed**, and
  Trustpilot flags "no history of asking for reviews," so the score is thin and not
  representative. Category tag is Skin Care Clinic. Capture:
  reputation-trustpilot-2026-06-30.png.

- **bbb**: N/A, no profile. A BBB search for "Good Molecules" returns no results, and
  no accredited or unaccredited business profile exists. Capture of the no-results page:
  reputation-bbb-2026-06-30.png.

- **consumeraffairs**: N/A, no profile. A ConsumerAffairs search for "Good Molecules"
  surfaces only an unrelated 2015 news article, no brand review page. Capture:
  reputation-consumeraffairs-2026-06-30.png.

- **reddit**: active and mixed-to-positive, the strongest text corpus. Discussion spans
  r/30PlusSkinCare, r/SkincareAddiction, r/Melasmaskincare, r/koreanskincare,
  r/IndianSkincareAddicts, r/Blackskincare, and r/EuroSkincare. Reddit's own summary
  splits sentiment: many call the Discoloration Correcting Serum effective for
  post-acne red marks and PIE, while several report little change on stubborn
  hyperpigmentation and melasma. A representative r/30PlusSkinCare thread ("What do you
  think of good molecules discoloration correcting serum?") drew 43 votes and about 100
  comments. Capture: reputation-reddit-2026-06-30.png.

- **youtube**: active creator corpus and the richest video channel. Multiple dedicated
  review videos and Shorts, including a "2 months trial... detailed and honest review"
  at roughly 33K views, plus haul and try-on Shorts. Sentiment skews toward detailed,
  favorable long-run trials. Capture: reputation-youtube-2026-06-30.png.

- **retailer (Amazon)**: strong. The Discoloration Correcting Serum (1 fl oz) holds
  4.4 / 5 across about 15.2K ratings, carries an Amazon "Overall Pick" badge, and shows
  20K+ bought in the past month at $11.94. Adjacent Good Molecules listings (Blemish
  Scar & Discoloration Duo, Brightening Skincare Duo) sit at 4.5 with hundreds of
  ratings. Good Molecules is a Beautylish-exclusive DTC brand, so Amazon is the main
  third-party retailer engines fall back to, and its review depth here is real.
  Capture: reputation-retailer-amazon-2026-06-30.png.

## sameAs / entity linkage

The recon homepage JSON-LD (`recon-2026-06-30.md`) declares OnlineStore, WebSite,
ContactPoint, and SearchAction types but no `sameAs` array pointing at any of these
reputation profiles. So the genuine reputation, strong on Amazon, active on Reddit and
YouTube, is stranded off the machine-readable entity. This is the reputation finding:
the rating exists but is not connected to the brand's structured identity, which is the
part on-site schema fixes can move (link out via sameAs) and the part off-site seeding
(reviewer/UGC panel) can grow.

## Read

Reputation is bimodal. Third-party retailer and social proof are solid (Amazon 4.4 /
15.2K, active Reddit and YouTube), while the formal review aggregators are weak or
absent (Trustpilot 2.8 on 4 unclaimed reviews, no BBB or ConsumerAffairs profile). The
weakness is not the sentiment; it is that the strong reputation lives on Amazon and in
UGC and is neither claimed on the aggregators nor linked from the brand entity.
