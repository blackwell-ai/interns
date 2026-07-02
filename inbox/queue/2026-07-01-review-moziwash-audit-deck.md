---
title: Review Mozi Wash audit deck before anything is sent
created: 2026-07-01
created_by: geo
assignee: armaan
priority: high
claimed_by:
claimed_at:
---

## Task

The full nine-phase AI visibility audit for moziwash.com is done and gated
(verify-evidence PASS, zero dashes in HTML and PDF text, 18-page visual QA).
Per the charter, no deck reaches a customer without human review, so this one
is parked here.

Draft deck: `brain/customers/documents/moziwash-audit.pdf` (18 pages).
Working source: `agents/geo/moziwash/moziwash-ai-visibility-audit.html` with
captures in `agents/geo/moziwash/assets/`. Durable findings:
[[moziwash]] (`brain/customers/moziwash.md`). Per-pass evidence:
`agents/geo/moziwash/battery-log.md`.

Headline: composite 60 (C, one point above D). Mozi Wash was named in 1 of 8
engine passes (a Gemini render that did not repeat on re-run); Laundry Sauce is
named in every live answer on every engine and wins the "Mozi Wash vs Laundry
Sauce" head-to-head on ChatGPT. Reputation an engine can see: no aggregator
profiles, Amazon 3.8 to 4.2 stars on ~1,500 ratings, r/laundry led by
packaging-failure complaints. Strengths: full UCP layer and the deepest
llms.txt in the set.

**Engagement context (confirmed 2026-07-01 from the Dartmouth email thread
"Stanford Student Question"):** this is a requested audit, not a cold
leave-behind. Ethan Zhou cold-emailed Geno Quaid (geno@moziwash.com) on
2026-06-30; Geno asked for proof ("I get 5-10 of these emails a week... want to
make sure that you can deliver"); Armaan replied with Public Goods results and
offered the audit; Geno wrote back "Okay, please send it over. I will review and
if there is something worth chating about, Ill reach out to connect." Recipient
when approved: Geno Quaid, as a reply on that thread from Armaan's Dartmouth
address. Full context in `brain/customers/moziwash.md`. The GEO agent has not
contacted and will not contact the customer.

**Framing note for the review:** Geno's ask was proof of delivery, and he
committed only to reading it. The flagship finding (named in 1 of 8 passes,
ChatGPT inventing an inverted brand profile in the head-to-head with Laundry
Sauce) answers his question directly. Check that the deck's two-phase $1,000
close reads right for someone who has not agreed to a call.

**Reply draft ready (2026-07-01):** a Gmail draft to Geno (cc Ethan, Samarjit,
Shamit) sits in Armaan's Dartmouth drafts as a reply on the thread, voice
matched to the outreach Supabase voice card, with `moziwash-audit.pdf`
attached (created via gog after the Gmail MCP path turned out not to support
attachments). Nothing has been sent.

## Done when

- Armaan (or another founder) has read the deck and either approved it,
  requested changes, or killed it.
- If approved: Armaan sends the prepared draft (or edits first), and the
  result is noted here and in the brain file.
