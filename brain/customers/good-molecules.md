# Good Molecules

goodmolecules.com — skincare, ~$100M brand.
Last updated June 10, 2026. Source: founder-provided canonical context.

## Documents

- Audit deck: [documents/good-molecules-audit.pdf](documents/good-molecules-audit.pdf)
- Engagement letter ("AI visibility remediation", June 2026 — WAF
  reconfiguration for AI crawlers, server-side Product/Offer structured data,
  schema correction, llms.txt/agents.md guide files, before/after measurement,
  plus the no-cost AI assistant pilot):
  [documents/good-molecules-engagement-letter.pdf](documents/good-molecules-engagement-letter.pdf)

## Delivered

- Full AI visibility audit, composite D/61, eight findings (two Critical, two
  High, three Medium, one Strength)
- **Key discovery: the dividing line for AI visibility is crawler access, not
  model quality.** Search-index-fed surfaces (Gemini, Google AI Mode, AI
  Overviews, Bing) allow Googlebot/Bingbot through and show the brand.
  Standalone assistants (ChatGPT, Claude, Perplexity, Copilot) are blocked at
  the WAF and answer from retailers and Reddit instead
- Live AI search testing executed via Claude Code browser automation overturned
  a draft finding (Gemini was assumed blocked; testing showed it cites
  goodmolecules.com as its primary source)
- Claude's verbatim admission that it could not pull prices from the site and
  fell back to Amazon and third-party retailers became the evidence centerpiece
  of Finding 02
- Bing reached the brand but reported the shipping policy as the product price,
  which became its own finding

## Initial pitch call — May 21, 2026 ("Website structure review")

Source: Granola notes, filed June 10, 2026. **Caveat: Granola's speaker labels
on this call are scrambled** (it attributes the Blackwell side to "two Berkeley
freshmen" and places Armaan on the customer side). Reconstruction, to be
confirmed by Armaan:

- Blackwell pitched the Good Molecules/Beautylish contact on AI visibility
- Evidence used live: ChatGPT asked for "smaller specialty online beauty
  stores" suggests competitors (Credo Beauty, Violet Grey, etc.) but not Good
  Molecules; site lacks FAQ sections and LLM-readable structure
- Pitched a 30-day pilot at **$250** with full refund if baseline thresholds
  not met (pricing later evolved — see engagement letter)
- The contact agreed to review a one-pager and share it with a colleague —
  confirmed from the Dartmouth inbox (June 10): the contact is **Nils Johnson**
  (nils@beautylish.com, Beautylish co-founder, angel-invests in YC companies)
  and the colleague is **Sameer Iyengar** (sameer@beautylish.com), who Granola
  had transcribed as "Samir"
- Next step from the call: send one-pager; follow-up the next week. The email
  thread started as a May 21 cold email and stayed active through May 27+
  (subject: "Stanford Student Question - thoughts on AI retail tools")

## Engagement

- One-page engagement letter delivered at $1,000 upfront with full refund if
  benchmarks are not met, including a no-cost AI assistant pilot where the team
  texts an assistant to manage products, prices, stock, and orders on the live
  site
