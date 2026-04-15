#!/bin/bash
# agent-tracker.sh — Tracks subagent lifecycle for statusline display
# Registered as both PreToolUse and PostToolUse hook (matcher: Agent)
# Writes state to /tmp/claude-agent-tracker-{session_id}.json
set -f

input=$(timeout 3 cat 2>/dev/null)
[ -z "$input" ] && exit 0

session_id=$(echo "$input" | jq -r '.session_id // empty' 2>/dev/null)
[ -z "$session_id" ] && exit 0

event=$(echo "$input" | jq -r '.hook_event_name // empty' 2>/dev/null)
tool_use_id=$(echo "$input" | jq -r '.tool_use_id // empty' 2>/dev/null)
[ -z "$tool_use_id" ] && exit 0

state_file="/tmp/claude-agent-tracker-${session_id}.json"
now=$(date +%s)

# Initialize state file if missing
[ -f "$state_file" ] || echo '{"agents":[]}' > "$state_file"

if [ "$event" = "PreToolUse" ]; then
    agent_type=$(echo "$input" | jq -r '.tool_input.subagent_type // "general"' 2>/dev/null)
    desc=$(echo "$input" | jq -r '.tool_input.description // ""' 2>/dev/null)

    jq --arg id "$tool_use_id" \
       --arg type "$agent_type" \
       --arg desc "$desc" \
       --argjson ts "$now" \
       '.agents += [{"tool_use_id":$id,"type":$type,"desc":$desc,"started_at":$ts,"status":"running"}]' \
       "$state_file" > "${state_file}.tmp" && mv "${state_file}.tmp" "$state_file"

elif [ "$event" = "PostToolUse" ]; then
    duration=$(echo "$input" | jq -r '.tool_response.totalDurationMs // 0' 2>/dev/null)
    tokens=$(echo "$input" | jq -r '.tool_response.totalTokens // 0' 2>/dev/null)

    jq --arg id "$tool_use_id" \
       --argjson ts "$now" \
       --argjson dur "$duration" \
       --argjson tok "$tokens" \
       '(.agents[] | select(.tool_use_id == $id)) |= . + {"status":"done","finished_at":$ts,"duration_ms":$dur,"tokens":$tok}' \
       "$state_file" > "${state_file}.tmp" && mv "${state_file}.tmp" "$state_file"
fi

exit 0
