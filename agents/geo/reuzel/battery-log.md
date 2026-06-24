# Reuzel AI engine battery (phase 5): clean re-run

Run 2026-06-22, headed Chromium + stealth via `/browse`. Fixed query:
**"best men's pomade for strong hold"**. Two passes: OFF = training only; ON =
live web retrieval. This is a clean re-run, with in-app incognito/temporary/guest
where the profile is logged in, specifically to settle whether the original deck's
"recommended in half the engines" read was real signal or profile contamination.

## Result table

| Engine | Pass | Incognito/clean | Reuzel named? | How / other brands |
|---|---|---|---|---|
| ChatGPT | off | Temporary Chat | **YES** | "Reuzel Blue Pomade, strong water-based hold, high shine" among Uppercut, Baxter |
| ChatGPT | on | Temporary Chat | **YES (top pick)** | "My pick is Reuzel Extreme Hold Matte... 11/10 hold"; also Layrite, Blind Barber, Suavecito |
| Claude | off | new chat | NO | Suavecito, Layrite, Imperial, Baxter, Hanz de Fuko, Murray's (no Reuzel in priors) |
| Claude | on | new chat | **YES** | Reuzel surfaced on web retrieval (cited reuzel.com); also Uppercut, American Crew, Imperial |
| Gemini | off | logged in (contaminated) | YES | Reuzel, Suavecito, Layrite, Uppercut |
| Gemini | on | logged in (contaminated) | YES | Reuzel, Suavecito, Layrite |
| Perplexity | on | **Incognito** (clean) | **YES** | "Reuzel strong-hold pomade: classic feel, reliable hold" cited reuzel.com; Suavecito, Brickell |
| Copilot | on | guest (clean) | YES | Reuzel, Suavecito |
| Google AI Overview | on | logged-in Google | YES (this render) | Reuzel in the AIO block with Suavecito, Blind Barber, Duke Cannon |

## Read: the contamination concern is largely resolved

The clean sessions still name Reuzel. ChatGPT in a **Temporary Chat** makes Reuzel
Extreme Hold Matte its outright top pick on the ON pass. Perplexity in **Incognito**
(no memory, no history) names "Reuzel strong-hold pomade" as a best pick and cites
reuzel.com. Copilot as **guest** names it. So Reuzel's recommendability is genuine,
not an artifact of the logged-in "Rishi Patel" profile. The deck's composite 79 /
Recommendability 76 looks justified, arguably conservative.

This corrects my own earlier review:

- **Claude claim (deck said Reuzel is a pick):** true for the browsing-ON pass
  (web retrieval surfaces Reuzel, cites reuzel.com), even though Claude's parametric
  pass does NOT name Reuzel. The original deck's Claude screenshot was a weak
  capture (mid-search), but the underlying claim holds.
- **Perplexity contamination (I flagged it):** clean incognito still names Reuzel,
  and more favorably than the deck's "only the Liquid Death collab." Genuine signal.

## Real methodological findings

- **Google AI Overview is non-deterministic.** Earlier the same evening, a fresh
  AIO for this exact query did NOT contain Reuzel (named Suavecito, Blind Barber,
  Duke Cannon; Reuzel only in a Reddit result below the AIO). This run, Reuzel is
  inside the AIO block. Same query, same day, different output. A single AIO
  screenshot overstates certainty; the deck should say "appears in some renders."
- **Gemini could not be run clean** (no temporary mode; logged-in Rishi profile has
  prior Reuzel searches). Its Reuzel mentions are contaminated and discounted; the
  clean engines carry the finding.

## OFF-pass coverage limitations (documented, not skipped)

- **Copilot (copilot) off**: N/A limitation. Guest Copilot grounds on Bing with no
  toggle to disable retrieval. ON captured.
- **Perplexity (perplexity) off**: N/A limitation. Perplexity defaults to retrieval;
  no from-training-only mode. ON captured in incognito.
- **Google AI Overview (googleaio) off**: N/A limitation by design; always
  web-grounded. ON captured.

## Contrast with the cold prospects

Where GhostBed and BeautyStat are absent across all clean engines, Reuzel is named
across ChatGPT (top pick), Claude (on retrieval), Perplexity (incognito), Copilot
(guest), and Google AIO. Reuzel's gap is schema and aggregateRating, not basic
recommendability; this battery confirms that framing.
