# Claude Status Line

Custom status line for Claude Code CLI — shows model, context, tokens, rate limits, git, GSD state, and more in a configurable multi-line display.

## Architecture

- `statusline.sh` — Main renderer. Reads JSON from stdin (Claude Code status line contract), outputs ANSI-colored text. 636 lines, pure bash + jq.
- `statusline.conf` — Declarative config. 22+ segments across 3 lines. Sourced by statusline.sh at runtime.
- `hooks/` — Supporting Claude Code hooks:
  - `agent-tracker.sh` — PreToolUse/PostToolUse hook tracking subagent lifecycle
  - `hook-status-bridge.sh` — PostToolUse hook recording which hooks fired per tool call
  - `gsd-statusline.js` — GSD plugin's simpler statusline (Node.js, context bridge writer)

## Config

Global: `~/.claude/statusline.conf`
Per-project override: `<project>/.claude/statusline.conf`

## Installation

1. Copy `statusline.sh` to `~/.claude/statusline.sh`
2. Copy `statusline.conf` to `~/.claude/statusline.conf`
3. Register in `~/.claude/settings.json`:
   ```json
   {
     "statusline": {
       "command": "bash ~/.claude/statusline.sh"
     }
   }
   ```
4. Optional: copy hooks from `hooks/` to `~/.claude/hooks/` and register in settings.json

## Development

- Shell: bash 4+, jq required
- State files: `~/.claude/statusline-state/` (session token tracking), `/tmp/claude-*` (hook bridge files)
- Test: `echo '{"model":{"display_name":"Claude"},"context_window":{"context_window_size":200000}}' | bash statusline.sh`

## Conventions

- No external dependencies beyond bash, jq, git, awk, sed
- All segments degrade gracefully — missing data = segment hidden
- Colors use 24-bit ANSI (RGB)
- Config is bash `source`-able — no YAML/JSON parsing needed
