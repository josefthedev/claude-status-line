# Phase 1: Test Fixtures and Harness - Context

**Gathered:** 2026-04-15
**Status:** Ready for planning
**Mode:** Auto-generated (infrastructure phase — discuss skipped)

<domain>
## Phase Boundary

Create JSON test fixtures representing real Claude Code statusline input and a test runner script. No production code written in this phase — only test infrastructure.

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion
All implementation choices are at Claude's discretion — pure infrastructure phase. Use ROADMAP phase goal, success criteria, and the implementation plan at docs/plans/2026-04-15-statusline-rewrite.md to guide decisions.

Key details from the plan:
- `tests/fixtures/minimal.json` — minimal CC JSON (model, context_window, cwd, session_id)
- `tests/fixtures/full.json` — full CC JSON with rate_limits (five_hour 48.3%, seven_day 12.1%)
- `tests/fixtures/narrow.json` — narrow terminal scenario (high context usage)
- `tests/run.sh` — integration test runner using STATUSLINE_WIDTH env var for width control

</decisions>

<code_context>
## Existing Code Insights

### Existing Structure
- `tests/` directory does not exist yet
- `statusline.sh` (bash) exists as reference for what CC JSON looks like
- The CC JSON schema is known from leaked source research: model, context_window, rate_limits, cwd, session_id

### Integration Points
- `tests/run.sh` will call `python3 statusline.py` (not yet existing) — must handle gracefully
- `STATUSLINE_WIDTH` env var overrides terminal width detection

</code_context>

<specifics>
## Specific Ideas

- Fixture epoch values for rate_limits.five_hour.resets_at: use 1776200000 (far future, always shows TTL)
- Narrow fixture: context at 50% (100k/200k) to test color thresholds
- Full fixture uses Opus 4.6 model for cost estimation testing

</specifics>

<deferred>
## Deferred Ideas

None — infrastructure phase.

</deferred>
