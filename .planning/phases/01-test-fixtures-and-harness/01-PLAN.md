# Phase 1: Test Fixtures and Harness — Plan

## Objective

Create the `tests/` directory with three JSON fixtures representing real CC statusline input and a test runner script that exercises `statusline.py` (gracefully handling its absence).

---

## Tasks

### Task 1: Create test fixture directory and JSON files

**Files:**
- `tests/fixtures/minimal.json`
- `tests/fixtures/full.json`
- `tests/fixtures/narrow.json`

- [ ] **Step 1.1: Create directory structure**

  ```bash
  mkdir -p tests/fixtures
  ```

- [ ] **Step 1.2: Create `tests/fixtures/minimal.json`**

  Exact content:

  ```json
  {
    "model": {"display_name": "Claude Sonnet 4.6", "id": "claude-sonnet-4-6"},
    "context_window": {
      "context_window_size": 200000,
      "current_usage": {
        "input_tokens": 64000,
        "cache_creation_input_tokens": 0,
        "cache_read_input_tokens": 128000
      },
      "total_input_tokens": 8500,
      "total_output_tokens": 1200
    },
    "cwd": "/home/josef/workspace-linux/claude-status-line",
    "session_id": "test-session-001"
  }
  ```

  Notes:
  - `context_window_size` = 200000 (full context window)
  - `current_usage` represents a realistic mid-session state: 64k direct input + 128k cache read = 192k active tokens
  - No `rate_limits` field (intentionally absent — tests that segment is silently skipped)

- [ ] **Step 1.3: Create `tests/fixtures/full.json`**

  Exact content:

  ```json
  {
    "model": {"display_name": "Claude Opus 4.6", "id": "claude-opus-4-6"},
    "context_window": {
      "context_window_size": 200000,
      "current_usage": {
        "input_tokens": 64000,
        "cache_creation_input_tokens": 0,
        "cache_read_input_tokens": 128000
      },
      "total_input_tokens": 85000,
      "total_output_tokens": 22000
    },
    "rate_limits": {
      "five_hour": {
        "used_percentage": 48.3,
        "resets_at": 1776200000
      },
      "seven_day": {
        "used_percentage": 12.1,
        "resets_at": 1776700000
      }
    },
    "cwd": "/home/josef/workspace-linux/claude-status-line",
    "session_id": "test-session-002"
  }
  ```

  Notes:
  - Uses Opus 4.6 (higher cost model, tests cost estimation segment)
  - `five_hour.used_percentage` = 48.3 (just under warning threshold)
  - `seven_day.used_percentage` = 12.1 (well within limits)
  - `resets_at` epoch values are far-future (1776200000 ≈ year 2026), ensuring TTL display is always positive
  - Higher session token counts (85k in, 22k out) for realistic heavy-session rendering

- [ ] **Step 1.4: Create `tests/fixtures/narrow.json`**

  Exact content:

  ```json
  {
    "model": {"display_name": "Claude Sonnet 4.6", "id": "claude-sonnet-4-6"},
    "context_window": {
      "context_window_size": 200000,
      "current_usage": {
        "input_tokens": 100000,
        "cache_creation_input_tokens": 0,
        "cache_read_input_tokens": 0
      },
      "total_input_tokens": 5000,
      "total_output_tokens": 800
    },
    "cwd": "/home/josef/workspace-linux/claude-status-line",
    "session_id": "test-session-003"
  }
  ```

  Notes:
  - `current_usage.input_tokens` = 100000 out of 200000 = exactly 50% context usage (tests amber/warning color threshold)
  - No cache reads (all direct — worst case for context counting)
  - Small session token counts (5k in, 800 out) simulating a new session with high context
  - No `rate_limits` (tests narrow rendering without rate limit segment)

- [ ] **Step 1.5: Verify JSON validity**

  ```bash
  python3 -c "import json; [json.load(open(f)) for f in ['tests/fixtures/minimal.json', 'tests/fixtures/full.json', 'tests/fixtures/narrow.json']]; print('All fixtures valid JSON')"
  ```

  Expected output: `All fixtures valid JSON`

- [ ] **Step 1.6: Commit fixtures**

  ```bash
  git add tests/fixtures/
  git commit -m "test: add JSON fixtures for CC statusline input"
  ```

---

### Task 2: Create test runner script

**Files:**
- `tests/run.sh`

- [ ] **Step 2.1: Create `tests/run.sh`**

  Exact content:

  ```bash
  #!/bin/bash
  # Integration test runner for statusline.py
  # Uses STATUSLINE_WIDTH env var to override terminal width detection.
  # Gracefully skips integration tests if statusline.py does not exist yet.

  set -euo pipefail
  cd "$(dirname "$0")/.."

  STATUSLINE_PY="statusline.py"

  echo "=== Python unit tests ==="
  python3 -m pytest tests/ -v 2>/dev/null || python3 -m unittest discover tests/ -v
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
  ```

  Notes:
  - `set -euo pipefail` — fail fast on errors, except the unit test block which handles missing pytest gracefully
  - `cd "$(dirname "$0")/.."` — always runs from repo root regardless of where the script is called from
  - Missing `statusline.py` prints a warning and exits 0 (not a failure — Phase 1 is pre-implementation)
  - Unit test block tries pytest first, falls back to unittest discover (handles both installed and stdlib)
  - `STATUSLINE_WIDTH` and `STATUSLINE_LINES` env vars control rendering without a real TTY

- [ ] **Step 2.2: Make script executable**

  ```bash
  chmod +x tests/run.sh
  ```

- [ ] **Step 2.3: Verify script runs without errors**

  ```bash
  bash tests/run.sh
  ```

  Expected: Script runs, prints unit test output (no tests exist yet, so likely 0 tests), prints `WARNING: statusline.py not found — skipping integration tests`, exits 0.

  If exit code is non-zero, inspect output — the only expected non-zero case is a pytest/unittest failure (which means something is wrong with the test discovery, not the fixtures).

- [ ] **Step 2.4: Commit run.sh**

  ```bash
  git add tests/run.sh
  git commit -m "test: add integration test runner harness"
  ```

---

## Verification

Run all success criteria checks in order:

```bash
# 1. All fixture files exist
ls -la tests/fixtures/minimal.json tests/fixtures/full.json tests/fixtures/narrow.json

# 2. All fixtures are valid JSON
python3 -c "
import json
fixtures = {
    'minimal': 'tests/fixtures/minimal.json',
    'full': 'tests/fixtures/full.json',
    'narrow': 'tests/fixtures/narrow.json',
}
for name, path in fixtures.items():
    data = json.load(open(path))
    assert 'model' in data, f'{name}: missing model'
    assert 'context_window' in data, f'{name}: missing context_window'
    assert 'cwd' in data, f'{name}: missing cwd'
    assert 'session_id' in data, f'{name}: missing session_id'
    print(f'{name}: OK')

# Verify full.json has rate_limits
full = json.load(open('tests/fixtures/full.json'))
assert 'rate_limits' in full, 'full.json missing rate_limits'
assert full['rate_limits']['five_hour']['used_percentage'] == 48.3
assert full['rate_limits']['seven_day']['used_percentage'] == 12.1
print('rate_limits: OK')

# Verify narrow.json has 50% context usage
narrow = json.load(open('tests/fixtures/narrow.json'))
usage = narrow['context_window']['current_usage']['input_tokens']
total = narrow['context_window']['context_window_size']
assert usage / total == 0.5, f'Expected 50% context, got {usage/total:.1%}'
print('narrow context 50%: OK')
"

# 3. run.sh exists and is executable
test -x tests/run.sh && echo "run.sh is executable: OK"

# 4. run.sh exits 0 (statusline.py absent is handled gracefully)
bash tests/run.sh && echo "run.sh exit 0: OK"
```

All four checks must pass without error.
