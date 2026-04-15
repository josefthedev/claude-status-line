# Phase 7: Safe Install and Backup System - Context

**Gathered:** 2026-04-15
**Status:** Ready for planning
**Mode:** Auto-generated (infrastructure phase)

<domain>
## Phase Boundary

Create `install.sh` and `uninstall.sh` for safe, reversible deployment of the Python statusline to `~/.claude/`. NEVER overwrites without a timestamped backup. `~/.claude/statusline.sh` (the user's installed bash renderer) must be preserved. install.sh prints instructions for settings.json update but does NOT modify it.

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion

**install.sh behaviour:**
- `--dry-run` flag: show what would happen, change nothing
- Copy `lib/` → `~/.claude/statusline-lib/` (entire directory)
- Copy `statusline.py` → `~/.claude/statusline.py`
- If `~/.claude/statusline.sh` exists: backup to `~/.claude/statusline.sh.bak.YYYYMMDD_HHMMSS` before any overwrite
- Do NOT copy/overwrite `~/.claude/statusline.sh` — that's the user's existing bash renderer
- Print instructions for settings.json at end:
  ```
  To activate, update ~/.claude/settings.json:
    "statusline": { "command": "python3 ~/.claude/statusline.py" }
  ```
- Exit 0 on success

**uninstall.sh behaviour:**
- Find most recent `~/.claude/statusline.sh.bak.*` backup
- Restore it to `~/.claude/statusline.sh`
- Remove `~/.claude/statusline.py` and `~/.claude/statusline-lib/`
- Print reminder to revert settings.json
- Exit 0 on success, non-zero if no backup found

**Safety rules:**
- Both scripts: `set -euo pipefail`
- Check that source files exist before copying
- Never `rm -rf` without confirmation
- Backup timestamp format: `date +%Y%m%d_%H%M%S`

**No tests for install.sh** — it touches filesystem at ~/ which is unsafe in tests. Manual verification only (ROADMAP success criteria are human-verified).

</decisions>

<code_context>
## Existing Code Insights

### Files to install
- `statusline.py` — main entry point
- `lib/__init__.py`, `lib/ansi.py`, `lib/config.py`, `lib/segments.py`, `lib/packer.py`

### Currently installed
- `~/.claude/statusline.sh` — user's bash renderer (635 lines) — MUST NOT be overwritten
- `~/.claude/statusline.conf` — user's config — do NOT touch

</code_context>

<specifics>
## Specific Ideas

- `install.sh` should be idempotent: re-running just refreshes the installed files
- Dry-run output format: `[DRY-RUN] would copy lib/ → ~/.claude/statusline-lib/`

</specifics>

<deferred>
## Deferred Ideas

None.

</deferred>
