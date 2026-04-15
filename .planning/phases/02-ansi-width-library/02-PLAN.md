---
phase: 02-ansi-width-library
plan: 01
type: tdd
wave: 1
depends_on: []
files_modified:
  - lib/__init__.py
  - lib/ansi.py
  - tests/test_ansi.py
autonomous: true
requirements:
  - ANSI-STRIP-01
  - ANSI-WIDTH-01
  - ANSI-TRUNC-01

must_haves:
  truths:
    - "strip_ansi() removes all ANSI/CSI/OSC escape sequences, leaving plain text"
    - "visible_width() returns the printable character count, ignoring escape codes"
    - "truncate_ansi() never cuts mid-sequence, appends suffix and reset when truncating"
    - "All 11 test cases in tests/test_ansi.py pass with python3 tests/test_ansi.py"
  artifacts:
    - path: "lib/__init__.py"
      provides: "Makes lib/ a Python package"
    - path: "lib/ansi.py"
      provides: "strip_ansi, visible_width, truncate_ansi"
      exports: ["strip_ansi", "visible_width", "truncate_ansi"]
    - path: "tests/test_ansi.py"
      provides: "11 test functions covering plain, color, RGB, dim, 256-color, truncation edge cases"
  key_links:
    - from: "tests/test_ansi.py"
      to: "lib/ansi.py"
      via: "from lib.ansi import strip_ansi, visible_width, truncate_ansi"
      pattern: "from lib\\.ansi import"
---

<objective>
Implement the ANSI-aware string utility library: strip escape sequences, calculate visible width, and truncate safely without cutting mid-sequence.

Purpose: All downstream phases (segments, packer, statusline) need accurate visible-width arithmetic. This library provides the single source of truth.
Output: lib/__init__.py, lib/ansi.py, tests/test_ansi.py — all tests passing.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Write failing tests then implement lib/ansi.py</name>
  <files>lib/__init__.py, lib/ansi.py, tests/test_ansi.py</files>
  <behavior>
    RED — create tests first, confirm ImportError:
    - test_strip_plain: strip_ansi("hello") == "hello"
    - test_strip_color: strip_ansi("\033[31mhello\033[0m") == "hello"
    - test_strip_rgb: strip_ansi("\033[38;2;0;153;255mhello\033[0m") == "hello"
    - test_strip_dim: strip_ansi("\033[2mhello\033[22m") == "hello"
    - test_strip_256: strip_ansi("\033[38;5;208mhello\033[0m") == "hello"
    - test_visible_width_plain: visible_width("hello") == 5
    - test_visible_width_colored: visible_width("\033[31mhello\033[0m") == 5
    - test_visible_width_unicode: visible_width("│") == 1
    - test_truncate_ansi_no_cut: truncate_ansi("\033[31mhi\033[0m", 10) == "\033[31mhi\033[0m"
    - test_truncate_ansi_cuts_at_visible: visible_width(truncate_ansi("\033[31mhello world\033[0m", 5)) &lt;= 5 AND "\033[0m" in result
    - test_truncate_ansi_mid_escape: visible_width(truncate_ansi("abc\033[38;2;0;153;255mdef\033[0m", 4)) &lt;= 4

    GREEN — implement lib/ansi.py so all 11 tests pass.
  </behavior>
  <action>
Step 1 (RED): Create the package and test file.

Create lib/__init__.py as an empty file.

Create tests/test_ansi.py with this exact content:

```python
import sys, os; sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from lib.ansi import strip_ansi, visible_width, truncate_ansi

def test_strip_plain():
    assert strip_ansi("hello") == "hello"

def test_strip_color():
    assert strip_ansi("\033[31mhello\033[0m") == "hello"

def test_strip_rgb():
    assert strip_ansi("\033[38;2;0;153;255mhello\033[0m") == "hello"

def test_strip_dim():
    assert strip_ansi("\033[2mhello\033[22m") == "hello"

def test_strip_256():
    assert strip_ansi("\033[38;5;208mhello\033[0m") == "hello"

def test_visible_width_plain():
    assert visible_width("hello") == 5

def test_visible_width_colored():
    assert visible_width("\033[31mhello\033[0m") == 5

def test_visible_width_unicode():
    assert visible_width("│") == 1

def test_truncate_ansi_no_cut():
    s = "\033[31mhi\033[0m"
    assert truncate_ansi(s, 10) == s

def test_truncate_ansi_cuts_at_visible():
    s = "\033[31mhello world\033[0m"
    result = truncate_ansi(s, 5)
    assert visible_width(result) <= 5
    assert "\033[0m" in result  # reset appended

def test_truncate_ansi_mid_escape():
    # Must not cut in the middle of an escape sequence
    s = "abc\033[38;2;0;153;255mdef\033[0m"
    result = truncate_ansi(s, 4)
    assert visible_width(result) <= 4

if __name__ == "__main__":
    import unittest
    # Run tests defined above using manual discovery
    tests = [v for k, v in globals().items() if k.startswith("test_")]
    passed = failed = 0
    for t in tests:
        try:
            t()
            print(f"  PASS {t.__name__}")
            passed += 1
        except Exception as e:
            print(f"  FAIL {t.__name__}: {e}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)
```

Run `python3 tests/test_ansi.py` — expect ImportError (RED confirmed).

Step 2 (GREEN): Create lib/ansi.py with this exact content:

```python
# lib/ansi.py
"""ANSI escape sequence stripping and visible-width calculation.

All width calculations use visible (printable) character count only.
Unicode chars assumed to be single-width (sufficient for our use case).
"""

import re

# Matches all CSI sequences: ESC [ ... final-byte
# Also matches OSC sequences: ESC ] ... ST
# Also matches simple ESC + single char (e.g. ESC[s, ESC[u)
_ANSI_ESCAPE = re.compile(
    r'\033'           # ESC
    r'(?:'
    r'\[[0-9;]*[A-Za-z]'   # CSI: ESC [ params final-byte
    r'|'
    r'\][^\033]*(?:\033\\|\007)'  # OSC: ESC ] ... ST or BEL
    r'|'
    r'[@-_]'          # ESC + single char (Fe sequences)
    r')'
)


def strip_ansi(s: str) -> str:
    """Remove all ANSI/CSI/OSC escape sequences from s."""
    return _ANSI_ESCAPE.sub('', s)


def visible_width(s: str) -> int:
    """Return the visible (printable) width of s, ignoring escape codes."""
    return len(strip_ansi(s))


def truncate_ansi(s: str, max_width: int, suffix: str = '…') -> str:
    """Truncate s to at most max_width visible chars.

    Preserves ANSI escape sequences (never cuts mid-sequence).
    Appends suffix (default '…') if truncation occurs.
    Always appends reset (ESC[0m) after truncation.
    """
    if visible_width(s) <= max_width:
        return s

    suffix_width = visible_width(suffix)
    target = max_width - suffix_width
    if target <= 0:
        return suffix[:max_width]

    result = []
    visible = 0
    i = 0
    while i < len(s):
        # Check if we're at an escape sequence
        m = _ANSI_ESCAPE.match(s, i)
        if m:
            result.append(m.group())
            i = m.end()
            continue
        # Regular character
        if visible >= target:
            break
        result.append(s[i])
        visible += 1
        i += 1

    return ''.join(result) + suffix + '\033[0m'
```

Run `python3 tests/test_ansi.py` — all 11 tests must PASS.
  </action>
  <verify>
    <automated>cd /home/josef/workspace-linux/claude-status-line && python3 tests/test_ansi.py</automated>
  </verify>
  <done>11 passed, 0 failed printed to stdout; exit code 0.</done>
</task>

<task type="auto">
  <name>Task 2: Commit the library</name>
  <files>lib/__init__.py, lib/ansi.py, tests/test_ansi.py</files>
  <action>
Stage and commit the three files:

```bash
cd /home/josef/workspace-linux/claude-status-line
git add lib/__init__.py lib/ansi.py tests/test_ansi.py
git commit -m "feat: ANSI-aware width calculation library"
```
  </action>
  <verify>
    <automated>cd /home/josef/workspace-linux/claude-status-line && git log --oneline -1</automated>
  </verify>
  <done>Git log shows the commit "feat: ANSI-aware width calculation library" as HEAD.</done>
</task>

</tasks>

<verification>
Run the full test suite to confirm no regressions:

```bash
cd /home/josef/workspace-linux/claude-status-line && python3 tests/test_ansi.py
```

Verify the three files exist:

```bash
ls /home/josef/workspace-linux/claude-status-line/lib/__init__.py \
   /home/josef/workspace-linux/claude-status-line/lib/ansi.py \
   /home/josef/workspace-linux/claude-status-line/tests/test_ansi.py
```
</verification>

<success_criteria>
- lib/__init__.py exists (empty, makes lib/ a Python package)
- lib/ansi.py exports strip_ansi, visible_width, truncate_ansi using the specified regex and logic
- tests/test_ansi.py contains all 11 test functions and exits 0
- Commit "feat: ANSI-aware width calculation library" exists in git history
</success_criteria>

<output>
After completion, create `.planning/phases/02-ansi-width-library/02-01-SUMMARY.md` documenting:
- Files created
- Regex pattern used (_ANSI_ESCAPE covering CSI, OSC, Fe sequences)
- All three function signatures
- Test count and result
</output>
