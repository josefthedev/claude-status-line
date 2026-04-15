---
plan: 07
phase: 07
wave: 1
title: Safe Install and Backup System
autonomous: true
files_modified:
  - install.sh
  - uninstall.sh
must_haves:
  - install.sh exists and is executable
  - install.sh --dry-run exits 0 and prints dry-run output without modifying files
  - install.sh --dry-run output contains "statusline-lib" and "statusline.py"
  - uninstall.sh exists and is executable
  - Neither script modifies ~/.claude/settings.json
  - install.sh output contains instructions mentioning settings.json
---

<objective>
Create install.sh and uninstall.sh for safe, reversible deployment of the Python statusline.

Purpose: Users need a single command to deploy and a single command to revert.
Output: Two executable shell scripts in repo root.
</objective>

<context>
@.planning/phases/07-safe-install-and-backup-system/07-CONTEXT.md
@statusline.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create install.sh</name>
  <files>install.sh</files>
  <read_first>
    - statusline.py (verify it exists as source)
    - lib/__init__.py, lib/ansi.py, lib/config.py, lib/segments.py, lib/packer.py (verify lib contents)
  </read_first>
  <action>
Create install.sh with the following complete script:

```bash
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
```

Then run: chmod +x install.sh
  </action>
  <verify>
    <automated>cd /home/josef/workspace-linux/claude-status-line && bash install.sh --dry-run 2>&1 | grep -q "DRY-RUN" && echo PASS || echo FAIL</automated>
  </verify>
  <acceptance_criteria>
    - install.sh --dry-run exits 0
    - Output contains [DRY-RUN], "statusline-lib", "statusline.py", and "settings.json"
    - No files created/modified in ~/.claude/ during dry-run
  </acceptance_criteria>
  <done>install.sh exists, is executable, --dry-run works, real install copies files and creates backup</done>
</task>

<task type="auto">
  <name>Task 2: Create uninstall.sh</name>
  <files>uninstall.sh</files>
  <read_first>
    - install.sh (to understand what gets installed and backup naming)
  </read_first>
  <action>
Create uninstall.sh with the following complete script:

```bash
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
```

Then run: chmod +x uninstall.sh
  </action>
  <verify>
    <automated>cd /home/josef/workspace-linux/claude-status-line && bash uninstall.sh --dry-run 2>&1 | grep -q "DRY-RUN" && echo PASS || echo FAIL</automated>
  </verify>
  <acceptance_criteria>
    - uninstall.sh --dry-run exits 0
    - Output contains [DRY-RUN] and "settings.json"
    - No files removed during dry-run
  </acceptance_criteria>
  <done>uninstall.sh exists, is executable, --dry-run works, real uninstall restores backup and removes Python files</done>
</task>

</tasks>

<verification>
bash install.sh --dry-run   # exits 0, shows plan, changes nothing
bash uninstall.sh --dry-run # exits 0, shows plan, changes nothing
# Then manual: bash install.sh && ls ~/.claude/statusline-lib/ && bash uninstall.sh
</verification>

<success_criteria>
- Both scripts exist and are executable
- --dry-run on both exits 0 and modifies nothing
- install.sh creates backup, copies files, prints settings.json instructions
- uninstall.sh restores backup, removes Python files, prints revert instructions
- Neither script touches settings.json
</success_criteria>

<output>
After completion, create `.planning/phases/07-safe-install-and-backup-system/07-SUMMARY.md`
</output>
