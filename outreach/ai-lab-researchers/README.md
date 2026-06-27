# AI lab researcher email list

189 verified work emails of AI researchers and technical staff at OpenAI,
Anthropic, Google, Google DeepMind, and Stripe. Built 2026-06-26 for cold
outreach about Blackwell's agentic-commerce / product-quality work.

## Files

- `researcher-emails.csv` — name, company, email. 189 rows, deduplicated.

## How it was built

Origami (Blackwell org) researched a pool of 459 people in technical and
research roles at the five companies, prioritizing anyone whose profile mentions
agentic commerce, AI shopping, checkout, or payments. Origami table (full 459
with all candidates): https://origami.chat/workspace/dab856c2-b05e-45b0-b499-4e762dd57565?table=777812f8-ece7-4982-a625-ec82411d4bb3

This CSV is the filtered subset: only people whose verified email is at the
company's own domain (google.com, anthropic.com, openai.com, stripe.com and the
Stripe aliases stri.pe / stripe.io, deepmind.com, youtube.com).

## Counts

Google 101, Anthropic 39, Stripe 25, OpenAI 14, Google DeepMind 8, YouTube 2.

## Caveats, read before sending

- Of the 459 researched, 241 had no verified email and were left out.
- About 29 had a "verified" email at a non-company domain (job-changers or bad
  matches: neptune.ai, microsoft.com, fb.com, a German engineering firm). Those
  were dropped, not in this file.
- Some very short Anthropic local parts (`a@`, `b@`, `mf@`, `ml@`, `sg@`, `vs@`)
  look like initials-based guesses rather than real individual mailboxes. Verify
  deliverability before sending. The longer, name-shaped addresses
  (e.g. `naomibashkansky@openai.com`, `lspecht@stripe.com`, `beenkim@google.com`)
  are far more credible. Hunter's email verifier is the cheapest way to confirm.
