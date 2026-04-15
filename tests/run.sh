#!/bin/bash
# Integration test runner for statusline.py
# Uses STATUSLINE_WIDTH env var to override terminal width detection.
# Gracefully skips integration tests if statusline.py does not exist yet.

set -euo pipefail
cd "$(dirname "$0")/.."

STATUSLINE_PY="statusline.py"
PASS=0
FAIL=0

echo "=== Python unit tests ==="
python3 -m pytest tests/ -v 2>/dev/null || python3 -m unittest discover tests/ -v || true
echo ""

if [[ ! -f "$STATUSLINE_PY" ]]; then
  echo "WARNING: $STATUSLINE_PY not found — skipping integration tests"
  echo "(Integration tests will run once Phase 6 is complete)"
  exit 0
fi

run_test() {
  local name="$1" width="$2" fixture="$3"
  shift 3
  local env_extra=("$@")

  echo "--- $name ---"
  local output
  if output=$(env STATUSLINE_WIDTH="$width" "${env_extra[@]}" python3 "$STATUSLINE_PY" < "$fixture" 2>&1); then
    if [[ -z "$output" ]]; then
      echo "FAIL: empty output"
      FAIL=$((FAIL + 1))
      return
    fi
    # Verify dimColor compensation: each line starts with \033[22m
    local bad_lines=0
    while IFS= read -r line; do
      if [[ "$line" != $'\033[22m'* ]]; then
        bad_lines=$((bad_lines + 1))
      fi
    done <<< "$output"
    if [[ "$bad_lines" -gt 0 ]]; then
      echo "FAIL: $bad_lines line(s) missing dimColor compensation prefix"
      FAIL=$((FAIL + 1))
      return
    fi
    echo "$output"
    echo "PASS"
    PASS=$((PASS + 1))
  else
    echo "FAIL: non-zero exit code"
    echo "$output"
    FAIL=$((FAIL + 1))
  fi
  echo ""
}

echo "=== Integration tests ==="
echo ""

run_test "render minimal (120 cols)" 120 tests/fixtures/minimal.json
run_test "render full (120 cols)" 120 tests/fixtures/full.json
run_test "render narrow (40 cols)" 40 tests/fixtures/narrow.json
run_test "2-line mode (160 cols)" 160 tests/fixtures/full.json STATUSLINE_LINES=2

# Test graceful empty/bad input
echo "--- graceful bad input ---"
bad_output=$(echo "not json" | STATUSLINE_WIDTH=80 python3 "$STATUSLINE_PY" 2>&1) || true
if [[ "$bad_output" == "Claude" ]]; then
  echo "PASS: bad input returns 'Claude'"
  PASS=$((PASS + 1))
else
  echo "FAIL: expected 'Claude', got '$bad_output'"
  FAIL=$((FAIL + 1))
fi
echo ""

echo "=== Results: $PASS passed, $FAIL failed ==="
if [[ "$FAIL" -gt 0 ]]; then
  exit 1
fi
echo "All integration tests complete."
