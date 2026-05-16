# canslim — action log

## 2026-05-15 23:55 PDT
Switch refresh cron to hourly + explain same-date run handling.
- Edited `.github/workflows/refresh.yml`: replaced `0 6/14 UTC` (twice-daily) with `0 * * * *` (hourly). NOT yet committed/pushed — pending user confirmation.
- Same-date run logic: `discover_runs()` in `build_dashboard.py:31-43` keeps the latest stamp per date (lexicographic sort of 6-digit zero-padded timestamps + dict overwrite). For 5/14's three intraday runs (033341 / 222006 / 225336), only 225336 is rendered. Earlier intraday runs are silently dropped.
Files: .github/workflows/refresh.yml, log.md

## 2026-05-15 23:45 PDT
Diagnose why dashboard is missing 5/15 upstream report.
- Upstream `runs/2026-05-15_224319` published 22:43 UTC on 5/15 (= 15:43 PDT). Latest local `data.json` only has 5/14/5/13/5/12/5/10.
- Today's two scheduled refreshes both fired *before* upstream publish: 5/15 08:47 UTC (06:00 cron, late) saw only 5/14; 5/15 15:53 UTC (14:00 cron, late) — upstream still hadn't published yet (came 6h 50m later). No diff → no commit.
- Confirmed via GH Actions API + `curl -I https://shuaitang5.github.io/canslim-dashboard/data.json` → `last-modified: Fri, 15 May 2026 08:48:02 GMT`.
- Root cause = schedule mistake, not a bug. The 5/14 schedule fix assumed upstream publishes early-UTC, but 5/15 upstream landed at 22:43 UTC — no evening-UTC tick to catch it.
- Did NOT yet fix or trigger manually — pending user decision (manual `workflow_dispatch` vs add evening tick e.g. 23:00/00:00 UTC vs 3-tick schedule 02/14/23).
Files: ../canslim/log.md

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

## 2026-05-14 ~12:00 PDT
Show AD column on mobile.
- Reallocated 22px from ticker(96→82) + score(30→28) + delta(42→38) + rank(18→16) to make room for AD(22). Total still 186px.
- Removed previous "AD width:0; padding:0" rule — column is now 22px and visible. Layout stability still preserved (table-layout:fixed sees 5 real columns; colspan=5 blurb-row unchanged).
- Side effect: enrich_companies.py picked up 2 new tickers from upstream's mid-day refresh (VIAV / VIK) — companies.json + data.json regenerated.
Files: build_dashboard.py, companies.json, data.json, dashboard.html, log.md

## 2026-05-14 ~11:30 PDT
Layout-jump fix — ticker column halved on row expansion.
- Reproduced: at 390px viewport, cell widths went from 18/96/30/0/42 (rank/ticker/score/ad/delta) to 18/48/30/0/42 the moment a row was clicked. All rows in the table re-laid out at the new widths, so the user saw the entire left column "shrink" on expand.
- Root cause: `td.ad { display: none }` removed the AD column from the table layout, but the new `<tr class="blurb-row"><td colspan="5">` still references 5 columns. With `table-layout: fixed`, the browser couldn't reconcile a 4-visible-column layout with a 5-column-spanning cell, and re-distributed the unsized ticker column width to "make room" — landed on exactly half.
- Fix: replace `display: none` on the AD column with `width: 0; padding: 0; border: 0; font-size: 0; overflow: hidden;` so the column stays in the table layout but renders as a 0px-wide invisible cell. Now colspan=5 references 5 real columns (one of which is 0-width) and the layout doesn't reflow on expand.
- Verified: cell widths identical before/after expand at 390px (18/96/30/0/42 in both states). Desktop verifier still passes.
Files: build_dashboard.py, dashboard.html, log.md

## 2026-05-14 ~11:00 PDT
Blurb wrap fix — full panel width, not stuck in ticker column.
- Problem: when expanded, blurb was a `<span>` inside `td.ticker` (~80–96px wide on mobile), so each line wrapped at ~10 chars and a 1-sentence company description took 18 visual lines. User flagged this as too cramped.
- Fix: emit blurb as its own `<tr class="blurb-row">` sibling with `<td colspan="5">` cell. CSS hides it by default; `tr.main-row.expanded + tr.blurb-row { display: table-row }` reveals it adjacent to the expanded main row, spanning all 5 columns (~186px on mobile, full panel width on desktop).
- Mobile column rebalance: tightened rank (22→18), score (34→30), delta (50→42) to give ticker column ~96px (vs 80px) — industries now wrap to 2 lines instead of 4.
- Dropped the leading "· " bullet on industry on mobile via a wrapped `<span class="bullet">` that's hidden in the mobile media query — saved a leading line break in narrow cells.
- Click handler scoped to `.main-row` only (since `.blurb-row` is now also a `<tr>` under tbody and we don't want to flip its expansion state).
- Verifier: scope `query_selector_all` to `tr.main-row` so 14 rows ≠ 28 (was counting blurb rows). Read blurb via `el.nextElementSibling.querySelector('.blurb')` instead of inside the row.
Files: build_dashboard.py, verify_dashboard.py, dashboard.html, log.md

## 2026-05-14 ~10:30 PDT
Collapsible blurb + industry always visible on mobile.
- Blurb is now hidden by default everywhere (desktop + mobile). Clicking anywhere on a row except the ticker link expands the blurb; clicking another row collapses the previous and expands the new (single-expansion rule).
- Click handler: event delegation on each `tbody`, `e.target.closest("a")` short-circuits so the ticker link still navigates. `tbody.innerHTML` reset on date-switch wipes state cleanly; listeners survive (attached to `tbody`, not rows).
- Mobile: `.industry` now renders as its own line (block) below the ticker — was previously hidden along with `.co`/`.blurb`. `.co` (company name) still hidden on mobile (saves vertical space; row click reveals everything in the blurb anyway).
- Mobile expansion fix: original `.panel { overflow: hidden }` clipped the expanded blurb; added rule to let `.industry`/`.blurb` wrap freely (`white-space: normal; overflow: visible`) while other cells stay nowrap+ellipsis.
- Verifier updated: ensures blurb hidden by default → click row's `td.rank` (not `.ticker` link) → blurb visible → click next row → first row collapses. All assertions pass.
Files: build_dashboard.py, verify_dashboard.py, dashboard.html, log.md

## 2026-05-14 ~10:00 PDT
Show full match list (drop top-10 cap) + mobile side-by-side + AD legend.
- `build_dashboard.py`: removed `TOP_N=10` constant + `.slice(0, TOP_N)` calls; both panels now render the entire `full_matches` list. Headers updated to "{date} — N full matches".
- `verify_dashboard.py`: replaced `top10_*[:10]` with full `expected_*` lists; assertions now require row count exactly equals upstream full-match count.
- Mobile (`@media (max-width: 760px)`): forced `grid-template-columns: 1fr 1fr` so panels stay side-by-side at iPhone widths (was collapsing at 1100px). Compressed: hide `.co`/`.industry`/`.blurb`, hide AD column, shrink padding/fonts, `table-layout: fixed`, narrow column widths. Tested at 390px viewport: `body.scrollWidth=390` (no horizontal scroll), 14+11 row lists both visible.
- Status badges: emit dual `.badge-long` ("↓ to #14") + `.badge-short` ("↓#14") spans; mobile CSS swaps which one shows.
- Pitfall hit and fixed: original `@media` block was placed before the desktop rules in the stylesheet, so same-specificity desktop rules won the cascade and mobile rules silently no-op'd. Moved media block to end of `<style>` and added `!important` on the show/hide toggles. Confirmed via Playwright `getComputedStyle` checks.
- AD column documentation: added `title=` tooltip on the desktop `<th>` (Accumulation/Distribution grade A–E from up-day vs down-day volume over ~13 weeks). Added a "what's AD?" toggle in the header that expands a one-line legend covering AD / Score / Δ — works on mobile where tooltips don't.
- Added `<meta name="viewport" content="width=device-width, initial-scale=1">` so iOS Safari renders at device width instead of zoomed-out desktop scale.
- `_verify_closeup.png` will go stale (pre-mobile-redesign); not regenerated this round.
Files: build_dashboard.py, verify_dashboard.py, dashboard.html, data.json, companies.json, README.md, log.md

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
