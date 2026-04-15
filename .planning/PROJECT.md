# Claude Status Line — Project

## Vision

A standalone, production-grade status line renderer for Claude Code CLI. Replaces the bash prototype with a Python implementation that correctly handles CC's multi-line truncation bug, compensates for dimColor wrapping, and provides real terminal width detection. Includes a tmux integration track for unlimited multi-line status outside CC's control.

## Core Principles

- **Safety first**: Never touch `~/.claude/` files without explicit user approval (install.sh gated)
- **Zero dependencies**: Python stdlib only — `json`, `os`, `fcntl`, `termios`, `struct`, `re`
- **Degrade gracefully**: Every segment returns None when data is missing — never errors
- **Correct by construction**: cli-truncate workaround baked into the packer algorithm

## Non-Negotiables

- Existing `~/.claude/statusline.sh` must be preserved (timestamped backup on install)
- All new code lives in the repo before any install
- Each segment must be independently testable
- Install/uninstall must be fully reversible

## Tech Stack

- Python 3 (3.10+)
- No external packages
- Bash for config sourcing + tmux integration
- Git for version control

## User

Josef — power user, Linux/WSL2, tmux, Claude Code heavy user, multiple projects.
