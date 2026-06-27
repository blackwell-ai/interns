---
title: Draft and run outreach to AI lab researchers (agentic commerce)
created: 2026-06-26
created_by: Armaan (via agent)
assignee: Shamit
priority: normal
claimed_by:
claimed_at:
---

## Task

We have a list of 189 verified work emails of researchers and technical staff at
OpenAI, Anthropic, Google, Google DeepMind, and Stripe:
`outreach/ai-lab-researchers/researcher-emails.csv` (name, company, email). How
it was built and the caveats are in `outreach/ai-lab-researchers/README.md`.

Your job: draft the cold outreach email for this audience, then run the send.

Context for the draft. This complements the outreach Armaan has been sending to
ACP and agentic-commerce people from `armaan@tryblackwell.com` (founder to
founder, cofounders cc'd). That email is short and runs: who Armaan is (YC S26,
building in agentic commerce), one specific line tying the recipient's work to
ours, then the pitch in one breath: Blackwell works the layer above the
transaction, on what an AI agent recommends in the first place, which is product
quality and taste signal in commerce where the open-web data agents lean on is
contradictory and easy to game. Close with a 20 to 30 minute ask. Voice rules in
`skills/humanizer/SKILL.md` (no em or en dashes, no AI tells, scan before
sending).

These recipients are individual researchers and engineers, not the senior
protocol owners, so adjust the angle: less "where is ACP heading" and more "you
build the models that will do the recommending, here is the data problem that
sits in front of that." Keep it one short, personal-feeling email, not a
template that reads like a blast.

How to proceed with the list:

1. Verify deliverability first. Run the 189 through Hunter's email verifier and
   drop anything that comes back invalid. Pay attention to the short Anthropic
   local parts (`a@`, `b@`, `mf@`, ...) flagged in the README, several are
   likely initials-based guesses, not real mailboxes.
2. Draft the email (above). Get Armaan's eyes on it before it goes out.
3. Send from a warmed address, paced, with a small canary batch first and a
   bounce check before the rest. `tryblackwell.com` is fresh, so watch the
   bounce rate. gogcli (`gog -a armaan@tryblackwell.com gmail send`) is the
   sender we have been using; cofounders cc'd.

## Done when

The list is verified and trimmed to deliverable addresses, the email is drafted
and approved by Armaan, and the sends are out (or scheduled), with a short result
note appended here.
