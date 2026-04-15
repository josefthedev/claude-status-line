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
