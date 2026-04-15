# Phase 8: Tmux Integration - Context

**Gathered:** 2026-04-15
**Status:** Ready for planning
**Mode:** Auto-generated (infrastructure phase)

<domain>
## Phase Boundary

Create `tmux/statusline.sh` — a bash script that renders CC session info in tmux status-right. Reads CC state files directly (`~/.claude/statusline-state/`, `/tmp/claude-hook-status-*.json`). No dependency on CC's rendering pipeline. Also create `tmux/README.md` with setup instructions.

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion

**What to show (tmux status-right):**
- Tokens used in current session (from most recent state file)
- Avg tokens/msg
- Session timer (elapsed since first_ts)
- Last hook event (from /tmp/claude-hook-status-*.json)
- Active agents count (from /tmp/claude-agent-tracker-*.json)
- Shows "cc: idle" when no active session found

**State file detection:**
- Most recent `~/.claude/statusline-state/*.json` by mtime = active session
- If no files or all older than 2h: "cc: idle"
- Hook status: `/tmp/claude-hook-status-{session_id}.json` — read `event` field
- Agent tracker: `/tmp/claude-agent-tracker-{session_id}.json` — count running agents

**Output format (tmux-friendly, no newlines):**
```
cc: 34.5k tkns │ 8.2k/msg │ 23m │ hook:Agent │ 2 agents
```
or just:
```
cc: idle
```

**Colors:** tmux #[fg=colour] syntax — NOT ANSI escape codes
- Numbers: `#[fg=colour39]` (blue)
- Labels: `#[fg=colour240]` (dim grey)
- Idle: `#[fg=colour240]`
- Reset: `#[fg=default]`

**Script requirements:**
- Pure bash, no external deps beyond jq (already required by statusline.sh)
- Runs in ~20ms (tmux polls frequently)
- `set -f` to avoid glob expansion on /tmp patterns

**README.md content:**
- How to add to tmux.conf: `set -g status-right "$(~/.claude/tmux/statusline.sh)"`
- Actually: `set -g status-right "#(~/.claude/tmux/statusline.sh)"`
- Refresh interval recommendation: `set -g status-interval 5`
- Note: independent of CC rendering pipeline

**No tests** — reads live state files, manual verification only.

</decisions>

<code_context>
## Existing Code Insights

### State file format (from statusline.sh)
- `~/.claude/statusline-state/{session_id}.json`: `{"total":N,"msgs":N,"ts":N,"first_ts":N,"history":"N,N"}`
- `/tmp/claude-hook-status-{session_id}.json`: hook event info
- `/tmp/claude-agent-tracker-{session_id}.json`: `{"agents":[{"status":"running","type":"..."}]}`

### Helper functions to port from statusline.sh
- `format_tokens()` — "34.5k", "1.2M"
- Session timer calculation from first_ts

</code_context>

<specifics>
## Specific Ideas

- `tmux/statusline.sh` should be installable to `~/.claude/tmux/statusline.sh`
- update install.sh to also copy tmux/ directory

</specifics>

<deferred>
## Deferred Ideas

None.

</deferred>
