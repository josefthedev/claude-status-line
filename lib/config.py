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
