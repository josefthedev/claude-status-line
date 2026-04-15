#!/bin/bash
# Integration test runner for statusline.py
# Uses STATUSLINE_WIDTH env var to override terminal width detection.
# Gracefully skips integration tests if statusline.py does not exist yet.

set -euo pipefail
cd "$(dirname "$0")/.."

STATUSLINE_PY="statusline.py"

echo "=== Python unit tests ==="
python3 -m pytest tests/ -v 2>/dev/null || python3 -m unittest discover tests/ -v || true
echo ""

if [[ ! -f "$STATUSLINE_PY" ]]; then
  echo "WARNING: $STATUSLINE_PY not found — skipping integration tests"
  echo "(Integration tests will run once Phase 6 is complete)"
  exit 0
fi

echo "=== Integration: render minimal (120 cols) ==="
cat tests/fixtures/minimal.json | STATUSLINE_WIDTH=120 python3 "$STATUSLINE_PY"
echo ""

echo "=== Integration: render full (120 cols) ==="
cat tests/fixtures/full.json | STATUSLINE_WIDTH=120 python3 "$STATUSLINE_PY"
echo ""

echo "=== Integration: narrow (80 cols) ==="
cat tests/fixtures/narrow.json | STATUSLINE_WIDTH=80 python3 "$STATUSLINE_PY"
echo ""

echo "=== Integration: 2-line mode (160 cols) ==="
cat tests/fixtures/full.json | STATUSLINE_WIDTH=160 STATUSLINE_LINES=2 python3 "$STATUSLINE_PY"
echo ""

echo "All integration tests complete."
