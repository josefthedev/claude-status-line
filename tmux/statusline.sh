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
