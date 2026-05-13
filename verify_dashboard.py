"""Headless playwright check for dashboard.html.

Asserts:
  - page loads, shows regime badge
  - left table renders <= 10 rows of primary-date full matches
  - right table renders <= 10 rows of prior-date full matches
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

    top10_today = [it["ticker"] for it in primary["full_matches"][:10]]
    top10_prior = [it["ticker"] for it in prior_report["full_matches"][:10]]

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
        assert 0 < len(left_rows) <= 10, "left should be 1..10 rows"
        assert 0 < len(right_rows) <= 10, "right should be 1..10 rows"

        left_tickers = [r.query_selector("td.ticker .sym").inner_text().strip()
                        for r in left_rows]
        right_tickers = [r.query_selector("td.ticker .sym").inner_text().strip()
                         for r in right_rows]
        print(f"[check] left tickers : {left_tickers}")
        print(f"[check] right tickers: {right_tickers}")
        assert left_tickers == top10_today[:len(left_rows)], \
            f"left mismatch\n got {left_tickers}\n exp {top10_today}"
        assert right_tickers == top10_prior[:len(right_rows)], \
            f"right mismatch\n got {right_tickers}\n exp {top10_prior}"

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

        # Company name + blurb must render for the top 3 rows.
        companies = data.get("companies") or {}
        for i in range(min(3, len(left_rows))):
            tk = left_tickers[i]
            co = companies.get(tk) or {}
            row = left_rows[i]
            name_el  = row.query_selector("td.ticker .co")
            blurb_el = row.query_selector("td.ticker .blurb")
            name  = name_el.inner_text().strip()  if name_el  else ""
            blurb = blurb_el.inner_text().strip() if blurb_el else ""
            print(f"[check] row {i+1} {tk}: name={name!r}  blurb[0:80]={blurb[:80]!r}")
            assert co.get("name"), f"no cached company name for {tk}"
            assert name == co["name"], f"{tk} rendered name != cache"
            if co.get("blurb"):
                assert blurb.startswith(co["blurb"][:40]), \
                    f"{tk} blurb mismatch"

        # Switch date dropdown to prior date and re-check left table.
        page.select_option("#dateSelect", prior)
        page.wait_for_timeout(200)
        left_rows2 = page.query_selector_all("#leftTable tbody tr")
        left_tickers2 = [r.query_selector("td.ticker .sym").inner_text().strip()
                         for r in left_rows2]
        print(f"[check] after switch left tickers: {left_tickers2}")
        assert left_tickers2 == top10_prior[:len(left_rows2)], \
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
