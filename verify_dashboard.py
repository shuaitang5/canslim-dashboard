"""Headless playwright check for dashboard.html.

Asserts:
  - page loads, shows regime badge
  - left table renders the full primary-date full-match list
  - right table renders the full prior-date full-match list
  - delta badges appear (NEW / ↑N / ↓N / DROPPED)
  - switching the date dropdown changes the left table contents
  - captures screenshot to _verify.png
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent


def main() -> int:
    data = json.loads((HERE / "data.json").read_text())
    dates = data["dates"]
    assert len(dates) >= 2, "need at least 2 dates for diff testing"
    latest = dates[0]
    prior = dates[1]

    primary = data["reports"][latest]
    prior_report = data["reports"][prior]

    expected_today = [it["ticker"] for it in primary["full_matches"]]
    expected_prior = [it["ticker"] for it in prior_report["full_matches"]]

    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 1400, "height": 900})
        page = ctx.new_page()
        url = (HERE / "dashboard.html").as_uri()
        page.goto(url)
        page.wait_for_selector("#leftTable tbody tr")

        regime = page.text_content("#regime")
        print(f"[check] regime text: {regime!r}")
        assert regime, "regime badge empty"

        left_rows = page.query_selector_all("#leftTable tbody tr")
        right_rows = page.query_selector_all("#rightTable tbody tr")
        print(f"[check] left rows={len(left_rows)}  right rows={len(right_rows)}")
        assert len(left_rows) == len(expected_today), \
            f"left rows={len(left_rows)} expected={len(expected_today)}"
        assert len(right_rows) == len(expected_prior), \
            f"right rows={len(right_rows)} expected={len(expected_prior)}"

        left_tickers = [r.query_selector("td.ticker .sym").inner_text().strip()
                        for r in left_rows]
        right_tickers = [r.query_selector("td.ticker .sym").inner_text().strip()
                         for r in right_rows]
        print(f"[check] left tickers : {left_tickers}")
        print(f"[check] right tickers: {right_tickers}")
        assert left_tickers == expected_today, \
            f"left mismatch\n got {left_tickers}\n exp {expected_today}"
        assert right_tickers == expected_prior, \
            f"right mismatch\n got {right_tickers}\n exp {expected_prior}"

        badges = page.query_selector_all("#leftTable tbody .badge")
        badge_texts = [b.inner_text().strip() for b in badges]
        print(f"[check] left badges  : {badge_texts}")
        assert any(b in ("NEW", "=") or b.startswith("↑") or b.startswith("↓")
                   for b in badge_texts), "no recognized diff badges"

        right_badges = page.query_selector_all("#rightTable tbody .badge")
        right_badge_texts = [b.inner_text().strip() for b in right_badges]
        print(f"[check] right badges : {right_badge_texts}")

        # Confirm the ticker anchor href points at #c-TICKER on the source run.
        first_link = page.query_selector("#leftTable tbody tr td.ticker a")
        href = first_link.get_attribute("href")
        print(f"[check] first link   : {href}")
        assert f"#c-{left_tickers[0]}" in href, "ticker link missing anchor"

        # Company name renders by default; blurb hidden until row is clicked.
        companies = data.get("companies") or {}
        for i in range(min(3, len(left_rows))):
            tk = left_tickers[i]
            co = companies.get(tk) or {}
            row = left_rows[i]
            name_el  = row.query_selector("td.ticker .co")
            name  = name_el.inner_text().strip()  if name_el  else ""
            print(f"[check] row {i+1} {tk}: name={name!r}")
            assert co.get("name"), f"no cached company name for {tk}"
            assert name == co["name"], f"{tk} rendered name != cache"

            # Ensure no row is already expanded (could be from prior iteration).
            page.evaluate("document.querySelectorAll('tbody tr.expanded').forEach(r => r.classList.remove('expanded'))")
            # Click on the rank cell (not the ticker link) to expand.
            row.query_selector("td.rank").click()
            page.wait_for_timeout(50)
            assert "expanded" in (row.get_attribute("class") or ""), \
                f"row {tk} did not expand on click"
            blurb_el = row.query_selector("td.ticker .blurb")
            blurb = blurb_el.inner_text().strip() if blurb_el else ""
            if co.get("blurb"):
                assert blurb.startswith(co["blurb"][:40]), \
                    f"{tk} blurb mismatch when expanded"

            # Single-expansion rule: clicking another row should collapse this one.
            if i + 1 < len(left_rows):
                left_rows[i + 1].query_selector("td.rank").click()
                page.wait_for_timeout(50)
                assert "expanded" not in (row.get_attribute("class") or ""), \
                    f"row {tk} should have collapsed when row {i+2} expanded"

        # Switch date dropdown to prior date and re-check left table.
        page.select_option("#dateSelect", prior)
        page.wait_for_timeout(200)
        left_rows2 = page.query_selector_all("#leftTable tbody tr")
        left_tickers2 = [r.query_selector("td.ticker .sym").inner_text().strip()
                         for r in left_rows2]
        print(f"[check] after switch left tickers: {left_tickers2}")
        assert left_tickers2 == expected_prior, \
            "date-switch did not re-render correctly"

        # Switch back and screenshot.
        page.select_option("#dateSelect", latest)
        page.wait_for_timeout(200)
        shot = HERE / "_verify.png"
        page.screenshot(path=str(shot), full_page=True)
        print(f"[ok] screenshot -> {shot}")

        browser.close()

    print("[pass] all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
