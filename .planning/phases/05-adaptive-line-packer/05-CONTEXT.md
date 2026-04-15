# Phase 5: Adaptive Line Packer - Context

**Gathered:** 2026-04-15
**Status:** Ready for planning
**Mode:** Auto-generated (infrastructure phase)

<domain>
## Phase Boundary

Implement `lib/packer.py` — greedy segment packer that takes rendered segments and packs them into lines within a visible-width budget. The cli-truncate workaround is the core constraint: each output line must be ≤ `terminal_width / N` visible chars (where N = number of lines). Segments are dropped (not truncated) when they don't fit. Tests go in `tests/test_packer.py`.

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion
Pure infrastructure. Key constraints:

**Function signature:**
```python
def pack_lines(
    segments: list[str],     # list of (name, rendered_str) tuples where rendered_str may be None
    line_defs: list[list[str]],  # e.g. [['model','effort','cwd'], ['hook','agents']]
    renderer: SegmentRenderer,   # from lib.segments
    budget: int,             # max visible chars per line (= terminal_width // n_lines)
    sep: str = ' │ ',        # separator between segments on same line
) -> list[str]               # list of rendered line strings (ANSI), one per line_def
```

**Algorithm:**
1. For each line_def (list of segment names):
   - Render each segment via `renderer.render(name)` → str or None
   - Skip None segments silently
   - Build line greedily: add segment+sep if visible_width(current + sep + segment) ≤ budget
   - Drop segment if it doesn't fit (never truncate mid-segment)
   - Special case: `git_status` attaches to `git_branch` without separator (just a space)
2. Return list of line strings

**Special git attachment rule:**
- If the previous non-None segment was `git_branch` and current is `git_status`, join with `" "` instead of sep

**Separator:** sep is built as `f' {dim}{sep_char}{reset} '` where dim=`\033[2m`, reset=`\033[0m`

**Width calculation:** use `visible_width()` from `lib.ansi`

**Empty line handling:** if no segments fit on a line, return empty string for that line (not None)

**Tests:**
- `tests/test_packer.py` — unittest.TestCase (not pytest functions)
- Test: normal packing, budget overflow drops segment, git_status attachment, all-None segments, empty line_def

</decisions>

<code_context>
## Existing Code Insights

### Existing Structure
- `lib/ansi.py` — `visible_width(s)` already implemented
- `lib/segments.py` — `SegmentRenderer(data, config).render(name) -> str | None`
- `lib/config.py` — `load_config() -> dict` (has SEP_CHAR key)

### Integration Points
- `lib/packer.py` imported by `statusline.py` (Phase 6)
- `tests/test_packer.py` run by `tests/run.sh`

</code_context>

<specifics>
## Specific Ideas

- The cli-truncate workaround is the whole point: caller (statusline.py) must compute budget = terminal_width // n_lines before calling pack_lines
- packer itself just respects budget — doesn't know about terminal width
- Keep it simple: greedy left-to-right, first-fit, drop if doesn't fit

</specifics>

<deferred>
## Deferred Ideas

None — infrastructure phase.

</deferred>
