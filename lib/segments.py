"""Segment renderers — port of bash statusline.sh render_segment() to Python.

Each segment returns an ANSI-colored string or None if data is missing/empty.
Colors use 24-bit RGB (brighter than bash dim defaults).
"""

import json
import os
import subprocess
import time

BLUE   = '\033[38;2;0;153;255m'
ORANGE = '\033[38;2;255;176;85m'
GREEN  = '\033[38;2;0;175;80m'
RED    = '\033[38;2;255;85;85m'
YELLOW = '\033[38;2;230;200;0m'
WHITE  = '\033[38;2;220;220;220m'
DIM    = '\033[2m'
RESET  = '\033[0m'


class SegmentRenderer:
    def __init__(self, data: dict, config: dict):
        self.data = data
        self.config = config
        self._extract_data()

    def _extract_data(self):
        """Pre-extract values from CC JSON, mirroring bash lines 110-144."""
        model = self.data.get('model', {})
        self.model_name = model.get('display_name', 'Claude')
        self.model_id = model.get('id', '')

        ctx = self.data.get('context_window', {})
        self.context_window_size = ctx.get('context_window_size', 200000) or 200000
        usage = ctx.get('current_usage', {})
        self.input_tokens = usage.get('input_tokens', 0)
        self.cache_creation = usage.get('cache_creation_input_tokens', 0)
        self.cache_read = usage.get('cache_read_input_tokens', 0)
        self.current = self.input_tokens + self.cache_creation + self.cache_read
        self.pct_used = (self.current * 100 // self.context_window_size) if self.context_window_size > 0 else 0

        self.session_in = ctx.get('total_input_tokens', 0)
        self.session_out = ctx.get('total_output_tokens', 0)
        self.session_total = self.session_in + self.session_out

        self.cache_pct = (self.cache_read * 100 // self.current) if self.current > 0 else 0

        rate = self.data.get('rate_limits', {})
        five = rate.get('five_hour', {})
        self.five_pct = five.get('used_percentage')
        if self.five_pct is not None:
            self.five_pct = int(round(self.five_pct))
        self.five_reset_epoch = five.get('resets_at')

        seven = rate.get('seven_day', {})
        self.seven_pct = seven.get('used_percentage')
        if self.seven_pct is not None:
            self.seven_pct = int(round(self.seven_pct))
        self.seven_reset_epoch = seven.get('resets_at')

        self.cwd = self.data.get('cwd', '') or os.getcwd()
        self.cwd_basename = os.path.basename(self.cwd)
        self.session_id = self.data.get('session_id', '')

        # Effort: env var > settings files > "auto"
        self.effort = os.environ.get('CLAUDE_CODE_EFFORT_LEVEL', '')
        if not self.effort:
            for sf in ['.claude/settings.local.json', '.claude/settings.json',
                       os.path.expanduser('~/.claude/settings.local.json'),
                       os.path.expanduser('~/.claude/settings.json')]:
                try:
                    with open(sf) as f:
                        val = json.load(f).get('effortLevel')
                        if val:
                            self.effort = val
                            break
                except (FileNotFoundError, json.JSONDecodeError, PermissionError):
                    pass
        if not self.effort:
            self.effort = 'auto'

        # Git data (lazy — computed once on first git segment access)
        self._git_computed = False
        self._git_branch = ''
        self._git_info = ''
        self._worktree_name = ''

        # Session state (lazy)
        self._session_state_loaded = False
        self._avg_tokens_per_msg = 0
        self._session_first_ts = 0
        self._all_sessions_avg = 0

        # Hook state (lazy)
        self._hook_loaded = False
        self._hook_event_name = ''
        self._hook_tool_name = ''
        self._hook_scripts = ''
        self._hookify_configured = False
        self._hookify_match_text = ''

        # GSD state (lazy)
        self._gsd_loaded = False
        self._gsd_phase_num = ''
        self._gsd_status = ''
        self._gsd_completed_phases = ''
        self._gsd_total_phases = ''
        self._gsd_completed_plans = ''
        self._gsd_total_plans = ''

        # Plugins (lazy)
        self._plugins_loaded = False
        self._plugins_count = 0

    @staticmethod
    def _color_for_pct(pct: int) -> str:
        """Color threshold matching bash color_for_pct (line 43-49)."""
        if pct >= 90: return RED
        if pct >= 70: return YELLOW
        if pct >= 50: return ORANGE
        return GREEN

    @staticmethod
    def _color_for_cache_pct(pct: int) -> str:
        """Color threshold matching bash color_for_cache_pct (line 52-58)."""
        if pct >= 70: return GREEN
        if pct >= 40: return YELLOW
        if pct >= 15: return ORANGE
        return RED

    @staticmethod
    def _build_bar(pct: int, width: int = 6) -> str:
        """Build ▓░ bar with color, matching bash build_bar (line 61-72)."""
        pct = max(0, min(100, pct))
        filled = pct * width // 100
        empty = width - filled
        color = SegmentRenderer._color_for_pct(pct)
        return f"{color}{'▓' * filled}{'░' * empty}{RESET}"

    @staticmethod
    def _format_tokens(n: int) -> str:
        """Format token count: 1.2M, 34.5k, 123. Matching bash format_tokens (line 97-103)."""
        if n >= 1_000_000:
            return f"{n / 1_000_000:.1f}M"
        if n >= 1000:
            return f"{n / 1000:.1f}k"
        return str(n)

    @staticmethod
    def _format_ttl_epoch(val) -> str | None:
        """Format epoch or ISO string to '2d3h', '4h5m', '12m', 'now'.
        Matching bash format_ttl_epoch (line 74-95)."""
        if val is None or val == '' or val == 'null':
            return None
        if isinstance(val, (int, float)):
            epoch = int(val)
        elif isinstance(val, str):
            if val.isdigit():
                epoch = int(val)
            else:
                try:
                    from datetime import datetime, timezone
                    dt = datetime.fromisoformat(val.replace('Z', '+00:00'))
                    epoch = int(dt.timestamp())
                except (ValueError, TypeError):
                    return None
        else:
            return None
        now = int(time.time())
        diff = epoch - now
        if diff <= 0:
            return 'now'
        days = diff // 86400
        hours = (diff % 86400) // 3600
        mins = (diff % 3600) // 60
        if days > 0:
            return f"{days}d{hours}h"
        if hours > 0:
            return f"{hours}h{mins}m"
        return f"{mins}m"

    def _lbl(self, text: str) -> str:
        """Dim label prefix if SHOW_LABELS=true. Matching bash lbl (line 105-107)."""
        if self.config.get('SHOW_LABELS', True):
            return f"{DIM}{text}:{RESET} "
        return ''

    def _estimate_cost(self) -> str | None:
        """Estimate session cost. Matching bash estimate_cost (line 358-373)."""
        if self.session_total <= 0:
            return None
        price_opus = self.config.get('PRICE_OPUS', '15 75')
        price_sonnet = self.config.get('PRICE_SONNET', '3 15')
        price_haiku = self.config.get('PRICE_HAIKU', '0.80 4')

        ident = (self.model_id + self.model_name).lower()
        if 'opus' in ident:
            prices = price_opus
        elif 'haiku' in ident:
            prices = price_haiku
        else:
            prices = price_sonnet

        if isinstance(prices, str):
            parts = prices.split()
        else:
            parts = [str(p) for p in prices]
        in_p, out_p = float(parts[0]), float(parts[1])
        cost = (self.session_in * in_p + self.session_out * out_p) / 1_000_000
        if cost < 0.001:
            return f"${cost:.5f}"
        if cost < 0.01:
            return f"${cost:.4f}"
        if cost < 0.10:
            return f"${cost:.3f}"
        return f"${cost:.2f}"

    def _ensure_git(self):
        """Compute git branch, status, worktree once. Matching bash lines 150-182."""
        if self._git_computed:
            return
        self._git_computed = True
        cwd = self.cwd
        try:
            r = subprocess.run(['git', '-C', cwd, 'rev-parse', '--is-inside-work-tree'],
                               capture_output=True, text=True, timeout=5)
            if r.returncode != 0:
                return
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return

        # Branch
        r = subprocess.run(['git', '-C', cwd, 'symbolic-ref', '--short', 'HEAD'],
                           capture_output=True, text=True, timeout=5)
        self._git_branch = r.stdout.strip() if r.returncode == 0 else ''

        # Ahead/behind + porcelain
        info_parts = []
        r = subprocess.run(['git', '-C', cwd, 'rev-parse', '--abbrev-ref', '@{upstream}'],
                           capture_output=True, text=True, timeout=5)
        if r.returncode == 0 and r.stdout.strip():
            r2 = subprocess.run(['git', '-C', cwd, 'rev-list', '--count', '@{upstream}..HEAD'],
                                capture_output=True, text=True, timeout=5)
            ahead = int(r2.stdout.strip()) if r2.returncode == 0 else 0
            r3 = subprocess.run(['git', '-C', cwd, 'rev-list', '--count', 'HEAD..@{upstream}'],
                                capture_output=True, text=True, timeout=5)
            behind = int(r3.stdout.strip()) if r3.returncode == 0 else 0
            if ahead > 0:
                info_parts.append(f"{GREEN}↑{ahead}{RESET}")
            if behind > 0:
                info_parts.append(f"{RED}↓{behind}{RESET}")

        r = subprocess.run(['git', '-C', cwd, 'status', '--porcelain'],
                           capture_output=True, text=True, timeout=5)
        if r.returncode == 0 and r.stdout.strip():
            lines = r.stdout.strip().split('\n')
            staged = sum(1 for l in lines if len(l) >= 1 and l[0] in 'MADRCT')
            unstaged = sum(1 for l in lines if len(l) >= 2 and l[1] in 'MADRCT?')
            if staged > 0:
                info_parts.append(f"{YELLOW}+{staged}{RESET}")
            if unstaged > 0:
                info_parts.append(f"{ORANGE}~{unstaged}{RESET}")
        self._git_info = ''.join(info_parts)

        # Worktree detection (bash lines 171-182)
        r = subprocess.run(['git', '-C', cwd, 'worktree', 'list', '--porcelain'],
                           capture_output=True, text=True, timeout=5)
        if r.returncode == 0:
            wt_lines = [l for l in r.stdout.split('\n') if l.startswith('worktree ')]
            if len(wt_lines) > 1:
                main_wt = wt_lines[0].replace('worktree ', '', 1)
                real_cwd = os.path.realpath(cwd)
                if real_cwd != main_wt:
                    self._worktree_name = os.path.basename(real_cwd)

    def _ensure_session_state(self):
        """Load session state file for avg_tokens and session_timer. Matching bash lines 189-251."""
        if self._session_state_loaded:
            return
        self._session_state_loaded = True
        if not self.session_id or self.session_total <= 0:
            return

        state_dir = os.path.expanduser('~/.claude/statusline-state')
        os.makedirs(state_dir, exist_ok=True)
        state_file = os.path.join(state_dir, f'{self.session_id}.json')
        now_epoch = int(time.time())

        if os.path.isfile(state_file):
            try:
                with open(state_file) as f:
                    state = json.load(f)
            except (json.JSONDecodeError, PermissionError):
                state = {}
            prev_total = state.get('total', 0)
            msg_count = state.get('msgs', 0)
            self._session_first_ts = state.get('first_ts', 0) or now_epoch
            history = state.get('history', '')

            if self.session_total > prev_total:
                msg_count += 1
                self._avg_tokens_per_msg = self.session_total // msg_count
                h_list = [x for x in history.split(',') if x] if history else []
                h_list.append(str(self._avg_tokens_per_msg))
                h_list = h_list[-8:]
                history = ','.join(h_list)
                with open(state_file, 'w') as f:
                    json.dump({'total': self.session_total, 'msgs': msg_count,
                               'ts': now_epoch, 'first_ts': self._session_first_ts,
                               'history': history}, f)
            else:
                if msg_count > 0:
                    self._avg_tokens_per_msg = self.session_total // msg_count
        else:
            self._session_first_ts = now_epoch
            self._avg_tokens_per_msg = self.session_total
            with open(state_file, 'w') as f:
                json.dump({'total': self.session_total, 'msgs': 1,
                           'ts': now_epoch, 'first_ts': now_epoch,
                           'history': str(self.session_total)}, f)

        # Cross-session average (bash lines 238-251)
        if os.path.isdir(state_dir):
            all_total = 0
            all_msgs = 0
            try:
                for fname in os.listdir(state_dir):
                    if not fname.endswith('.json'):
                        continue
                    fpath = os.path.join(state_dir, fname)
                    try:
                        with open(fpath) as f:
                            s = json.load(f)
                        all_total += s.get('total', 0)
                        all_msgs += s.get('msgs', 0)
                    except (json.JSONDecodeError, PermissionError):
                        pass
            except PermissionError:
                pass
            if all_msgs > 0:
                self._all_sessions_avg = all_total // all_msgs

    def _ensure_hook_state(self):
        """Load hook bridge state. Matching bash lines 253-271."""
        if self._hook_loaded:
            return
        self._hook_loaded = True
        if not self.session_id:
            return
        hook_file = f'/tmp/claude-hook-status-{self.session_id}.json'
        if not os.path.isfile(hook_file):
            return
        try:
            with open(hook_file) as f:
                h = json.load(f)
        except (json.JSONDecodeError, PermissionError):
            return
        self._hook_event_name = h.get('hook_event', '')
        self._hook_tool_name = h.get('tool_name', '')
        hooks_ran = h.get('hooks_ran', [])
        self._hook_scripts = ','.join(hooks_ran) if isinstance(hooks_ran, list) else str(hooks_ran)
        self._hookify_configured = h.get('hookify_configured', False)
        hookify_rules = h.get('hookify_rules', [])
        if hookify_rules:
            self._hookify_match_text = ', '.join(
                f"{r.get('name', '')} ({r.get('action', '')})" for r in hookify_rules
            )

    def _ensure_gsd_state(self):
        """Load GSD state from .planning/STATE.md. Matching bash lines 274-292."""
        if self._gsd_loaded:
            return
        self._gsd_loaded = True
        state_md = os.path.join(self.cwd, '.planning', 'STATE.md')
        if not os.path.isfile(state_md):
            return
        try:
            with open(state_md) as f:
                content = f.read()
        except (PermissionError, FileNotFoundError):
            return

        # Parse YAML frontmatter between first two --- lines
        parts = content.split('---', 2)
        if len(parts) >= 3:
            fm = parts[1]
            for line in fm.split('\n'):
                line = line.strip()
                if line.startswith('status:'):
                    self._gsd_status = line.split(':', 1)[1].strip().strip('"')
                elif line.startswith('completed_phases:'):
                    self._gsd_completed_phases = line.split(':', 1)[1].strip()
                elif line.startswith('total_phases:'):
                    self._gsd_total_phases = line.split(':', 1)[1].strip()
                elif line.startswith('completed_plans:'):
                    self._gsd_completed_plans = line.split(':', 1)[1].strip()
                elif line.startswith('total_plans:'):
                    self._gsd_total_plans = line.split(':', 1)[1].strip()

        # Phase number from body: "Phase: N"
        for line in content.split('\n'):
            if line.startswith('Phase:'):
                self._gsd_phase_num = line.split(':', 1)[1].strip()
                break

    def _ensure_plugins(self):
        """Load plugin count from settings. Matching bash lines 294-304."""
        if self._plugins_loaded:
            return
        self._plugins_loaded = True
        for sf in [os.path.expanduser('~/.claude/settings.json'),
                   os.path.expanduser('~/.claude/settings.local.json')]:
            try:
                with open(sf) as f:
                    data = json.load(f)
                pc = len(data.get('plugins', []))
                if pc > 0:
                    self._plugins_count = pc
                    break
            except (FileNotFoundError, json.JSONDecodeError, PermissionError):
                pass

    def _format_time_to_exhaust(self, pct, reset_epoch, window_secs: int) -> str | None:
        """Matching bash format_time_to_exhaust (lines 307-327)."""
        if pct is None or reset_epoch is None:
            return None
        if pct <= 0:
            return None
        if pct >= 100:
            return 'now'
        now = int(time.time())
        if isinstance(reset_epoch, str):
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(reset_epoch.replace('Z', '+00:00'))
                reset_epoch = int(dt.timestamp())
            except (ValueError, TypeError):
                return None
        reset_epoch = int(reset_epoch)
        window_start = reset_epoch - window_secs
        elapsed = now - window_start
        if elapsed <= 0:
            return None
        remaining_secs = int(elapsed * (100 - pct) / pct)
        if remaining_secs <= 0:
            return 'now'
        days = remaining_secs // 86400
        hours = (remaining_secs % 86400) // 3600
        mins = (remaining_secs % 3600) // 60
        if days > 0:
            return f"{days}d{hours}h"
        if hours > 0:
            return f"{hours}h{mins}m"
        return f"{mins}m"

    def _exhaust_secs(self, pct, reset_epoch, window_secs: int) -> int:
        """Return remaining seconds estimate (for downtime calc)."""
        if pct is None or reset_epoch is None or pct <= 0:
            return 0
        now = int(time.time())
        if isinstance(reset_epoch, str):
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(reset_epoch.replace('Z', '+00:00'))
                reset_epoch = int(dt.timestamp())
            except (ValueError, TypeError):
                return 0
        reset_epoch = int(reset_epoch)
        ws = now - (reset_epoch - window_secs)
        if ws <= 0 or pct <= 0:
            return 0
        return int(ws * (100 - pct) / pct)

    def _render_rate(self, label: str, pct, epoch) -> str | None:
        """Matching bash render_rate (lines 376-393)."""
        if pct is None:
            return None
        style = self.config.get('RATE_STYLE', 'bar_pct')
        if style == 'off':
            return None
        bar_width = self.config.get('BAR_WIDTH', 6)
        if isinstance(bar_width, str):
            bar_width = int(bar_width)
        color = self._color_for_pct(pct)
        out = f"{DIM}{label}{RESET} "
        if style == 'bar_pct':
            out += f"{self._build_bar(pct, bar_width)} {color}{pct}%{RESET}"
        elif style == 'pct':
            out += f"{color}{pct}%{RESET}"
        elif style == 'bar':
            out += self._build_bar(pct, bar_width)
        if self.config.get('SHOW_TTL', True) and epoch is not None and epoch != 'null':
            ttl = self._format_ttl_epoch(epoch)
            if ttl:
                out += f" {WHITE}{ttl}{RESET}"
        return out

    def render(self, name: str) -> str | None:
        """Render a named segment. Returns ANSI string or None."""
        method = getattr(self, f'_seg_{name}', None)
        if method is None:
            return None
        try:
            return method()
        except Exception:
            return None

    def _seg_model(self) -> str | None:
        return f"{BLUE}{self.model_name}{RESET}"

    def _seg_context_pct(self) -> str | None:
        color = self._color_for_pct(self.pct_used)
        return f"{color}{self.pct_used}%{RESET}"

    def _seg_tokens(self) -> str | None:
        if self.session_total <= 0:
            return None
        style = self.config.get('TOKEN_STYLE', 'total')
        if style == 'in_out':
            return (f"{self._lbl('tokens')}{WHITE}"
                    f"↑{self._format_tokens(self.session_in)} "
                    f"↓{self._format_tokens(self.session_out)}{RESET}")
        return f"{self._lbl('tokens')}{WHITE}{self._format_tokens(self.session_total)}{RESET}"

    def _seg_cost(self) -> str | None:
        if self.session_total <= 0:
            return None
        c = self._estimate_cost()
        if c is None:
            return None
        return f"{self._lbl('cost')}{WHITE}{c}{RESET}"

    def _seg_cache_pct(self) -> str | None:
        if self.current <= 0:
            return None
        cc = self._color_for_cache_pct(self.cache_pct)
        return f"{self._lbl('cache')}{cc}{self.cache_pct}%{RESET}"

    def _seg_effort(self) -> str | None:
        color = DIM
        if self.effort == 'low':
            color = GREEN
        elif self.effort == 'medium':
            color = YELLOW
        elif self.effort == 'high':
            color = ORANGE
        elif self.effort == 'max':
            color = RED
        return f"{self._lbl('effort')}{color}{self.effort}{RESET}"

    def _seg_cwd(self) -> str | None:
        return f"{WHITE}{self.cwd_basename}{RESET}"

    def _seg_git_branch(self) -> str | None:
        self._ensure_git()
        if not self._git_branch:
            return None
        branch = self._git_branch
        max_len = self.config.get('GIT_BRANCH_MAX', 20)
        if isinstance(max_len, str):
            max_len = int(max_len)
        if len(branch) > max_len:
            branch = branch[:max_len - 1] + '…'
        return f"{GREEN}{branch}{RESET}"

    def _seg_git_status(self) -> str | None:
        self._ensure_git()
        return self._git_info or None

    def _seg_worktree(self) -> str | None:
        self._ensure_git()
        if not self._worktree_name:
            return None
        return f"{DIM}wt:{RESET}{YELLOW}{self._worktree_name}{RESET}"

    def _seg_rate_5h(self) -> str | None:
        return self._render_rate('5h', self.five_pct, self.five_reset_epoch)

    def _seg_rate_7d(self) -> str | None:
        return self._render_rate('7d', self.seven_pct, self.seven_reset_epoch)

    def _seg_avg_tokens(self) -> str | None:
        self._ensure_session_state()
        if self._avg_tokens_per_msg <= 0:
            return None
        fmt = self._format_tokens(self._avg_tokens_per_msg)
        pct_str = ''
        if self._all_sessions_avg > 0:
            pct_of = self._avg_tokens_per_msg * 100 / self._all_sessions_avg
            all_fmt = self._format_tokens(self._all_sessions_avg)
            pct_str = f" {DIM}({pct_of:.2f}% of {all_fmt}){RESET}"
        return f"{self._lbl('tkns/msg')}{WHITE}{fmt}{RESET}{pct_str}"

    def _seg_session_timer(self) -> str | None:
        self._ensure_session_state()
        if self._session_first_ts <= 0:
            return None
        now = int(time.time())
        elapsed = now - self._session_first_ts
        if elapsed <= 60:
            return None
        h = elapsed // 3600
        m = (elapsed % 3600) // 60
        if h > 0:
            timer_str = f"{h}h{m}m"
            color = ORANGE
        else:
            timer_str = f"{m}m"
            color = WHITE
        return f"{self._lbl('session')}{color}{timer_str}{RESET}"

    def _seg_exhaust_5h(self) -> str | None:
        exhaust = self._format_time_to_exhaust(self.five_pct, self.five_reset_epoch, 18000)
        if not exhaust:
            return None
        color = self._color_for_pct(self.five_pct or 0)
        return f"{DIM}5h out in{RESET} {color}{exhaust}{RESET}"

    def _seg_exhaust_7d(self) -> str | None:
        exhaust = self._format_time_to_exhaust(self.seven_pct, self.seven_reset_epoch, 604800)
        if not exhaust:
            return None
        color = self._color_for_pct(self.seven_pct or 0)
        return f"{DIM}7d out in{RESET} {color}{exhaust}{RESET}"

    def _seg_downtime(self) -> str | None:
        if self.five_pct is None or self.five_reset_epoch is None:
            return None
        five_exhaust_secs = self._exhaust_secs(self.five_pct, self.five_reset_epoch, 18000)
        if five_exhaust_secs <= 0:
            return None
        now = int(time.time())
        reset_ep = self.five_reset_epoch
        if isinstance(reset_ep, str):
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(reset_ep.replace('Z', '+00:00'))
                reset_ep = int(dt.timestamp())
            except (ValueError, TypeError):
                return None
        time_to_reset = int(reset_ep) - now
        downtime_secs = time_to_reset - five_exhaust_secs
        if downtime_secs <= 0:
            return f"{GREEN}no downtime{RESET}"
        d_hrs = downtime_secs // 3600
        d_mins = (downtime_secs % 3600) // 60
        dt_str = f"{d_hrs}h{d_mins}m" if d_hrs > 0 else f"{d_mins}m"
        color = RED if downtime_secs > 3600 else ORANGE
        return f"{DIM}downtime:{RESET} {color}{dt_str}{RESET} {DIM}at this rate{RESET}"

    def _seg_hook(self) -> str | None:
        self._ensure_hook_state()
        if not self._hook_event_name:
            return None
        display = self._hook_tool_name or self._hook_event_name
        if self._hook_scripts:
            display += f" {DIM}({self._hook_scripts}){RESET}"
        return f"{self._lbl('hooks')}{WHITE}{display}{RESET}"

    def _seg_hookify_rule(self) -> str | None:
        self._ensure_hook_state()
        if not self._hookify_configured or not self._hookify_match_text:
            return None
        rule_color = RED if '(block)' in self._hookify_match_text else YELLOW
        rule_count = len([x for x in self._hookify_match_text.split(',') if x.strip()])
        return f"{DIM}rule:{RESET}{rule_color}{rule_count}{RESET}"

    def _seg_agents(self) -> str | None:
        if not self.session_id:
            return None
        tracker_file = f'/tmp/claude-agent-tracker-{self.session_id}.json'
        if not os.path.isfile(tracker_file):
            return None
        try:
            with open(tracker_file) as f:
                data = json.load(f)
        except (json.JSONDecodeError, PermissionError):
            return None
        agents = data.get('agents', [])
        active = [a for a in agents if a.get('status') == 'running']
        done = [a for a in agents if a.get('status') == 'done']
        if active:
            types = ','.join(a.get('type', '') for a in active)
            return f"{self._lbl('agents')}{BLUE}{len(active)}{RESET} {DIM}({types}){RESET}"
        if done:
            return f"{self._lbl('agents')}{DIM}{len(done)} done{RESET}"
        return None

    def _seg_plugins(self) -> str | None:
        self._ensure_plugins()
        if self._plugins_count <= 0:
            return None
        return f"{self._lbl('plugins')}{WHITE}{self._plugins_count}{RESET}"

    def _seg_gsd_phase(self) -> str | None:
        self._ensure_gsd_state()
        if not self._gsd_phase_num:
            return None
        color = WHITE
        status_str = ''
        s = self._gsd_status
        if s == 'executing':
            color = BLUE; status_str = f" {DIM}[exec]{RESET}"
        elif s == 'verifying':
            color = YELLOW; status_str = f" {DIM}[verify]{RESET}"
        elif s == 'complete':
            color = GREEN; status_str = f" {DIM}[done]{RESET}"
        elif s == 'planning':
            color = DIM; status_str = f" {DIM}[plan]{RESET}"
        return f"{self._lbl('phase')}{color}{self._gsd_phase_num}{RESET}{status_str}"

    def _seg_gsd_progress(self) -> str | None:
        self._ensure_gsd_state()
        if not self._gsd_completed_phases:
            return None
        phases_str = f"{self._gsd_completed_phases}/{self._gsd_total_phases}"
        plans_str = ''
        if self._gsd_completed_plans:
            plans_str = f" {DIM}{self._gsd_completed_plans}/{self._gsd_total_plans}p{RESET}"
        return f"{self._lbl('gsd')}{WHITE}{phases_str}{DIM}ph{RESET}{plans_str}"
