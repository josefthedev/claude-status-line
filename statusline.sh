#!/bin/bash
set -f

input=$(cat)

if [ -z "$input" ]; then
    printf "Claude"
    exit 0
fi

# ── Defaults (overridden by statusline.conf) ───────────
LINE1="model context_pct cwd git_branch git_status effort tokens cache_pct rate_5h rate_7d"
LINE2=""
LINE3=""
RATE_STYLE="bar_pct"
BAR_WIDTH=6
TOKEN_STYLE="total"
SHOW_LABELS=true
SHOW_TTL=true
SEP_CHAR="│"
CC_UI_LINE=0
GIT_BRANCH_MAX=20
PRICE_OPUS="15 75"
PRICE_SONNET="3 15"
PRICE_HAIKU="0.80 4"

CONF="${HOME}/.claude/statusline.conf"
[ -f "$CONF" ] && source "$CONF"

# ── Colors ──────────────────────────────────────────────
blue='\033[38;2;0;153;255m'
orange='\033[38;2;255;176;85m'
green='\033[38;2;0;175;80m'
red='\033[38;2;255;85;85m'
yellow='\033[38;2;230;200;0m'
white='\033[38;2;220;220;220m'
dim='\033[2m'
reset='\033[0m'

sep=" ${dim}${SEP_CHAR}${reset} "

# ── Helpers ─────────────────────────────────────────────
color_for_pct() {
    local pct=$1
    if   [ "$pct" -ge 90 ]; then printf "%s" "$red"
    elif [ "$pct" -ge 70 ]; then printf "%s" "$yellow"
    elif [ "$pct" -ge 50 ]; then printf "%s" "$orange"
    else printf "%s" "$green"
    fi
}

color_for_cache_pct() {
    local pct=$1
    if   [ "$pct" -ge 70 ]; then printf "%s" "$green"
    elif [ "$pct" -ge 40 ]; then printf "%s" "$yellow"
    elif [ "$pct" -ge 15 ]; then printf "%s" "$orange"
    else printf "%s" "$red"
    fi
}

build_bar() {
    local pct=$1 width=$2
    [ "$pct" -lt 0 ]   2>/dev/null && pct=0
    [ "$pct" -gt 100 ] 2>/dev/null && pct=100
    local filled=$(( pct * width / 100 ))
    local empty=$(( width - filled ))
    local bar_color filled_str="" empty_str=""
    bar_color=$(color_for_pct "$pct")
    for ((i=0; i<filled; i++)); do filled_str+="▓"; done
    for ((i=0; i<empty;  i++)); do empty_str+="░";  done
    printf "%b" "${bar_color}${filled_str}${empty_str}${reset}"
}

format_ttl_epoch() {
    local val="$1"
    [ -z "$val" ] || [ "$val" = "null" ] && return
    local epoch
    if [[ "$val" =~ ^[0-9]+$ ]]; then
        epoch="$val"
    else
        epoch=$(date -d "$val" +%s 2>/dev/null)
        [ -z "$epoch" ] && return
    fi
    local now diff days hours mins
    now=$(date +%s)
    diff=$(( epoch - now ))
    [ "$diff" -le 0 ] && { printf "now"; return; }
    days=$(( diff / 86400 ))
    hours=$(( (diff % 86400) / 3600 ))
    mins=$(( (diff % 3600) / 60 ))
    if   [ "$days"  -gt 0 ]; then printf "%dd%dh" "$days"  "$hours"
    elif [ "$hours" -gt 0 ]; then printf "%dh%dm" "$hours" "$mins"
    else printf "%dm" "$mins"
    fi
}

format_tokens() {
    local n=$1
    if   [ "$n" -ge 1000000 ]; then awk "BEGIN{printf \"%.1fM\", $n/1000000}"
    elif [ "$n" -ge 1000 ];    then awk "BEGIN{printf \"%.1fk\", $n/1000}"
    else printf "%d" "$n"
    fi
}

lbl() {
    [ "$SHOW_LABELS" = "true" ] && printf "%b" "${dim}${1}:${reset} "
}

# ── Data extraction ─────────────────────────────────────
model_name=$(echo "$input" | jq -r '.model.display_name // "Claude"')
model_id=$(echo "$input"   | jq -r '.model.id // ""')

session_in=$(echo  "$input" | jq -r '.context_window.total_input_tokens  // 0')
session_out=$(echo "$input" | jq -r '.context_window.total_output_tokens // 0')
session_total=$(( session_in + session_out ))

size=$(echo         "$input" | jq -r '.context_window.context_window_size // 200000')
input_tokens=$(echo "$input" | jq -r '.context_window.current_usage.input_tokens // 0')
cache_create=$(echo "$input" | jq -r '.context_window.current_usage.cache_creation_input_tokens // 0')
cache_read=$(echo   "$input" | jq -r '.context_window.current_usage.cache_read_input_tokens // 0')
[ "$size" -eq 0 ] 2>/dev/null && size=200000
current=$(( input_tokens + cache_create + cache_read ))
pct_used=$(( size > 0 ? current * 100 / size : 0 ))
cache_pct=$(( current > 0 ? cache_read * 100 / current : 0 ))

effort=""
if [ -n "$CLAUDE_CODE_EFFORT_LEVEL" ]; then
    effort="$CLAUDE_CODE_EFFORT_LEVEL"
else
    for sf in ".claude/settings.local.json" ".claude/settings.json" \
              "$HOME/.claude/settings.local.json" "$HOME/.claude/settings.json"; do
        if [ -f "$sf" ]; then
            val=$(jq -r '.effortLevel // empty' "$sf" 2>/dev/null)
            if [ -n "$val" ] && [ "$val" != "null" ]; then
                effort="$val"; break
            fi
        fi
    done
fi
[ -z "$effort" ] && effort="auto"

cwd=$(echo "$input" | jq -r '.cwd // ""')
[ -z "$cwd" ] || [ "$cwd" = "null" ] && cwd=$(pwd)
cwd_basename=$(basename "$cwd")

# Per-project config override (loaded after cwd is known)
_proj_conf="${cwd}/.claude/statusline.conf"
[ -f "$_proj_conf" ] && source "$_proj_conf"

git_branch=""
git_info=""
if git -C "$cwd" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    git_branch=$(git -C "$cwd" symbolic-ref --short HEAD 2>/dev/null)
    upstream=$(git -C "$cwd" rev-parse --abbrev-ref '@{upstream}' 2>/dev/null)
    if [ -n "$upstream" ]; then
        ahead=$(git  -C "$cwd" rev-list --count '@{upstream}..HEAD' 2>/dev/null)
        behind=$(git -C "$cwd" rev-list --count 'HEAD..@{upstream}' 2>/dev/null)
        [ "$ahead"  -gt 0 ] 2>/dev/null && git_info+="${green}↑${ahead}${reset}"
        [ "$behind" -gt 0 ] 2>/dev/null && git_info+="${red}↓${behind}${reset}"
    fi
    porcelain=$(git -C "$cwd" status --porcelain 2>/dev/null)
    if [ -n "$porcelain" ]; then
        staged=$(echo   "$porcelain" | grep -c '^[MADRCT]')
        unstaged=$(echo "$porcelain" | grep -c '^.[MADRCT?]')
        [ "$staged"   -gt 0 ] && git_info+="${yellow}+${staged}${reset}"
        [ "$unstaged" -gt 0 ] && git_info+="${orange}~${unstaged}${reset}"
    fi
fi

# ── Worktree detection ───────────────────────────────────
worktree_name=""
if git -C "$cwd" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    _wt_list=$(git -C "$cwd" worktree list --porcelain 2>/dev/null)
    _wt_count=$(echo "$_wt_list" | grep -c '^worktree ')
    if [ "${_wt_count:-0}" -gt 1 ] 2>/dev/null; then
        _main_wt=$(echo "$_wt_list" | grep '^worktree ' | head -1 | sed 's/^worktree //')
        _real_cwd=$(realpath "$cwd" 2>/dev/null || echo "$cwd")
        if [ "$_real_cwd" != "$_main_wt" ]; then
            worktree_name=$(basename "$_real_cwd")
        fi
    fi
fi

five_pct=$(echo         "$input" | jq -r '.rate_limits.five_hour.used_percentage // empty' | awk '{printf "%.0f", $1}')
five_reset_epoch=$(echo "$input" | jq -r '.rate_limits.five_hour.resets_at // empty')
seven_pct=$(echo         "$input" | jq -r '.rate_limits.seven_day.used_percentage // empty' | awk '{printf "%.0f", $1}')
seven_reset_epoch=$(echo "$input" | jq -r '.rate_limits.seven_day.resets_at // empty')

# ── Session average tokens ───────────────────────────────
# Track per-session message count + token history in a state file.
session_id=$(echo "$input" | jq -r '.session_id // empty')
avg_tokens_per_msg=""
session_first_ts=0
session_history=""
if [ -n "$session_id" ] && [ "$session_total" -gt 0 ]; then
    state_dir="${HOME}/.claude/statusline-state"
    mkdir -p "$state_dir"
    state_file="${state_dir}/${session_id}.json"
    now_epoch=$(date +%s)

    if [ -f "$state_file" ]; then
        prev_total=$(jq -r '.total     // 0'  "$state_file" 2>/dev/null)
        msg_count=$(jq  -r '.msgs      // 0'  "$state_file" 2>/dev/null)
        session_first_ts=$(jq -r '.first_ts // 0' "$state_file" 2>/dev/null)
        session_history=$(jq  -r '.history  // ""' "$state_file" 2>/dev/null)
        [ "${session_first_ts:-0}" -eq 0 ] 2>/dev/null && session_first_ts=$now_epoch
        if [ "$session_total" -gt "$prev_total" ] 2>/dev/null; then
            msg_count=$(( msg_count + 1 ))
            avg_tokens_per_msg=$(awk "BEGIN{printf \"%.0f\", $session_total / $msg_count}")
            # Append to history, keep last 8 readings
            if [ -n "$session_history" ]; then
                session_history="${session_history},${avg_tokens_per_msg}"
            else
                session_history="$avg_tokens_per_msg"
            fi
            session_history=$(echo "$session_history" | awk -F',' '{
                n=split($0,a,","); start=(n>8)?n-8+1:1
                for(i=start;i<=n;i++){if(i>start)printf ","; printf a[i]}
            }')
            printf '{"total":%d,"msgs":%d,"ts":%d,"first_ts":%d,"history":"%s"}' \
                "$session_total" "$msg_count" "$now_epoch" "$session_first_ts" "$session_history" > "$state_file"
        else
            [ "$msg_count" -gt 0 ] 2>/dev/null && \
                avg_tokens_per_msg=$(awk "BEGIN{printf \"%.0f\", $session_total / $msg_count}")
        fi
    else
        msg_count=1
        session_first_ts=$now_epoch
        avg_tokens_per_msg="$session_total"
        session_history="$session_total"
        printf '{"total":%d,"msgs":%d,"ts":%d,"first_ts":%d,"history":"%s"}' \
            "$session_total" "$msg_count" "$now_epoch" "$session_first_ts" "$session_history" > "$state_file"
    fi
fi

# ── Cross-session total tokens ───────────────────────────
all_sessions_avg=""
if [ -d "$HOME/.claude/statusline-state" ]; then
    set +f
    _all_total=0; _all_msgs=0
    for sf in "$HOME"/.claude/statusline-state/*.json; do
        [ -f "$sf" ] || continue
        t=$(jq -r '.total // 0' "$sf" 2>/dev/null)
        m=$(jq -r '.msgs  // 0' "$sf" 2>/dev/null)
        _all_total=$(( _all_total + t ))
        _all_msgs=$(( _all_msgs + m ))
    done
    set -f
    [ "$_all_msgs" -gt 0 ] 2>/dev/null && \
        all_sessions_avg=$(awk "BEGIN{printf \"%.0f\", $_all_total / $_all_msgs}")
fi

# ── Hook status bridge ──────────────────────────────────
hook_event_name=""
hook_tool_name=""
hook_scripts=""
hookify_match_text=""
hookify_configured="false"
if [ -n "$session_id" ]; then
    hook_state_file="/tmp/claude-hook-status-${session_id}.json"
    if [ -f "$hook_state_file" ]; then
        hook_event_name=$(jq -r '.hook_event // empty' "$hook_state_file" 2>/dev/null)
        hook_tool_name=$(jq -r '.tool_name // empty' "$hook_state_file" 2>/dev/null)
        hook_scripts=$(jq -r '.hooks_ran // [] | join(",")' "$hook_state_file" 2>/dev/null)
        hookify_configured=$(jq -r '.hookify_configured // false' "$hook_state_file" 2>/dev/null)
        hookify_count=$(jq -r '.hookify_rules | length' "$hook_state_file" 2>/dev/null)
        if [ "$hookify_count" -gt 0 ] 2>/dev/null; then
            hookify_match_text=$(jq -r '.hookify_rules[] | "\(.name) (\(.action))"' "$hook_state_file" 2>/dev/null | paste -sd',' | sed 's/,/, /g')
        fi
    fi
fi

# ── GSD project state ────────────────────────────────────
gsd_phase_num=""
gsd_phase_pct=""
gsd_status=""
gsd_completed_phases=""
gsd_total_phases=""
gsd_completed_plans=""
gsd_total_plans=""
_state_md="${cwd}/.planning/STATE.md"
if [ -f "$_state_md" ]; then
    # Parse YAML frontmatter (everything between the first two --- lines)
    _fm=$(sed -n '1,/^---$/p' "$_state_md" | grep -v '^---$')
    gsd_status=$(echo "$_fm" | grep '^status:' | sed 's/^status:[[:space:]]*//' | tr -d '"')
    gsd_completed_phases=$(echo "$_fm" | grep 'completed_phases:' | sed 's/.*completed_phases:[[:space:]]*//')
    gsd_total_phases=$(echo "$_fm" | grep 'total_phases:' | sed 's/.*total_phases:[[:space:]]*//')
    gsd_completed_plans=$(echo "$_fm" | grep 'completed_plans:' | sed 's/.*completed_plans:[[:space:]]*//')
    gsd_total_plans=$(echo "$_fm" | grep 'total_plans:' | sed 's/.*total_plans:[[:space:]]*//')
    gsd_phase_pct=$(echo "$_fm" | grep 'percent:' | sed 's/.*percent:[[:space:]]*//')
    gsd_phase_num=$(grep -m1 '^Phase:' "$_state_md" | sed 's/^Phase:[[:space:]]*//')
fi

# ── Plugin count ─────────────────────────────────────────
plugins_count=""
for _sf in "$HOME/.claude/settings.json" "$HOME/.claude/settings.local.json"; do
    if [ -f "$_sf" ]; then
        _pc=$(jq '.plugins | length // 0' "$_sf" 2>/dev/null)
        if [ "${_pc:-0}" -gt 0 ] 2>/dev/null; then
            plugins_count="$_pc"
            break
        fi
    fi
done

# ── Time until quota exhaustion ─────────────────────────
format_time_to_exhaust() {
    local pct="$1" reset_epoch="$2" window_secs="$3"
    [ -z "$pct" ] || [ -z "$reset_epoch" ] || [ -z "$window_secs" ] && return
    [ "$pct" -le 0 ] 2>/dev/null && return
    [ "$pct" -ge 100 ] 2>/dev/null && { printf "now"; return; }
    local now window_start elapsed
    now=$(date +%s)
    window_start=$(( reset_epoch - window_secs ))
    elapsed=$(( now - window_start ))
    [ "$elapsed" -le 0 ] 2>/dev/null && return
    local remaining_secs days hours mins
    remaining_secs=$(awk "BEGIN{printf \"%.0f\", $elapsed * (100 - $pct) / $pct}")
    [ "$remaining_secs" -le 0 ] 2>/dev/null && { printf "now"; return; }
    days=$(( remaining_secs / 86400 ))
    hours=$(( (remaining_secs % 86400) / 3600 ))
    mins=$(( (remaining_secs % 3600) / 60 ))
    if   [ "$days"  -gt 0 ]; then printf "%dd%dh" "$days"  "$hours"
    elif [ "$hours" -gt 0 ]; then printf "%dh%dm" "$hours" "$mins"
    else printf "%dm" "$mins"
    fi
}

five_exhaust=""; five_exhaust_secs=0
if [ -n "$five_pct" ] && [ -n "$five_reset_epoch" ]; then
    five_exhaust=$(format_time_to_exhaust "$five_pct" "$five_reset_epoch" 18000)
    _now=$(date +%s)
    _ws=$(( _now - (five_reset_epoch - 18000) ))
    [ "$_ws" -gt 0 ] && [ "${five_pct:-0}" -gt 0 ] 2>/dev/null && \
        five_exhaust_secs=$(awk "BEGIN{printf \"%.0f\", $_ws * (100 - ${five_pct}) / ${five_pct}}")
fi

seven_exhaust=""; seven_exhaust_secs=0
if [ -n "$seven_pct" ] && [ -n "$seven_reset_epoch" ]; then
    seven_exhaust=$(format_time_to_exhaust "$seven_pct" "$seven_reset_epoch" 604800)
    _now=$(date +%s)
    _ws=$(( _now - (seven_reset_epoch - 604800) ))
    [ "$_ws" -gt 0 ] && [ "${seven_pct:-0}" -gt 0 ] 2>/dev/null && \
        seven_exhaust_secs=$(awk "BEGIN{printf \"%.0f\", $_ws * (100 - ${seven_pct}) / ${seven_pct}}")
fi

# ── Derived colors (computed once) ──────────────────────
pct_color=$(color_for_pct "$pct_used")
effort_color="$dim"
case "$effort" in
    low)    effort_color="$green"  ;;
    medium) effort_color="$yellow" ;;
    high)   effort_color="$orange" ;;
    max)    effort_color="$red"    ;;
esac

# ── Cost estimation ─────────────────────────────────────
estimate_cost() {
    [ "$session_total" -gt 0 ] || return
    local in_p out_p
    case "${model_id}${model_name}" in
        *opus*|*Opus*)   read -r in_p out_p <<< "$PRICE_OPUS"   ;;
        *haiku*|*Haiku*) read -r in_p out_p <<< "$PRICE_HAIKU"  ;;
        *)               read -r in_p out_p <<< "$PRICE_SONNET" ;;
    esac
    awk -v i="$session_in" -v o="$session_out" -v ip="$in_p" -v op="$out_p" 'BEGIN{
        cost = (i * ip + o * op) / 1000000
        if      (cost < 0.001) printf "$%.5f", cost
        else if (cost < 0.01)  printf "$%.4f", cost
        else if (cost < 0.10)  printf "$%.3f", cost
        else                   printf "$%.2f", cost
    }'
}

# ── Rate segment renderer ────────────────────────────────
render_rate() {
    local label="$1" pct="$2" epoch="$3"
    [ -z "$pct" ] && return
    [ "$RATE_STYLE" = "off" ] && return
    local color out ttl
    color=$(color_for_pct "$pct")
    out="${dim}${label}${reset} "
    case "$RATE_STYLE" in
        bar_pct) out+="$(build_bar "$pct" "$BAR_WIDTH") ${color}${pct}%${reset}" ;;
        pct)     out+="${color}${pct}%${reset}" ;;
        bar)     out+="$(build_bar "$pct" "$BAR_WIDTH")" ;;
    esac
    if [ "$SHOW_TTL" = "true" ] && [ -n "$epoch" ] && [ "$epoch" != "null" ]; then
        ttl=$(format_ttl_epoch "$epoch")
        [ -n "$ttl" ] && out+=" ${white}${ttl}${reset}"
    fi
    printf "%b" "$out"
}

# ── Segment renderer ─────────────────────────────────────
render_segment() {
    local name="$1"
    case "$name" in
        model)
            printf "%b" "${blue}${model_name}${reset}"
            ;;
        context_pct)
            printf "%b" "${pct_color}${pct_used}%${reset}"
            ;;
        tokens)
            [ "$session_total" -gt 0 ] || return
            if [ "$TOKEN_STYLE" = "in_out" ]; then
                local in_fmt out_fmt
                in_fmt=$(format_tokens "$session_in")
                out_fmt=$(format_tokens "$session_out")
                printf "%b" "$(lbl tokens)${white}↑${in_fmt} ↓${out_fmt}${reset}"
            else
                printf "%b" "$(lbl tokens)${white}$(format_tokens "$session_total")${reset}"
            fi
            ;;
        cost)
            [ "$session_total" -gt 0 ] || return
            local c
            c=$(estimate_cost)
            [ -n "$c" ] || return
            printf "%b" "$(lbl cost)${white}${c}${reset}"
            ;;
        cache_pct)
            [ "$current" -gt 0 ] || return
            local cc
            cc=$(color_for_cache_pct "$cache_pct")
            printf "%b" "$(lbl cache)${cc}${cache_pct}%${reset}"
            ;;
        effort)
            printf "%b" "$(lbl effort)${effort_color}${effort}${reset}"
            ;;
        cwd)
            printf "%b" "${white}${cwd_basename}${reset}"
            ;;
        git_branch)
            [ -n "$git_branch" ] || return
            local display_branch="$git_branch"
            if [ "${#git_branch}" -gt "${GIT_BRANCH_MAX:-20}" ]; then
                display_branch="${git_branch:0:$(( ${GIT_BRANCH_MAX:-20} - 1 ))}…"
            fi
            printf "%b" "${green}${display_branch}${reset}"
            ;;
        git_status)
            [ -n "$git_info" ] || return
            printf "%b" "$git_info"
            ;;
        rate_5h)
            render_rate "5h" "$five_pct" "$five_reset_epoch"
            ;;
        rate_7d)
            render_rate "7d" "$seven_pct" "$seven_reset_epoch"
            ;;
        avg_tokens)
            [ -n "$avg_tokens_per_msg" ] && [ "$avg_tokens_per_msg" -gt 0 ] 2>/dev/null || return
            local fmt pct_of_avg pct_str
            fmt=$(format_tokens "$avg_tokens_per_msg")
            if [ -n "$all_sessions_avg" ] && [ "$all_sessions_avg" -gt 0 ] 2>/dev/null; then
                pct_of_avg=$(awk "BEGIN{printf \"%.2f\", $avg_tokens_per_msg * 100 / $all_sessions_avg}")
                all_avg_fmt=$(format_tokens "$all_sessions_avg")
                pct_str=" ${dim}(${pct_of_avg}% of ${all_avg_fmt})${reset}"
            fi
            printf "%b" "$(lbl tkns/msg)${white}${fmt}${reset}${pct_str}"
            ;;
        exhaust_5h)
            [ -n "$five_exhaust" ] || return
            local color
            color=$(color_for_pct "${five_pct:-0}")
            printf "%b" "${dim}5h out in${reset} ${color}${five_exhaust}${reset}"
            ;;
        exhaust_7d)
            [ -n "$seven_exhaust" ] || return
            local color
            color=$(color_for_pct "${seven_pct:-0}")
            printf "%b" "${dim}7d out in${reset} ${color}${seven_exhaust}${reset}"
            ;;
        downtime)
            [ -n "$five_reset_epoch" ] && [ "${five_exhaust_secs:-0}" -gt 0 ] 2>/dev/null || return
            local now time_to_reset downtime_secs d_hrs d_mins
            now=$(date +%s)
            time_to_reset=$(( five_reset_epoch - now ))
            downtime_secs=$(( time_to_reset - five_exhaust_secs ))
            if [ "$downtime_secs" -le 0 ] 2>/dev/null; then
                printf "%b" "${green}no downtime${reset}"
            else
                d_hrs=$(( downtime_secs / 3600 ))
                d_mins=$(( (downtime_secs % 3600) / 60 ))
                local dt_str color
                [ "$d_hrs" -gt 0 ] && dt_str="${d_hrs}h${d_mins}m" || dt_str="${d_mins}m"
                [ "$downtime_secs" -gt 3600 ] && color="$red" || color="$orange"
                printf "%b" "${dim}downtime:${reset} ${color}${dt_str}${reset} ${dim}at this rate${reset}"
            fi
            ;;
        hook)
            [ -z "$hook_event_name" ] && return
            local display="${hook_tool_name:-$hook_event_name}"
            if [ -n "$hook_scripts" ]; then
                display+=" ${dim}(${hook_scripts})${reset}"
            fi
            printf "%b" "$(lbl hooks)${white}${display}${reset}"
            ;;
        hookify_rule)
            [ "$hookify_configured" != "true" ] && return
            [ -z "$hookify_match_text" ] && return
            local rule_color="$yellow"
            echo "$hookify_match_text" | grep -q "(block)" && rule_color="$red"
            local rule_count
            rule_count=$(echo "$hookify_match_text" | tr ',' '\n' | grep -c .)
            printf "%b" "${dim}rule:${reset}${rule_color}${rule_count}${reset}"
            ;;
        session_timer)
            [ "${session_first_ts:-0}" -gt 0 ] 2>/dev/null || return
            local now elapsed_secs h m timer_str color
            now=$(date +%s)
            elapsed_secs=$(( now - session_first_ts ))
            [ "$elapsed_secs" -le 60 ] 2>/dev/null && return
            h=$(( elapsed_secs / 3600 ))
            m=$(( (elapsed_secs % 3600) / 60 ))
            if [ "$h" -gt 0 ]; then
                timer_str="${h}h${m}m"
                color="$orange"
            else
                timer_str="${m}m"
                color="$white"
            fi
            printf "%b" "$(lbl session)${color}${timer_str}${reset}"
            ;;
        gsd_phase)
            [ -z "$gsd_phase_num" ] && return
            local status_str="" color
            color="$white"
            case "$gsd_status" in
                executing)  color="$blue";   status_str=" ${dim}[exec]${reset}"   ;;
                verifying)  color="$yellow"; status_str=" ${dim}[verify]${reset}" ;;
                complete)   color="$green";  status_str=" ${dim}[done]${reset}"   ;;
                planning)   color="$dim";    status_str=" ${dim}[plan]${reset}"   ;;
            esac
            printf "%b" "$(lbl phase)${color}${gsd_phase_num}${reset}${status_str}"
            ;;
        gsd_progress)
            [ -z "$gsd_completed_phases" ] && return
            local phases_str plans_str=""
            phases_str="${gsd_completed_phases}/${gsd_total_phases}"
            if [ -n "$gsd_completed_plans" ]; then
                plans_str=" ${dim}${gsd_completed_plans}/${gsd_total_plans}p${reset}"
            fi
            printf "%b" "$(lbl gsd)${white}${phases_str}${dim}ph${reset}${plans_str}"
            ;;
        worktree)
            [ -z "$worktree_name" ] && return
            printf "%b" "${dim}wt:${reset}${yellow}${worktree_name}${reset}"
            ;;
        plugins)
            [ -z "$plugins_count" ] || [ "${plugins_count:-0}" -eq 0 ] 2>/dev/null && return
            printf "%b" "$(lbl plugins)${white}${plugins_count}${reset}"
            ;;
        agents)
            [ -z "$session_id" ] && return
            local tracker_file="/tmp/claude-agent-tracker-${session_id}.json"
            [ -f "$tracker_file" ] || return
            local active_count active_types total_done
            active_count=$(jq '[.agents[] | select(.status=="running")] | length' "$tracker_file" 2>/dev/null)
            total_done=$(jq '[.agents[] | select(.status=="done")] | length' "$tracker_file" 2>/dev/null)
            if [ "${active_count:-0}" -gt 0 ] 2>/dev/null; then
                active_types=$(jq -r '[.agents[] | select(.status=="running") | .type] | join(",")' "$tracker_file" 2>/dev/null)
                printf "%b" "$(lbl agents)${blue}${active_count}${reset} ${dim}(${active_types})${reset}"
            elif [ "${total_done:-0}" -gt 0 ] 2>/dev/null; then
                printf "%b" "$(lbl agents)${dim}${total_done} done${reset}"
            fi
            ;;
        *)
            ;;
    esac
}

# ── Line builder ─────────────────────────────────────────
build_line() {
    local segments="$1"
    local line="" rendered prev_seg=""
    for seg in $segments; do
        rendered=$(render_segment "$seg")
        [ -z "$rendered" ] && { prev_seg="$seg"; continue; }
        if [ "$seg" = "git_status" ] && [ "$prev_seg" = "git_branch" ]; then
            line+=" ${rendered}"
        else
            [ -n "$line" ] && line+="$sep"
            line+="$rendered"
        fi
        prev_seg="$seg"
    done
    printf "%s" "$line"
}

# ── Assemble output ──────────────────────────────────────
out1=$(build_line "$LINE1")
out2=$(build_line "$LINE2")
out3=$(build_line "$LINE3")

content_lines=()
[ -n "$out1" ] && content_lines+=("$out1")
[ -n "$out2" ] && content_lines+=("$out2")
[ -n "$out3" ] && content_lines+=("$out3")

if [ "${CC_UI_LINE:-0}" -gt 0 ] 2>/dev/null; then
    result=""
    insert_pos=$(( CC_UI_LINE - 1 ))
    ci=0
    for ((row=0; row < ${#content_lines[@]} + 1; row++)); do
        if [ "$row" -eq "$insert_pos" ]; then
            [ -n "$result" ] && result+="\n"
        else
            if [ "$ci" -lt "${#content_lines[@]}" ]; then
                [ -n "$result" ] && result+="\n"
                result+="${content_lines[$ci]}"
                ci=$(( ci + 1 ))
            fi
        fi
    done
else
    result=""
    for line in "${content_lines[@]}"; do
        [ -n "$result" ] && result+="\n"
        result+="$line"
    done
fi

printf "%b" "$result"
exit 0
