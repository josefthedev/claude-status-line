#!/usr/bin/env bash
set -euo pipefail

DEST="$HOME/.claude"
DRY_RUN=false

if [[ "${1:-}" == "--dry-run" ]]; then
    DRY_RUN=true
fi

log() { echo "  $1"; }
dry() { echo "  [DRY-RUN] $1"; }

echo ""
echo "Claude Status Line — Uninstall"
echo "==============================="
echo ""

# Find most recent backup
LATEST_BAK=""
if compgen -G "$DEST/statusline.sh.bak.*" > /dev/null 2>&1; then
    LATEST_BAK="$(ls -1t "$DEST"/statusline.sh.bak.* 2>/dev/null | head -1)"
fi

# Restore backup
if [[ -n "$LATEST_BAK" ]]; then
    if $DRY_RUN; then
        dry "would restore $LATEST_BAK → $DEST/statusline.sh"
    else
        cp "$LATEST_BAK" "$DEST/statusline.sh"
        log "restored $LATEST_BAK → $DEST/statusline.sh"
    fi
else
    echo "WARNING: No backup found at $DEST/statusline.sh.bak.*" >&2
    echo "         Skipping statusline.sh restore." >&2
fi

# Remove installed Python files
if [[ -f "$DEST/statusline.py" ]]; then
    if $DRY_RUN; then
        dry "would remove $DEST/statusline.py"
    else
        rm "$DEST/statusline.py"
        log "removed $DEST/statusline.py"
    fi
fi

if [[ -d "$DEST/statusline-lib" ]]; then
    if $DRY_RUN; then
        dry "would remove $DEST/statusline-lib/"
    else
        rm -r "$DEST/statusline-lib"
        log "removed $DEST/statusline-lib/"
    fi
fi

echo ""
echo "To revert, update ~/.claude/settings.json:"
echo ""
echo '  "statusline": { "command": "bash ~/.claude/statusline.sh" }'
echo ""

if $DRY_RUN; then
    echo "[DRY-RUN] No files were modified."
fi
