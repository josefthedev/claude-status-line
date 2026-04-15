#!/bin/bash
# hook-status-bridge.sh — Records hook activity for statusline display
# Runs as PostToolUse hook. Writes state to /tmp/claude-hook-status-{session_id}.json
# so the statusline can show which hooks fired and which hookify rules matched.
set -f

input=$(timeout 3 cat 2>/dev/null)
[ -z "$input" ] && exit 0

session_id=$(echo "$input" | jq -r '.session_id // empty' 2>/dev/null)
[ -z "$session_id" ] && exit 0

tool_name=$(echo "$input" | jq -r '.tool_name // empty' 2>/dev/null)
hook_event="PostToolUse"
cwd=$(echo "$input" | jq -r '.cwd // empty' 2>/dev/null)
[ -z "$cwd" ] && cwd=$(pwd)
now=$(date +%s)

# ── Determine which user hooks ran for this event+tool ─────
# Parse ~/.claude/settings.json to find PostToolUse hooks whose matcher
# includes this tool_name (or has no matcher = matches all).
hooks_ran=""
settings_file="$HOME/.claude/settings.json"
if [ -f "$settings_file" ]; then
    # Extract PostToolUse hook groups
    num_groups=$(jq -r '.hooks.PostToolUse | length' "$settings_file" 2>/dev/null)
    for ((i=0; i<num_groups; i++)); do
        matcher=$(jq -r ".hooks.PostToolUse[$i].matcher // empty" "$settings_file" 2>/dev/null)
        # Check if this group matches the current tool
        matched=false
        if [ -z "$matcher" ]; then
            matched=true
        elif echo "$matcher" | grep -qw "$tool_name" 2>/dev/null; then
            matched=true
        fi
        if [ "$matched" = "true" ]; then
            # Extract the command basename (strip path and extension)
            cmd=$(jq -r ".hooks.PostToolUse[$i].hooks[0].command // empty" "$settings_file" 2>/dev/null)
            if [ -n "$cmd" ]; then
                # Get just the filename, strip extension, abbreviate to short tags
                base=$(basename "$cmd" | sed 's/\.[^.]*$//' | sed 's/"//g')
                # Map to short recognizable tags
                case "$base" in
                    gsd-context-monitor) base="gsd" ;;
                    gsd-prompt-guard)    base="guard" ;;
                    mem0-tool-logger)    base="m0" ;;
                    mem0-session-recall) base="m0-recall" ;;
                    hook-status-bridge)  base="bridge" ;;
                    *) base=$(echo "$base" | sed 's/^gsd-//' | sed 's/^mem0-/m0-/') ;;
                esac
                [ -n "$hooks_ran" ] && hooks_ran+=","
                hooks_ran+="$base"
            fi
        fi
    done
fi

# ── Scan hookify rules ─────────────────────────────────────
# Look for .claude/hookify.*.local.md in cwd (project-level rules)
hookify_configured=false
hookify_rules="[]"

rule_files=$(find "$cwd/.claude" -maxdepth 1 -name "hookify.*.local.md" 2>/dev/null)
if [ -n "$rule_files" ]; then
    hookify_configured=true
    rules_json="["
    first=true
    while IFS= read -r rfile; do
        [ -z "$rfile" ] && continue
        # Parse YAML frontmatter (between --- lines)
        frontmatter=$(sed -n '/^---$/,/^---$/p' "$rfile" 2>/dev/null | grep -v '^---$')
        rname=$(echo "$frontmatter" | grep '^name:' | head -1 | sed 's/^name:[[:space:]]*//')
        renabled=$(echo "$frontmatter" | grep '^enabled:' | head -1 | sed 's/^enabled:[[:space:]]*//')
        revent=$(echo "$frontmatter" | grep '^event:' | head -1 | sed 's/^event:[[:space:]]*//')
        raction=$(echo "$frontmatter" | grep '^action:' | head -1 | sed 's/^action:[[:space:]]*//')

        # Skip disabled rules
        [ "$renabled" = "false" ] && continue
        # Skip if rule name is empty
        [ -z "$rname" ] && continue

        # Check if this rule's event matches the current tool context
        event_match=false
        case "$revent" in
            all)  event_match=true ;;
            bash) [ "$tool_name" = "Bash" ] && event_match=true ;;
            file) echo "$tool_name" | grep -qE "^(Edit|Write|MultiEdit)$" && event_match=true ;;
            stop) ;; # Stop events don't fire during PostToolUse
            prompt) ;; # UserPromptSubmit doesn't fire here
            *) event_match=true ;; # Unknown event type, show it
        esac

        if [ "$event_match" = "true" ]; then
            [ "$first" = "true" ] && first=false || rules_json+=","
            rules_json+="{\"name\":\"$rname\",\"action\":\"${raction:-warn}\"}"
        fi
    done <<< "$rule_files"
    rules_json+="]"
    hookify_rules="$rules_json"
fi

# ── Write state file ───────────────────────────────────────
state_file="/tmp/claude-hook-status-${session_id}.json"
# Build JSON manually (jq not needed for output — faster)
hooks_ran_json=$(echo "$hooks_ran" | awk -F',' '{
    printf "["
    for(i=1;i<=NF;i++) {
        if(i>1) printf ","
        gsub(/^[[:space:]]+|[[:space:]]+$/,"",$i)
        printf "\"%s\"", $i
    }
    printf "]"
}')
[ -z "$hooks_ran" ] && hooks_ran_json="[]"

cat > "$state_file" <<EOF
{"ts":${now},"hook_event":"${hook_event}","tool_name":"${tool_name}","hooks_ran":${hooks_ran_json},"hookify_rules":${hookify_rules},"hookify_configured":${hookify_configured}}
EOF

exit 0
