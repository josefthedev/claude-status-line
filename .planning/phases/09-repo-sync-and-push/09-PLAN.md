---
plan: 09
phase: 09
wave: 1
title: Repo Sync and Push
autonomous: true
files_modified:
  - statusline.sh
  - statusline.conf
  - change_log.md
must_haves:
  - statusline.sh matches ~/.claude/statusline.sh (diff returns empty)
  - statusline.conf contains OVERRIDE_DIMCOLOR
  - statusline.conf contains MAX_LINES
  - change_log.md contains 2026-04-16 entry
  - git log shows final sync commit
  - git push exits 0
---

<objective>
Sync installed statusline.sh into repo, add Python renderer config keys to statusline.conf, update change_log.md, commit and push everything.

Purpose: Final phase — make repo match deployed state and document the Python rewrite milestone.
Output: Clean commit pushed to origin/master with all files in sync.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/ROADMAP.md
@statusline.conf
@change_log.md
</context>

<tasks>

<task type="auto">
  <name>Task 1: Sync statusline.sh and update statusline.conf</name>
  <files>statusline.sh, statusline.conf</files>
  <action>
1. Copy installed statusline.sh into repo:
```bash
cp ~/.claude/statusline.sh ./statusline.sh
```

2. Append Python renderer settings to statusline.conf (after the COST ESTIMATION section at the end of the file):
```bash
cat >> statusline.conf << 'CONF'

# ─────────────────────────────────────────────────────────
# PYTHON RENDERER SETTINGS
# ─────────────────────────────────────────────────────────
# These keys are used by statusline.py (the Python renderer).
# They have no effect on the bash statusline.sh.

# dimColor compensation — prefix each line with \033[22m to reset
# the dim attribute that Claude Code applies to statusline output.
# OVERRIDE_DIMCOLOR=true

# Maximum number of output lines (1–3). The Python renderer
# calculates per-line budgets as terminal_width // MAX_LINES.
# MAX_LINES=3
CONF
```
  </action>
  <verify>
```bash
diff ~/.claude/statusline.sh ./statusline.sh && echo "MATCH" || echo "DIFFER"
grep -q "OVERRIDE_DIMCOLOR" statusline.conf && echo "HAS_DIMCOLOR"
grep -q "MAX_LINES" statusline.conf && echo "HAS_MAXLINES"
```
All three checks print their success string.
  </verify>
  <done>statusline.sh identical to installed version; statusline.conf contains both new keys with documentation comments.</done>
</task>

<task type="auto">
  <name>Task 2: Update change_log.md, commit, and push</name>
  <files>change_log.md</files>
  <action>
1. Append a new entry to change_log.md after the existing content:
```bash
cat >> change_log.md << 'LOG'
## 2026-04-16 — Python statusline rewrite complete

- Phases 1-8: built Python renderer (statusline.py), ANSI library (lib/ansi.py), config parser (lib/config.py), segment renderers (lib/segments.py), adaptive line packer (lib/packer.py)
- Safe install/uninstall system (install.sh, uninstall.sh) with timestamped backups
- Tmux integration (tmux/statusline.sh) for CC session info in tmux status-right
- Synced statusline.sh from ~/.claude/ into repo
- Added OVERRIDE_DIMCOLOR and MAX_LINES Python renderer keys to statusline.conf
LOG
```

2. Stage and commit all changes:
```bash
git add statusline.sh statusline.conf change_log.md
git commit -m "sync: repo matches installed state, add Python config keys, update changelog"
```

3. Push to remote:
```bash
git push origin master
```
  </action>
  <verify>
```bash
git log --oneline -1 | grep -q "sync:" && echo "COMMITTED"
git diff origin/master..HEAD --stat | wc -l  # should be 0 after push
```
  </verify>
  <done>All changes committed in a single commit and pushed to origin/master. git status is clean.</done>
</task>

</tasks>

<verification>
```bash
diff ~/.claude/statusline.sh ./statusline.sh
grep "OVERRIDE_DIMCOLOR" statusline.conf
grep "MAX_LINES" statusline.conf
grep "2026-04-16" change_log.md
git log --oneline -1
git status --short  # should be empty
```
</verification>

<success_criteria>
- `diff ~/.claude/statusline.sh ./statusline.sh` produces no output
- statusline.conf contains documented OVERRIDE_DIMCOLOR and MAX_LINES keys
- change_log.md has a 2026-04-16 entry summarizing the Python rewrite
- git log shows the sync commit
- git status is clean, push succeeded
</success_criteria>

<output>
After completion, create `.planning/phases/09-repo-sync-and-push/09-SUMMARY.md`
</output>
