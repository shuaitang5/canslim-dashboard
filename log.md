# canslim — action log

## 2026-05-13 10:55 PDT
Bootstrap the CANSLIM dashboard: parse full-match tickers from the github.io reports and render a side-by-side top-10 page with day-over-day rank deltas.
- Reverse-engineered the `canslim` zsh function → index lives at `https://zhoutongchar.github.io/canslim-scanner/runs/YYYY-MM-DD_HHMMSS/`. Only 3 runs currently indexed (2026-05-13, 2026-05-12, 2026-05-10).
- Wrote `build_dashboard.py` — discovers runs from the index page, parses each run HTML for `<section class="bucket bucket-matches">` → extracts `data-ticker`, score, gates, A/D, regime. Emits `data.json` + self-contained `dashboard.html` with data embedded.
- Dashboard UX: left panel = primary-date top 10 with `NEW / ↑N / ↓N / =` badges vs prior available report; right panel = prior-date top 10 with `held / ↑ to #X / ↓ to #X / DROPPED` status. Date dropdown to replay earlier days. Each ticker links to the matching `#c-TICKER` anchor on the source report.
- Rank deltas use full-list rank (not top-10 rank) so a ticker moving #12→#7 correctly shows `↑5` instead of `NEW`.
- Wrote `verify_dashboard.py` (Playwright headless) — loads the page, asserts row counts, compares rendered tickers to `data.json`, exercises the date dropdown, and screenshots `_verify.png`. All checks pass.
- Installed playwright + chromium headless shell (first-time setup on this machine).
Files: build_dashboard.py, verify_dashboard.py, dashboard.html, data.json, _verify.png

## 2026-05-13 11:20 PDT
Add 1-2 sentence company description on every ticker row.
- Wrote `enrich_companies.py` — pulls `longName`, `industry`, `sector`, and a trimmed 1-2 sentence summary from yfinance's `.info` for each unique ticker across all parsed reports. Caches to `companies.json`; reruns are cheap (only fetches missing tickers unless `--refresh`).
- Summary-trim rule: first sentence always; second sentence only if first < 180 chars; hard-cap 320 chars with ellipsis. Keeps UI rows tidy.
- Pulled descriptions for all 16 unique tickers in one pass: ENS/XOMA/APLS/CBL/CLS/CRDO/GCT/GEV/HWM/INOD/OUT/PARR/STRL/TGTX/ZVRA/ALAB. Company names and industries cleanly identified (EnerSys / XOMA Royalty Corp / Apellis Pharma / etc).
- `build_dashboard.py` now merges `companies.json` into the embedded payload under `DATA.companies`. Dashboard JS renders each row as `TICKER  Company Name · Industry` on line 1, blurb on line 2 in muted type.
- Widened max-width 1400→1700 so two panels don't squeeze each other with the longer ticker column. Collapsed breakpoint 820→1100.
- Updated `verify_dashboard.py` — checks top-3 rows have `.co` (name) + `.blurb` spans rendered and their text matches `companies.json`. All assertions pass.
Files: enrich_companies.py, build_dashboard.py, verify_dashboard.py, dashboard.html, companies.json, data.json

## 2026-05-13 11:40 PDT
Add a one-command refresh wrapper + README for future self.
- `refresh.sh` — runs `enrich_companies.py` then `build_dashboard.py`. Passes `--refresh` through to force re-fetching every company blurb. `cd`s to its own dir so it works from anywhere. Tested end-to-end.
- `README.md` — describes what the dashboard shows, how the pipeline works (discover → parse → enrich → render), how to refresh (`./refresh.sh`), variants, file roles, dependencies, and known limitations (static snapshot, yfinance rate limits, full matches only).
Files: refresh.sh, README.md
