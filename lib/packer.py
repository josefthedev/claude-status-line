# lib/packer.py
from lib.ansi import visible_width

DIM = '\033[2m'
RESET = '\033[0m'

def pack_lines(
    line_defs: list,             # list of lists of segment names
    renderer,                    # SegmentRenderer instance
    budget,                      # int (equal per-line) or list[int] (per-line budgets)
    sep_char: str = '│',         # from config SEP_CHAR
) -> list:                       # list of str, one per line_def
    sep = f' {DIM}{sep_char}{RESET} '
    sep_width = visible_width(sep)
    budgets = budget if isinstance(budget, list) else [budget] * len(line_defs)
    result = []
    for line_budget, names in zip(budgets, line_defs):
        line = ''
        prev_name = None
        for name in names:
            rendered = renderer.render(name)
            if rendered is None:
                continue
            seg_width = visible_width(rendered)
            if not line:
                if seg_width <= line_budget:
                    line = rendered
                    prev_name = name
            else:
                if name == 'git_status' and prev_name == 'git_branch':
                    candidate = line + ' ' + rendered
                    if visible_width(candidate) <= line_budget:
                        line = candidate
                        prev_name = name
                else:
                    candidate = line + sep + rendered
                    if visible_width(candidate) <= line_budget:
                        line = candidate
                        prev_name = name
        result.append(line)
    return result
