# Phase 3: Config Parser - Context

**Gathered:** 2026-04-15
**Status:** Ready for planning
**Mode:** Auto-generated (infrastructure phase)

<domain>
## Phase Boundary

Implement `lib/config.py` — parse bash `KEY=value` config files into a Python dict. Handles `~/.claude/statusline.conf` as base config and `<cwd>/.claude/statusline.conf` as per-project override. Returns normalized types (int, bool, list). No production code beyond config parsing — pure utility with tests.

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion
Pure infrastructure. Key constraints:
- Read base config from `~/.claude/statusline.conf`
- Read per-project override from `<cwd>/.claude/statusline.conf` (merge, project wins)
- Handle quoted values (single and double quotes)
- Handle inline comments (# after value)
- Missing files: return empty dict, no error
- Normalize types: strings that look like ints → int, "true"/"false"/"yes"/"no" → bool, comma-separated → list
- `lib/__init__.py` already exists (Phase 2)
- Reference: `statusline.conf` in repo shows real keys/values in use

</decisions>

<code_context>
## Existing Code Insights

### Existing Structure
- `lib/__init__.py` exists (Phase 2)
- `lib/ansi.py` exists (Phase 2)
- `statusline.conf` in repo root has 105 lines showing real config keys
- `tests/run.sh` exists and will run `tests/test_config.py`

### Integration Points
- `lib/config.py` will be imported by `lib/segments.py` (Phase 4) and `statusline.py` (Phase 6)
- Tests will be in `tests/test_config.py`

</code_context>

<specifics>
## Specific Ideas

Config keys used in `statusline.conf`:
- LINE1, LINE2, LINE3 — space-separated segment lists
- SHOW_* — boolean toggles
- MAX_LINES — integer
- COLOR_* — ANSI color strings

</specifics>

<deferred>
## Deferred Ideas

None — infrastructure phase.

</deferred>
