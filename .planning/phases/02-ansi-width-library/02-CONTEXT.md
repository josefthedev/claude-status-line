# Phase 2: ANSI Width Library - Context

**Gathered:** 2026-04-15
**Status:** Ready for planning
**Mode:** Auto-generated (infrastructure phase)

<domain>
## Phase Boundary

Implement `lib/ansi.py` — ANSI escape sequence stripping and visible-width calculation. Three functions: `strip_ansi()`, `visible_width()`, `truncate_ansi()`. No production code, no segment rendering — pure string utility library with tests.

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion
Pure infrastructure. Use regex approach (re.compile) for performance. The ANSI pattern must cover CSI sequences (ESC [ params final-byte), OSC sequences (ESC ] ... ST/BEL), and Fe sequences (ESC + single char). See full implementation in docs/plans/2026-04-15-statusline-rewrite.md Task 2.

Key constraints:
- `truncate_ansi()` must never cut in the middle of an escape sequence
- Must append `\033[0m` reset after truncation
- Must append suffix (default '…') when truncation occurs
- `lib/__init__.py` must exist to make lib a Python package

</decisions>

<code_context>
## Existing Code Insights

### Existing Structure
- `lib/` directory does not exist yet
- `tests/fixtures/` exists (Phase 1)
- `tests/test_ansi.py` does not exist yet — will be created in this phase

### Integration Points
- `lib/ansi.py` will be imported by `lib/segments.py` (Phase 4), `lib/packer.py` (Phase 5), and `statusline.py` (Phase 6)
- Tests will be run by `tests/run.sh`

</code_context>

<specifics>
## Specific Ideas

Full implementation specified in docs/plans/2026-04-15-statusline-rewrite.md Task 2, including exact regex pattern and all three function implementations.

</specifics>

<deferred>
## Deferred Ideas

None — infrastructure phase.

</deferred>
