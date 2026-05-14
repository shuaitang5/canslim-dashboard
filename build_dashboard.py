"""Build the CANSLIM dashboard.

Fetches the canslim-scanner github.io index, downloads each available run's
HTML, parses the full-match tickers (rank / score / A/D grade / regime), and
emits two artifacts into this directory:

  - data.json        : raw parsed data, one entry per available date
  - dashboard.html   : self-contained static page (data inlined)

Usage:
    python3 build_dashboard.py
"""

from __future__ import annotations

import json
import re
import sys
import urllib.request
from pathlib import Path

BASE_URL = "https://zhoutongchar.github.io/canslim-scanner/"
HERE = Path(__file__).resolve().parent


def fetch(url: str) -> str:
    with urllib.request.urlopen(url, timeout=30) as r:
        return r.read().decode("utf-8", errors="replace")


def discover_runs() -> list[tuple[str, str]]:
    """Return [(date, run_url)] sorted newest-first."""
    index_html = fetch(BASE_URL)
    paths = sorted(set(re.findall(r'runs/(\d{4}-\d{2}-\d{2})_(\d+)/', index_html)))
    # one run per day — keep the latest timestamp per date
    by_date: dict[str, str] = {}
    for date, stamp in paths:
        by_date[date] = stamp  # later overwrites earlier -> kept latest
    out = []
    for date in sorted(by_date.keys(), reverse=True):
        stamp = by_date[date]
        out.append((date, f"{BASE_URL}runs/{date}_{stamp}/"))
    return out


CANDIDATE_RE = re.compile(
    r'<details class="candidate"[^>]*data-ticker="([^"]+)"[^>]*>\s*<summary>(.*?)</summary>',
    re.DOTALL,
)
MATCHES_SECTION_RE = re.compile(
    r'<section class="bucket bucket-matches"[^>]*>(.*?)</section>',
    re.DOTALL,
)
SCORE_RE = re.compile(r'<span class="score mono">([^<]+)</span>')
GATES_RE = re.compile(r'<span class="gates">([^<]+)</span>')
AD_RE = re.compile(r'AD:\s*([A-Z+\-]+)')
REGIME_RE = re.compile(
    r'<span class="regime-badge regime-(\w+)[^"]*"[^>]*>([^<]+)</span>'
)


def parse_report(html: str, date: str, source_url: str) -> dict:
    section = MATCHES_SECTION_RE.search(html)
    items: list[dict] = []
    if section:
        body = section.group(1)
        for idx, m in enumerate(CANDIDATE_RE.finditer(body), start=1):
            ticker = m.group(1)
            summary = m.group(2)
            score = SCORE_RE.search(summary)
            gates = GATES_RE.search(summary)
            ad = AD_RE.search(summary)
            items.append(
                {
                    "rank": idx,
                    "ticker": ticker,
                    "score": float(score.group(1)) if score else None,
                    "gates": gates.group(1) if gates else "",
                    "ad": ad.group(1) if ad else "",
                }
            )
    regime_m = REGIME_RE.search(html)
    return {
        "date": date,
        "source_url": source_url,
        "regime": regime_m.group(2) if regime_m else "",
        "full_matches_total": len(items),
        "full_matches": items,
    }


def build_data() -> dict:
    runs = discover_runs()
    print(f"[discover] {len(runs)} run(s) found", file=sys.stderr)
    by_date: dict[str, dict] = {}
    for date, url in runs:
        print(f"[fetch] {date} -> {url}", file=sys.stderr)
        html = fetch(url)
        by_date[date] = parse_report(html, date, url)
    dates_desc = sorted(by_date.keys(), reverse=True)
    return {"dates": dates_desc, "reports": by_date}


HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>CANSLIM full-match dashboard</title>
<style>
  :root {
    --bg: #ffffff; --bg-alt: #f7f8f9; --bg-dark: #eceef0;
    --border: #d8dde3; --text: #1a1f2b; --muted: #5b6473;
    --accent: #1a4480; --pass: #2e7d32; --fail: #c62828;
    --warn: #e9740b; --info: #0277bd;
    --mono: ui-monospace, "SF Mono", Menlo, monospace;
    --sans: -apple-system, "Inter", "Segoe UI", system-ui, sans-serif;
  }
  * { box-sizing: border-box; }
  body { font: 13px/1.5 var(--sans); color: var(--text); background: var(--bg); margin: 0; }
  header { padding: 14px 20px; border-bottom: 1px solid var(--border);
           display: flex; gap: 16px; align-items: center; flex-wrap: wrap;
           position: sticky; top: 0; background: var(--bg); z-index: 10; }
  header h1 { margin: 0; font-size: 16px; font-weight: 600; }
  .regime { display: inline-block; padding: 2px 10px; border-radius: 3px;
            font-size: 11px; font-weight: 700; letter-spacing: 0.05em; }
  .regime-UPTREND { background: var(--pass); color: white; }
  .regime-CAUTION { background: var(--warn); color: white; }
  .regime-DOWN    { background: var(--fail); color: white; }
  header select { font: inherit; padding: 4px 8px; border: 1px solid var(--border);
                  border-radius: 3px; background: white; }
  header a { color: var(--accent); text-decoration: none; font-family: var(--mono); font-size: 12px; }
  header a:hover { text-decoration: underline; }
  .compare-note { color: var(--muted); font-size: 12px; }

  main { display: grid; grid-template-columns: 1fr 1fr; gap: 20px;
         padding: 20px; max-width: 1700px; margin: 0 auto; }
  .badge-short { display: none; }
  .badge-long { display: inline; }
  .panel h2 { margin: 0 0 4px 0; font-size: 14px; }
  .panel .sub { color: var(--muted); font-size: 12px; margin-bottom: 10px; }
  table { width: 100%; border-collapse: collapse; }
  th, td { padding: 6px 8px; border-bottom: 1px solid var(--border); text-align: left; font-size: 13px; }
  th { background: var(--bg-alt); font-size: 11px; text-transform: uppercase;
       letter-spacing: 0.04em; color: var(--muted); font-weight: 600; }
  td.rank { font-family: var(--mono); color: var(--muted); width: 28px; vertical-align: top; }
  td.ticker { vertical-align: top; min-width: 240px; }
  td.ticker .sym { font-family: var(--mono); font-weight: 700; }
  td.ticker .sym a { color: var(--accent); text-decoration: none; }
  td.ticker .sym a:hover { text-decoration: underline; }
  td.ticker .co { color: var(--text); margin-left: 6px; font-size: 12px; }
  td.ticker .industry { color: var(--muted); font-size: 11px; margin-left: 6px; }
  /* Blurb lives in its own full-width row (colspan=5), hidden until main row
     is .expanded — gives the description the full panel width to wrap into. */
  tbody tr.main-row { cursor: pointer; }
  tbody tr.blurb-row { display: none; }
  tbody tr.main-row.expanded + tr.blurb-row { display: table-row; }
  tbody tr.main-row.expanded td { background: var(--bg-alt); }
  td.blurb-cell { padding: 6px 12px 10px; background: var(--bg-alt);
                  border-bottom: 1px solid var(--border); }
  td.blurb-cell .blurb { color: var(--muted); font-size: 11.5px;
                         line-height: 1.5; max-width: none; }
  td.num { font-family: var(--mono); text-align: right; vertical-align: top; }
  td.ad { font-family: var(--mono); text-align: center; width: 34px; vertical-align: top; }
  td.delta { text-align: right; width: 110px; vertical-align: top; }
  .badge { display: inline-block; padding: 2px 8px; border-radius: 10px;
           font-size: 11px; font-weight: 700; font-family: var(--mono); }
  .b-new   { background: #e1f5fe; color: var(--info); }
  .b-up    { background: #c8e6c9; color: var(--pass); }
  .b-down  { background: #ffcdd2; color: var(--fail); }
  .b-same  { background: var(--bg-dark); color: var(--muted); }
  .b-drop  { background: #ffcdd2; color: var(--fail); text-decoration: line-through; }
  tr.dropped td { color: var(--muted); }
  .empty { color: var(--muted); padding: 20px; text-align: center; font-style: italic; }

  /* On narrow screens (phones), keep side-by-side but compress: hide blurb/industry,
     drop AD column (legend explains it), shrink padding & fonts so both panels fit
     on ~390px viewports. Status badges show short variant ("h#3" / "↑#5" / "drop"). */
  @media (max-width: 760px) {
    main { gap: 6px; padding: 6px; grid-template-columns: 1fr 1fr; }
    body { font-size: 11px; }
    .panel { min-width: 0; overflow: hidden; }
    table { table-layout: fixed; width: 100%; }
    th, td { padding: 3px 3px; font-size: 10.5px; white-space: nowrap;
             overflow: hidden; text-overflow: ellipsis; }
    /* Ticker cell holds symbol + industry — needs to wrap, not clip. */
    td.ticker { white-space: normal; overflow: visible; text-overflow: clip; }
    td.ticker .industry { white-space: normal; overflow: visible; text-overflow: clip; }
    td.blurb-cell { padding: 4px 6px 8px; white-space: normal; overflow: visible;
                    text-overflow: clip; }
    td.blurb-cell .blurb { font-size: 10.5px; line-height: 1.45;
                           white-space: normal; overflow: visible; text-overflow: clip; }
    td.rank, th:first-child { width: 18px; padding-right: 0; padding-left: 4px; }
    td.ticker { min-width: 0; }
    /* Ticker column gets all remaining width — score and delta are tightened. */
    td.ticker .co { display: none !important; }
    td.ticker .industry { display: block; margin-left: 0; margin-top: 2px;
                          font-size: 9.5px; white-space: normal; }
    /* Hide the desktop bullet prefix on mobile (saved as ::before via JS data). */
    td.ticker .industry .bullet { display: none; }
    th.num, td.num { width: 30px; font-size: 9.5px; padding-left: 1px; padding-right: 1px; }
    th.ad-col, td.ad { display: none; }
    th.delta, td.delta { width: 42px; padding-left: 1px; padding-right: 2px; font-size: 9.5px; }
    /* Shrink table headers so they don't overflow at 186px panel width. */
    th { font-size: 9px; padding: 3px 2px; letter-spacing: 0; }
    .badge { padding: 1px 3px; font-size: 9.5px; }
    .badge-long { display: none !important; }
    .badge-short { display: inline !important; }
    .panel h2 { font-size: 11.5px; }
    .panel .sub { display: none; }
    header { padding: 8px 10px; gap: 8px; }
    header h1 { font-size: 13px; }
  }
</style>
</head>
<body>

<header>
  <h1>CANSLIM full matches</h1>
  <span id="regime" class="regime"></span>
  <label class="compare-note">Date <select id="dateSelect"></select></label>
  <span class="compare-note" id="compareNote"></span>
  <a id="sourceLink" href="#" target="_blank" rel="noopener">open source report ↗</a>
  <a id="legendToggle" href="#" class="compare-note" style="cursor:pointer">what's AD?</a>
</header>
<div id="legend" style="display:none; padding: 8px 20px; background: var(--bg-alt); border-bottom: 1px solid var(--border); font-size: 12px; color: var(--muted);">
  <strong>AD</strong> = Accumulation/Distribution grade (A–E). A/B = institutional buying, D/E = institutional selling, C = neutral. Based on up-day vs down-day volume over the prior ~13 weeks. &nbsp;·&nbsp;
  <strong>Score</strong> = composite CANSLIM score from upstream. &nbsp;·&nbsp;
  <strong>Δ vs prior</strong>: NEW = wasn't in yesterday's full-match list; ↑N/↓N = rank moved by N spots.
</div>

<main>
  <section class="panel">
    <h2 id="leftTitle">Today — full matches</h2>
    <div class="sub" id="leftSub"></div>
    <table id="leftTable">
      <thead>
        <tr><th>#</th><th>Ticker</th><th class="num">Score</th><th class="ad-col" title="Accumulation/Distribution grade (A–E). A/B = institutional buying, D/E = institutional selling, C = neutral. Based on volume on up-days vs down-days over the prior ~13 weeks.">AD</th><th class="delta">Δ vs prior</th></tr>
      </thead>
      <tbody></tbody>
    </table>
  </section>
  <section class="panel">
    <h2 id="rightTitle">Prior day — full matches</h2>
    <div class="sub" id="rightSub"></div>
    <table id="rightTable">
      <thead>
        <tr><th>#</th><th>Ticker</th><th class="num">Score</th><th class="ad-col" title="Accumulation/Distribution grade (A–E). A/B = institutional buying, D/E = institutional selling, C = neutral. Based on volume on up-days vs down-days over the prior ~13 weeks.">AD</th><th class="delta">Status today</th></tr>
      </thead>
      <tbody></tbody>
    </table>
  </section>
</main>

<script id="data" type="application/json">__DATA_JSON__</script>
<script>
(function () {
  const DATA = JSON.parse(document.getElementById("data").textContent);
  const dates = DATA.dates;
  const reports = DATA.reports;
  const companies = DATA.companies || {};

  function escapeHtml(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }

  const sel = document.getElementById("dateSelect");
  dates.forEach((d, i) => {
    const o = document.createElement("option");
    o.value = d; o.textContent = d + (i === 0 ? "  (latest)" : "");
    sel.appendChild(o);
  });
  sel.value = dates[0];
  sel.addEventListener("change", render);

  document.getElementById("legendToggle").addEventListener("click", function (e) {
    e.preventDefault();
    const el = document.getElementById("legend");
    el.style.display = (el.style.display === "none") ? "block" : "none";
  });

  function rankMap(report) {
    const m = new Map();
    (report.full_matches || []).forEach(it => m.set(it.ticker, it));
    return m;
  }

  function deltaBadge(primaryItem, priorMap) {
    if (!priorMap) return { cls: "b-same", text: "—" };
    const prior = priorMap.get(primaryItem.ticker);
    if (!prior) return { cls: "b-new", text: "NEW" };
    const delta = prior.rank - primaryItem.rank; // +ve = moved up
    if (delta === 0) return { cls: "b-same", text: "=" };
    if (delta > 0) return { cls: "b-up", text: "↑" + delta };
    return { cls: "b-down", text: "↓" + Math.abs(delta) };
  }

  function priorStatus(priorItem, primaryMap) {
    if (!primaryMap) return { cls: "b-same", text: "—", short: "—" };
    const today = primaryMap.get(priorItem.ticker);
    if (!today) return { cls: "b-drop", text: "DROPPED", short: "drop" };
    const delta = priorItem.rank - today.rank;
    if (delta === 0) return { cls: "b-same", text: "held #" + today.rank, short: "h#" + today.rank };
    if (delta > 0) return { cls: "b-up", text: "↑ to #" + today.rank, short: "↑#" + today.rank };
    return { cls: "b-down", text: "↓ to #" + today.rank, short: "↓#" + today.rank };
  }

  function renderTable(tbody, items, deltaFn, options={}) {
    tbody.innerHTML = "";
    if (!items.length) {
      const tr = document.createElement("tr");
      tr.innerHTML = '<td colspan="5" class="empty">No full matches.</td>';
      tbody.appendChild(tr);
      return;
    }
    items.forEach(it => {
      const tr = document.createElement("tr");
      tr.className = "main-row";
      const d = deltaFn(it);
      if (options.droppedCheck && options.droppedCheck(it)) {
        tr.classList.add("dropped");
      }
      const co = companies[it.ticker] || {};
      const nameHtml = co.name     ? '<span class="co">' + escapeHtml(co.name) + '</span>' : '';
      const indHtml  = co.industry ? '<span class="industry"><span class="bullet">· </span>' + escapeHtml(co.industry) + '</span>' : '';
      tr.innerHTML =
        '<td class="rank">' + it.rank + '</td>' +
        '<td class="ticker">' +
          '<span class="sym"><a href="' + options.sourceUrl + '#c-' + it.ticker + '" target="_blank" rel="noopener">' + it.ticker + '</a></span>' +
          nameHtml + indHtml +
        '</td>' +
        '<td class="num">' + (it.score != null ? it.score.toFixed(2) : '—') + '</td>' +
        '<td class="ad">' + (it.ad || '—') + '</td>' +
        '<td class="delta"><span class="badge ' + d.cls + '">' +
          '<span class="badge-long">' + d.text + '</span>' +
          '<span class="badge-short">' + (d.short || d.text) + '</span>' +
        '</span></td>';
      tbody.appendChild(tr);

      // Sibling row holds the blurb spanning all columns; CSS shows it when
      // main row has `.expanded`. Always rendered (even if blurb empty) so the
      // sibling-selector arithmetic stays predictable.
      const blurbTr = document.createElement("tr");
      blurbTr.className = "blurb-row";
      const blurbHtml = co.blurb ? escapeHtml(co.blurb) : '';
      blurbTr.innerHTML =
        '<td colspan="5" class="blurb-cell"><div class="blurb">' + blurbHtml + '</div></td>';
      tbody.appendChild(blurbTr);
    });
  }

  function render() {
    const primaryDate = sel.value;
    const idx = dates.indexOf(primaryDate);
    const priorDate = dates[idx + 1] || null;
    const primary = reports[primaryDate];
    const prior = priorDate ? reports[priorDate] : null;

    const regimeEl = document.getElementById("regime");
    regimeEl.textContent = primary.regime || "UNKNOWN";
    regimeEl.className = "regime regime-" + (primary.regime || "UNKNOWN");

    document.getElementById("sourceLink").href = primary.source_url;
    document.getElementById("compareNote").textContent =
      prior ? "comparing " + primaryDate + "  vs  " + priorDate
            : "no prior report available for comparison";

    document.getElementById("leftTitle").textContent =
      primaryDate + " — " + primary.full_matches_total + " full matches";
    document.getElementById("leftSub").textContent =
      "Full CANSLIM matches ranked by composite score.";

    document.getElementById("rightTitle").textContent =
      prior ? priorDate + " — " + prior.full_matches_total + " full matches"
            : "No prior report";
    document.getElementById("rightSub").textContent =
      prior ? "Prior trading day — used as the comparison baseline." : "";

    const primaryTop = primary.full_matches || [];
    const priorTop   = prior ? (prior.full_matches || []) : [];

    const primaryMap = rankMap(primary);
    const priorMap   = prior ? rankMap(prior) : null;

    renderTable(
      document.querySelector("#leftTable tbody"),
      primaryTop,
      it => deltaBadge(it, priorMap),
      { sourceUrl: primary.source_url }
    );
    renderTable(
      document.querySelector("#rightTable tbody"),
      priorTop,
      it => priorStatus(it, primaryMap),
      {
        sourceUrl: prior ? prior.source_url : "#",
        droppedCheck: it => primaryMap && !primaryMap.has(it.ticker),
      }
    );
  }

  render();

  // Row click expands the blurb; clicking the ticker link follows the link.
  // Only one main-row can be expanded at a time across BOTH tables.
  function onRowClick(e) {
    if (e.target.closest("a")) return;  // let ticker link navigate
    const tr = e.target.closest("tr.main-row");
    if (!tr || tr.querySelector(".empty")) return;
    const wasExpanded = tr.classList.contains("expanded");
    document.querySelectorAll("tbody tr.main-row.expanded").forEach(r => r.classList.remove("expanded"));
    if (!wasExpanded) tr.classList.add("expanded");
  }
  document.querySelector("#leftTable tbody").addEventListener("click", onRowClick);
  document.querySelector("#rightTable tbody").addEventListener("click", onRowClick);
})();
</script>

</body>
</html>
"""


def main() -> None:
    data = build_data()
    companies_path = HERE / "companies.json"
    if companies_path.exists():
        data["companies"] = json.loads(companies_path.read_text())
        print(f"[merge] {len(data['companies'])} company entries from "
              f"{companies_path.name}", file=sys.stderr)
    else:
        data["companies"] = {}
        print("[warn] companies.json not found — run enrich_companies.py",
              file=sys.stderr)
    (HERE / "data.json").write_text(json.dumps(data, indent=2))
    html = HTML_TEMPLATE.replace("__DATA_JSON__", json.dumps(data))
    (HERE / "dashboard.html").write_text(html)
    print(f"[write] {HERE / 'data.json'}", file=sys.stderr)
    print(f"[write] {HERE / 'dashboard.html'}", file=sys.stderr)


if __name__ == "__main__":
    main()
