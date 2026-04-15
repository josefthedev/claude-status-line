---
phase: 07
plan: 07
title: Safe Install and Backup System
subsystem: install
tags: [install, uninstall, backup, dry-run]
dependency_graph:
  requires: []
  provides: [install.sh, uninstall.sh]
  affects: []
tech_stack:
  added: []
  patterns: [timestamped-backup, dry-run-flag]
key_files:
  created:
    - install.sh
    - uninstall.sh
  modified: []
decisions:
  - install.sh copies lib/ to statusline-lib/ (not lib/) to avoid collision with any other ~/.claude/lib/
  - Neither script touches settings.json — user must update manually (printed in output)
  - Backup uses timestamp suffix (statusline.sh.bak.YYYYMMDD_HHMMSS) so multiple runs don't overwrite each other
  - uninstall restores most recent backup by mtime sort
metrics:
  duration_minutes: 5
  completed_date: "2026-04-15"
  tasks_completed: 2
  files_created: 2
---

# Phase 07 Plan 07: Safe Install and Backup System Summary

Install.sh and uninstall.sh providing one-command deployment and safe revert with timestamped backup of the existing bash statusline.

## What Was Built

**install.sh** — Verifies all source files exist, backs up `~/.claude/statusline.sh` with a timestamp, copies `statusline.py` and `lib/*.py` (as `statusline-lib/`) to `~/.claude/`, and prints manual settings.json activation instructions. Supports `--dry-run` which shows the full plan without touching the filesystem.

**uninstall.sh** — Finds the most recent timestamped backup, restores it to `statusline.sh`, removes `statusline.py` and `statusline-lib/`, and prints revert instructions. Also supports `--dry-run`.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Create install.sh | 3d890db | install.sh |
| 2 | Create uninstall.sh | 1ee78de | uninstall.sh |

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None.

## Self-Check: PASSED

- install.sh exists and is executable: FOUND
- uninstall.sh exists and is executable: FOUND
- install.sh --dry-run exits 0: PASS
- Output contains [DRY-RUN], statusline-lib, statusline.py, settings.json: PASS
- uninstall.sh --dry-run exits 0: PASS
- Neither script modifies settings.json: PASS (confirmed by design — output only)
