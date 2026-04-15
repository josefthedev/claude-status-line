#!/usr/bin/env python3
"""Claude Code statusline renderer.

Reads CC JSON from stdin, detects terminal width via /dev/tty,
loads config, renders segments, packs lines, outputs ANSI text.
"""

import fcntl
import json
import os
import struct
import sys
import termios

from lib.config import load_config
from lib.segments import SegmentRenderer
from lib.packer import pack_lines

NORMAL_INTENSITY = '\033[22m'


def get_terminal_width() -> int:
    """Detect terminal width from /dev/tty (not stdout, which CC captures).

    Falls back to STATUSLINE_WIDTH env var, then 80.
    """
    try:
        with open('/dev/tty') as tty:
            ws = struct.unpack('hh', fcntl.ioctl(tty, termios.TIOCGWINSZ, b'\0' * 4))
            if ws[1] > 0:
                return ws[1]
    except Exception:
        pass
    try:
        return int(os.environ.get('STATUSLINE_WIDTH', '0')) or 80
    except ValueError:
        return 80


def main():
    # Read JSON from stdin; graceful fallback on bad input
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        print('Claude', end='')
        return

    if not isinstance(data, dict):
        print('Claude', end='')
        return

    cwd = data.get('cwd', '') or os.getcwd()
    config = load_config(cwd=cwd)

    width = get_terminal_width()

    # Build line definitions from config
    line_defs = []
    for key in ['LINE1', 'LINE2', 'LINE3']:
        val = config.get(key, '')
        if val:
            if isinstance(val, list):
                line_defs.append(val)
            else:
                line_defs.append(str(val).split())
    if not line_defs:
        line_defs = [['model', 'context_pct', 'cwd', 'git_branch', 'git_status']]

    n_lines = len(line_defs)
    # Proportional budgets: line 1 gets more (it's the densest).
    # Total visible chars across all lines must stay ≤ terminal_width
    # to avoid cli-truncate's multi-line bug (#37522).
    total = max(40, width - (n_lines - 1))  # subtract newline chars
    if n_lines == 1:
        budgets = [total]
    elif n_lines == 2:
        budgets = [int(total * 0.55), total - int(total * 0.55)]
    elif n_lines == 3:
        b1 = int(total * 0.45)
        b2 = int(total * 0.35)
        budgets = [b1, b2, total - b1 - b2]
    else:
        per = total // n_lines
        budgets = [per] * n_lines

    renderer = SegmentRenderer(data, config)
    sep_char = config.get('SEP_CHAR', '│')

    lines = pack_lines(line_defs, renderer, budgets, sep_char=sep_char)

    # Apply dimColor compensation and output
    output = '\n'.join(NORMAL_INTENSITY + line for line in lines if line)
    print(output, end='')


if __name__ == '__main__':
    main()
