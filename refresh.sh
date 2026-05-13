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

echo "==> enrich_companies.py"
if [[ "${1:-}" == "--refresh" ]]; then
  "$PYTHON" enrich_companies.py --refresh
else
  "$PYTHON" enrich_companies.py
fi

echo
echo "==> build_dashboard.py"
"$PYTHON" build_dashboard.py

echo
echo "Done. Open:"
echo "  file://$PWD/dashboard.html"
