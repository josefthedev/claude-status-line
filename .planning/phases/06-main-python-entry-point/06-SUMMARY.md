---
phase: 06-main-python-entry-point
plan: 06
subsystem: cli
tags: [python, ansi, statusline, terminal]

requires:
  - phase: 05-adaptive-line-packer
    provides: pack_lines() greedy packer
  - phase: 04-segment-renderers
    provides: SegmentRenderer class
  - phase: 03-config-parser
    provides: load_config() function

provides:
  - statusline.py — working entry point that reads CC JSON, renders segments, outputs ANSI text
  - Integration test suite in tests/run.sh covering all fixtures and edge cases

affects: [install, deployment, end-to-end testing]

tech-stack:
  added: []
  patterns:
    - "get_terminal_width(): /dev/tty ioctl instead of stdout (CC captures stdout)"
    - "NORMAL_INTENSITY prefix on every output line cancels CC dimColor wrapping"
    - "budget = max(20, (width-4)//n_lines) prevents cli-truncate mangling"

key-files:
  created:
    - statusline.py
  modified:
    - tests/run.sh

key-decisions:
  - "STATUSLINE_WIDTH env var override enables integration testing without a real TTY"
  - "Graceful fallback: invalid/non-dict JSON outputs 'Claude' and exits 0"
  - "line_defs handles both list and string config values via isinstance check"

patterns-established:
  - "Entry point pattern: load config from cwd, detect width, build line_defs, pack, prefix NORMAL_INTENSITY"
  - "Integration test pattern: run_test helper validates exit code + non-empty output + dimColor prefix"

requirements-completed: []

duration: 8min
completed: 2026-04-15
---

# Phase 06: Main Python Entry Point Summary

**statusline.py wires all lib/ modules into a working CC statusline renderer with /dev/tty width detection, dimColor compensation, and graceful JSON fallback**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-04-15T20:15:00Z
- **Completed:** 2026-04-15T20:23:00Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- `statusline.py` reads CC JSON from stdin, detects terminal width via `/dev/tty` (not stdout), loads config, renders all segments, packs into budget-constrained lines, and outputs ANSI text with `\033[22m` dimColor compensation
- `get_terminal_width()` uses `/dev/tty` ioctl (`TIOCGWINSZ`) with `STATUSLINE_WIDTH` env override for testing
- `tests/run.sh` upgraded with `run_test` helper that validates exit code, non-empty output, and dimColor prefix on every output line; tests minimal/full/narrow/2-line/bad-input scenarios

## Task Commits

1. **Task 1: Implement statusline.py** - `fc5e8d9` (feat)
2. **Task 2: Update tests/run.sh with integration tests** - `d050088` (feat)

## Files Created/Modified
- `statusline.py` — Main entry point: reads stdin JSON, renders segments, packs lines, outputs ANSI
- `tests/run.sh` — Integration test runner with pass/fail counters and dimColor verification

## Decisions Made
- `STATUSLINE_WIDTH` env var fallback enables CI/test use without a real TTY
- Graceful fallback outputs `Claude` on invalid JSON (not an error exit) — consistent with bash predecessor behavior
- `line_defs` handles both `list` (comma-normalized config) and `str` (space-split) — matches config.py normalization

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- All 6 plans in Phase 06 are complete
- `statusline.py` is the final integration point — all lib/ modules are now wired and tested
- Ready for Phase 07 (installation/packaging) or direct use via `echo '...' | STATUSLINE_WIDTH=120 python3 statusline.py`

---
*Phase: 06-main-python-entry-point*
*Completed: 2026-04-15*
