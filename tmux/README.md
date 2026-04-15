# Tmux Integration for Claude Status Line

Shows Claude Code session info in your tmux status bar: tokens, avg/msg, session timer, hook events, active agents.

Reads CC state files directly — no dependency on CC's rendering pipeline.

## Setup

Add to your `~/.tmux.conf`:

    set -g status-right "#(~/.claude/tmux/statusline.sh)"
    set -g status-right-length 80
    set -g status-interval 5

Then reload tmux config:

    tmux source-file ~/.tmux.conf

## What it shows

    cc: 34.5k tkns │ 8.2k/msg │ 23m │ hook:Agent │ 2 agents

When no active CC session (state files missing or >2h old):

    cc: idle

## Requirements

- bash 4+
- jq
- State files written by the main statusline.sh (runs automatically when CC is active)

## Install

Run `install.sh` from the repo root — it copies `tmux/` to `~/.claude/tmux/`.
