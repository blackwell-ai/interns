# Stream2Sea AI engine battery (phase 5)

Run 2026-06-29, headed Chromium + stealth via `/browse`. Two passes per engine:
OFF = training only ("without searching the web"); ON = live web retrieval
("search the web"). Captures in
`assets/<engine>-<query-slug>-<pass>-2026-06-29.png`.

Competitor set: Raw Elements, Badger, Thinksport (and any others the engines name).

## Fixed queries (written before any engine was queried)

- **Q1 category (primary, run on every engine):** `best reef-safe sunscreen 2026`
  — slug `reef-safe-sunscreen`
- **Q2 adjacent:** `best mineral sunscreen for snorkeling and diving 2026`
  — slug `snorkel-sunscreen`
- **Q3 brand-defense:** `Stream2Sea vs Raw Elements` — slug `s2s-vs-raw`

## Result table (Q1, fill as captured)

| Engine | Pass | Incognito/clean | Stream2Sea named? | How / other brands |
|---|---|---|---|---|
| ChatGPT | off | Temporary Chat | **YES (6th of 7)** | Named "Stream2Sea Sport SPF 30" for "diving/snorkeling trips," cites aquatic-toxicity testing. NOT in its top 3 (ThinkSport, Blue Lizard, Badger). Also: Raw Elements, All Good, Babo. |
| ChatGPT | on | Temporary Chat | **VARIES (named in 1 of 2 renders)** | Run 1 cited Treeline Review and named Stream2Sea Sport SPF 30 at #5 ("best niche pick for divers and water sports," HEL certified, flagged longer ingredient list / more white cast). Run 2 cited Travel+Leisure + Good Housekeeping and did NOT name it (Thrive Natural Care, All Good, Badger, Blue Lizard, Thinksport). Source-dependent. |
| Claude | off | new chat | **YES (#3 of 7)** | "Stream2Sea SPF 30 — The standout if you actually snorkel or dive. They do real aquatic ecotoxicity testing rather than just claiming reef-safe, and the formula is biodegradable. A favorite in the diving community." Ahead of Raw Elements, Kokua, Blue Lizard, Suntegrity; behind Thinksport (#1), Badger (#2). |
| Claude | on | new chat | **YES** | In "other brands recommended across multiple sources": "Stream2Sea — Designed specifically for ocean environments. Tested and proven biodegradable in both salt and fresh water... A favorite for snorkeling and reef." Consensus #1 was Badger (only widely available HEL-certified pick). Also Thinksport, Blue Lizard, Babo, Supergoop. Sources: Treeline Review, Project Reef. |
| Gemini | off | logged-out (clean) | N/A | Guest Gemini grounds on Google Search; no from-training-only mode reachable. ON captured. |
| Gemini | on | logged-out (clean) | **NO** | Ranked: 1. Project Reef (Best Overall & Eco-Conscious, "born in Hawaii," plastic-negative), 2. Badger, 3. Blue Lizard Sensitive, then Raw Elements, Thinksport, Thinkbaby. Sources: Project Reef, Treeline Review, NonToxicLab, Enriching Pursuits. Stream2Sea absent. Logged-out so no contamination. |
| Perplexity | on | logged-in (low contam.) | **NO** | Named Project Reef (top overall), Thrive Bodyshield SPF 50, Badger Clear Zinc, Thinksport, Raw Elements, All Good, Supergoop. Sources: projectreef, nytimes, aoskincare. Stream2Sea absent. History sidebar shows only unrelated priors (pomade, mowers, mattress), so contamination low. Could not reach in-app incognito; disclosed. |
| Copilot | on | guest (clean) | **NO** | "Top takeaway: Project Reef, Raw Elements, Kōkua Sun Care, All Good, and Blue Lizard Sensitive, with Supergoop and COOLA." Top-brands list led by Project Reef. Stream2Sea absent. |
| Google AI Overview | on | logged-out | **NO (this render)** | AIO named "Best Overall: Badger Sport Mineral SPF 40" (first to achieve HEL "Protect Land + Sea" cert), referenced Project Reef. Stream2Sea not in the visible AIO. Page-1 organic also Stream2Sea-free: Project Reef, NYT Wirecutter, Enriching Pursuits (Thinksport), aoskincare, Hawaii.com, Badger Balm, Reddit r/SkincareAddiction. AIO flaked on 2 reloads (non-deterministic); captured render shown. |

## OFF-pass coverage limitations (documented per methodology)

- **Perplexity off:** N/A by design (always retrieves); run ON in Incognito.
- **Copilot off:** N/A (guest grounds on Bing, no retrieval toggle); ON captured.
- **Google AI Overview (googleaio) off:** N/A limitation by design (always
  web-grounded; no from-training-only mode); AIO is non-deterministic. ON captured.

## Read

The defining pattern is a **memory/retrieval split**. Stream2Sea is well known in the
models' parametric memory but largely absent from live category answers.

- **From memory (OFF passes): named in both, favorably and accurately.** ChatGPT
  listed "Stream2Sea Sport SPF 30" for "diving/snorkeling trips" (6th of 7). Claude
  ranked it #3 and called it "the standout if you actually snorkel or dive," citing
  its real aquatic ecotoxicity testing and biodegradable formula. The brand has
  earned genuine standing in the training data.
- **From live retrieval (ON passes): mostly absent.** Named only by Claude ON, and
  by ChatGPT ON in 1 of 2 renders (only when it cited Treeline Review). Absent in
  Perplexity, Copilot, Gemini, and the Google AI Overview. Roughly one to two of six
  live answers name it.
- **Why:** live answers are assembled from third-party roundups (Treeline Review,
  NYT Wirecutter, Travel+Leisure, Good Housekeeping, Vogue, Enriching Pursuits,
  aoskincare, and Project Reef's own blog). Stream2Sea appears in a few niche tested
  roundups (Treeline) but is missing from the mainstream guides engines cite most.
  **Project Reef and Badger dominate** the live answers: Project Reef through heavy
  reef-safe content/SEO (its blog is cited as a source across engines), Badger
  through the Haereticus (HEL) "Protect Land + Sea" certification that roundups call
  "Best Overall."
- **The opportunity:** the reputation already exists (the models know Stream2Sea is a
  diver favorite that does real testing); it is stranded in memory, not in the live
  citation graph. Recommendability is the gap, and the lever is source authority in
  the guides engines retrieve, plus the HEL certification angle competitors use.

## Contamination notes

- **ChatGPT**: both passes in Temporary Chat (true clean session, no memory/history).
- **Claude**: fresh `claude.ai/new` chats, both passes; no incognito mode exists, this
  is the cleanest available.
- **Perplexity**: logged-in profile (could not reach in-app incognito), but the
  history sidebar held only unrelated priors (pomade, mowers, mattresses), so
  sunscreen contamination is low; disclosed.
- **Copilot**: guest session, clean by default.
- **Gemini**: logged-out guest, clean (no personalization).
- **Google AI Overview**: logged-out; always web-grounded and non-deterministic. AIO
  rendered once (captured) and failed to generate on two reloads.
