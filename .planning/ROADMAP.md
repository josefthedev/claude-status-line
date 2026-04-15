---
milestone: v1.0
name: Python Statusline Rewrite
status: in_progress
total_phases: 9
completed_phases: 0
---

# Milestone v1.0 — Python Statusline Rewrite

## Overview

Replace bash statusline renderer with Python. Fix multi-line truncation (CC bug #37522), compensate dimColor, detect real terminal width, adaptive packing, safe install with backups, tmux integration.

## Phases

### Phase 1: Test Fixtures and Harness
**Goal:** Create JSON fixtures representing real CC statusline input and a test runner script.
**Success Criteria:**
- `tests/fixtures/minimal.json` exists with valid CC JSON
- `tests/fixtures/full.json` exists with rate_limits, all fields
- `tests/fixtures/narrow.json` exists for narrow terminal scenario
- `tests/run.sh` exists and runs without errors

### Phase 2: ANSI Width Library
**Goal:** Implement ANSI-aware string stripping and visible-width calculation in `lib/ansi.py`.
**Success Criteria:**
- `strip_ansi()` removes all CSI, OSC, Fe sequences
- `visible_width()` returns correct printable character count
- `truncate_ansi()` truncates at visible boundary without cutting escape sequences
- All tests in `tests/test_ansi.py` pass

### Phase 3: Config Parser
**Goal:** Parse bash `KEY=value` config files into Python dict in `lib/config.py`.
**Success Criteria:**
- Reads `~/.claude/statusline.conf` correctly
- Handles quoted values, inline comments, missing files
- Per-project override from `<cwd>/.claude/statusline.conf`
- Returns normalized types (int, bool, list)

### Phase 4: Segment Renderers
**Goal:** Port all 22 segment renderers from bash `statusline.sh` to Python `lib/segments.py`.
**Success Criteria:**
- `SegmentRenderer.render(name)` returns ANSI string or None for all 22 segments
- Colors are brighter than bash version (dimColor compensation)
- All tests in `tests/test_segments.py` pass
- None returned for missing/empty data (no errors)

### Phase 5: Adaptive Line Packer
**Goal:** Implement greedy segment packer with cli-truncate workaround in `lib/packer.py`.
**Success Criteria:**
- `pack_lines()` packs segments within line_budget visible chars
- git_status attaches to git_branch without separator
- None segments skipped silently
- All tests in `tests/test_packer.py` pass

### Phase 6: Main Python Entry Point
**Goal:** Wire everything together in `statusline.py` — read JSON, detect terminal width, compute budgets, render, pack, output.
**Success Criteria:**
- Terminal width detected via `/dev/tty` (not stdout)
- N-line budget calculation: each line ≤ `width // N` visible chars
- dimColor compensation: `\033[22m` prefix on each line
- Integration tests pass: `bash tests/run.sh` exits 0
- cli-truncate workaround verified: total visible width ≤ terminal width for 2-line mode

### Phase 7: Safe Install and Backup System
**Goal:** Create `install.sh` and `uninstall.sh` for safe, reversible deployment.
**Success Criteria:**
- `install.sh --dry-run` shows what would happen, changes nothing
- `install.sh` copies lib/ to `~/.claude/statusline-lib/`, copies `statusline.py`
- Existing `~/.claude/statusline.sh` gets timestamped `.bak` copy before any overwrite
- `uninstall.sh` restores from most recent backup
- Instructions for updating `settings.json` command printed (not auto-modified)

### Phase 8: Tmux Integration
**Goal:** Create `tmux/statusline.sh` rendering CC session info in tmux status-right.
**Success Criteria:**
- Script reads CC state files (`~/.claude/statusline-state/`, `/tmp/claude-hook-status-*.json`)
- Shows: tokens, avg/msg, session timer, hook event, active agents
- No dependency on CC's rendering pipeline
- `bash tmux/statusline.sh` runs without errors (shows "cc: idle" if no session)
- `tmux/README.md` explains setup with exact tmux.conf lines

### Phase 9: Repo Sync and Push
**Goal:** Sync installed statusline.sh into repo, update conf with Python settings, commit + push everything.
**Success Criteria:**
- `statusline.sh` in repo matches `~/.claude/statusline.sh`
- `statusline.conf` includes OVERRIDE_DIMCOLOR and MAX_LINES docs
- `change_log.md` updated
- All changes committed and pushed to GitHub
