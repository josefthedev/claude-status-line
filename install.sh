#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEST="$HOME/.claude"
DRY_RUN=false

if [[ "${1:-}" == "--dry-run" ]]; then
    DRY_RUN=true
fi

log() { echo "  $1"; }
dry() { echo "  [DRY-RUN] $1"; }

# Verify source files exist
for f in "$SCRIPT_DIR/statusline.py" "$SCRIPT_DIR/lib/__init__.py" "$SCRIPT_DIR/lib/ansi.py" \
         "$SCRIPT_DIR/lib/config.py" "$SCRIPT_DIR/lib/segments.py" "$SCRIPT_DIR/lib/packer.py"; do
    if [[ ! -f "$f" ]]; then
        echo "ERROR: Source file not found: $f" >&2
        exit 1
    fi
done

# Verify destination directory exists
if [[ ! -d "$DEST" ]]; then
    echo "ERROR: $DEST does not exist" >&2
    exit 1
fi

echo ""
echo "Claude Status Line — Install"
echo "============================="
echo ""

# Backup existing statusline.sh if present
if [[ -f "$DEST/statusline.sh" ]]; then
    TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
    BAK="$DEST/statusline.sh.bak.$TIMESTAMP"
    if $DRY_RUN; then
        dry "would backup $DEST/statusline.sh → $BAK"
    else
        cp "$DEST/statusline.sh" "$BAK"
        log "backed up $DEST/statusline.sh → $BAK"
    fi
fi

# Copy statusline.py
if $DRY_RUN; then
    dry "would copy statusline.py → $DEST/statusline.py"
else
    cp "$SCRIPT_DIR/statusline.py" "$DEST/statusline.py"
    log "copied statusline.py → $DEST/statusline.py"
fi

# Copy lib/ → statusline-lib/
if $DRY_RUN; then
    dry "would copy lib/ → $DEST/statusline-lib/"
else
    mkdir -p "$DEST/statusline-lib"
    cp "$SCRIPT_DIR/lib/"*.py "$DEST/statusline-lib/"
    log "copied lib/ → $DEST/statusline-lib/"
fi

echo ""
echo "To activate, update ~/.claude/settings.json:"
echo ""
echo '  "statusline": { "command": "python3 ~/.claude/statusline.py" }'
echo ""

if $DRY_RUN; then
    echo "[DRY-RUN] No files were modified."
fi
