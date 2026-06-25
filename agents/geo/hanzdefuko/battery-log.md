# Hanz de Fuko AI engine battery (phase 5)

Run 2026-06-25, headed Chromium + stealth via `/browse`. Fixed query:
**"best men's hair clay 2026"** (Hanz's hero Claymation is a clay; Quicksand its
matte paste). Two passes: OFF = training only ("without searching the web"); ON =
live web retrieval. Captures in `assets/<engine>-best-hair-clay-<pass>-2026-06-25.png`.

## Result table

| Engine | Pass | Incognito/clean | Hanz named? | How / other brands |
|---|---|---|---|---|
| ChatGPT | off | Temporary Chat | **YES (top pick)** | "best all-around men's hair clay is Hanz de Fuko Claymation" |
| ChatGPT | on | Temporary Chat | **YES** | Claymation listed ($28, strong hold, matte); Baxter, Uppercut, Suavecito, Reuzel |
| Claude | off | new chat | **YES** | Hanz de Fuko among Baxter and others |
| Claude | on | new chat | **YES** | Hanz de Fuko with Reuzel, Layrite, Baxter |
| Gemini | off | logged in (contaminated) | YES | Hanz de Fuko, Baxter, Layrite |
| Gemini | on | logged in (contaminated) | YES | Hanz de Fuko, Layrite, Baxter, American Crew |
| Perplexity | on | **Incognito** (clean) | **NO** | Layrite, American Crew, Suavecito |
| Copilot | on | guest (clean) | **YES** | Hanz de Fuko, Layrite, Baxter |
| Google AI Overview | on | logged-in Google | **YES** | "Hanz de Fuko Claymation for all-around versatility"; also Church California, Reuzel |

## Read

Hanz de Fuko is named in **five of the six engines**, and is ChatGPT's outright top
pick from memory ("the best all-around men's hair clay is Hanz de Fuko Claymation").
Google's AI Overview names "Hanz de Fuko Claymation for all-around versatility" as a
top performer. Recommendability is a genuine strength, on par with Reuzel and well
ahead of the cold-prospect cosmetics audits.

The one clean miss is **Perplexity in incognito**, which named Layrite, American
Crew, and Suavecito but not Hanz. That is the specific gap to close: Perplexity
leans on third-party category guides, and Hanz is under-represented in the ones it
cites. Claymation's strong presence everywhere else shows the brand has the
reputation; the fix is source authority in the channels Perplexity reads.

## OFF-pass coverage limitations (documented, not skipped)

- **Copilot (copilot) off**: N/A limitation. Guest Copilot grounds on Bing with no
  toggle to disable retrieval. ON captured.
- **Perplexity (perplexity) off**: N/A limitation. Perplexity defaults to retrieval;
  no from-training-only mode. ON captured in incognito.
- **Google AI Overview (googleaio) off**: N/A limitation by design; always
  web-grounded. ON captured.

## Contamination notes

ChatGPT used Temporary Chat; Perplexity ran in Incognito; Copilot as guest. Gemini
ran on the logged-in profile (no clean private mode), but "hair clay" is unrelated
to any prior audit search on this profile, so contamination risk is low; its result
is consistent with the clean engines.
