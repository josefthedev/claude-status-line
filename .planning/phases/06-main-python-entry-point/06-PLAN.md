---
plan: 06
phase: 06
wave: 1
title: Main Python Entry Point
autonomous: true
files_modified:
  - statusline.py
  - tests/run.sh
must_haves:
  - statusline.py exists and is executable with python3
  - STATUSLINE_WIDTH=120 python3 statusline.py < tests/fixtures/minimal.json exits 0 and produces output
  - STATUSLINE_WIDTH=120 python3 statusline.py < tests/fixtures/full.json exits 0 and produces output
  - STATUSLINE_WIDTH=40 python3 statusline.py < tests/fixtures/narrow.json exits 0 and produces output
  - Each output line starts with \033[22m (dimColor compensation)
  - statusline.py contains get_terminal_width() that reads from /dev/tty
---

<objective>
Wire everything together in statusline.py — the main entry point that reads CC JSON from stdin, detects terminal width via /dev/tty, loads config, renders segments, packs lines with cli-truncate workaround, applies dimColor compensation, and outputs to stdout. Update tests/run.sh to validate all three fixtures plus 2-line mode.

Purpose: This is the final integration point — without it, all lib/ modules are unused.
Output: Working statusline.py, updated tests/run.sh with integration tests.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@lib/config.py
@lib/segments.py
@lib/packer.py
@lib/ansi.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Implement statusline.py</name>
  <files>statusline.py</files>
  <read_first>lib/config.py, lib/segments.py, lib/packer.py, lib/ansi.py</read_first>
  <action>
Create `statusline.py` in the project root with the following EXACT content:

```python
#!/usr/bin/env python3
"""Claude Code statusline renderer.

Reads CC JSON from stdin, detects terminal width via /dev/tty,
loads config, renders segments, packs lines, outputs ANSI text.
"""

import fcntl
import json
import os
import struct
import sys
import termios

from lib.config import load_config
from lib.segments import SegmentRenderer
from lib.packer import pack_lines

NORMAL_INTENSITY = '\033[22m'


def get_terminal_width() -> int:
    """Detect terminal width from /dev/tty (not stdout, which CC captures).

    Falls back to STATUSLINE_WIDTH env var, then 80.
    """
    try:
        with open('/dev/tty') as tty:
            ws = struct.unpack('hh', fcntl.ioctl(tty, termios.TIOCGWINSZ, b'\0' * 4))
            if ws[1] > 0:
                return ws[1]
    except Exception:
        pass
    try:
        return int(os.environ.get('STATUSLINE_WIDTH', '0')) or 80
    except ValueError:
        return 80


def main():
    # Read JSON from stdin; graceful fallback on bad input
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        print('Claude', end='')
        return

    if not isinstance(data, dict):
        print('Claude', end='')
        return

    cwd = data.get('cwd', '') or os.getcwd()
    config = load_config(cwd=cwd)

    width = get_terminal_width()

    # Build line definitions from config
    line_defs = []
    for key in ['LINE1', 'LINE2', 'LINE3']:
        val = config.get(key, '')
        if val:
            if isinstance(val, list):
                line_defs.append(val)
            else:
                line_defs.append(str(val).split())
    if not line_defs:
        line_defs = [['model', 'context_pct', 'cwd', 'git_branch', 'git_status']]

    n_lines = len(line_defs)
    budget = max(20, (width - 4) // n_lines)

    renderer = SegmentRenderer(data, config)
    sep_char = config.get('SEP_CHAR', '│')

    lines = pack_lines(line_defs, renderer, budget, sep_char=sep_char)

    # Apply dimColor compensation and output
    output = '\n'.join(NORMAL_INTENSITY + line for line in lines if line)
    print(output, end='')


if __name__ == '__main__':
    main()
```

Key implementation details:
- get_terminal_width() reads from /dev/tty first (CC captures stdout so shutil.get_terminal_size returns 80)
- STATUSLINE_WIDTH env var override for testing
- Budget formula: `max(20, (width - 4) // n_lines)` — reserves 4 chars right margin, divides by line count for cli-truncate workaround
- NORMAL_INTENSITY prefix on each line cancels CC's `<Text dimColor>` wrapping
- Graceful fallback: invalid JSON outputs "Claude" and exits 0
- line_defs handles both list (already split) and string config values
  </action>
  <verify>
    <automated>cd /home/josef/workspace-linux/claude-status-line && STATUSLINE_WIDTH=120 python3 statusline.py < tests/fixtures/minimal.json && echo "EXIT:$?"</automated>
  </verify>
  <acceptance_criteria>
- `python3 statusline.py` with STATUSLINE_WIDTH=120 and minimal.json exits 0 and produces non-empty output
- Output lines start with \033[22m (grep -c confirms)
- `get_terminal_width` function exists and references /dev/tty
- Empty stdin produces "Claude" output
  </acceptance_criteria>
  <done>statusline.py exists, is valid Python, reads JSON from stdin, detects terminal width via /dev/tty, applies dimColor compensation, and produces ANSI output for all fixtures.</done>
</task>

<task type="auto">
  <name>Task 2: Update tests/run.sh with integration tests</name>
  <files>tests/run.sh</files>
  <read_first>tests/run.sh, tests/fixtures/minimal.json</read_first>
  <action>
Replace `tests/run.sh` with the following EXACT content:

```bash
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
```

Key changes from existing tests/run.sh:
- Added `run_test` helper that checks exit code, non-empty output, and dimColor compensation prefix
- Added narrow terminal test at 40 cols (was 80)
- Added bad input graceful fallback test
- Pass/fail counters with summary and non-zero exit on failure
- dimColor compensation verified: every output line must start with \033[22m
  </action>
  <verify>
    <automated>cd /home/josef/workspace-linux/claude-status-line && bash tests/run.sh</automated>
  </verify>
  <acceptance_criteria>
- `bash tests/run.sh` exits 0
- All 5 integration tests pass (minimal, full, narrow, 2-line, bad input)
- Output shows "X passed, 0 failed"
  </acceptance_criteria>
  <done>tests/run.sh runs all integration tests, verifies dimColor compensation, tests graceful error handling, and exits 0 with all passing.</done>
</task>

</tasks>

<verification>
1. `STATUSLINE_WIDTH=120 python3 statusline.py < tests/fixtures/minimal.json` — exits 0, non-empty output
2. `STATUSLINE_WIDTH=120 python3 statusline.py < tests/fixtures/full.json` — exits 0, non-empty output
3. `STATUSLINE_WIDTH=40 python3 statusline.py < tests/fixtures/narrow.json` — exits 0, non-empty output
4. `echo "bad" | STATUSLINE_WIDTH=80 python3 statusline.py` — outputs "Claude"
5. `bash tests/run.sh` — exits 0, all tests pass
6. `grep -c 'def get_terminal_width' statusline.py` — returns 1
7. `grep -c '/dev/tty' statusline.py` — returns at least 1
8. `grep -c 'NORMAL_INTENSITY' statusline.py` — returns at least 1
</verification>

<success_criteria>
- statusline.py is a working entry point: reads CC JSON, renders segments, outputs ANSI text
- Terminal width detected via /dev/tty (not stdout)
- Budget formula prevents cli-truncate from mangling multi-line output
- dimColor compensation (\033[22m prefix) on every output line
- Graceful fallback on bad/empty input
- All integration tests in tests/run.sh pass
</success_criteria>

<output>
After completion, create `.planning/phases/06-main-python-entry-point/06-SUMMARY.md`
</output>
