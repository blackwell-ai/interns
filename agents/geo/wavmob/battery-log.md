# WavMob AI engine battery (phase 5)

Run 2026-07-01 through gstack `/browse` headed on the real display; logins cleared
by hand by Armaan, Google captcha cleared by hand, Copilot as guest. Live retrieval
(ON) pass. Query: "best used wheelchair accessible vehicle dealers UK" / "which UK
WAV dealers would you recommend". Captures in `assets/`.

| Engine | Pass | WavMob named? | Position | Capture |
|---|---|---|---|---|
| ChatGPT (search on) | ON | No | Named Allied Mobility, GowringsVersa, WavsGB, GM Coachwork, Brotherwood, Jubilee | chatgpt-wavdealers-on-2026-07-01.png |
| Perplexity | ON | No | Named Allied Mobility, Brotherwood, GM Coachwork, Jubilee, WavsGB | perplexity-wavdealers-on-2026-07-01.png |
| Google AI Overview | ON | No | Named Allied Mobility, Jubilee, WavsGB, GowringsVersa | googleaio-wavdealers-on-2026-07-01.png |
| Gemini | ON | Yes | Second-tier "Highly Rated Regional Specialist" (South Coast / Hampshire), below the national leaders | gemini-wavdealers-on-2026-07-01.png |
| Claude | ON | Yes | Listed under "Regional specialists with good reputations" (delivers nationwide, part-exchange, finance), below national leaders | claude-wavdealers-on-2026-07-01.png |
| Copilot (guest) | ON | Yes | Prominent: "best-reviewed and most established UK WAV dealers include Jubilee, WavsGB, WavMob, ..." | copilot-wavdealers-on-2026-07-01.png |

Result: split. 3 of 6 omit WavMob entirely (ChatGPT, Perplexity, Google AI Overview);
3 of 6 name it (Copilot prominently, Claude and Gemini as a regional specialist). The
national leaders (Allied Mobility, Jubilee, WavsGB, GowringsVersa) appear in all six.

The mechanism matters for the pitch: every WavMob mention is sourced from third-party
pages (MotaClarity, directory listings, and the search-index snippet of
wavmob.co.uk's homepage title), never from a live fetch of the site, because WavMob
blocks all seven AI crawlers (HTTP 403). So WavMob has no control over its AI
narrative and its live inventory, finance terms, and full reputation never reach the
engines. Where it is named, it is a regional afterthought; where the leaders win,
they win because their own content is readable and structured (Allied Mobility ships
a 16-Q&A FAQPage; Brotherwood carries AutoDealer schema; both leave AI crawlers open).
Unblocking the crawlers, adding Vehicle/Offer and AggregateRating schema, and
connecting the real Trustpilot/Google reputation is what moves WavMob from
inconsistent third-party mentions toward consistent, self-authored top-tier
inclusion.

Limitations (documented): ON pass only (OFF pass not run).
