"""Pull company name + short blurb for every ticker in data.json.

Uses yfinance's `info` (which wraps Yahoo Finance's quote summary). Cached to
companies.json so repeat runs are free and robust to Yahoo rate limits.

Usage:
    python3 enrich_companies.py              # enrich missing tickers only
    python3 enrich_companies.py --refresh    # re-fetch everything
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA_FILE = HERE / "data.json"
CACHE_FILE = HERE / "companies.json"


def first_two_sentences(text: str) -> str:
    """Return first 1-2 sentences, capped at ~320 chars for UI tidy-ness."""
    if not text:
        return ""
    text = re.sub(r"\s+", " ", text).strip()
    parts = re.split(r"(?<=[.!?])\s+", text)
    out = parts[0] if parts else text
    if len(parts) > 1 and len(out) < 180:
        out += " " + parts[1]
    if len(out) > 320:
        out = out[:317].rstrip() + "…"
    return out


def fetch_one(ticker: str) -> dict:
    import yfinance as yf

    info = yf.Ticker(ticker).info or {}
    name = info.get("longName") or info.get("shortName") or ticker
    industry = info.get("industry") or ""
    sector = info.get("sector") or ""
    blurb = first_two_sentences(info.get("longBusinessSummary") or "")
    return {
        "ticker": ticker,
        "name": name,
        "industry": industry,
        "sector": sector,
        "blurb": blurb,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true",
                    help="re-fetch every ticker, ignoring cache")
    args = ap.parse_args()

    data = json.loads(DATA_FILE.read_text())
    tickers = sorted({
        it["ticker"]
        for rpt in data["reports"].values()
        for it in rpt["full_matches"]
    })
    print(f"[discover] {len(tickers)} unique tickers: {tickers}", file=sys.stderr)

    cache: dict[str, dict] = {}
    if CACHE_FILE.exists() and not args.refresh:
        cache = json.loads(CACHE_FILE.read_text())
        print(f"[cache] {len(cache)} cached entries", file=sys.stderr)

    todo = [t for t in tickers if t not in cache]
    print(f"[todo] fetching {len(todo)} ticker(s)", file=sys.stderr)

    for t in todo:
        try:
            cache[t] = fetch_one(t)
            print(f"  [ok] {t} — {cache[t]['name']}", file=sys.stderr)
        except Exception as e:
            print(f"  [err] {t}: {e}", file=sys.stderr)
            cache[t] = {
                "ticker": t, "name": t, "industry": "", "sector": "",
                "blurb": "",
            }
        time.sleep(0.2)  # be nice to Yahoo

    CACHE_FILE.write_text(json.dumps(cache, indent=2))
    print(f"[write] {CACHE_FILE}", file=sys.stderr)

    # quick sanity: any blank blurbs?
    blanks = [t for t, v in cache.items() if not v.get("blurb")]
    if blanks:
        print(f"[warn] no blurb for: {blanks} "
              f"(will render with name only)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
