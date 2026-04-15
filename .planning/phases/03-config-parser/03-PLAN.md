---
plan: 03
phase: 03
wave: 1
title: Config Parser Implementation
autonomous: true
files_modified:
  - lib/config.py
  - tests/test_config.py
must_haves:
  - lib/config.py exists with load_config() function
  - tests/test_config.py passes with python3 -m unittest tests.test_config
  - load_config() returns dict with normalized types
  - Missing config file returns empty dict without error
  - Per-project .claude/statusline.conf values override base config
depends_on: []
requirements:
  - CONFIG-01
---

<objective>
Implement `lib/config.py` — a stdlib-only parser for bash `KEY=value` config files that returns
a normalized Python dict. Then write `tests/test_config.py` to verify every parsing rule.

Purpose: Phases 4 (segments) and 6 (main entry point) both import `load_config()`. Getting the
contract right here prevents cascading bugs in downstream phases.

Output:
- `lib/config.py` — `load_config(cwd=None) -> dict`
- `tests/test_config.py` — full unit test coverage
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/03-config-parser/03-CONTEXT.md

<!-- Key interface this plan produces — referenced by phases 4 and 6 -->
<interfaces>
From lib/config.py (to be created):
```python
def load_config(cwd: str = None) -> dict:
    """Load ~/.claude/statusline.conf then merge <cwd>/.claude/statusline.conf.

    Project values override base values. Missing files are silently skipped.
    Returns normalized dict: int, bool, list, or str per value.

    Args:
        cwd: Project directory to look for .claude/statusline.conf override.
             Defaults to os.getcwd() when None.

    Returns:
        dict with string keys and normalized typed values.
    """
```
</interfaces>

Real config keys in use (from statusline.conf):
- LINE1, LINE2, LINE3 — space-separated segment lists (normalize to list)
- SHOW_LABELS, SHOW_TTL — booleans ("true"/"false")
- BAR_WIDTH, GIT_BRANCH_MAX, CC_UI_LINE, MAX_LINES — integers
- RATE_STYLE, TOKEN_STYLE, SEP_CHAR — plain strings
- COLOR_* — ANSI color strings (keep as string, not list even if they contain commas)
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Implement lib/config.py</name>
  <files>lib/config.py</files>

  <read_first>
    - lib/ansi.py — see module docstring and code style to match conventions
    - statusline.conf — study real key/value shapes before writing parser
    - lib/__init__.py — confirm package marker exists (no action needed)
  </read_first>

  <behavior>
    Parsing rules (all tested in Task 2):
    - Lines matching `^(\w+)\s*=\s*(.*)$` are parsed; all others silently skipped
    - Strip leading/trailing whitespace from the raw value
    - Inline comments: strip ` #...` suffix (space + hash) ONLY when value is not quoted
    - Quoted values: if raw value starts with `"` or `'`, strip the matching outer quotes,
      then strip inline comments from the inner content (after unquoting)
    - Empty value (after stripping) → empty string (not normalized further)

    Type normalization applied after stripping/unquoting (in priority order):
    1. Try `int(value)` — if succeeds, return int
    2. If lowercased value is one of `true yes` → return `True`
    3. If lowercased value is one of `false no` → return `False`
    4. If `','` in value → split on `','`, strip each part, return list of strings
    5. Otherwise → return the string as-is

    Config loading:
    - Base path: `os.path.expanduser("~/.claude/statusline.conf")`
    - Override path: `os.path.join(cwd or os.getcwd(), ".claude", "statusline.conf")`
    - `_parse_file(path) -> dict` — reads one file, returns dict (empty dict if file missing)
    - `load_config(cwd=None) -> dict` — calls `_parse_file` for base, then override;
      merges with `base | override` (override wins)
  </behavior>

  <action>
    Create `lib/config.py` with the following structure:

    ```python
    # lib/config.py
    """Parse bash KEY=value config files into normalized Python dicts.

    Supports ~/.claude/statusline.conf as base config and
    <cwd>/.claude/statusline.conf as per-project override (project wins).
    No external dependencies — stdlib only.
    """

    import os
    import re

    # Matches KEY=value lines; ignores comments, blank lines, section headers
    _LINE_RE = re.compile(r'^(\w+)\s*=\s*(.*)$')

    # Inline comment: space+hash not inside quotes (applied to already-unquoted value)
    _COMMENT_RE = re.compile(r'\s+#.*$')


    def _strip_comment(s: str) -> str:
        """Remove trailing inline comment ( # ...) from an already-unquoted value."""
        return _COMMENT_RE.sub('', s)


    def _unquote(raw: str) -> str:
        """Strip matching outer quotes and trailing inline comment from raw value.

        If raw starts with ' or ", treat everything inside as the value; strip that
        same quote char at the end (if present) and then remove inline comments
        from the inner string. If not quoted, strip inline comments directly.
        """
        raw = raw.strip()
        if raw and raw[0] in ('"', "'"):
            quote = raw[0]
            # Find closing quote
            end = raw.rfind(quote, 1)
            if end > 0:
                inner = raw[1:end]
            else:
                inner = raw[1:]  # Unclosed quote — take everything after opening
            return _strip_comment(inner).strip()
        return _strip_comment(raw).strip()


    def _normalize(value: str):
        """Apply type normalization to a stripped string value.

        Priority: int > bool keyword > list (comma) > str.
        """
        if value == '':
            return value
        try:
            return int(value)
        except ValueError:
            pass
        lower = value.lower()
        if lower in ('true', 'yes'):
            return True
        if lower in ('false', 'no'):
            return False
        if ',' in value:
            return [part.strip() for part in value.split(',')]
        return value


    def _parse_file(path: str) -> dict:
        """Parse a single KEY=value file. Returns {} if file is missing or unreadable."""
        try:
            with open(path, encoding='utf-8') as f:
                lines = f.readlines()
        except (FileNotFoundError, PermissionError):
            return {}
        result = {}
        for line in lines:
            m = _LINE_RE.match(line.rstrip('\n'))
            if not m:
                continue
            key, raw = m.group(1), m.group(2)
            value = _unquote(raw)
            result[key] = _normalize(value)
        return result


    def load_config(cwd: str = None) -> dict:
        """Load base config then merge per-project override (project wins).

        Args:
            cwd: Project directory containing optional .claude/statusline.conf.
                 Defaults to os.getcwd() when None.

        Returns:
            Merged dict with normalized types.
        """
        base_path = os.path.expanduser('~/.claude/statusline.conf')
        project_dir = cwd if cwd is not None else os.getcwd()
        override_path = os.path.join(project_dir, '.claude', 'statusline.conf')
        base = _parse_file(base_path)
        override = _parse_file(override_path)
        return {**base, **override}
    ```

    Style notes (match lib/ansi.py conventions):
    - Module-level docstring explaining purpose
    - Private helpers prefixed with `_`
    - Type hints on public functions
    - Inline comments only where non-obvious
  </action>

  <verify>
    <automated>cd /home/josef/workspace-linux/claude-status-line && python3 -c "from lib.config import load_config, _parse_file, _normalize, _unquote; print('imports ok')"</automated>
  </verify>

  <done>
    - `lib/config.py` exists and imports cleanly from the package
    - `load_config()` callable with no args, returns a dict
    - `_parse_file('/nonexistent')` returns `{}` without raising
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Write tests/test_config.py</name>
  <files>tests/test_config.py</files>

  <read_first>
    - lib/config.py — read the implementation written in Task 1 before writing tests
    - statusline.conf — extract real key/value pairs to use as representative fixtures
    - tests/run.sh — confirm test discovery command (`python3 -m unittest discover tests/`)
  </read_first>

  <behavior>
    Test cases required (each as a separate test method):

    _parse_file behavior:
    - Missing file returns empty dict
    - Comment-only file (lines starting with #) returns empty dict
    - Blank lines skipped
    - KEY=value with no quotes parsed correctly
    - KEY="value" (double quotes) strips quotes
    - KEY='value' (single quotes) strips quotes
    - KEY=value # comment strips the inline comment
    - KEY="value" # comment (quoted with trailing comment) strips comment but not the value
    - KEY=42 parsed as int 42
    - KEY=true parsed as bool True
    - KEY=false parsed as bool False
    - KEY=yes parsed as bool True
    - KEY=no parsed as bool False
    - KEY=a,b,c parsed as list ['a', 'b', 'c']
    - KEY="a,b,c" (quoted comma list) parsed as list ['a', 'b', 'c']
    - KEY= (empty value) returns empty string ''
    - Lines without = are ignored
    - KEY with leading/trailing spaces around = (KEY  =  value) parsed correctly

    load_config behavior:
    - No config files present → returns {}
    - Only base config present → returns base values
    - Only project override present → returns override values
    - Both present → project values win for conflicting keys, base values kept for non-conflicting

    Real-world key smoke test:
    - Parse a multi-line config string matching the shape of statusline.conf;
      verify LINE1 becomes a list, BAR_WIDTH becomes int 6, SHOW_LABELS becomes True

    Use `unittest.mock.patch('builtins.open', ...)` and `tempfile.TemporaryDirectory`
    for file-based tests. Do NOT rely on the real `~/.claude/statusline.conf` being present.
  </behavior>

  <action>
    Create `tests/test_config.py`. Structure:

    ```python
    """Tests for lib/config.py — config file parser."""

    import os
    import tempfile
    import unittest

    from lib.config import _normalize, _parse_file, _unquote, load_config


    class TestNormalize(unittest.TestCase):
        def test_int(self): self.assertEqual(_normalize('42'), 42)
        def test_zero(self): self.assertEqual(_normalize('0'), 0)
        def test_true(self): self.assertIs(_normalize('true'), True)
        def test_True_caps(self): self.assertIs(_normalize('True'), True)
        def test_yes(self): self.assertIs(_normalize('yes'), True)
        def test_false(self): self.assertIs(_normalize('false'), False)
        def test_no(self): self.assertIs(_normalize('no'), False)
        def test_list(self): self.assertEqual(_normalize('a,b,c'), ['a', 'b', 'c'])
        def test_list_strips_spaces(self):
            self.assertEqual(_normalize('a, b, c'), ['a', 'b', 'c'])
        def test_plain_string(self): self.assertEqual(_normalize('bar_pct'), 'bar_pct')
        def test_empty(self): self.assertEqual(_normalize(''), '')
        def test_ansi_string(self):
            # COLOR values are strings even if they look unusual
            self.assertEqual(_normalize('\\033[32m'), '\\033[32m')


    class TestUnquote(unittest.TestCase):
        def test_double_quotes(self): self.assertEqual(_unquote('"hello"'), 'hello')
        def test_single_quotes(self): self.assertEqual(_unquote("'hello'"), 'hello')
        def test_no_quotes(self): self.assertEqual(_unquote('hello'), 'hello')
        def test_inline_comment(self):
            self.assertEqual(_unquote('bar_pct # my comment'), 'bar_pct')
        def test_quoted_inline_comment(self):
            # Comment outside quotes should be stripped
            self.assertEqual(_unquote('"bar_pct" # comment'), 'bar_pct')
        def test_empty_string(self): self.assertEqual(_unquote(''), '')
        def test_quoted_empty(self): self.assertEqual(_unquote('""'), '')


    class TestParseFile(unittest.TestCase):
        def _write(self, tmp, content):
            path = os.path.join(tmp, 'test.conf')
            with open(path, 'w') as f:
                f.write(content)
            return path

        def test_missing_file(self):
            self.assertEqual(_parse_file('/nonexistent/path/config.conf'), {})

        def test_comment_only(self):
            with tempfile.TemporaryDirectory() as tmp:
                path = self._write(tmp, '# just a comment\n# another\n')
                self.assertEqual(_parse_file(path), {})

        def test_blank_lines_skipped(self):
            with tempfile.TemporaryDirectory() as tmp:
                path = self._write(tmp, '\n\nKEY=val\n\n')
                self.assertEqual(_parse_file(path), {'KEY': 'val'})

        def test_unquoted_value(self):
            with tempfile.TemporaryDirectory() as tmp:
                path = self._write(tmp, 'RATE_STYLE=bar_pct\n')
                self.assertEqual(_parse_file(path), {'RATE_STYLE': 'bar_pct'})

        def test_double_quoted_value(self):
            with tempfile.TemporaryDirectory() as tmp:
                path = self._write(tmp, 'SEP_CHAR="│"\n')
                self.assertEqual(_parse_file(path), {'SEP_CHAR': '│'})

        def test_single_quoted_value(self):
            with tempfile.TemporaryDirectory() as tmp:
                path = self._write(tmp, "SEP_CHAR='│'\n")
                self.assertEqual(_parse_file(path), {'SEP_CHAR': '│'})

        def test_inline_comment_stripped(self):
            with tempfile.TemporaryDirectory() as tmp:
                path = self._write(tmp, 'RATE_STYLE=bar_pct # explanation\n')
                self.assertEqual(_parse_file(path), {'RATE_STYLE': 'bar_pct'})

        def test_quoted_with_inline_comment(self):
            with tempfile.TemporaryDirectory() as tmp:
                path = self._write(tmp, 'RATE_STYLE="bar_pct" # explanation\n')
                self.assertEqual(_parse_file(path), {'RATE_STYLE': 'bar_pct'})

        def test_int_normalization(self):
            with tempfile.TemporaryDirectory() as tmp:
                path = self._write(tmp, 'BAR_WIDTH=6\n')
                self.assertEqual(_parse_file(path), {'BAR_WIDTH': 6})
                self.assertIsInstance(_parse_file(path)['BAR_WIDTH'], int)

        def test_bool_true(self):
            with tempfile.TemporaryDirectory() as tmp:
                path = self._write(tmp, 'SHOW_LABELS=true\n')
                self.assertIs(_parse_file(path)['SHOW_LABELS'], True)

        def test_bool_false(self):
            with tempfile.TemporaryDirectory() as tmp:
                path = self._write(tmp, 'SHOW_TTL=false\n')
                self.assertIs(_parse_file(path)['SHOW_TTL'], False)

        def test_list_normalization(self):
            with tempfile.TemporaryDirectory() as tmp:
                path = self._write(tmp, 'LINE1="model effort context_pct"\n')
                # Space-separated inside quotes is a plain string, not a list
                result = _parse_file(path)['LINE1']
                self.assertIsInstance(result, str)

        def test_comma_list(self):
            with tempfile.TemporaryDirectory() as tmp:
                path = self._write(tmp, 'ITEMS=a,b,c\n')
                self.assertEqual(_parse_file(path)['ITEMS'], ['a', 'b', 'c'])

        def test_empty_value(self):
            with tempfile.TemporaryDirectory() as tmp:
                path = self._write(tmp, 'LINE3=\n')
                self.assertEqual(_parse_file(path)['LINE3'], '')

        def test_no_equals_ignored(self):
            with tempfile.TemporaryDirectory() as tmp:
                path = self._write(tmp, 'not_a_key_value\nKEY=val\n')
                self.assertEqual(_parse_file(path), {'KEY': 'val'})

        def test_spaces_around_equals(self):
            with tempfile.TemporaryDirectory() as tmp:
                path = self._write(tmp, 'KEY  =  value\n')
                self.assertEqual(_parse_file(path), {'KEY': 'value'})

        def test_multiple_keys(self):
            with tempfile.TemporaryDirectory() as tmp:
                path = self._write(tmp, 'A=1\nB=hello\nC=true\n')
                self.assertEqual(_parse_file(path), {'A': 1, 'B': 'hello', 'C': True})


    class TestLoadConfig(unittest.TestCase):
        def test_no_files_returns_empty(self):
            with tempfile.TemporaryDirectory() as tmp:
                # Neither ~/.claude/statusline.conf nor <cwd>/.claude/statusline.conf
                # exist in this temp environment; mock both paths to non-existent
                import unittest.mock as mock
                with mock.patch('lib.config.os.path.expanduser', return_value='/nonexistent/base.conf'):
                    result = load_config(cwd=tmp)
                self.assertEqual(result, {})

        def test_base_only(self):
            with tempfile.TemporaryDirectory() as tmp:
                base_conf = os.path.join(tmp, 'base.conf')
                with open(base_conf, 'w') as f:
                    f.write('BAR_WIDTH=6\nSHOW_LABELS=true\n')
                with unittest.mock.patch('lib.config.os.path.expanduser', return_value=base_conf):
                    result = load_config(cwd='/nonexistent_project')
                self.assertEqual(result['BAR_WIDTH'], 6)
                self.assertIs(result['SHOW_LABELS'], True)

        def test_project_override_wins(self):
            with tempfile.TemporaryDirectory() as base_tmp:
                with tempfile.TemporaryDirectory() as project_tmp:
                    base_conf = os.path.join(base_tmp, 'base.conf')
                    with open(base_conf, 'w') as f:
                        f.write('BAR_WIDTH=6\nSHOW_LABELS=true\n')

                    # Create <project>/.claude/statusline.conf
                    dot_claude = os.path.join(project_tmp, '.claude')
                    os.makedirs(dot_claude)
                    override_conf = os.path.join(dot_claude, 'statusline.conf')
                    with open(override_conf, 'w') as f:
                        f.write('BAR_WIDTH=10\n')  # Override BAR_WIDTH

                    with unittest.mock.patch('lib.config.os.path.expanduser', return_value=base_conf):
                        result = load_config(cwd=project_tmp)

                    # Project value wins
                    self.assertEqual(result['BAR_WIDTH'], 10)
                    # Base value preserved for non-conflicting keys
                    self.assertIs(result['SHOW_LABELS'], True)

        def test_project_only(self):
            with tempfile.TemporaryDirectory() as project_tmp:
                dot_claude = os.path.join(project_tmp, '.claude')
                os.makedirs(dot_claude)
                override_conf = os.path.join(dot_claude, 'statusline.conf')
                with open(override_conf, 'w') as f:
                    f.write('BAR_WIDTH=8\n')

                with unittest.mock.patch('lib.config.os.path.expanduser', return_value='/nonexistent/base.conf'):
                    result = load_config(cwd=project_tmp)

                self.assertEqual(result['BAR_WIDTH'], 8)

        def test_real_conf_shape(self):
            """Smoke test with content shaped like real statusline.conf."""
            sample = (
                '# layout\n'
                'LINE1="model effort context_pct"\n'
                'LINE2="hook agents rate_5h"\n'
                'BAR_WIDTH=6\n'
                'SHOW_LABELS=true\n'
                'SHOW_TTL=false\n'
                'RATE_STYLE=bar_pct # default\n'
                'CC_UI_LINE=0\n'
            )
            with tempfile.TemporaryDirectory() as tmp:
                path = os.path.join(tmp, 'statusline.conf')
                with open(path, 'w') as f:
                    f.write(sample)
                result = _parse_file(path)

            self.assertEqual(result['BAR_WIDTH'], 6)
            self.assertIsInstance(result['BAR_WIDTH'], int)
            self.assertIs(result['SHOW_LABELS'], True)
            self.assertIs(result['SHOW_TTL'], False)
            self.assertEqual(result['RATE_STYLE'], 'bar_pct')
            self.assertEqual(result['CC_UI_LINE'], 0)
            # LINE1/LINE2 are space-separated strings inside quotes → str, not list
            self.assertIsInstance(result['LINE1'], str)
            self.assertIn('model', result['LINE1'])


    if __name__ == '__main__':
        unittest.main()
    ```
  </action>

  <verify>
    <automated>cd /home/josef/workspace-linux/claude-status-line && python3 -m unittest tests.test_config -v 2>&1 | tail -20</automated>
  </verify>

  <acceptance_criteria>
    - Command `python3 -m unittest tests.test_config -v` exits 0
    - Output contains "OK" on final line (no failures or errors)
    - At least 30 test methods run (grep "test_" tests/test_config.py | wc -l shows 30+)
    - `python3 -m unittest discover tests/ -v` also exits 0 (existing test_ansi.py still passes)
    - No test method relies on the real `~/.claude/statusline.conf` being present
  </acceptance_criteria>

  <done>
    - All test methods in `tests/test_config.py` pass
    - Full test suite (`tests/run.sh`) exits 0 with both test_ansi and test_config reported
  </done>
</task>

</tasks>

<verification>
After both tasks complete, run the full test suite:

```bash
cd /home/josef/workspace-linux/claude-status-line
python3 -m unittest discover tests/ -v
```

Expected: all tests from `test_ansi.py` and `test_config.py` pass, exit code 0.

Also verify:
```bash
python3 -c "
from lib.config import load_config
cfg = load_config(cwd='/nonexistent')
print(type(cfg))  # <class 'dict'>
"
```

And verify graceful missing-file handling:
```bash
python3 -c "
from lib.config import _parse_file
result = _parse_file('/tmp/does_not_exist_xyzzy.conf')
assert result == {}, f'Expected empty dict, got {result}'
print('missing file: ok')
"
```
</verification>

<success_criteria>
- `lib/config.py` exists, imports cleanly, exposes `load_config(cwd=None) -> dict`
- `tests/test_config.py` exists with 30+ test methods covering all parsing rules
- `python3 -m unittest tests.test_config` exits 0 with no failures
- `python3 -m unittest discover tests/` exits 0 (both test_ansi and test_config pass together)
- `_parse_file('/nonexistent')` returns `{}` — verified by automated check
- `load_config()` called with a project dir that has `.claude/statusline.conf` returns merged dict where project keys win over base keys
</success_criteria>

<output>
After completion, create `.planning/phases/03-config-parser/03-01-SUMMARY.md` following the
summary template at `$HOME/.claude/get-shit-done/templates/summary.md`.
</output>
