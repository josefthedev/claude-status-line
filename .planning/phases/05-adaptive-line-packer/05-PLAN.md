---
plan: 05
phase: 05
wave: 1
title: Adaptive Line Packer
autonomous: true
files_modified:
  - lib/packer.py
  - tests/test_packer.py
must_haves:
  - lib/packer.py exists with pack_lines() function
  - pack_lines() drops segments that exceed budget (never truncates)
  - git_status attaches to git_branch with space not separator
  - None segments are skipped silently
  - tests/test_packer.py passes with python3 -m unittest tests.test_packer
---

<objective>
Implement greedy segment packer in lib/packer.py that packs rendered segments into lines within a visible-width budget.

Purpose: Core layout engine for the Python statusline — segments that don't fit are dropped (never truncated), solving the cli-truncate bug.
Output: lib/packer.py, tests/test_packer.py
</objective>

<context>
@lib/ansi.py (visible_width function)
@lib/segments.py (SegmentRenderer.render() -> str | None)
@tests/test_segments.py (unittest.TestCase style reference)
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Implement lib/packer.py</name>
  <read_first>lib/ansi.py, lib/segments.py</read_first>
  <files>lib/packer.py</files>
  <action>
Create lib/packer.py with the following complete implementation:

```python
# lib/packer.py
from lib.ansi import visible_width

DIM = '\033[2m'
RESET = '\033[0m'

def pack_lines(
    line_defs: list,      # list of lists of segment names
    renderer,             # SegmentRenderer instance
    budget: int,          # max visible chars per line
    sep_char: str = '│',  # from config SEP_CHAR
) -> list:               # list of str, one per line_def
    sep = f' {DIM}{sep_char}{RESET} '
    sep_width = visible_width(sep)
    result = []
    for names in line_defs:
        line = ''
        prev_name = None
        for name in names:
            rendered = renderer.render(name)
            if rendered is None:
                continue
            seg_width = visible_width(rendered)
            if not line:
                # First segment on line
                if seg_width <= budget:
                    line = rendered
                    prev_name = name
            else:
                # Attach git_status directly to git_branch
                if name == 'git_status' and prev_name == 'git_branch':
                    candidate = line + ' ' + rendered
                    if visible_width(candidate) <= budget:
                        line = candidate
                        prev_name = name
                else:
                    candidate = line + sep + rendered
                    if visible_width(candidate) <= budget:
                        line = candidate
                        prev_name = name
                # else: drop segment silently
        result.append(line)
    return result
```

Key design points:
- Greedy left-to-right packing: first segment that fits starts the line, subsequent segments added with separator if they fit
- git_status after git_branch uses space instead of dim separator (special attachment rule)
- None from renderer.render() skipped without affecting prev_name tracking
- Segments that exceed remaining budget are silently dropped
- Empty lines (no segments fit) return empty string, not None
  </action>
  <verify>
    <automated>cd /home/josef/workspace-linux/claude-status-line && python3 -c "from lib.packer import pack_lines; print('import ok')"</automated>
  </verify>
  <acceptance_criteria>
    - `grep -q "def pack_lines" lib/packer.py` succeeds
    - `grep -q "visible_width" lib/packer.py` succeeds
    - `grep -q "git_status" lib/packer.py` succeeds
    - `grep -q "git_branch" lib/packer.py` succeeds
  </acceptance_criteria>
  <done>lib/packer.py exists, imports cleanly, contains pack_lines() with greedy packing, git attachment rule, and None-skipping</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Create tests/test_packer.py</name>
  <read_first>lib/packer.py, tests/test_segments.py, lib/ansi.py</read_first>
  <files>tests/test_packer.py</files>
  <behavior>
    - Test normal packing: 2 segments fit within budget, output contains both with separator
    - Test budget overflow: segment dropped when it would exceed budget
    - Test git_status attachment: git_status after git_branch joined with space, not separator
    - Test all-None segments: line_def where renderer returns None for all names produces empty string
    - Test empty line_def: empty list produces empty string
    - Test None skipped silently: None segment between two valid segments doesn't break packing
  </behavior>
  <action>
Create tests/test_packer.py using unittest.TestCase style (matching test_segments.py conventions). Use a mock renderer that returns predefined values per segment name. Use plain strings (no ANSI) for predictable visible_width calculations in most tests. Include one test with ANSI to verify width calculation uses visible_width correctly.

Mock renderer pattern:
```python
class MockRenderer:
    def __init__(self, segments: dict):
        self._segments = segments
    def render(self, name: str):
        return self._segments.get(name)
```

Test cases:
1. TestPackLines.test_two_segments_fit — budget=40, two short segments, both appear in output separated by separator
2. TestPackLines.test_segment_dropped_over_budget — budget=15, first segment 10 chars, second 10 chars, only first appears
3. TestPackLines.test_git_status_attachment — git_branch then git_status, output has space not dim separator between them
4. TestPackLines.test_all_none — all segments return None, result is empty string
5. TestPackLines.test_empty_line_def — empty names list, result is empty string
6. TestPackLines.test_none_skipped — seg_a (None), seg_b (valid), seg_c (valid) — output has seg_b and seg_c
7. TestPackLines.test_multiple_lines — two line_defs, returns list of length 2
8. TestPackLines.test_first_segment_exceeds_budget — single segment wider than budget, line is empty string
  </action>
  <verify>
    <automated>cd /home/josef/workspace-linux/claude-status-line && python3 -m unittest tests.test_packer -v</automated>
  </verify>
  <acceptance_criteria>
    - `python3 -m unittest tests.test_packer` exits 0
    - `grep -c "def test_" tests/test_packer.py` shows at least 8 tests
    - `grep -q "git_status" tests/test_packer.py` succeeds
    - `grep -q "MockRenderer" tests/test_packer.py` succeeds
  </acceptance_criteria>
  <done>All 8+ tests pass, covering normal packing, overflow drops, git attachment, None handling, empty cases</done>
</task>

</tasks>

<verification>
```bash
cd /home/josef/workspace-linux/claude-status-line
python3 -m unittest tests.test_packer -v
python3 -c "from lib.packer import pack_lines; print('pack_lines imported successfully')"
```
</verification>

<success_criteria>
- lib/packer.py contains pack_lines() function
- pack_lines() greedy-packs segments, drops on overflow, never truncates
- git_status attaches to git_branch with space (not separator)
- None segments skipped silently
- python3 -m unittest tests.test_packer passes all tests
</success_criteria>

<output>
After completion, create `.planning/phases/05-adaptive-line-packer/05-SUMMARY.md`
</output>
