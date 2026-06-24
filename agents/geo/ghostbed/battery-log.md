# GhostBed AI engine battery (phase 5)

Run 2026-06-22, headed Chromium + stealth via `/browse`. Fixed query:
**"best cooling mattress for hot sleepers 2026"** (GhostBed's own core category and
homepage tagline). Two passes: OFF = answer from training only ("without searching
the web"); ON = forced live web retrieval. Captures in `assets/<engine>-...-<pass>-2026-06-22.png`.

## Result table

| Engine | Pass | Incognito/clean | GhostBed named? | Brands the engine recommended |
|---|---|---|---|---|
| ChatGPT | off | Temporary Chat (logged in) | NO | Helix, Saatva, Purple, Tempur, Brooklyn, Bear, Avocado |
| ChatGPT | on | Temporary Chat (logged in) | NO | Helix, Brooklyn, Bear, Saatva, Tempur, Leesa, WinkBed |
| Claude | off | new chat (logged in) | **YES** | Tempur-Pedic, GhostBed Luxe, Helix, Saatva, Purple, Avocado, Birch, Cocoon, Layla |
| Claude | on | new chat (logged in) | NO | Helix, Brooklyn, Saatva, Nectar, Leesa, Nolah, Avocado, BedJet |
| Gemini | off | logged in (Rishi, memory on) | NO | Helix, Brooklyn, Leesa, Saatva, Nectar |
| Gemini | on | logged in (Rishi, memory on) | NO | Helix, Brooklyn, Nectar, Leesa |
| Perplexity | on | **Incognito** (anonymous session) | NO | Helix, Brooklyn, Saatva |
| Google AI Overview | on | logged-in Google (R) | NO | Helix Midnight Luxe, Brooklyn Bedding Aurora Luxe |
| Copilot | on | guest (not logged in) | NO | Tempur, Helix, DreamCloud, Nectar |

## Read

Eight of nine passes do not name GhostBed at all, including every live-retrieval
(ON) pass across all six engines and its own homepage category. The single
appearance is **Claude's OFF/parametric pass**, where it names "GhostBed Luxe,
built around a cooling cover, their coldest model" from training knowledge. That
is the whole GEO thesis in one data point: the brand exists in model priors, but
the live recommendation layer (the listicles and schema the engines retrieve)
drops it, so it is never recommended at the moment of intent. The contrast inside
a single engine (Claude knows it from memory, omits it on retrieval) is the
cleanest evidence in the deck.

Where GhostBed's own homepage tagline is "cooling," not one ON pass returned it,
while Helix, Brooklyn Bedding, Saatva, and Nectar recur across every engine.

## OFF-pass coverage limitations (documented, not skipped)

- **Copilot off**: parametric pass is an N/A limitation. Guest Copilot grounds on
  Bing by default and exposes no toggle to disable web retrieval, so a clean
  from-memory pass is not separable. ON pass captured.
- **Perplexity off**: parametric pass is an N/A limitation. Perplexity defaults to
  retrieval and the incognito session still searches; there is no from-training-only
  mode in the UI. ON pass captured in incognito (the clean read that matters for
  contamination).
- **Google AI Overview (googleaio) off**: parametric pass is an N/A limitation by
  design. The AI Overview is always web-grounded; there is no from-memory variant.
  ON captured.

## Contamination notes

- Perplexity ON was run in **Incognito** specifically because the logged-in "Rishi
  Patel" profile carries Memory and prior audit search history (this is what
  inflated the earlier Reuzel read). Clean incognito still returned GhostBed
  absent, so the absence is robust, not a memory artifact.
- ChatGPT used **Temporary Chat**. Gemini had no clean private mode and ran on the
  logged-in profile; memory contamination there biases toward presence, yet
  GhostBed was still absent, which only strengthens the finding.
- Copilot was guest (no account), so no contamination.
