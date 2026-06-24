# BeautyStat AI engine battery (phase 5)

Run 2026-06-22, headed Chromium + stealth via `/browse`. Fixed query:
**"best vitamin C serum 2026"** (BeautyStat's hero category, the Universal C Skin
Refiner). Two passes: OFF = training only ("without searching the web"); ON =
forced live web retrieval. Captures in `assets/<engine>-...-<pass>-2026-06-22.png`.

## Result table

| Engine | Pass | Incognito/clean | BeautyStat named? | Brands the engine recommended |
|---|---|---|---|---|
| ChatGPT | off | Temporary Chat (logged in) | NO | SkinCeuticals, Timeless, Drunk Elephant, Maelove, La Roche-Posay, Sunday Riley, The Ordinary |
| ChatGPT | on | Temporary Chat (logged in) | NO | SkinCeuticals, Geek & Gorgeous, Timeless, Drunk Elephant, La Roche-Posay, Maelove |
| Claude | off | new chat (logged in) | NO | SkinCeuticals C E Ferulic (benchmark) + price-tier list |
| Claude | on | new chat (logged in) | NO | TruSkin, SkinCeuticals, Timeless, Maelove, La Roche-Posay, CeraVe |
| Gemini | off | logged in (Rishi, memory on) | NO | SkinCeuticals, Timeless, TruSkin, CeraVe, La Roche-Posay |
| Gemini | on | logged in (Rishi, memory on) | NO | SkinCeuticals, Timeless, TruSkin |
| Perplexity | on | **Incognito** (anonymous session) | NO | SkinCeuticals, The Ordinary, La Roche-Posay, CeraVe, Sunday Riley |
| Google AI Overview | on | logged-in Google (R) | NO | SkinCeuticals C E Ferulic, Sunday Riley C.E.O. |
| Copilot | on | guest (not logged in) | NO | SkinCeuticals, Paula's Choice, Naturium, Sunday Riley |

## Read

**Nine of nine passes omit BeautyStat**, including every browsing-OFF parametric
pass. This is a harder absence than GhostBed: GhostBed at least surfaced in Claude's
training memory, BeautyStat does not appear even there. BeautyStat is a smaller,
younger brand, so it is thin in model priors AND absent from the retrieval layer.

The audit's specific prediction holds live: the value brand **TruSkin** is named by
ChatGPT, Claude, and Gemini, partly because TruSkin publishes its own
"best vitamin C serums" category guide that engines cite. BeautyStat, with a
patented 20% L-ascorbic acid formula and a cosmetic-chemist founder, publishes no
such category content and is invisible to the recommendation. SkinCeuticals C E
Ferulic is the near-universal benchmark across all nine passes.

## OFF-pass coverage limitations (documented, not skipped)

- **Copilot (copilot) off**: N/A limitation. Guest Copilot grounds on Bing by
  default with no toggle to disable retrieval. ON captured.
- **Perplexity (perplexity) off**: N/A limitation. Perplexity defaults to retrieval;
  no from-training-only mode in the UI. ON captured in incognito.
- **Google AI Overview (googleaio) off**: N/A limitation by design; the AI Overview
  is always web-grounded. ON captured.

## Contamination notes

Perplexity ON ran in **Incognito**; ChatGPT in **Temporary Chat**; Copilot as
guest. Gemini ran on the logged-in profile (no clean private mode), which biases
toward presence, yet BeautyStat was still absent, which strengthens the finding.
Vitamin C serum is unrelated to any prior audit search on this profile, so
contamination risk here is low regardless.
