# OpenAI demo: the same model, with and without our corpus

A frozen, side-by-side ChatGPT interaction. Each shopping question is answered
twice by the same OpenAI model (gpt-5.5). The only difference is that the grounded
run can call `query_blackwell_corpus`, a tool backed by `../data/preference_data.json`.
The result is rendered as a page on the marketing site at `tryblackwell.com/demo`
(source in the `tryblackwell` repo under `app/demo/`).

## Files

- `run_demo.py` — runs each query baseline (no tools) and grounded (with the
  corpus tool) against the live OpenAI API, attaches approximate source
  timestamps from the transcripts, and writes `frozen.json`.
- `make_page_data.py` — trims `frozen.json` to the three hero queries the page
  shows, keeping each product's best-two and worst-two scored dimensions, and
  writes `demo-data.json`.
- `frozen.json` — the full captured run (all four candidate queries).
- `demo-data.json` — the page payload. Copy this into the site at
  `app/demo/demo-data.json` after regenerating.

## Regenerate

```bash
cd platform/scraper
source .venv/bin/activate
set -a; . ../../credentials/.env; set +a      # loads OPENAI_API_KEY
python demo/run_demo.py                        # -> demo/frozen.json (live API calls)
python demo/make_page_data.py                  # -> demo/demo-data.json
cp demo/demo-data.json ../../website/app/demo/demo-data.json   # if website checked out beside interns
```

## Notes

- Both runs use the same model so the only variable is corpus access. That
  controlled framing is the whole point; keep it.
- Every grounded claim was checked against the corpus before freezing. The cited
  channels and quotes are real (e.g. BottlePro's "leaks like crazy even when set
  to closed", Hope Baskett's "the 40 oz quencher is not leakproof").
- The page is honest that this is a seven-product proof of the method, not the
  full corpus.
