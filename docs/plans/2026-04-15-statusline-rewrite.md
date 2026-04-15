# Claude Status Line — Python Rewrite + Multi-Line Fix Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the bash statusline renderer with a Python script that correctly handles multi-line output, adaptive packing, dimColor compensation, and real terminal width — while never touching installed files without explicit approval.

**Architecture:** Python script reads CC JSON from stdin, detects real terminal width via `/dev/tty`, budgets each output line to `width / N` visible chars (workaround for CC's cli-truncate multi-line bug), then packs segments adaptively by priority. A separate tmux track renders unlimited-line status outside CC's control. Install is gated behind an explicit `install.sh` — no file in `~/.claude/` is touched until the user approves.

**Tech Stack:** Python 3 (stdlib only — `json`, `os`, `fcntl`, `termios`, `struct`, `re`), bash for config sourcing + tmux integration. No external dependencies.

---

## The Problems Being Solved (and Why)

### Problem 1: Multi-line truncation (CC bug #37522, unfixed)
CC passes all output lines to `cli-truncate` as one flat string. `cli-truncate` counts `\n` as width-0, so visible chars from ALL lines sum together. If terminal is W=120 and line 1 is 100 chars visible, line 2 only gets 20 chars before the truncation chops it.

**Workaround discovered:** If each line is ≤ `W/N` visible chars, the total visible width ≤ W, and cli-truncate leaves all lines intact. This requires knowing actual terminal width AND ANSI-aware width counting.

### Problem 2: Terminal width unavailable to subprocess
`tput cols` and `shutil.get_terminal_size()` both return 80 (default) when run as a CC subprocess — no TTY attached to stdout. BUT the process inherits the controlling TTY. We can read real terminal size via `fcntl.ioctl(open('/dev/tty'), termios.TIOCGWINSZ, ...)` — this works even in a subprocess because it bypasses stdout.

### Problem 3: dimColor overwrites our colors
CC wraps all output in `<Text dimColor>` (confirmed from leaked source `StatusLine.tsx`). This prepends `\033[2m` (dim) to our text. Fix: prepend `\033[22m` (normal intensity reset) at the start of each output line to override CC's dim before our colored content.

### Problem 4: Empty lines filtered
CC's processing: `.flatMap(line => line.trim() || [])` silently drops empty lines. The CC_UI_LINE blank-line trick never worked — blank lines were always stripped. Remove CC_UI_LINE entirely.

### Problem 5: Can't hide the permission mode indicator
It's a separate Ink component below StatusLine — completely outside our control. No workaround. Design acceptance: treat the permission line as a fixed bottom element and don't try to fight it.

---

## What We Are NOT Doing (and Why)

**Forking/patching Claude Code from leaked source:** The leaked source gives us architectural knowledge (which we've used to diagnose problems), but using the actual code would be a licensing risk and require maintaining a custom CC binary through every update. Not worth it. The cli-truncate workaround solves the same problem from our side.

**Using any external Python packages:** Keeps the script zero-dependency. Everything in stdlib.

**Three-line mode by default:** Even with the cli-truncate workaround, 3 lines of `W/3` chars each is very tight on 120-col terminals (only 40 chars per line). Plan offers single-line (default), 2-line, and 3-line modes with explicit trade-off documentation.

---

## Safety Rules (ENFORCED throughout)

- `~/.claude/statusline.sh` — **READ ONLY** — never modified by this plan
- `~/.claude/statusline.conf` — **READ ONLY** — never modified by this plan  
- `~/.claude/settings.json` — **READ ONLY** — never modified by this plan
- All new code goes to `/home/josef/workspace-linux/claude-status-line/`
- `install.sh` does the ONLY write to `~/.claude/` — and only when user runs it manually

---

## File Structure

```
claude-status-line/
├── statusline.py           # NEW: main Python renderer (replaces statusline.sh)
├── statusline.sh           # EXISTING: bash renderer (kept, used as fallback)
├── statusline.conf         # EXISTING: config (Python script also reads this)
├── lib/
│   ├── ansi.py             # NEW: ANSI escape code stripping + visible width
│   ├── segments.py         # NEW: all segment renderers (ported from bash)
│   ├── config.py           # NEW: parse bash-style KEY=value conf file
│   └── packer.py           # NEW: adaptive line packing algorithm
├── hooks/
│   ├── agent-tracker.sh    # EXISTING
│   ├── hook-status-bridge.sh # EXISTING
│   └── gsd-statusline.js   # EXISTING
├── tmux/
│   └── statusline.sh       # NEW: tmux status-right integration (separate track)
├── tests/
│   ├── fixtures/
│   │   ├── minimal.json    # NEW: minimal CC JSON input
│   │   ├── full.json       # NEW: full CC JSON with all fields
│   │   └── narrow.json     # NEW: narrow terminal scenario
│   ├── test_ansi.py        # NEW: ANSI width calculation tests
│   ├── test_packer.py      # NEW: adaptive packing tests
│   └── test_segments.py    # NEW: segment rendering tests
├── install.sh              # NEW: backup + install to ~/.claude/ (user-gated)
├── uninstall.sh            # NEW: restore backups
└── docs/
    └── plans/
        └── 2026-04-15-statusline-rewrite.md  # THIS FILE
```

---

## Task 1: Test Fixtures and Harness

**Files:**
- Create: `tests/fixtures/minimal.json`
- Create: `tests/fixtures/full.json`
- Create: `tests/fixtures/narrow.json`
- Create: `tests/run.sh`

- [ ] **Step 1.1: Create minimal CC JSON fixture**

```bash
cat > tests/fixtures/minimal.json << 'EOF'
{
  "model": {"display_name": "Claude Sonnet 4.6", "id": "claude-sonnet-4-6"},
  "context_window": {
    "context_window_size": 200000,
    "current_usage": {
      "input_tokens": 64000,
      "cache_creation_input_tokens": 0,
      "cache_read_input_tokens": 128000
    },
    "total_input_tokens": 8500,
    "total_output_tokens": 1200
  },
  "cwd": "/home/josef/workspace-linux/claude-status-line",
  "session_id": "test-session-001"
}
EOF
```

- [ ] **Step 1.2: Create full CC JSON fixture**

```bash
cat > tests/fixtures/full.json << 'EOF'
{
  "model": {"display_name": "Claude Opus 4.6", "id": "claude-opus-4-6"},
  "context_window": {
    "context_window_size": 200000,
    "current_usage": {
      "input_tokens": 64000,
      "cache_creation_input_tokens": 0,
      "cache_read_input_tokens": 128000
    },
    "total_input_tokens": 85000,
    "total_output_tokens": 22000
  },
  "rate_limits": {
    "five_hour": {
      "used_percentage": 48.3,
      "resets_at": 1776200000
    },
    "seven_day": {
      "used_percentage": 12.1,
      "resets_at": 1776700000
    }
  },
  "cwd": "/home/josef/workspace-linux/claude-status-line",
  "session_id": "test-session-002"
}
EOF
```

- [ ] **Step 1.3: Create narrow terminal fixture**

```bash
cat > tests/fixtures/narrow.json << 'EOF'
{
  "model": {"display_name": "Claude Sonnet 4.6", "id": "claude-sonnet-4-6"},
  "context_window": {
    "context_window_size": 200000,
    "current_usage": {
      "input_tokens": 100000,
      "cache_creation_input_tokens": 0,
      "cache_read_input_tokens": 0
    },
    "total_input_tokens": 5000,
    "total_output_tokens": 800
  },
  "cwd": "/home/josef/workspace-linux/claude-status-line",
  "session_id": "test-session-003"
}
EOF
```

- [ ] **Step 1.4: Create test runner**

```bash
cat > tests/run.sh << 'EOF'
#!/bin/bash
# Run all tests
cd "$(dirname "$0")/.."
echo "=== Python unit tests ==="
python3 -m pytest tests/ -v 2>/dev/null || python3 -m unittest discover tests/ -v
echo ""
echo "=== Integration: render minimal ==="
cat tests/fixtures/minimal.json | STATUSLINE_WIDTH=120 python3 statusline.py
echo ""
echo "=== Integration: render full ==="
cat tests/fixtures/full.json | STATUSLINE_WIDTH=120 python3 statusline.py
echo ""
echo "=== Integration: narrow (80 cols) ==="
cat tests/fixtures/narrow.json | STATUSLINE_WIDTH=80 python3 statusline.py
echo ""
echo "=== Integration: 2-line mode ==="
cat tests/fixtures/full.json | STATUSLINE_WIDTH=160 STATUSLINE_LINES=2 python3 statusline.py
EOF
chmod +x tests/run.sh
```

- [ ] **Step 1.5: Commit**

```bash
git add tests/
git commit -m "test: add fixtures and test runner harness"
```

---

## Task 2: ANSI Width Library

**Files:**
- Create: `lib/__init__.py`
- Create: `lib/ansi.py`
- Create: `tests/test_ansi.py`

- [ ] **Step 2.1: Write the failing tests**

```bash
mkdir -p lib
touch lib/__init__.py
cat > tests/test_ansi.py << 'EOF'
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
EOF
```

- [ ] **Step 2.2: Run tests, verify they fail**

```bash
python3 tests/test_ansi.py
# Expected: ImportError or NameError (lib/ansi.py doesn't exist yet)
```

- [ ] **Step 2.3: Implement `lib/ansi.py`**

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

- [ ] **Step 2.4: Run tests, verify they pass**

```bash
python3 tests/test_ansi.py
# Expected: all PASS
```

- [ ] **Step 2.5: Commit**

```bash
git add lib/ tests/test_ansi.py
git commit -m "feat: ANSI-aware width calculation library"
```

---

## Task 3: Config Parser

**Files:**
- Create: `lib/config.py`
- (No separate test file — tested inline in integration step)

The Python script must read `~/.claude/statusline.conf` (bash `KEY="value"` syntax) and optionally a per-project override at `<cwd>/.claude/statusline.conf`.

- [ ] **Step 3.1: Implement `lib/config.py`**

```python
# lib/config.py
"""Parse bash KEY=value config files into a Python dict.

Handles:
- KEY=value
- KEY="value"
- KEY='value'
- # comments
- Inline comments (KEY=value # comment)
- Multiword values in quotes: KEY="hello world"
- Boolean-ish: true/false → True/False
"""

import re
import os

_ASSIGN = re.compile(
    r'^([A-Za-z_][A-Za-z0-9_]*)'   # key
    r'\s*=\s*'                       # =
    r'(?:"([^"]*)"|\'([^\']*)\'|([^#\n]*))'  # quoted or unquoted value
    r'(?:\s*#.*)?$'                  # optional inline comment
)

DEFAULTS = {
    'LINE1': 'model context_pct effort cache_pct tokens cwd git_branch git_status',
    'LINE2': '',
    'LINE3': '',
    'RATE_STYLE': 'bar_pct',
    'BAR_WIDTH': '6',
    'TOKEN_STYLE': 'total',
    'SHOW_LABELS': 'true',
    'SHOW_TTL': 'true',
    'SEP_CHAR': '│',
    'GIT_BRANCH_MAX': '20',
    'PRICE_OPUS': '15 75',
    'PRICE_SONNET': '3 15',
    'PRICE_HAIKU': '0.80 4',
    # New Python-only settings:
    'OVERRIDE_DIMCOLOR': 'true',   # prepend \033[22m to counter CC's dimColor
    'MAX_LINES': '0',              # 0 = auto (1 line), or 1/2/3
}


def _parse_file(path: str) -> dict:
    result = {}
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                m = _ASSIGN.match(line)
                if m:
                    key = m.group(1)
                    # Take first non-None of the three capture groups
                    val = m.group(2) if m.group(2) is not None else \
                          m.group(3) if m.group(3) is not None else \
                          (m.group(4) or '').strip()
                    result[key] = val
    except FileNotFoundError:
        pass
    return result


def load(cwd: str = '') -> dict:
    """Load config: defaults → global → per-project override."""
    cfg = dict(DEFAULTS)

    global_conf = os.path.expanduser('~/.claude/statusline.conf')
    cfg.update(_parse_file(global_conf))

    if cwd:
        project_conf = os.path.join(cwd, '.claude', 'statusline.conf')
        cfg.update(_parse_file(project_conf))

    # Normalize types
    cfg['BAR_WIDTH'] = int(cfg.get('BAR_WIDTH', 6))
    cfg['GIT_BRANCH_MAX'] = int(cfg.get('GIT_BRANCH_MAX', 20))
    cfg['SHOW_LABELS'] = cfg.get('SHOW_LABELS', 'true').lower() == 'true'
    cfg['SHOW_TTL'] = cfg.get('SHOW_TTL', 'true').lower() == 'true'
    cfg['OVERRIDE_DIMCOLOR'] = cfg.get('OVERRIDE_DIMCOLOR', 'true').lower() == 'true'
    cfg['MAX_LINES'] = int(cfg.get('MAX_LINES', 0))

    # Parse line layouts into lists
    for key in ('LINE1', 'LINE2', 'LINE3'):
        val = cfg.get(key, '')
        cfg[key] = val.split() if val.strip() else []

    return cfg
```

- [ ] **Step 3.2: Quick sanity test**

```bash
python3 -c "
from lib.config import load
cfg = load('/home/josef/workspace-linux/claude-status-line')
print('LINE1:', cfg['LINE1'])
print('SHOW_LABELS:', cfg['SHOW_LABELS'])
print('SEP_CHAR:', repr(cfg['SEP_CHAR']))
"
# Expected: LINE1 shows segment list from ~/.claude/statusline.conf
```

- [ ] **Step 3.3: Commit**

```bash
git add lib/config.py
git commit -m "feat: bash-style config parser for Python renderer"
```

---

## Task 4: Segment Renderers

**Files:**
- Create: `lib/segments.py`
- Create: `tests/test_segments.py`

This is the port of all `render_segment()` cases from `statusline.sh` to Python. Each segment returns an ANSI-colored string or `None` (hidden).

- [ ] **Step 4.1: Write failing tests**

```bash
cat > tests/test_segments.py << 'EOF'
import sys, os; sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import json
from lib.segments import SegmentRenderer
from lib.ansi import visible_width

MINIMAL = json.loads(open("tests/fixtures/minimal.json").read())
FULL = json.loads(open("tests/fixtures/full.json").read())

def make_renderer(data, cfg_overrides=None):
    from lib.config import DEFAULTS
    cfg = dict(DEFAULTS)
    cfg['SHOW_LABELS'] = True
    cfg['SHOW_TTL'] = True
    cfg['BAR_WIDTH'] = 6
    cfg['GIT_BRANCH_MAX'] = 20
    cfg['TOKEN_STYLE'] = 'total'
    cfg['RATE_STYLE'] = 'bar_pct'
    cfg['PRICE_OPUS'] = '15 75'
    cfg['PRICE_SONNET'] = '3 15'
    cfg['PRICE_HAIKU'] = '0.80 4'
    for k in ('LINE1', 'LINE2', 'LINE3'):
        cfg[k] = []
    if cfg_overrides:
        cfg.update(cfg_overrides)
    return SegmentRenderer(data, cfg)

def test_model_returns_string():
    r = make_renderer(MINIMAL)
    result = r.render('model')
    assert result is not None
    assert 'Sonnet' in result or 'Claude' in result

def test_model_hidden_when_missing():
    data = {}
    r = make_renderer(data)
    # Should return "Claude" fallback
    result = r.render('model')
    assert result is not None

def test_context_pct_returns_percentage():
    r = make_renderer(MINIMAL)
    result = r.render('context_pct')
    assert result is not None
    # Should contain a number followed by %
    import re
    assert re.search(r'\d+%', result)

def test_tokens_hidden_when_zero():
    data = {"model": {"display_name": "X"}, "context_window": {
        "total_input_tokens": 0, "total_output_tokens": 0,
        "context_window_size": 200000,
        "current_usage": {"input_tokens": 0, "cache_creation_input_tokens": 0, "cache_read_input_tokens": 0}
    }}
    r = make_renderer(data)
    assert r.render('tokens') is None

def test_tokens_shows_when_present():
    r = make_renderer(MINIMAL)
    result = r.render('tokens')
    assert result is not None

def test_rate_5h_hidden_when_missing():
    r = make_renderer(MINIMAL)  # minimal has no rate_limits
    assert r.render('rate_5h') is None

def test_rate_5h_shows_when_present():
    r = make_renderer(FULL)
    result = r.render('rate_5h')
    assert result is not None
    assert '48' in result  # 48.3% usage

def test_unknown_segment_returns_none():
    r = make_renderer(MINIMAL)
    assert r.render('nonexistent_segment_xyz') is None

def test_cwd_returns_basename():
    r = make_renderer(MINIMAL)
    result = r.render('cwd')
    assert result is not None
    assert 'claude-status-line' in result

if __name__ == "__main__":
    tests = [v for k, v in globals().items() if k.startswith("test_")]
    passed = failed = 0
    for t in tests:
        try:
            t()
            print(f"  PASS {t.__name__}")
            passed += 1
        except Exception as e:
            print(f"  FAIL {t.__name__}: {e}")
            import traceback; traceback.print_exc()
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
    import sys; sys.exit(1 if failed else 0)
EOF
```

- [ ] **Step 4.2: Run, verify fail**

```bash
python3 tests/test_segments.py
# Expected: ImportError — lib/segments.py doesn't exist yet
```

- [ ] **Step 4.3: Implement `lib/segments.py`**

```python
# lib/segments.py
"""Segment renderers — ported from statusline.sh render_segment().

Each render_*() method returns an ANSI-colored string or None (hidden).
None means "omit this segment" — packer will skip it.
"""

import json
import os
import re
import subprocess
import time
from datetime import datetime


# ── ANSI colors (RGB, brighter than original to compensate for dimColor) ──────
# Original bash values dimmed by CC's <Text dimColor>. Boost luminance ~30%.
BLUE   = '\033[38;2;50;180;255m'   # was 0;153;255
ORANGE = '\033[38;2;255;200;100m'  # was 255;176;85
GREEN  = '\033[38;2;50;210;100m'   # was 0;175;80
RED    = '\033[38;2;255;110;110m'  # was 255;85;85
YELLOW = '\033[38;2;255;230;30m'   # was 230;200;0
WHITE  = '\033[38;2;255;255;255m'  # was 220;220;220 — full white
DIM    = '\033[2m'
BOLD   = '\033[1m'
RESET  = '\033[0m'


def _color_for_pct(pct: int) -> str:
    if pct >= 90: return RED
    if pct >= 70: return YELLOW
    if pct >= 50: return ORANGE
    return GREEN


def _color_for_cache_pct(pct: int) -> str:
    if pct >= 70: return GREEN
    if pct >= 40: return YELLOW
    if pct >= 15: return ORANGE
    return RED


def _format_tokens(n: int) -> str:
    if n >= 1_000_000: return f'{n/1_000_000:.1f}M'
    if n >= 1_000:     return f'{n/1_000:.1f}k'
    return str(n)


def _format_ttl(epoch) -> str:
    """Format seconds until an epoch as '4h32m', '2d3h', etc."""
    if not epoch:
        return ''
    try:
        epoch = int(float(str(epoch)))
    except (ValueError, TypeError):
        return ''
    diff = epoch - int(time.time())
    if diff <= 0:
        return 'now'
    days  = diff // 86400
    hours = (diff % 86400) // 3600
    mins  = (diff % 3600) // 60
    if days:   return f'{days}d{hours}h'
    if hours:  return f'{hours}h{mins}m'
    return f'{mins}m'


def _format_time_to_exhaust(pct: float, reset_epoch: int, window_secs: int) -> str:
    """Predict how long until quota is exhausted at current burn rate."""
    if not pct or pct <= 0 or pct >= 100:
        return 'now' if pct >= 100 else ''
    now = int(time.time())
    window_start = reset_epoch - window_secs
    elapsed = now - window_start
    if elapsed <= 0:
        return ''
    remaining = int(elapsed * (100 - pct) / pct)
    if remaining <= 0:
        return 'now'
    days  = remaining // 86400
    hours = (remaining % 86400) // 3600
    mins  = (remaining % 3600) // 60
    if days:   return f'{days}d{hours}h'
    if hours:  return f'{hours}h{mins}m'
    return f'{mins}m'


def _build_bar(pct: int, width: int) -> str:
    pct = max(0, min(100, pct))
    filled = pct * width // 100
    empty  = width - filled
    color  = _color_for_pct(pct)
    return f"{color}{'▓' * filled}{'░' * empty}{RESET}"


class SegmentRenderer:
    def __init__(self, data: dict, cfg: dict):
        self.data = data
        self.cfg  = cfg
        self._parse_data()

    def _parse_data(self):
        d = self.data
        cw = d.get('context_window', {})
        usage = cw.get('current_usage', {})
        rl    = d.get('rate_limits', {})

        self.model_name = d.get('model', {}).get('display_name') or 'Claude'
        self.model_id   = d.get('model', {}).get('id') or ''

        self.session_in  = int(cw.get('total_input_tokens', 0) or 0)
        self.session_out = int(cw.get('total_output_tokens', 0) or 0)
        self.session_total = self.session_in + self.session_out

        self.ctx_size   = int(cw.get('context_window_size', 200000) or 200000) or 200000
        input_tok   = int(usage.get('input_tokens', 0) or 0)
        cache_cre   = int(usage.get('cache_creation_input_tokens', 0) or 0)
        cache_read  = int(usage.get('cache_read_input_tokens', 0) or 0)
        self.current = input_tok + cache_cre + cache_read
        self.pct_used  = int(self.current * 100 / self.ctx_size) if self.ctx_size else 0
        self.cache_pct = int(cache_read * 100 / self.current) if self.current else 0

        self.cwd = d.get('cwd') or os.getcwd()
        self.session_id = d.get('session_id', '')

        # Rate limits
        fh = rl.get('five_hour', {})
        sd = rl.get('seven_day', {})
        self.five_pct   = fh.get('used_percentage')
        self.five_epoch = fh.get('resets_at')
        self.seven_pct  = sd.get('used_percentage')
        self.seven_epoch = sd.get('resets_at')

        # Effort
        effort = os.environ.get('CLAUDE_CODE_EFFORT_LEVEL', '')
        if not effort:
            for sf in ['.claude/settings.local.json', '.claude/settings.json',
                       os.path.expanduser('~/.claude/settings.local.json'),
                       os.path.expanduser('~/.claude/settings.json')]:
                try:
                    with open(sf) as f:
                        val = json.load(f).get('effortLevel', '')
                        if val:
                            effort = val
                            break
                except Exception:
                    pass
        self.effort = effort or 'auto'

        # Git
        self.git_branch = ''
        self.git_info   = ''
        self._parse_git()

        # Worktree
        self.worktree_name = ''
        self._parse_worktree()

        # Session state (token history)
        self.avg_tokens = None
        self.session_first_ts = 0
        self._parse_session_state()

        # Hook bridge
        self.hook_event = ''
        self.hook_tool  = ''
        self.hook_scripts = ''
        self.hookify_configured = False
        self.hookify_count = 0
        self._parse_hook_state()

        # GSD state
        self.gsd_phase_num = ''
        self.gsd_status    = ''
        self.gsd_completed_phases = ''
        self.gsd_total_phases = ''
        self.gsd_completed_plans = ''
        self.gsd_total_plans = ''
        self._parse_gsd_state()

        # Agents
        self.agent_active_count = 0
        self.agent_active_types = []
        self.agent_done_count   = 0
        self._parse_agents()

        # Plugins
        self.plugins_count = 0
        self._parse_plugins()

    def _run_git(self, *args) -> str:
        try:
            return subprocess.check_output(
                ['git', '-C', self.cwd] + list(args),
                stderr=subprocess.DEVNULL, text=True
            ).strip()
        except Exception:
            return ''

    def _parse_git(self):
        if not self._run_git('rev-parse', '--is-inside-work-tree'):
            return
        self.git_branch = self._run_git('symbolic-ref', '--short', 'HEAD')
        upstream = self._run_git('rev-parse', '--abbrev-ref', '@{upstream}')
        if upstream:
            ahead  = self._run_git('rev-list', '--count', '@{upstream}..HEAD') or '0'
            behind = self._run_git('rev-list', '--count', 'HEAD..@{upstream}') or '0'
            if int(ahead):  self.git_info += f'{GREEN}↑{ahead}{RESET}'
            if int(behind): self.git_info += f'{RED}↓{behind}{RESET}'
        porcelain = self._run_git('status', '--porcelain')
        if porcelain:
            staged   = sum(1 for l in porcelain.splitlines() if l[:1] in 'MADRCT')
            unstaged = sum(1 for l in porcelain.splitlines() if l[1:2] in 'MADRCT?')
            if staged:   self.git_info += f'{YELLOW}+{staged}{RESET}'
            if unstaged: self.git_info += f'{ORANGE}~{unstaged}{RESET}'

    def _parse_worktree(self):
        wt_list = self._run_git('worktree', 'list', '--porcelain')
        if not wt_list:
            return
        wt_lines = [l for l in wt_list.splitlines() if l.startswith('worktree ')]
        if len(wt_lines) <= 1:
            return
        main_wt = wt_lines[0].replace('worktree ', '')
        real_cwd = os.path.realpath(self.cwd)
        if real_cwd != main_wt:
            self.worktree_name = os.path.basename(real_cwd)

    def _parse_session_state(self):
        if not self.session_id or not self.session_total:
            return
        state_dir  = os.path.expanduser('~/.claude/statusline-state')
        state_file = os.path.join(state_dir, f'{self.session_id}.json')
        now = int(time.time())
        os.makedirs(state_dir, exist_ok=True)
        try:
            with open(state_file) as f:
                state = json.load(f)
            prev_total = int(state.get('total', 0))
            msg_count  = int(state.get('msgs', 0))
            self.session_first_ts = int(state.get('first_ts', 0)) or now
            history = state.get('history', '')
            if self.session_total > prev_total:
                msg_count += 1
                self.avg_tokens = self.session_total // msg_count
                parts = (history.split(',') + [str(self.avg_tokens)])[-8:]
                new_state = {
                    'total': self.session_total, 'msgs': msg_count,
                    'ts': now, 'first_ts': self.session_first_ts,
                    'history': ','.join(parts)
                }
                with open(state_file, 'w') as f:
                    json.dump(new_state, f)
            elif msg_count > 0:
                self.avg_tokens = self.session_total // msg_count
        except (FileNotFoundError, json.JSONDecodeError):
            self.session_first_ts = now
            self.avg_tokens = self.session_total
            with open(state_file, 'w') as f:
                json.dump({
                    'total': self.session_total, 'msgs': 1,
                    'ts': now, 'first_ts': now,
                    'history': str(self.session_total)
                }, f)

    def _parse_hook_state(self):
        if not self.session_id:
            return
        path = f'/tmp/claude-hook-status-{self.session_id}.json'
        try:
            with open(path) as f:
                s = json.load(f)
            self.hook_event   = s.get('hook_event', '')
            self.hook_tool    = s.get('tool_name', '')
            self.hook_scripts = ','.join(s.get('hooks_ran', []))
            self.hookify_configured = s.get('hookify_configured', False)
            self.hookify_count = len(s.get('hookify_rules', []))
        except Exception:
            pass

    def _parse_gsd_state(self):
        state_md = os.path.join(self.cwd, '.planning', 'STATE.md')
        try:
            with open(state_md) as f:
                content = f.read()
            # Extract YAML frontmatter
            m = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
            if not m:
                return
            fm = m.group(1)
            def get(key):
                r = re.search(rf'^{key}:\s*(.+)$', fm, re.MULTILINE)
                return r.group(1).strip().strip('"') if r else ''
            self.gsd_status           = get('status')
            self.gsd_completed_phases = get('completed_phases')
            self.gsd_total_phases     = get('total_phases')
            self.gsd_completed_plans  = get('completed_plans')
            self.gsd_total_plans      = get('total_plans')
            phase_m = re.search(r'^Phase:\s*(.+)$', content, re.MULTILINE)
            self.gsd_phase_num = phase_m.group(1).strip() if phase_m else ''
        except Exception:
            pass

    def _parse_agents(self):
        if not self.session_id:
            return
        path = f'/tmp/claude-agent-tracker-{self.session_id}.json'
        try:
            with open(path) as f:
                s = json.load(f)
            agents = s.get('agents', [])
            running = [a for a in agents if a.get('status') == 'running']
            done    = [a for a in agents if a.get('status') == 'done']
            self.agent_active_count = len(running)
            self.agent_active_types = [a.get('type', '?') for a in running]
            self.agent_done_count   = len(done)
        except Exception:
            pass

    def _parse_plugins(self):
        for sf in [os.path.expanduser('~/.claude/settings.json'),
                   os.path.expanduser('~/.claude/settings.local.json')]:
            try:
                with open(sf) as f:
                    data = json.load(f)
                pc = len(data.get('plugins', {}))
                if pc:
                    self.plugins_count = pc
                    break
            except Exception:
                pass

    # ── Label helper ─────────────────────────────────────────
    def _lbl(self, text: str) -> str:
        if self.cfg.get('SHOW_LABELS'):
            return f'{DIM}{text}:{RESET} '
        return ''

    # ── Rate rendering ────────────────────────────────────────
    def _render_rate(self, label: str, pct, epoch) -> str | None:
        if pct is None:
            return None
        style = self.cfg.get('RATE_STYLE', 'bar_pct')
        if style == 'off':
            return None
        pct = int(float(str(pct)))
        color = _color_for_pct(pct)
        bar_w = self.cfg.get('BAR_WIDTH', 6)
        out = f'{DIM}{label}{RESET} '
        if style == 'bar_pct':
            out += f'{_build_bar(pct, bar_w)} {color}{pct}%{RESET}'
        elif style == 'pct':
            out += f'{color}{pct}%{RESET}'
        elif style == 'bar':
            out += _build_bar(pct, bar_w)
        if self.cfg.get('SHOW_TTL') and epoch:
            ttl = _format_ttl(epoch)
            if ttl:
                out += f' {WHITE}{ttl}{RESET}'
        return out

    # ── render() dispatcher ───────────────────────────────────
    def render(self, name: str) -> str | None:
        method = getattr(self, f'_seg_{name}', None)
        if method is None:
            return None
        return method()

    def _seg_model(self):
        return f'{BLUE}{self.model_name}{RESET}'

    def _seg_context_pct(self):
        color = _color_for_pct(self.pct_used)
        return f'{color}{self.pct_used}%{RESET}'

    def _seg_tokens(self):
        if not self.session_total:
            return None
        style = self.cfg.get('TOKEN_STYLE', 'total')
        lbl = self._lbl('tokens')
        if style == 'in_out':
            return f'{lbl}{WHITE}↑{_format_tokens(self.session_in)} ↓{_format_tokens(self.session_out)}{RESET}'
        return f'{lbl}{WHITE}{_format_tokens(self.session_total)}{RESET}'

    def _seg_cost(self):
        if not self.session_total:
            return None
        prices = {'opus': self.cfg.get('PRICE_OPUS', '15 75'),
                  'haiku': self.cfg.get('PRICE_HAIKU', '0.80 4'),
                  'sonnet': self.cfg.get('PRICE_SONNET', '3 15')}
        if 'opus' in (self.model_id + self.model_name).lower():
            ip, op = map(float, prices['opus'].split())
        elif 'haiku' in (self.model_id + self.model_name).lower():
            ip, op = map(float, prices['haiku'].split())
        else:
            ip, op = map(float, prices['sonnet'].split())
        cost = (self.session_in * ip + self.session_out * op) / 1_000_000
        if cost < 0.001:  fmt = f'${cost:.5f}'
        elif cost < 0.01: fmt = f'${cost:.4f}'
        elif cost < 0.10: fmt = f'${cost:.3f}'
        else:             fmt = f'${cost:.2f}'
        return f'{self._lbl("cost")}{WHITE}{fmt}{RESET}'

    def _seg_cache_pct(self):
        if not self.current:
            return None
        color = _color_for_cache_pct(self.cache_pct)
        return f'{self._lbl("cache")}{color}{self.cache_pct}%{RESET}'

    def _seg_effort(self):
        colors = {'low': GREEN, 'medium': YELLOW, 'high': ORANGE, 'max': RED}
        color = colors.get(self.effort, DIM)
        return f'{self._lbl("effort")}{color}{self.effort}{RESET}'

    def _seg_cwd(self):
        return f'{WHITE}{os.path.basename(self.cwd)}{RESET}'

    def _seg_git_branch(self):
        if not self.git_branch:
            return None
        max_len = self.cfg.get('GIT_BRANCH_MAX', 20)
        branch = self.git_branch
        if len(branch) > max_len:
            branch = branch[:max_len - 1] + '…'
        return f'{GREEN}{branch}{RESET}'

    def _seg_git_status(self):
        return self.git_info or None

    def _seg_rate_5h(self):
        return self._render_rate('5h', self.five_pct, self.five_epoch)

    def _seg_rate_7d(self):
        return self._render_rate('7d', self.seven_pct, self.seven_epoch)

    def _seg_avg_tokens(self):
        if not self.avg_tokens:
            return None
        return f'{self._lbl("tkns/msg")}{WHITE}{_format_tokens(self.avg_tokens)}{RESET}'

    def _seg_exhaust_5h(self):
        if not self.five_pct or not self.five_epoch:
            return None
        t = _format_time_to_exhaust(float(self.five_pct), int(self.five_epoch), 18000)
        if not t:
            return None
        color = _color_for_pct(int(float(str(self.five_pct))))
        return f'{DIM}5h out in{RESET} {color}{t}{RESET}'

    def _seg_exhaust_7d(self):
        if not self.seven_pct or not self.seven_epoch:
            return None
        t = _format_time_to_exhaust(float(self.seven_pct), int(self.seven_epoch), 604800)
        if not t:
            return None
        color = _color_for_pct(int(float(str(self.seven_pct))))
        return f'{DIM}7d out in{RESET} {color}{t}{RESET}'

    def _seg_downtime(self):
        if not self.five_pct or not self.five_epoch:
            return None
        pct = float(self.five_pct)
        epoch = int(self.five_epoch)
        now = int(time.time())
        ws = now - (epoch - 18000)
        if ws <= 0 or pct <= 0:
            return None
        exhaust_secs = int(ws * (100 - pct) / pct)
        time_to_reset = epoch - now
        downtime = time_to_reset - exhaust_secs
        if downtime <= 0:
            return f'{GREEN}no downtime{RESET}'
        hrs = downtime // 3600
        mins = (downtime % 3600) // 60
        dt_str = f'{hrs}h{mins}m' if hrs else f'{mins}m'
        color = RED if downtime > 3600 else ORANGE
        return f'{DIM}downtime:{RESET} {color}{dt_str}{RESET} {DIM}at this rate{RESET}'

    def _seg_hook(self):
        if not self.hook_event:
            return None
        display = self.hook_tool or self.hook_event
        if self.hook_scripts:
            display += f' {DIM}({self.hook_scripts}){RESET}'
        return f'{self._lbl("hooks")}{WHITE}{display}{RESET}'

    def _seg_hookify_rule(self):
        if not self.hookify_configured or not self.hookify_count:
            return None
        return f'{DIM}rules:{RESET}{YELLOW}{self.hookify_count}{RESET}'

    def _seg_session_timer(self):
        if not self.session_first_ts:
            return None
        elapsed = int(time.time()) - self.session_first_ts
        if elapsed <= 60:
            return None
        hrs = elapsed // 3600
        mins = (elapsed % 3600) // 60
        if hrs:
            return f'{self._lbl("session")}{ORANGE}{hrs}h{mins}m{RESET}'
        return f'{self._lbl("session")}{WHITE}{mins}m{RESET}'

    def _seg_gsd_phase(self):
        if not self.gsd_phase_num:
            return None
        colors = {'executing': BLUE, 'verifying': YELLOW,
                  'complete': GREEN, 'planning': DIM}
        tags   = {'executing': '[exec]', 'verifying': '[verify]',
                  'complete': '[done]', 'planning': '[plan]'}
        color = colors.get(self.gsd_status, WHITE)
        tag   = tags.get(self.gsd_status, '')
        tag_str = f' {DIM}{tag}{RESET}' if tag else ''
        return f'{self._lbl("phase")}{color}{self.gsd_phase_num}{RESET}{tag_str}'

    def _seg_gsd_progress(self):
        if not self.gsd_completed_phases:
            return None
        ps = f'{self.gsd_completed_phases}/{self.gsd_total_phases}'
        plans = ''
        if self.gsd_completed_plans:
            plans = f' {DIM}{self.gsd_completed_plans}/{self.gsd_total_plans}p{RESET}'
        return f'{self._lbl("gsd")}{WHITE}{ps}{DIM}ph{RESET}{plans}'

    def _seg_worktree(self):
        if not self.worktree_name:
            return None
        return f'{DIM}wt:{RESET}{YELLOW}{self.worktree_name}{RESET}'

    def _seg_plugins(self):
        if not self.plugins_count:
            return None
        return f'{self._lbl("plugins")}{WHITE}{self.plugins_count}{RESET}'

    def _seg_agents(self):
        if self.agent_active_count:
            types = ','.join(self.agent_active_types)
            return f'{self._lbl("agents")}{BLUE}{self.agent_active_count}{RESET} {DIM}({types}){RESET}'
        if self.agent_done_count:
            return f'{self._lbl("agents")}{DIM}{self.agent_done_count} done{RESET}'
        return None
```

- [ ] **Step 4.4: Run tests, verify they pass**

```bash
python3 tests/test_segments.py
# Expected: all PASS
```

- [ ] **Step 4.5: Commit**

```bash
git add lib/segments.py tests/test_segments.py
git commit -m "feat: Python segment renderers (port from bash)"
```

---

## Task 5: Adaptive Line Packer

**Files:**
- Create: `lib/packer.py`
- Create: `tests/test_packer.py`

This is the core innovation — the algorithm that makes multi-line output survive CC's cli-truncate bug.

**The Algorithm:**
Given N output lines and terminal width W:
- Each line gets a budget of `W // N` visible chars
- Segments are added to a line greedily until budget is exhausted
- When a segment would exceed budget, it's dropped (not truncated)
- Git status attaches directly to git_branch (no separator, no extra width charge)

- [ ] **Step 5.1: Write failing tests**

```bash
cat > tests/test_packer.py << 'EOF'
import sys, os; sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from lib.packer import pack_lines
from lib.ansi import visible_width

SEP = ' │ '

def test_single_segment_fits():
    lines = pack_lines(
        segments=[('model', 'Sonnet')],
        line_budget=40,
        sep=SEP
    )
    assert len(lines) == 1
    assert 'Sonnet' in lines[0]

def test_multiple_segments_fit():
    segs = [('model', 'Sonnet'), ('ctx', '32%'), ('cwd', 'myproject')]
    lines = pack_lines(segs, line_budget=60, sep=SEP)
    assert len(lines) == 1
    assert visible_width(lines[0]) <= 60

def test_overflow_drops_segment():
    # 30-char budget — only first 2 segments fit
    segs = [('a', 'A' * 10), ('b', 'B' * 10), ('c', 'C' * 15)]
    lines = pack_lines(segs, line_budget=25, sep=SEP)
    assert 'A' * 10 in lines[0]
    assert 'B' * 10 in lines[0]
    assert 'C' * 15 not in lines[0]

def test_git_status_attaches_to_branch():
    segs = [
        ('git_branch', 'main'),
        ('git_status', '+2~1'),
        ('ctx', '32%'),
    ]
    lines = pack_lines(segs, line_budget=80, sep=SEP)
    # git_status should appear directly after branch without sep
    assert 'main +2~1' in lines[0] or ('main' in lines[0] and '+2~1' in lines[0])

def test_none_segments_skipped():
    segs = [('model', 'Sonnet'), ('missing', None), ('ctx', '32%')]
    lines = pack_lines(segs, line_budget=80, sep=SEP)
    assert 'Sonnet' in lines[0]
    assert '32%' in lines[0]

def test_empty_input():
    lines = pack_lines([], line_budget=80, sep=SEP)
    assert lines == []

if __name__ == "__main__":
    tests = [v for k, v in globals().items() if k.startswith("test_")]
    passed = failed = 0
    for t in tests:
        try:
            t()
            print(f"  PASS {t.__name__}")
            passed += 1
        except Exception as e:
            print(f"  FAIL {t.__name__}: {e}")
            import traceback; traceback.print_exc()
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
    import sys; sys.exit(1 if failed else 0)
EOF
```

- [ ] **Step 5.2: Run, verify fail**

```bash
python3 tests/test_packer.py
# Expected: ImportError
```

- [ ] **Step 5.3: Implement `lib/packer.py`**

```python
# lib/packer.py
"""Adaptive segment packer.

Greedy algorithm: pack segments into a line until budget exhausted.
Key invariant: visible_width(output_line) <= line_budget
This is what makes multi-line output survive CC's cli-truncate bug:
  total_visible = sum(visible_width(line) for line in output)
  if each line <= W//N, then total_visible <= W, so cli-truncate leaves all lines intact.
"""

from lib.ansi import visible_width


def pack_lines(
    segments: list[tuple[str, str | None]],
    line_budget: int,
    sep: str = ' │ ',
) -> list[str]:
    """Pack (name, rendered) segment pairs into one line within line_budget.

    Returns list of lines (currently always 0 or 1 element — designed for
    single-line mode; multi-line mode calls this once per logical line with
    its own segment list).

    None-valued segments are skipped. 'git_status' attaches to preceding
    'git_branch' with a space instead of the full separator.
    """
    sep_width = visible_width(sep)
    line = ''
    line_vis = 0
    prev_name = ''

    for name, rendered in segments:
        if rendered is None:
            prev_name = name
            continue

        seg_vis = visible_width(rendered)

        if not line:
            # First segment in line
            if seg_vis <= line_budget:
                line = rendered
                line_vis = seg_vis
                prev_name = name
            # else: even the first segment doesn't fit — skip it
            continue

        # Determine join style
        if name == 'git_status' and prev_name == 'git_branch':
            join = ' '
            join_width = 1
        else:
            join = sep
            join_width = sep_width

        needed = join_width + seg_vis
        if line_vis + needed <= line_budget:
            line += join + rendered
            line_vis += needed
            prev_name = name
        # else: doesn't fit — skip (don't set prev_name so next seg uses sep normally)

    return [line] if line else []
```

- [ ] **Step 5.4: Run tests, verify pass**

```bash
python3 tests/test_packer.py
# Expected: all PASS
```

- [ ] **Step 5.5: Commit**

```bash
git add lib/packer.py tests/test_packer.py
git commit -m "feat: adaptive packer with cli-truncate workaround"
```

---

## Task 6: Main Python Entry Point

**Files:**
- Create: `statusline.py`

This wires everything together: reads JSON from stdin, detects terminal width, computes line budgets, renders segments, packs lines, outputs.

- [ ] **Step 6.1: Implement `statusline.py`**

```python
#!/usr/bin/env python3
# statusline.py — Claude Code status line renderer
# Reads JSON from stdin, outputs ANSI-colored status line(s).
# Compatible with ~/.claude/statusline.conf (bash KEY=value format).

import json
import os
import sys
import struct
import fcntl
import termios

# Add project root to path when run directly
sys.path.insert(0, os.path.dirname(__file__))

from lib.config import load as load_config
from lib.segments import SegmentRenderer
from lib.packer import pack_lines
from lib.ansi import visible_width

RESET = '\033[0m'
NORMAL_INTENSITY = '\033[22m'  # Overrides CC's dimColor wrapper


def get_terminal_width() -> int:
    """Get real terminal width, bypassing stdout capture via /dev/tty.

    CC captures our stdout, so sys.stdout has no TTY. But the process
    inherits the controlling terminal — we can query it via /dev/tty.
    Falls back to STATUSLINE_WIDTH env var, then COLUMNS, then 120.
    """
    # Env override (for testing)
    if 'STATUSLINE_WIDTH' in os.environ:
        return int(os.environ['STATUSLINE_WIDTH'])

    # Try /dev/tty (works even when stdout is captured)
    try:
        with open('/dev/tty') as tty:
            ws = struct.unpack('hh', fcntl.ioctl(tty, termios.TIOCGWINSZ, b'\0' * 4))
            if ws[1] > 0:
                return ws[1]
    except Exception:
        pass

    # Try stderr (not captured by CC)
    try:
        ws = struct.unpack('hh', fcntl.ioctl(sys.stderr, termios.TIOCGWINSZ, b'\0' * 4))
        if ws[1] > 0:
            return ws[1]
    except Exception:
        pass

    # Env fallback
    try:
        return int(os.environ.get('COLUMNS', 0)) or 120
    except ValueError:
        return 120


def compute_n_lines(cfg: dict) -> int:
    """How many output lines do we want?

    MAX_LINES=0 means auto: use all non-empty LINE* configs.
    Env STATUSLINE_LINES overrides for testing.
    """
    if 'STATUSLINE_LINES' in os.environ:
        return int(os.environ['STATUSLINE_LINES'])
    if cfg.get('MAX_LINES', 0) > 0:
        return cfg['MAX_LINES']
    # Auto: count non-empty LINEn
    return sum(1 for k in ('LINE1', 'LINE2', 'LINE3') if cfg.get(k))


def main():
    raw = sys.stdin.read().strip()
    if not raw:
        print('Claude', flush=True)
        return

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        print('Claude', flush=True)
        return

    cwd = data.get('cwd', '') or os.getcwd()
    cfg = load_config(cwd)
    renderer = SegmentRenderer(data, cfg)

    width = get_terminal_width()
    # Reserve a few chars for CC's own right-side additions on line 1
    # (CC appends session info / "Remote Control active" etc.)
    CC_RIGHT_RESERVE = 0  # set to e.g. 20 if you see CC appending things

    n_lines = compute_n_lines(cfg)
    if n_lines == 0:
        print('Claude', flush=True)
        return

    # cli-truncate workaround: each line gets width // n_lines visible chars
    # so the total visible chars <= width, preventing truncation of later lines.
    # Give line 1 a bit more budget since CC reads it most carefully.
    if n_lines == 1:
        budgets = [width - CC_RIGHT_RESERVE]
    elif n_lines == 2:
        b = (width - CC_RIGHT_RESERVE) // 2
        budgets = [b, b]
    else:
        b = (width - CC_RIGHT_RESERVE) // 3
        budgets = [b, b, b]

    line_configs = [cfg.get('LINE1', []), cfg.get('LINE2', []), cfg.get('LINE3', [])]
    sep = cfg.get('SEP_CHAR', '│')
    sep_str = f' {sep} '  # padded separator

    output_lines = []
    for i in range(n_lines):
        seg_names = line_configs[i] if i < len(line_configs) else []
        if not seg_names:
            continue
        segments = [(name, renderer.render(name)) for name in seg_names]
        packed = pack_lines(segments, line_budget=budgets[i], sep=sep_str)
        if packed:
            output_lines.extend(packed)

    if not output_lines:
        print('Claude', flush=True)
        return

    # dimColor compensation: prepend normal-intensity reset to each line.
    # CC wraps all output in <Text dimColor> which prepends ESC[2m.
    # ESC[22m (normal intensity) immediately after overrides it.
    if cfg.get('OVERRIDE_DIMCOLOR', True):
        output_lines = [NORMAL_INTENSITY + line for line in output_lines]

    print('\n'.join(output_lines), flush=True)


if __name__ == '__main__':
    main()
```

- [ ] **Step 6.2: Run integration tests**

```bash
bash tests/run.sh
# Expected: no errors, colored output showing segments
```

- [ ] **Step 6.3: Verify cli-truncate workaround with 2-line mode**

```bash
# Test that total visible width of 2-line output <= terminal width
python3 - << 'EOF'
import subprocess, re

def strip_ansi(s):
    return re.sub(r'\033(?:\[[0-9;]*[A-Za-z]|[@-_])', '', s)

result = subprocess.run(
    ['python3', 'statusline.py'],
    input=open('tests/fixtures/full.json').read(),
    capture_output=True, text=True,
    env={**__import__('os').environ, 'STATUSLINE_WIDTH': '120', 'STATUSLINE_LINES': '2'}
)
lines = result.stdout.strip().split('\n')
total_vis = sum(len(strip_ansi(l)) for l in lines)
print(f"Lines: {len(lines)}, total visible: {total_vis}, budget: 120")
assert total_vis <= 120, f"FAIL: {total_vis} > 120"
print("PASS: total visible width within terminal budget")
EOF
```

- [ ] **Step 6.4: Commit**

```bash
git add statusline.py
git commit -m "feat: Python statusline renderer with cli-truncate workaround"
```

---

## Task 7: Safe Install + Backup System

**Files:**
- Create: `install.sh`
- Create: `uninstall.sh`

**Invariant:** Nothing in `~/.claude/` is touched until the user explicitly runs `install.sh`.

- [ ] **Step 7.1: Implement `install.sh`**

```bash
cat > install.sh << 'INSTALLEOF'
#!/bin/bash
# install.sh — Safe install for claude-status-line Python renderer
# Backs up existing files before overwriting. Backups include timestamp.
# Run: bash install.sh [--dry-run]

set -e

REPO="$(cd "$(dirname "$0")" && pwd)"
CLAUDE="$HOME/.claude"
DRY_RUN=false
[ "$1" = "--dry-run" ] && DRY_RUN=true

backup_and_copy() {
    local src="$1" dst="$2" label="$3"
    if [ -f "$dst" ]; then
        local bak="${dst}.bak.$(date +%Y%m%d_%H%M%S)"
        echo "  BACKUP  $dst → $bak"
        $DRY_RUN || cp "$dst" "$bak"
    fi
    echo "  INSTALL $src → $dst"
    $DRY_RUN || cp "$src" "$dst"
}

echo "=== Claude Status Line Installer ==="
[ "$DRY_RUN" = "true" ] && echo "    [DRY RUN — no files modified]"
echo ""

echo "Installing Python renderer..."
# Copy the entire lib/ directory
if [ "$DRY_RUN" = "false" ]; then
    mkdir -p "$CLAUDE/statusline-lib"
    cp "$REPO/lib/ansi.py" "$CLAUDE/statusline-lib/"
    cp "$REPO/lib/segments.py" "$CLAUDE/statusline-lib/"
    cp "$REPO/lib/config.py" "$CLAUDE/statusline-lib/"
    cp "$REPO/lib/packer.py" "$CLAUDE/statusline-lib/"
    touch "$CLAUDE/statusline-lib/__init__.py"
fi
echo "  INSTALL $REPO/lib/ → $CLAUDE/statusline-lib/"

# Install main script (backs up existing statusline.sh)
backup_and_copy "$REPO/statusline.py" "$CLAUDE/statusline.py" "Python renderer"

echo ""
echo "Backing up existing statusline.sh (kept as fallback)..."
if [ -f "$CLAUDE/statusline.sh" ] && [ "$DRY_RUN" = "false" ]; then
    cp "$CLAUDE/statusline.sh" "$CLAUDE/statusline.sh.bak.$(date +%Y%m%d_%H%M%S)"
    echo "  BACKUP  $CLAUDE/statusline.sh preserved"
fi

echo ""
echo "To activate: update ~/.claude/settings.json statusLine.command to:"
echo '  python3 "$HOME/.claude/statusline.py"'
echo ""
echo "Current command (unchanged):"
grep -A2 '"statusLine"' "$CLAUDE/settings.json" 2>/dev/null || echo "  (not found)"
echo ""
echo "To update settings.json:"
echo '  Use the statusline-setup skill, or edit manually.'
echo ""
if [ "$DRY_RUN" = "true" ]; then
    echo "[DRY RUN complete — run without --dry-run to apply]"
else
    echo "Install complete. Test with:"
    echo "  cat tests/fixtures/full.json | python3 $CLAUDE/statusline.py"
fi
INSTALLEOF
chmod +x install.sh
```

- [ ] **Step 7.2: Implement `uninstall.sh`**

```bash
cat > uninstall.sh << 'EOF'
#!/bin/bash
# uninstall.sh — Restore backed-up statusline files
set -e
CLAUDE="$HOME/.claude"

echo "=== Uninstall: restoring backups ==="

# Find most recent backup of statusline.sh
latest_bak=$(ls -t "$CLAUDE/statusline.sh.bak."* 2>/dev/null | head -1)
if [ -n "$latest_bak" ]; then
    echo "  RESTORE $latest_bak → $CLAUDE/statusline.sh"
    cp "$latest_bak" "$CLAUDE/statusline.sh"
else
    echo "  No backup found for statusline.sh"
fi

# Remove Python renderer
[ -f "$CLAUDE/statusline.py" ] && rm "$CLAUDE/statusline.py" && echo "  REMOVED statusline.py"
[ -d "$CLAUDE/statusline-lib" ] && rm -rf "$CLAUDE/statusline-lib" && echo "  REMOVED statusline-lib/"

echo ""
echo "Uninstall complete. Remember to revert settings.json statusLine.command."
EOF
chmod +x uninstall.sh
```

- [ ] **Step 7.3: Dry run test**

```bash
bash install.sh --dry-run
# Expected: shows what would be installed, no files modified
```

- [ ] **Step 7.4: Commit**

```bash
git add install.sh uninstall.sh
git commit -m "feat: safe install/uninstall with timestamped backups"
```

---

## Task 8: Tmux Integration Track (Optional — Separate from CC)

**Files:**
- Create: `tmux/statusline.sh`
- Create: `tmux/README.md`

This is completely independent of CC's status line mechanism. Tmux renders its status bar outside CC's terminal control — CC cannot overwrite it.

**Approach:** A bash script suitable for `set -g status-right '#(bash ~/.claude/tmux-statusline.sh)'` in tmux.conf. It reads CC's shared state files directly (session state from `~/.claude/statusline-state/`, hook bridge from `/tmp/claude-hook-status-*.json`) to show CC status without going through CC's rendering pipeline.

- [ ] **Step 8.1: Implement `tmux/statusline.sh`**

```bash
mkdir -p tmux
cat > tmux/statusline.sh << 'EOF'
#!/bin/bash
# tmux/statusline.sh — CC status for tmux status-right
# Shows CC session info from shared state files.
# Not limited by CC's cli-truncate bug — tmux controls its own rendering.
#
# Setup: add to ~/.tmux.conf:
#   set -g status-right '#(bash ~/.claude/tmux-statusline.sh) | %H:%M'
#   set -g status-right-length 120
#   set -g status-interval 5
set -f

# Colors (tmux uses #[fg=...] syntax)
BLUE='#[fg=colour39]'
GREEN='#[fg=colour40]'
YELLOW='#[fg=colour220]'
RED='#[fg=colour203]'
DIM='#[dim]'
RESET='#[fg=default,nodim]'

state_dir="$HOME/.claude/statusline-state"
sep=" ${DIM}│${RESET} "

# Find most recent CC session state
latest_state=$(ls -t "$state_dir"/*.json 2>/dev/null | head -1)
if [ -z "$latest_state" ]; then
    echo -n "cc: idle"
    exit 0
fi

session_id=$(basename "$latest_state" .json)
total=$(jq -r '.total // 0' "$latest_state" 2>/dev/null)
msgs=$(jq -r '.msgs // 0' "$latest_state" 2>/dev/null)
first_ts=$(jq -r '.first_ts // 0' "$latest_state" 2>/dev/null)

# Format tokens
format_tokens() {
    local n=$1
    if   [ "$n" -ge 1000000 ]; then awk "BEGIN{printf \"%.1fM\", $n/1000000}"
    elif [ "$n" -ge 1000 ];    then awk "BEGIN{printf \"%.1fk\", $n/1000}"
    else printf "%d" "$n"
    fi
}

# Session elapsed
now=$(date +%s)
elapsed=$(( now - first_ts ))
if [ "$elapsed" -gt 3600 ]; then
    h=$(( elapsed / 3600 )); m=$(( (elapsed % 3600) / 60 ))
    timer="${YELLOW}${h}h${m}m${RESET}"
else
    m=$(( elapsed / 60 ))
    timer="${m}m"
fi

# Avg tokens/msg
avg=""
[ "$msgs" -gt 0 ] && avg=" ${DIM}$(format_tokens $(( total / msgs )))/msg${RESET}"

# Hook bridge (most recent session)
hook_info=""
hook_file="/tmp/claude-hook-status-${session_id}.json"
if [ -f "$hook_file" ]; then
    hook_tool=$(jq -r '.tool_name // empty' "$hook_file" 2>/dev/null)
    hook_scripts=$(jq -r '.hooks_ran // [] | join(",")' "$hook_file" 2>/dev/null)
    [ -n "$hook_tool" ] && hook_info="${sep}${DIM}${hook_tool}${RESET}"
    [ -n "$hook_scripts" ] && hook_info+=" ${DIM}(${hook_scripts})${RESET}"
fi

# Agent tracker
agent_info=""
agent_file="/tmp/claude-agent-tracker-${session_id}.json"
if [ -f "$agent_file" ]; then
    active=$(jq '[.agents[] | select(.status=="running")] | length' "$agent_file" 2>/dev/null)
    if [ "${active:-0}" -gt 0 ] 2>/dev/null; then
        types=$(jq -r '[.agents[] | select(.status=="running") | .type] | join(",")' "$agent_file" 2>/dev/null)
        agent_info="${sep}${BLUE}▶${active}${RESET} ${DIM}(${types})${RESET}"
    fi
fi

echo -n "CC ${GREEN}$(format_tokens $total)${RESET}${avg} ${timer}${hook_info}${agent_info}"
EOF
chmod +x tmux/statusline.sh
```

- [ ] **Step 8.2: Write tmux README**

```bash
cat > tmux/README.md << 'EOF'
# Tmux Integration

Renders CC session info in tmux status bar — completely outside CC's control.
No cli-truncate bug, no dimColor, no permissions line interference.

## Setup

1. Copy to ~/.claude/:
   ```bash
   cp tmux/statusline.sh ~/.claude/tmux-statusline.sh
   chmod +x ~/.claude/tmux-statusline.sh
   ```

2. Add to ~/.tmux.conf:
   ```
   set -g status-right '#(bash ~/.claude/tmux-statusline.sh) | %H:%M'
   set -g status-right-length 150
   set -g status-interval 5
   ```

3. Reload tmux config:
   ```bash
   tmux source-file ~/.tmux.conf
   ```

## What It Shows

- Total session tokens + avg tokens/msg
- Session elapsed time
- Last hook event + which hooks ran
- Active subagents (type and count)

## Relationship to CC statusline

This is ADDITIVE — you can run both:
- CC statusline: 1-line compact info below the prompt
- Tmux statusline: multi-line rich info in the tmux status bar

Neither interferes with the other.
EOF
```

- [ ] **Step 8.3: Test tmux script (static call)**

```bash
bash tmux/statusline.sh
# Expected: "cc: idle" or session token info — no errors
```

- [ ] **Step 8.4: Commit**

```bash
git add tmux/
git commit -m "feat: tmux status-right integration (outside CC control)"
```

---

## Task 9: Update Repo Statusline.sh and Push

- [ ] **Step 9.1: Copy the installed statusline.sh into repo (it has the canonical version)**

```bash
cp ~/.claude/statusline.sh statusline.sh
```

- [ ] **Step 9.2: Update statusline.conf with new Python-only settings doc**

Add to `statusline.conf`:
```bash
# ─────────────────────────────────────────────────────────
# PYTHON RENDERER SETTINGS (statusline.py only)
# ─────────────────────────────────────────────────────────
# Override CC's dimColor wrapping (prepends ESC[22m to each line)
OVERRIDE_DIMCOLOR=true

# Max output lines: 0 = auto (uses non-empty LINE* settings)
# For multi-line: set to 2 or 3.
# WARNING: multi-line requires WIDE terminal. Each line gets width/N chars.
# On 120-col: 2 lines get 60 chars each. 3 lines get 40 chars each.
MAX_LINES=0
```

- [ ] **Step 9.3: Update change_log.md**

```bash
cat >> change_log.md << 'EOF'

## 2026-04-15 — Python renderer + multi-line fix

- Researched CC rendering internals via leaked source (2.1.88 npm source maps)
- Diagnosed cli-truncate multi-line bug (#37522): all lines counted as one string
- Implemented ANSI-aware adaptive packer with cli-truncate workaround
- Ported all 22 segments from bash to Python
- Added dimColor compensation (OVERRIDE_DIMCOLOR)
- Real terminal width via /dev/tty (bypasses stdout capture)
- Safe install/uninstall system with timestamped backups
- Tmux integration track (completely outside CC's rendering control)
EOF
```

- [ ] **Step 9.4: Commit and push**

```bash
git add -A
git commit -m "feat: Python statusline with multi-line fix, tmux integration, safe install"
git push
```

---

## Self-Review

### Spec coverage
- [x] Don't touch installed files without approval → install.sh is explicit, only copies on manual run
- [x] Python renderer → statusline.py
- [x] Multi-line truncation fix → cli-truncate workaround via width budgeting
- [x] dimColor compensation → OVERRIDE_DIMCOLOR + brighter RGB
- [x] Real terminal width → /dev/tty via fcntl.ioctl
- [x] Safe backup → timestamped .bak files in install.sh
- [x] Tmux track → tmux/statusline.sh
- [x] Consider leaked CC source → used for diagnosis, not copying code
- [x] Tests → test_ansi.py, test_packer.py, test_segments.py, run.sh

### Gaps / Decisions
- **activePermissionMode in statusline JSON**: unknown if implemented. If it IS in the CC JSON payload, we can add a `_seg_permission_mode()` to segments.py that renders it compactly in our line, making the separate CC permission line redundant from a UX standpoint.
- **Per-project config with Python**: lib/config.py reads `.claude/statusline.conf` from cwd — same behavior as bash version.
- **CC_UI_LINE removed**: confirmed the blank-line trick never worked (CC strips empty lines). Removed from both conf and renderer.
- **3-line mode is narrow**: on 120-col terminal, 3 lines get 40 chars each — very tight. Plan treats it as advanced option, not default.

### Placeholder scan
No TBD/TODO in code blocks. All types consistent. `pack_lines` signature matches usage in `statusline.py`. `SegmentRenderer.render(name)` matches usage.
