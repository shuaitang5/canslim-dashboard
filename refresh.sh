#!/usr/bin/env bash
# Refresh the CANSLIM dashboard end-to-end.
#
#   1. enrich_companies.py  — fetch company info for any new tickers
#   2. build_dashboard.py   — rebuild data.json + dashboard.html
#
# Usage:
#   ./refresh.sh              # normal refresh
#   ./refresh.sh --refresh    # also re-fetch every company (bypass cache)

set -euo pipefail

cd "$(dirname "$0")"

PYTHON="${PYTHON:-python3}"

# Build first so data.json reflects any new upstream report (and its new tickers)
# *before* enrich runs — otherwise new tickers appear in data.json but never get
# enriched until the *next* refresh cycle.
echo "==> build_dashboard.py (pre-enrich, refresh data.json)"
"$PYTHON" build_dashboard.py

echo
echo "==> enrich_companies.py"
if [[ "${1:-}" == "--refresh" ]]; then
  "$PYTHON" enrich_companies.py --refresh
else
  "$PYTHON" enrich_companies.py
fi

echo
echo "==> build_dashboard.py (post-enrich, merge fresh companies.json into dashboard.html)"
"$PYTHON" build_dashboard.py

echo
echo "Done. Open:"
echo "  file://$PWD/dashboard.html"
