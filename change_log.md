# Change Log

## 2026-04-15 — Initial repo setup

- Migrated statusline.sh (636-line bash renderer, 22+ segments) from claude-ai2 repo
- Migrated statusline.conf (declarative config with 3-line layout)
- Migrated hooks: agent-tracker.sh, hook-status-bridge.sh, gsd-statusline.js
- Created CLAUDE.md, .gitignore, change_log.md
- Initialized git repo and pushed to GitHub

## 2026-04-16 — Python statusline rewrite complete

- Phases 1-8: built Python renderer (statusline.py), ANSI library (lib/ansi.py), config parser (lib/config.py), segment renderers (lib/segments.py), adaptive line packer (lib/packer.py)
- Safe install/uninstall system (install.sh, uninstall.sh) with timestamped backups
- Tmux integration (tmux/statusline.sh) for CC session info in tmux status-right
- Synced statusline.sh from ~/.claude/ into repo
- Added OVERRIDE_DIMCOLOR and MAX_LINES Python renderer keys to statusline.conf
