# Requirements

## Must Have

- Python renderer that produces correct output within CC's rendering constraints
- ANSI-aware visible width calculation (strip escape codes before measuring)
- cli-truncate workaround: each line ≤ `terminal_width / N` visible chars
- Real terminal width detection via `/dev/tty` (bypasses CC's stdout capture)
- dimColor compensation via `\033[22m` prefix
- All 22 segments from bash version ported to Python
- Adaptive packing: segments dropped (not truncated) when line is full
- Safe install with timestamped backups
- Tests for ANSI lib, packer, and segment renderers
- Tmux integration script (outside CC's rendering control)

## Should Have

- Per-project config override (read `.claude/statusline.conf` from cwd)
- Session state persistence (avg tokens/msg, session timer)
- Hook bridge integration (show last hook event)
- Agent tracker integration (show active/done subagents)

## Won't Have (this milestone)

- External Python dependencies (rich, blessed, etc.)
- Web dashboard
- Windows support (WSL2 fine)
- Auto-install on git push
