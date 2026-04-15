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
