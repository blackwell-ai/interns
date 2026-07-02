# Good Molecules re-audit, Phase 5 engine battery log

Re-audit run 2026-06-30, measured against the June 1, 2026 audit (composite D/61).
Comparison-relevant inputs frozen to June 1; evidence coverage run to today's
verify-evidence.sh gate (gate-compliant superset, per client decision).

## Locked June 1 inputs (reproduced verbatim)

- **Category query:** best affordable dark spot serum for 2026
- **Price/ingredients probe:** price and ingredients of the Good Molecules
  Discoloration Correcting Serum
- **Brand-defense query (reconstructed):** Good Molecules vs The Ordinary for dark spots
- **Hero product:** Discoloration Correcting Serum (30ml $12 / 75ml $25;
  tranexamic acid 3%, niacinamide 4%; 4.3 / 7,624 reviews at audit)
- **Two passes** where a browsing toggle exists: OFF (parametric) then ON (retrieval).

## Engines

ChatGPT, Perplexity, Gemini, Claude, Google AI Overview, Microsoft Copilot.
Incognito / clean-profile where the profile is logged in (Temporary Chat, Perplexity
Incognito, fresh chats with memory off, Copilot guest).

## June 1 baseline to beat (from the deck)

- ChatGPT/Claude/Perplexity/Copilot were WAF-blocked and answered from Amazon / Ulta
  / Target / Reddit. Claude verbatim: could not pull prices, fell back to Amazon.
- Category query returned The Ordinary Alpha Arbutin, Differin, AXIS-Y; GM omitted.
- Search-fed surfaces (Gemini, Google AI Mode, AI Overview, Bing) did show the brand.

## Battery rows

Run 2026-06-30, evening PT. Category query on every engine: **best affordable dark
spot serum for 2026**. Clean-session handling per engine noted in the Incognito
column. Captures are full-window screenshots in `assets/`.

| Engine | Pass | Clean session | GM named? | Competitors named | Sources cited | Capture |
| --- | --- | --- | --- | --- | --- | --- |
| ChatGPT | OFF (parametric) | Temporary Chat (clean, memory off) | **Yes, #1 "Best overall"** | The Ordinary Alpha Arbutin (#2), Naturium Tranexamic 5% (#3) | none (from memory) | chatgpt-dark-spot-serum-off-2026-06-30.png |
| ChatGPT | ON (web) | Temporary Chat | **Yes, #1 "Best Overall Budget Pick"** | (others below GM) | yes, Consumer Health Digest +1 | chatgpt-dark-spot-serum-on-2026-06-30.png |
| Claude | OFF (parametric) | fresh claude.ai/new (no incognito mode exists) | **Yes, listed first, "best value-to-effectiveness"** | The Ordinary (Alpha Arbutin 2%+HA, Niacinamide 10%+Zinc) | none (from memory) | claude-dark-spot-serum-off-2026-06-30.png |
| Claude | ON (web) | fresh claude.ai/new | **No**, absent from retrieved sources; Claude states GM "wasn't named in these particular results" | La Roche-Posay Mela B3, Naturium azelaic, Goodal Green Tangerine, K-beauty ampoules | yes, Forbes Vetted, Yahoo/derm, DermApproved, Live Tinted, Consumer Health Digest | claude-dark-spot-serum-on-2026-06-30.png |
| Perplexity | ON only (OFF = N/A, always retrieves) | logged-in; no incognito exposed in current UI, History empty so low contamination | **No** | e.l.f. Holy Hydration Thirst Burst Drops ($18), Goodal Green Tangerine Vita C ($30), Truskin Vitamin C, Curology Dark Spot | yes, dermapproved, sanemd, welzo | perplexity-dark-spot-serum-on-2026-06-30.png |
| Gemini | OFF (parametric) | logged-in, no clean mode, **contaminated**; auto-grounded (DermApproved citation pills present despite from-memory prompt) | **No** | The Ordinary Aloe/NAG (#1), a ~$22 pick (#2), Goodal (#3), Neutrogena Rapid Tone (#4) | grounded (DermApproved) | gemini-dark-spot-serum-off-2026-06-30.png |
| Gemini | ON (web) | logged-in, **contaminated** (read as retrieval signal, not clean) | **Yes, #2 "Best Under-$15 Clinical Pick" ($12)** | La Roche-Posay Mela B3 (#1), Neutrogena Rapid Tone (#3), AXIS-Y (#4) | yes, Good Housekeeping, Marie Claire, Oprah Daily, Live Tinted, skincare subreddits | gemini-dark-spot-serum-on-2026-06-30.png |
| Google AI Overview | ON only (always web-grounded, non-deterministic) | logged-in Google profile; AIO is web-grounded (guest-equivalent read). This render named GM; say "in some renders" in the deck given non-determinism | **Yes, "the top overall pick" (< $15)** | product cards; roundup sources | yes, "15 Best Dark Spot Corrector Picks of 2026", Live Tinted | googleaio-dark-spot-serum-on-2026-06-30.png |
| Copilot | ON only (guest) | guest (not signed in, clean by default); human-check cleared by operator, then answered | **Yes, #2 "Best for uneven tone and PIH"; also named in the top-3 summary trio** | Anua Niacinamide 10% + TXA 4% (#1), The Ordinary Alpha Arbutin | Copilot live product cards ("live product data you triggered") | copilot-dark-spot-serum-on-2026-06-30.png |

### Google AI Overview OFF pass (2026-06-30)

googleaio OFF / parametric: N/A, documented limitation. Google AI Overview is always
web-grounded and has no browsing-OFF (from-memory) mode, so a parametric pass cannot
exist for this surface. ON capture stands alone by design.

### Copilot capture note (2026-06-30)

copilot OFF / parametric: N/A, documented limitation. Copilot guest runs ON-only
(always web-grounded); there is no browsing-OFF / from-memory pass to capture.


Copilot's guest session first returned a "Verify you are human" bot-verification
challenge. Completing CAPTCHA / bot-detection is prohibited, so the operator cleared
the human-check manually; Copilot then answered and the ON pass was captured cleanly.
In the June 1 baseline Copilot was WAF-blocked and fell back to Amazon, so its naming
GM in both the summary trio and the ranked #2 slot is a real gain.

## What changed vs the June 1 baseline

June 1: ChatGPT, Claude, Perplexity, Copilot were WAF-blocked and answered from
Amazon / Ulta / Target / Reddit with GM omitted; only search-fed surfaces (Gemini,
Google AI Mode, AI Overview, Bing) showed the brand.

2026-06-30, after the WAF fix and the shipped llms.txt:

- **From memory (parametric / OFF):** ChatGPT names GM #1, Claude names GM first.
  GM now sits in those two models' priors, where June 1 showed a fallback to Amazon.
  Gemini's OFF pass still omits GM (and auto-grounds, so it is not a clean parametric read).
- **Live retrieval (ON):** GM is named by ChatGPT (#1), Google AI Overview (top pick),
  Gemini (#2), and Copilot (#2). Four of six ON surfaces name GM. GM is still
  **absent** from Claude's and Perplexity's retrieved sources, which lean on
  affiliate/derm roundups (Forbes, Yahoo, DermApproved, e.l.f., Goodal) that do not
  list GM.
- **Read:** recommendability improved markedly on ChatGPT and the Google surfaces. The
  remaining gap is off-site presence in the specific listicles Claude and Perplexity
  cite, the reputation/off-site lever, not an on-site schema fix. Absence on a
  logged-in Gemini/Perplexity profile is conservative; the GM "yes" reads were on
  clean (ChatGPT Temporary Chat) or web-grounded surfaces, so they hold.
