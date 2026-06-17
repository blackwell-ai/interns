# Taste-data outreach list: 200 contacts who benefit from product quality / taste data

Date: 2026-06-16. Source: internal request (Samarjit) to build a 200-person list
across four buyer categories who would benefit from objective product-quality /
taste data (data on how good consumer products are and how much people keep them).

## The four categories (50 each)

1. **Subscription & curation services** (Stitch Fix, FabFitFun, meal-kits, niche
   boxes). Better taste data lifts match rates, cuts returns, lowers churn.
2. **Retail buyers & category managers** (mass, specialty, marketplace, grocery).
   A quality signal de-risks what to stock and in what quantity.
3. **Brand incubators & private-label developers** (Amazon aggregators, DTC brand
   studios, retailer owned-brands, product-dev firms). Taste data maps where the
   quality gaps are, which is the "what should we build" answer.
4. **Recommendation & affiliate media** (Wirecutter-style review labs, tech and
   lifestyle review desks, niche "best of" sites). Data-backed rankings protect
   credibility.

## What was built

200 unique, Hunter-verified work emails, 50 per category. Deliverable:
`skills/autonomous-outreach/taste-data/master_200.csv` plus four per-segment
files. Columns: email, first_name, last_name, title, org, domain, segment,
subarea, why_relevant, source_url, email_score, email_status. The `why_relevant`
column is a ready-made per-contact personalization hook.

## Method (named-individual sourcing, per learnings/06)

- **16 web-research agents** (4 per category, one per sub-segment) each returned
  real named people as first_name, last_name, domain, org, title, subarea,
  why_relevant, source_url, with a required source URL per person as a
  hallucination check. 541 raw rows, deduped to **529 unique candidates** (153
  domains).
- **`findemail.find --min-score 0`** (Hunter Email Finder) over all 529 -> **401
  emails found**, then filtered to status not invalid, non-generic local-part, and
  **score >= 70** -> 378.
- **Ledger dedup at sourcing time** via the `suppression` + `contacted` tables
  (learnings/07): suppression held 4,303 recipients; **5 candidates were already
  contacted** (Nordstrom, Stantt, Atlas Coffee, Hungryroot, Bokksu) and dropped.
- **Best 50 per category by score** -> 200. Score floor came out at **81**, median
  **96** (well above the 70 deliverability line). Status mix: 127 valid, 55
  accept_all, 18 unknown; 0 invalid.

## Cost

**401 Hunter search credits** (728 -> 1,129 of 2,000 used; misses are free, so the
128 not-found candidates cost nothing). ~871 credits left this cycle.

## Status / important

- **Sent 2026-06-16: all 200, 0 failures**, from samarjit.deshmukh.29@dartmouth.edu,
  co-founders CC'd, paced 8s, each claimed in the suppression ledger before send.
  Subject: "Stanford Student Question - Thoughts on Product Quality Data". A 4-email
  canary (one per segment) confirmed delivery first.
- **Template:** one body with a per-segment benefit line, intro "building in the
  ecommerce space", "$500 million" kept. Benefit lines: retail buyers ->
  "de-risk restocking decisions"; subscription -> "reduce returns and increase
  match rates"; incubators -> "maps where the quality gaps are, i.e. where a new
  or private-label product can win"; reco/affiliate -> "enrich reviews with
  defensible evidence". Sender + embedded templates:
  `skills/autonomous-outreach/taste-data/send_taste_data.py`.
- **Replies/bounces:** check the Dartmouth inbox over the next days
  (`gmail.replies`, `gmail.bounces`).
- Yield here (401/529 = 76%) was far better than the 2026-06-16 web-sourced DTC
  brand run (18%), because these are named people at known mid-to-large orgs with
  good Hunter coverage, confirming `harness/learnings/08`.

## Why this is company-relevant

Blackwell works in agentic commerce ([[overview]]). This list is a campaign asset
for a product-quality / taste-data offer, and the segmentation also maps who makes
product-quality and assortment decisions across the consumer stack.
