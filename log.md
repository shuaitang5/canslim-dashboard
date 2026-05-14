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

## 2026-05-14 09:30 PDT
Schedule fix — dashboard wasn't picking up 5/14 upstream report.
- Root cause: 23:00 UTC cron had two issues: (a) yesterday's first scheduled tick was missed because the workflow file landed at 23:54 UTC (after cron fired); (b) 23:00 UTC is the wrong window — upstream publishes overnight UTC (samples: 5/12 00:00, 5/13 00:38, 5/14 03:33), so 23:00 UTC would be ~20 hours late every day.
- Fired manual `gh workflow run` to update dashboard immediately with 5/14 data — succeeded, auto-commit `auto-refresh 2026-05-14 16:33Z` landed.
- Changed cron to twice-daily: 06:00 UTC (primary, ~2-3hrs after upstream's typical publish window) + 14:00 UTC (backup if upstream is delayed or first run failed).
Files: .github/workflows/refresh.yml, log.md

## 2026-05-13 ~17:00 PDT
Auto-refresh + README polish.
- Wrote `.github/workflows/refresh.yml` — daily cron `0 23 * * *` UTC + `workflow_dispatch`. Sets up Python 3.11, installs yfinance, runs `./refresh.sh`, commits with bot identity if `git status --porcelain` is non-empty, pushes. `concurrency: refresh-dashboard` prevents overlap. Pages auto-rebuilds on push.
- First manual run via `gh workflow run` succeeded in 19s (no-op since I'd just refreshed locally — proves the no-change path works).
- Fixed README broken `_verify_closeup.png` link: amended `.gitignore` to keep `_verify_closeup.png` out of ignore (`!_verify_closeup.png`) and committed the file.
- Added prominent live-dashboard URL near the top of README, kept the local `dashboard.html` instructions for offline use.
- Set repo homepage + description via `gh repo edit` so the GH sidebar advertises the live URL.
Files: .github/workflows/refresh.yml, .gitignore, _verify_closeup.png, README.md, log.md

## 2026-05-13 ~13:00 PDT
Publish dashboard to GitHub Pages so it can be viewed on phone / shared.
- Installed `gh` (Homebrew); user authed as `shuaitang5`.
- `git init` in canslim/ folder, scoped identity to `louistang0909@gmail.com` / Louis Tang (global Amazon identity untouched).
- Added `.gitignore` (verify pngs, __pycache__, .DS_Store).
- Initial commit + `gh repo create canslim-dashboard --public --source=. --push`.
- Enabled Pages via `gh api -X POST .../pages` on main/root; build succeeded.
- Live URL: https://shuaitang5.github.io/canslim-dashboard/dashboard.html
- Flagged but not yet fixed: `dashboard.html` template missing `<meta name="viewport">` — phone renders zoomed out until patched.
Files: .gitignore, log.md
