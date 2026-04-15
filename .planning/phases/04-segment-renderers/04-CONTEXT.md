# Phase 4: Segment Renderers - Context

**Gathered:** 2026-04-15
**Status:** Ready for planning
**Mode:** Auto-generated (infrastructure phase)

<domain>
## Phase Boundary

Implement `lib/segments.py` — a `SegmentRenderer` class that renders all 22 segments from the bash `statusline.sh` to ANSI strings. Port logic exactly from `statusline.sh`'s `render_segment()` function. Colors must be brighter (dimColor compensation: use full RGB values, not dim). Returns `None` for segments with missing/empty data. Tests go in `tests/test_segments.py`.

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion
Infrastructure port. Key constraints:

**Class design:**
- `SegmentRenderer(data: dict, config: dict)` — data is the parsed CC JSON, config is from `load_config()`
- `render(name: str) -> str | None` — returns ANSI string or None
- All 22 segments: model, context_pct, tokens, cost, cache_pct, effort, cwd, git_branch, git_status, worktree, rate_5h, rate_7d, avg_tokens, session_timer, exhaust_5h, exhaust_7d, downtime, hook, hookify_rule, agents, plugins, gsd_phase, gsd_progress

**Colors (24-bit RGB, matching bash exactly):**
- blue   = `\033[38;2;0;153;255m`
- orange = `\033[38;2;255;176;85m`
- green  = `\033[38;2;0;175;80m`
- red    = `\033[38;2;255;85;85m`
- yellow = `\033[38;2;230;200;0m`
- white  = `\033[38;2;220;220;220m`
- dim    = `\033[2m`
- reset  = `\033[0m`

**Data extraction (from CC JSON dict):**
- model_name: `data.get('model', {}).get('display_name', 'Claude')`
- model_id: `data.get('model', {}).get('id', '')`
- context_window_size: `data.get('context_window', {}).get('context_window_size', 200000)`
- input_tokens: `data.get('context_window', {}).get('current_usage', {}).get('input_tokens', 0)`
- cache_creation: `data.get('context_window', {}).get('current_usage', {}).get('cache_creation_input_tokens', 0)`
- cache_read: `data.get('context_window', {}).get('current_usage', {}).get('cache_read_input_tokens', 0)`
- session_in: `data.get('context_window', {}).get('total_input_tokens', 0)`
- session_out: `data.get('context_window', {}).get('total_output_tokens', 0)`
- rate_limits: `data.get('rate_limits', {})`
- cwd: `data.get('cwd', '') or os.getcwd()`
- session_id: `data.get('session_id', '')`

**Effort:** read from `CLAUDE_CODE_EFFORT_LEVEL` env var, then from settings.json files (`.claude/settings.local.json`, `.claude/settings.json`, `~/.claude/settings.local.json`, `~/.claude/settings.json`), fallback to "auto"

**Session state** (avg_tokens, session_timer): read/write `~/.claude/statusline-state/{session_id}.json` — same JSON format as bash: `{"total":N,"msgs":N,"ts":N,"first_ts":N,"history":"N,N,N"}`

**Helpers to implement:**
- `_color_for_pct(pct)` → green/orange/yellow/red thresholds: <50 green, 50-69 orange, 70-89 yellow, >=90 red
- `_color_for_cache_pct(pct)` → green/yellow/orange/red: >=70 green, 40-69 yellow, 15-39 orange, <15 red
- `_build_bar(pct, width=6)` → `▓░` bar string with color
- `_format_tokens(n)` → "1.2M", "34.5k", "123"
- `_format_ttl_epoch(epoch_or_str)` → "2d3h", "4h5m", "12m", "now"
- `_lbl(text)` → dim label prefix if config SHOW_LABELS=true
- `_estimate_cost()` → uses PRICE_OPUS/SONNET/HAIKU from config, model_id to pick rate

**Rate segment** (rate_5h, rate_7d): render based on config RATE_STYLE ("bar_pct" default):
- "bar_pct": build_bar + pct% + optional TTL
- "pct": just pct%
- "bar": just bar

**Separator:** `config.get('SEP_CHAR', '│')` — used by packer (not segments)

**Test approach:** tests/test_segments.py — unittest.TestCase subclasses (NOT pytest-style, so they run under python3 -m unittest). Construct minimal data dicts, assert rendered strings contain expected substrings or are None.

</decisions>

<code_context>
## Existing Code Insights

### Existing Structure
- `lib/__init__.py` exists
- `lib/ansi.py` — `strip_ansi()`, `visible_width()`, `truncate_ansi()`
- `lib/config.py` — `load_config(cwd=None) -> dict`
- `statusline.sh` — full reference implementation (627 lines)
- `statusline.conf` — real config with segment lists and settings

### Integration Points
- `lib/segments.py` imported by `lib/packer.py` (Phase 5) and `statusline.py` (Phase 6)
- `tests/test_segments.py` run by `tests/run.sh`

</code_context>

<specifics>
## Specific Ideas

- Port bash `render_segment()` cases verbatim — segment logic is correct, just translate idioms
- git_branch/git_status/worktree: use `subprocess.run(['git', '-C', cwd, ...], capture_output=True, text=True)`
- hook/hookify_rule/agents: read from `/tmp/claude-hook-status-{session_id}.json` and `/tmp/claude-agent-tracker-{session_id}.json`
- gsd_phase/gsd_progress: read from `.planning/STATE.md` in cwd if file exists
- session_timer: compare `session_first_ts` from state file to `time.time()`
- avg_tokens: update state file on each call if session_total changed

</specifics>

<deferred>
## Deferred Ideas

None — infrastructure phase.

</deferred>
