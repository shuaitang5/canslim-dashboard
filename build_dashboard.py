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
  @media (max-width: 1100px) { main { grid-template-columns: 1fr; } }
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
  td.ticker .blurb { display: block; color: var(--muted); font-size: 11.5px;
                     line-height: 1.45; margin-top: 2px; max-width: 520px; }
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
</style>
</head>
<body>

<header>
  <h1>CANSLIM full matches</h1>
  <span id="regime" class="regime"></span>
  <label class="compare-note">Date <select id="dateSelect"></select></label>
  <span class="compare-note" id="compareNote"></span>
  <a id="sourceLink" href="#" target="_blank" rel="noopener">open source report ↗</a>
</header>

<main>
  <section class="panel">
    <h2 id="leftTitle">Today — top 10</h2>
    <div class="sub" id="leftSub"></div>
    <table id="leftTable">
      <thead>
        <tr><th>#</th><th>Ticker</th><th class="num">Score</th><th>AD</th><th class="delta">Δ vs prior</th></tr>
      </thead>
      <tbody></tbody>
    </table>
  </section>
  <section class="panel">
    <h2 id="rightTitle">Prior day — top 10</h2>
    <div class="sub" id="rightSub"></div>
    <table id="rightTable">
      <thead>
        <tr><th>#</th><th>Ticker</th><th class="num">Score</th><th>AD</th><th class="delta">Status today</th></tr>
      </thead>
      <tbody></tbody>
    </table>
  </section>
</main>

<script id="data" type="application/json">__DATA_JSON__</script>
<script>
(function () {
  const DATA = JSON.parse(document.getElementById("data").textContent);
  const TOP_N = 10;
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
    if (!primaryMap) return { cls: "b-same", text: "—" };
    const today = primaryMap.get(priorItem.ticker);
    if (!today) return { cls: "b-drop", text: "DROPPED" };
    const delta = priorItem.rank - today.rank;
    if (delta === 0) return { cls: "b-same", text: "held #" + today.rank };
    if (delta > 0) return { cls: "b-up", text: "↑ to #" + today.rank };
    return { cls: "b-down", text: "↓ to #" + today.rank };
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
      const d = deltaFn(it);
      if (options.droppedCheck && options.droppedCheck(it)) {
        tr.classList.add("dropped");
      }
      const co = companies[it.ticker] || {};
      const nameHtml   = co.name     ? '<span class="co">' + escapeHtml(co.name) + '</span>' : '';
      const indHtml    = co.industry ? '<span class="industry">· ' + escapeHtml(co.industry) + '</span>' : '';
      const blurbHtml  = co.blurb    ? '<span class="blurb">' + escapeHtml(co.blurb) + '</span>' : '';
      tr.innerHTML =
        '<td class="rank">' + it.rank + '</td>' +
        '<td class="ticker">' +
          '<span class="sym"><a href="' + options.sourceUrl + '#c-' + it.ticker + '" target="_blank" rel="noopener">' + it.ticker + '</a></span>' +
          nameHtml + indHtml + blurbHtml +
        '</td>' +
        '<td class="num">' + (it.score != null ? it.score.toFixed(2) : '—') + '</td>' +
        '<td class="ad">' + (it.ad || '—') + '</td>' +
        '<td class="delta"><span class="badge ' + d.cls + '">' + d.text + '</span></td>';
      tbody.appendChild(tr);
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
      primaryDate + " — top " + TOP_N + " (of " + primary.full_matches_total + ")";
    document.getElementById("leftSub").textContent =
      "Full CANSLIM matches ranked by composite score.";

    document.getElementById("rightTitle").textContent =
      prior ? priorDate + " — top " + TOP_N + " (of " + prior.full_matches_total + ")"
            : "No prior report";
    document.getElementById("rightSub").textContent =
      prior ? "Prior trading day — used as the comparison baseline." : "";

    const primaryTop = (primary.full_matches || []).slice(0, TOP_N);
    const priorTop   = prior ? (prior.full_matches || []).slice(0, TOP_N) : [];

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
