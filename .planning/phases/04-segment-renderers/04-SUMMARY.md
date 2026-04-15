---
phase: 04
plan: 04
subsystem: segment-renderers
tags: [segments, rendering, ansi, python]
dependency_graph:
  requires: [lib/config.py, lib/ansi.py]
  provides: [lib/segments.py]
  affects: [statusline.py, tests/test_segments.py]
tech_stack:
  added: []
  patterns: [lazy-loading, dispatch-via-getattr, mock-based-testing]
key_files:
  created:
    - lib/segments.py
    - tests/test_segments.py
  modified: []
decisions:
  - Lazy loaders for git/session/hook/GSD/plugin state to avoid expensive I/O on every render
  - render() uses getattr dispatch (_seg_<name>) with exception catch returning None
  - settings file reads suppressed in _make() test helper via builtins.open patch
metrics:
  duration: "~15 minutes"
  completed: "2026-04-15"
  tasks_completed: 2
  files_created: 2
---

# Phase 04 Plan 04: Segment Renderers Implementation Summary

Port all 22 segment renderers from bash statusline.sh to Python SegmentRenderer class with full test coverage.

## What Was Built

`lib/segments.py` — SegmentRenderer class (721 lines) that mirrors bash `render_segment()`:
- 22 `_seg_*` methods: model, context_pct, tokens, cost, cache_pct, effort, cwd, git_branch, git_status, worktree, rate_5h, rate_7d, avg_tokens, session_timer, exhaust_5h, exhaust_7d, downtime, hook, hookify_rule, agents, plugins, gsd_phase, gsd_progress
- RGB color constants exactly matching bash: BLUE=0;153;255, GREEN=0;175;80, etc.
- `render(name)` dispatches via `getattr(self, '_seg_' + name)` and returns None for unknown or erroring segments
- Lazy loaders: `_ensure_git()`, `_ensure_session_state()`, `_ensure_hook_state()`, `_ensure_gsd_state()`, `_ensure_plugins()`
- Helper methods: `_color_for_pct()`, `_color_for_cache_pct()`, `_build_bar()`, `_format_tokens()`, `_format_ttl_epoch()`, `_lbl()`, `_estimate_cost()`, `_render_rate()`, `_format_time_to_exhaust()`, `_exhaust_secs()`

`tests/test_segments.py` — 67 unit tests across 20 TestCase classes covering every segment, all helper functions, edge cases (None for missing data), and render dispatch error handling.

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

None. All segment renderers produce real ANSI output or return None from live data sources.

## Self-Check: PASSED

- lib/segments.py exists: FOUND
- tests/test_segments.py exists: FOUND
- 7646e4a (feat commit): FOUND
- b129280 (test commit): FOUND
- All 67 tests: PASS
