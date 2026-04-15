---
plan: 08
phase: 08
wave: 1
title: Tmux Integration
autonomous: true
files_modified:
  - tmux/statusline.sh
  - tmux/README.md
  - install.sh
must_haves:
  - tmux/statusline.sh exists and is executable
  - bash tmux/statusline.sh exits 0 with no active session
  - output contains "cc:" prefix
  - tmux/README.md exists with tmux.conf example lines
  - install.sh updated to copy tmux/ directory
---

<objective>
Create a tmux status-right integration script that reads CC state files directly and renders a compact single-line status. Also document setup and update the installer.

Purpose: Let users see CC session info (tokens, avg/msg, session timer, hooks, agents) in their tmux status bar without depending on CC's rendering pipeline.
Output: tmux/statusline.sh, tmux/README.md, updated install.sh
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/08-tmux-integration/08-CONTEXT.md
@statusline.sh (reference for state file reading patterns, format_tokens)
@install.sh (needs tmux/ copy added)
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create tmux/statusline.sh and tmux/README.md</name>
  <files>tmux/statusline.sh, tmux/README.md</files>
  <read_first>
    - statusline.sh (lines 97-103 for format_tokens, lines 189-271 for state file reading, lines 556-569 for agent tracker reading)
    - .planning/phases/08-tmux-integration/08-CONTEXT.md
  </read_first>
  <action>
Create `tmux/statusline.sh` with the following complete implementation:

```bash
#!/usr/bin/env bash
# Tmux status-right segment for Claude Code session info.
# Reads CC state files directly — no dependency on CC's rendering pipeline.
# Output uses tmux color syntax (#[fg=colourN]), NOT ANSI escapes.
set -f

# ── Colors (tmux syntax) ──────────────────────────────────
c_blue="#[fg=colour39]"
c_dim="#[fg=colour240]"
c_white="#[fg=colour252]"
c_orange="#[fg=colour215]"
c_reset="#[fg=default]"

# ── Helpers ────────────────────────────────────────────────
format_tokens() {
    local n=$1
    if   [ "$n" -ge 1000000 ]; then awk "BEGIN{printf \"%.1fM\", $n/1000000}"
    elif [ "$n" -ge 1000 ];    then awk "BEGIN{printf \"%.1fk\", $n/1000}"
    else printf "%d" "$n"
    fi
}

# ── Find active session ───────────────────────────────────
# Most recent state file by mtime in ~/.claude/statusline-state/
# If missing or older than 2 hours, show idle.
state_dir="$HOME/.claude/statusline-state"
if [ ! -d "$state_dir" ]; then
    printf "cc: idle"
    exit 0
fi

state_file=""
latest_mtime=0
now=$(date +%s)
two_hours_ago=$(( now - 7200 ))

for f in "$state_dir"/*.json; do
    [ -f "$f" ] || continue
    mtime=$(stat -c %Y "$f" 2>/dev/null || stat -f %m "$f" 2>/dev/null)
    [ -z "$mtime" ] && continue
    if [ "$mtime" -gt "$latest_mtime" ] 2>/dev/null; then
        latest_mtime=$mtime
        state_file="$f"
    fi
done

if [ -z "$state_file" ] || [ "$latest_mtime" -lt "$two_hours_ago" ] 2>/dev/null; then
    printf "cc: idle"
    exit 0
fi

# ── Extract session_id from filename ──────────────────────
session_id=$(basename "$state_file" .json)

# ── Read state file ───────────────────────────────────────
total=$(jq -r '.total // 0' "$state_file" 2>/dev/null)
msgs=$(jq -r '.msgs // 0' "$state_file" 2>/dev/null)
first_ts=$(jq -r '.first_ts // 0' "$state_file" 2>/dev/null)

[ "${total:-0}" -eq 0 ] 2>/dev/null && { printf "cc: idle"; exit 0; }

# ── Tokens ────────────────────────────────────────────────
tkns=$(format_tokens "$total")

# ── Avg per message ───────────────────────────────────────
avg=""
if [ "${msgs:-0}" -gt 0 ] 2>/dev/null; then
    avg_raw=$(awk "BEGIN{printf \"%.0f\", $total / $msgs}")
    avg=$(format_tokens "$avg_raw")
fi

# ── Session timer ─────────────────────────────────────────
timer=""
if [ "${first_ts:-0}" -gt 0 ] 2>/dev/null; then
    elapsed=$(( now - first_ts ))
    if [ "$elapsed" -gt 60 ] 2>/dev/null; then
        h=$(( elapsed / 3600 ))
        m=$(( (elapsed % 3600) / 60 ))
        if [ "$h" -gt 0 ]; then
            timer="${h}h${m}m"
        else
            timer="${m}m"
        fi
    fi
fi

# ── Hook event ────────────────────────────────────────────
hook=""
hook_file="/tmp/claude-hook-status-${session_id}.json"
if [ -f "$hook_file" ]; then
    hook_event=$(jq -r '.hook_event // empty' "$hook_file" 2>/dev/null)
    hook_tool=$(jq -r '.tool_name // empty' "$hook_file" 2>/dev/null)
    [ -n "$hook_tool" ] && hook="$hook_tool" || hook="$hook_event"
fi

# ── Active agents ─────────────────────────────────────────
agents=""
tracker_file="/tmp/claude-agent-tracker-${session_id}.json"
if [ -f "$tracker_file" ]; then
    active=$(jq '[.agents[] | select(.status=="running")] | length' "$tracker_file" 2>/dev/null)
    [ "${active:-0}" -gt 0 ] 2>/dev/null && agents="${active} agents"
fi

# ── Build output ──────────────────────────────────────────
out="cc: ${c_blue}${tkns}${c_reset} ${c_dim}tkns${c_reset}"

[ -n "$avg" ] && out+=" ${c_dim}│${c_reset} ${c_blue}${avg}${c_reset}${c_dim}/msg${c_reset}"
[ -n "$timer" ] && out+=" ${c_dim}│${c_reset} ${c_white}${timer}${c_reset}"
[ -n "$hook" ] && out+=" ${c_dim}│${c_reset} ${c_dim}hook:${c_reset}${c_white}${hook}${c_reset}"
[ -n "$agents" ] && out+=" ${c_dim}│${c_reset} ${c_orange}${agents}${c_reset}"

printf "%s" "$out"
exit 0
```

Make it executable: `chmod +x tmux/statusline.sh`

Then create `tmux/README.md`:

```markdown
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
```
  </action>
  <verify>
    <automated>cd /home/josef/workspace-linux/claude-status-line && bash tmux/statusline.sh && echo " [exit:$?]"</automated>
  </verify>
  <acceptance_criteria>
    - tmux/statusline.sh exists and is executable
    - `bash tmux/statusline.sh` exits 0
    - Output starts with "cc:" (either "cc: idle" or "cc: " followed by token info)
    - tmux/README.md exists with tmux.conf example showing `#(~/.claude/tmux/statusline.sh)`
    - No ANSI escape codes in output — only tmux #[fg=...] color syntax
    - Output is a single line (no newlines)
  </acceptance_criteria>
  <done>Both files exist, script runs clean, output uses tmux color syntax</done>
</task>

<task type="auto">
  <name>Task 2: Update install.sh to copy tmux/ directory</name>
  <files>install.sh</files>
  <read_first>
    - install.sh
  </read_first>
  <action>
Add tmux/ directory copying to install.sh. Insert after the lib/ copy block (after line 62) and before the activation message:

1. Add `"$SCRIPT_DIR/tmux/statusline.sh"` to the source file existence check loop (line 16-20 area).

2. After the `lib/ → statusline-lib/` copy block, add:

```bash
# Copy tmux/ → tmux/
if $DRY_RUN; then
    dry "would copy tmux/ → $DEST/tmux/"
else
    mkdir -p "$DEST/tmux"
    cp "$SCRIPT_DIR/tmux/statusline.sh" "$DEST/tmux/statusline.sh"
    chmod +x "$DEST/tmux/statusline.sh"
    log "copied tmux/ → $DEST/tmux/"
fi
```

3. After the settings.json activation message, add a tmux setup hint:

```bash
echo "For tmux integration, add to ~/.tmux.conf:"
echo ""
echo '  set -g status-right "#(~/.claude/tmux/statusline.sh)"'
echo '  set -g status-interval 5'
echo ""
```
  </action>
  <verify>
    <automated>cd /home/josef/workspace-linux/claude-status-line && bash install.sh --dry-run 2>&1 | grep -q "tmux" && echo "PASS" || echo "FAIL"</automated>
  </verify>
  <acceptance_criteria>
    - `install.sh --dry-run` mentions tmux in its output
    - tmux/statusline.sh is in the source file existence check
    - Dry run shows "would copy tmux/" line
    - chmod +x applied to destination tmux/statusline.sh
  </acceptance_criteria>
  <done>install.sh --dry-run shows tmux copy operation, real install copies tmux/ to ~/.claude/tmux/</done>
</task>

</tasks>

<verification>
1. `bash tmux/statusline.sh` exits 0 and outputs something starting with "cc:"
2. Output contains no `\033[` or `\e[` ANSI escapes — only `#[fg=` tmux syntax
3. Output is single line (no embedded newlines)
4. `bash install.sh --dry-run` mentions tmux directory copy
5. tmux/README.md contains `#(~/.claude/tmux/statusline.sh)` tmux.conf example
</verification>

<success_criteria>
- tmux/statusline.sh runs independently of CC rendering pipeline
- Shows "cc: idle" when no active session
- Shows token info with tmux colors when session active
- install.sh updated to deploy tmux/ alongside existing files
- README.md provides copy-paste tmux.conf lines
</success_criteria>

<output>
After completion, create `.planning/phases/08-tmux-integration/08-SUMMARY.md`
</output>
