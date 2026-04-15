# Phase 6: Main Python Entry Point - Context

**Gathered:** 2026-04-15
**Status:** Ready for planning
**Mode:** Auto-generated (infrastructure phase)

<domain>
## Phase Boundary

Implement `statusline.py` — the main entry point that reads CC JSON from stdin, detects terminal width via /dev/tty, loads config, renders segments, packs lines with the cli-truncate workaround, applies dimColor compensation, and outputs to stdout. Also update `tests/run.sh` to actually test statusline.py end-to-end with the fixture JSONs.

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion

**Terminal width detection (CRITICAL — must use /dev/tty, not stdout):**
```python
import fcntl, termios, struct, os

def get_terminal_width() -> int:
    # CC captures stdout, so tput/shutil.get_terminal_size() return 80
    # Must read from /dev/tty directly
    try:
        with open('/dev/tty') as tty:
            ws = struct.unpack('hh', fcntl.ioctl(tty, termios.TIOCGWINSZ, b'\0' * 4))
            if ws[1] > 0:
                return ws[1]
    except Exception:
        pass
    # Env var override (used in tests)
    try:
        return int(os.environ.get('STATUSLINE_WIDTH', '0')) or 80
    except ValueError:
        return 80
```

**cli-truncate workaround (CRITICAL):**
- CC passes output through cli-truncate which sums visible widths of ALL lines
- If each line ≤ terminal_width // n_lines, total ≤ terminal_width → no truncation
- Formula: `budget = terminal_width // n_lines` for each line
- Reserve ~4 chars right margin: `budget = (terminal_width - 4) // n_lines`

**dimColor compensation (CRITICAL):**
- CC wraps statusline in `<Text dimColor>` which prepends `\033[2m` to all output
- Fix: prepend `\033[22m` (normal intensity) to each output line to cancel dim
- `NORMAL_INTENSITY = '\033[22m'`

**Main flow:**
```python
import sys, json, os
from lib.config import load_config
from lib.segments import SegmentRenderer
from lib.packer import pack_lines

NORMAL_INTENSITY = '\033[22m'

def main():
    data = json.load(sys.stdin)
    cwd = data.get('cwd', '') or os.getcwd()
    config = load_config(cwd=cwd)
    
    width = get_terminal_width()
    
    # Build line definitions from config
    line_defs = []
    for key in ['LINE1', 'LINE2', 'LINE3']:
        val = config.get(key, '')
        if val:
            line_defs.append(val.split())
    if not line_defs:
        line_defs = [['model', 'context_pct', 'cwd', 'git_branch', 'git_status']]
    
    n_lines = len(line_defs)
    budget = max(20, (width - 4) // n_lines)
    
    renderer = SegmentRenderer(data, config)
    sep_char = config.get('SEP_CHAR', '│')
    
    lines = pack_lines(line_defs, renderer, budget, sep_char=sep_char)
    
    # Apply dimColor compensation and output
    output = '\n'.join(NORMAL_INTENSITY + line for line in lines if line)
    print(output, end='')

if __name__ == '__main__':
    main()
```

**STATUSLINE_WIDTH env var:** used in tests to override terminal width (already in tests/run.sh)

**Graceful empty input:** if stdin is empty or not valid JSON, output "Claude" and exit 0

**Integration tests in tests/run.sh:**
- `STATUSLINE_WIDTH=120 python3 statusline.py < tests/fixtures/minimal.json`
- `STATUSLINE_WIDTH=120 python3 statusline.py < tests/fixtures/full.json`
- `STATUSLINE_WIDTH=40 python3 statusline.py < tests/fixtures/narrow.json`
- Each must exit 0 and produce non-empty output

**Note:** do NOT overwrite `~/.claude/statusline.sh` — that's install.sh's job (Phase 7)

</decisions>

<code_context>
## Existing Code Insights

### Existing Structure
- `lib/config.py` — `load_config(cwd=None) -> dict`
- `lib/segments.py` — `SegmentRenderer(data, config).render(name) -> str | None`
- `lib/packer.py` — `pack_lines(line_defs, renderer, budget, sep_char) -> list[str]`
- `lib/ansi.py` — `visible_width(s) -> int`
- `tests/fixtures/minimal.json`, `full.json`, `narrow.json` — exist
- `tests/run.sh` — exists, currently just runs unittest discover

### Integration Points
- `statusline.py` is the final output: CC calls `python3 statusline.py`
- After Phase 7 install.sh will copy it to `~/.claude/`

</code_context>

<specifics>
## Specific Ideas

- `statusline.py` should be runnable: `echo '{"model":{"display_name":"Claude"}}' | python3 statusline.py`
- Keep it short (~60 lines) — just wiring, no business logic

</specifics>

<deferred>
## Deferred Ideas

None — infrastructure phase.

</deferred>
