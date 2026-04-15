"""Tests for lib/segments.py — segment renderers."""

import json
import os
import subprocess
import tempfile
import time
import unittest
import unittest.mock as mock
from unittest.mock import MagicMock, mock_open, patch

from lib.segments import (
    BLUE, DIM, GREEN, ORANGE, RED, RESET, WHITE, YELLOW, SegmentRenderer,
)


def _make(data=None, config=None):
    """Create a SegmentRenderer with minimal data/config, suppressing settings file reads."""
    data = data or {}
    config = config or {}
    with patch('builtins.open', side_effect=FileNotFoundError):
        r = SegmentRenderer(data, config)
    return r


class TestColorHelpers(unittest.TestCase):
    def test_color_for_pct_green(self):
        self.assertEqual(SegmentRenderer._color_for_pct(30), GREEN)

    def test_color_for_pct_orange(self):
        self.assertEqual(SegmentRenderer._color_for_pct(55), ORANGE)

    def test_color_for_pct_yellow(self):
        self.assertEqual(SegmentRenderer._color_for_pct(75), YELLOW)

    def test_color_for_pct_red(self):
        self.assertEqual(SegmentRenderer._color_for_pct(95), RED)

    def test_color_for_cache_pct_green(self):
        self.assertEqual(SegmentRenderer._color_for_cache_pct(80), GREEN)

    def test_color_for_cache_pct_yellow(self):
        self.assertEqual(SegmentRenderer._color_for_cache_pct(50), YELLOW)

    def test_color_for_cache_pct_orange(self):
        self.assertEqual(SegmentRenderer._color_for_cache_pct(20), ORANGE)

    def test_color_for_cache_pct_red(self):
        self.assertEqual(SegmentRenderer._color_for_cache_pct(5), RED)


class TestFormatHelpers(unittest.TestCase):
    def test_format_tokens_millions(self):
        self.assertEqual(SegmentRenderer._format_tokens(1_500_000), '1.5M')

    def test_format_tokens_thousands(self):
        self.assertEqual(SegmentRenderer._format_tokens(42_000), '42.0k')

    def test_format_tokens_small(self):
        self.assertEqual(SegmentRenderer._format_tokens(500), '500')

    def test_build_bar_0pct(self):
        bar = SegmentRenderer._build_bar(0, 6)
        self.assertIn('░', bar)
        self.assertNotIn('▓', bar)
        self.assertIn(GREEN, bar)

    def test_build_bar_100pct(self):
        bar = SegmentRenderer._build_bar(100, 6)
        self.assertIn('▓', bar)
        self.assertNotIn('░', bar)
        self.assertIn(RED, bar)

    def test_build_bar_50pct(self):
        bar = SegmentRenderer._build_bar(50, 6)
        self.assertIn('▓', bar)
        self.assertIn('░', bar)

    def test_format_ttl_epoch_none(self):
        self.assertIsNone(SegmentRenderer._format_ttl_epoch(None))

    def test_format_ttl_epoch_past(self):
        past_epoch = int(time.time()) - 3600
        self.assertEqual(SegmentRenderer._format_ttl_epoch(past_epoch), 'now')

    def test_lbl_true(self):
        r = _make(config={'SHOW_LABELS': True})
        result = r._lbl('test')
        self.assertIn('test:', result)
        self.assertIn(DIM, result)

    def test_lbl_false(self):
        r = _make(config={'SHOW_LABELS': False})
        self.assertEqual(r._lbl('test'), '')


class TestSegmentModel(unittest.TestCase):
    def test_model_renders(self):
        r = _make(data={'model': {'display_name': 'Opus 4'}})
        result = r.render('model')
        self.assertIsNotNone(result)
        self.assertIn('Opus 4', result)
        self.assertIn(BLUE, result)

    def test_model_default(self):
        r = _make(data={})
        result = r.render('model')
        self.assertIn('Claude', result)


class TestSegmentContextPct(unittest.TestCase):
    def _make_ctx(self, input_tokens, window=200000):
        return {
            'context_window': {
                'context_window_size': window,
                'current_usage': {'input_tokens': input_tokens},
            }
        }

    def test_low_usage(self):
        r = _make(data=self._make_ctx(40000))  # 20%
        result = r.render('context_pct')
        self.assertIn(GREEN, result)
        self.assertIn('20%', result)

    def test_high_usage(self):
        r = _make(data=self._make_ctx(170000))  # 85%
        result = r.render('context_pct')
        self.assertIn(YELLOW, result)
        self.assertIn('85%', result)


class TestSegmentTokens(unittest.TestCase):
    def _make_session(self, session_in=0, session_out=0):
        return {
            'context_window': {
                'total_input_tokens': session_in,
                'total_output_tokens': session_out,
            }
        }

    def test_no_tokens(self):
        r = _make(data=self._make_session(0, 0))
        self.assertIsNone(r.render('tokens'))

    def test_total_style(self):
        r = _make(data=self._make_session(5000, 2000), config={'TOKEN_STYLE': 'total'})
        result = r.render('tokens')
        self.assertIsNotNone(result)
        self.assertIn('7.0k', result)

    def test_in_out_style(self):
        r = _make(data=self._make_session(5000, 2000), config={'TOKEN_STYLE': 'in_out'})
        result = r.render('tokens')
        self.assertIn('↑', result)
        self.assertIn('↓', result)


class TestSegmentCost(unittest.TestCase):
    def _make_session(self, session_in=0, session_out=0):
        return {
            'context_window': {
                'total_input_tokens': session_in,
                'total_output_tokens': session_out,
            }
        }

    def test_no_tokens_returns_none(self):
        r = _make(data=self._make_session(0, 0))
        self.assertIsNone(r.render('cost'))

    def test_cost_renders(self):
        r = _make(data=self._make_session(100000, 50000))
        result = r.render('cost')
        self.assertIsNotNone(result)
        self.assertIn('$', result)


class TestSegmentCachePct(unittest.TestCase):
    def _make_ctx(self, input_tokens=0, cache_read=0):
        return {
            'context_window': {
                'context_window_size': 200000,
                'current_usage': {
                    'input_tokens': input_tokens,
                    'cache_read_input_tokens': cache_read,
                },
            }
        }

    def test_no_current_returns_none(self):
        r = _make(data=self._make_ctx(0, 0))
        self.assertIsNone(r.render('cache_pct'))

    def test_high_cache(self):
        # 80% cache read
        r = _make(data=self._make_ctx(input_tokens=20, cache_read=80))
        result = r.render('cache_pct')
        self.assertIn(GREEN, result)

    def test_low_cache(self):
        # 5% cache read
        r = _make(data=self._make_ctx(input_tokens=95, cache_read=5))
        result = r.render('cache_pct')
        self.assertIn(RED, result)


class TestSegmentEffort(unittest.TestCase):
    def test_effort_auto(self):
        with patch.dict(os.environ, {}, clear=True):
            r = _make()
        result = r.render('effort')
        self.assertIn('auto', result)

    def test_effort_high(self):
        with patch.dict(os.environ, {'CLAUDE_CODE_EFFORT_LEVEL': 'high'}):
            r = _make()
        result = r.render('effort')
        self.assertIn(ORANGE, result)
        self.assertIn('high', result)


class TestSegmentCwd(unittest.TestCase):
    def test_cwd_basename(self):
        r = _make(data={'cwd': '/home/user/myproject'})
        result = r.render('cwd')
        self.assertIn('myproject', result)
        self.assertIn(WHITE, result)


def _make_git_side_effect(branch='main', has_upstream=False, ahead=0, behind=0,
                          porcelain='', worktree_lines=None):
    """Return a side_effect function for subprocess.run that simulates git output."""
    def side_effect(cmd, **kwargs):
        m = MagicMock()
        if 'rev-parse' in cmd and '--is-inside-work-tree' in cmd:
            m.returncode = 0
            m.stdout = 'true\n'
        elif 'symbolic-ref' in cmd:
            m.returncode = 0
            m.stdout = branch + '\n'
        elif '--abbrev-ref' in cmd and '@{upstream}' in cmd:
            m.returncode = 0 if has_upstream else 1
            m.stdout = 'origin/main\n' if has_upstream else ''
        elif 'rev-list' in cmd and '@{upstream}..HEAD' in cmd:
            m.returncode = 0
            m.stdout = str(ahead) + '\n'
        elif 'rev-list' in cmd and 'HEAD..@{upstream}' in cmd:
            m.returncode = 0
            m.stdout = str(behind) + '\n'
        elif 'status' in cmd and '--porcelain' in cmd:
            m.returncode = 0
            m.stdout = porcelain
        elif 'worktree' in cmd and 'list' in cmd:
            m.returncode = 0
            if worktree_lines is not None:
                m.stdout = '\n'.join(worktree_lines) + '\n'
            else:
                m.stdout = 'worktree /main/path\n'
        else:
            m.returncode = 1
            m.stdout = ''
        return m
    return side_effect


class TestSegmentGitBranch(unittest.TestCase):
    def test_no_git(self):
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stdout='')
            r = _make()
            result = r.render('git_branch')
        self.assertIsNone(result)

    def test_branch_renders(self):
        with patch('subprocess.run', side_effect=_make_git_side_effect('main')):
            r = _make()
            result = r.render('git_branch')
        self.assertIsNotNone(result)
        self.assertIn('main', result)
        self.assertIn(GREEN, result)

    def test_long_branch_truncated(self):
        long_branch = 'feature/very-long-branch-name-that-exceeds-limit'
        with patch('subprocess.run', side_effect=_make_git_side_effect(long_branch)):
            r = _make(config={'GIT_BRANCH_MAX': 10})
            result = r.render('git_branch')
        self.assertIn('…', result)


class TestSegmentGitStatus(unittest.TestCase):
    def test_no_git(self):
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stdout='')
            r = _make()
            result = r.render('git_status')
        self.assertIsNone(result)

    def test_ahead_behind(self):
        with patch('subprocess.run',
                   side_effect=_make_git_side_effect('main', has_upstream=True,
                                                     ahead=2, behind=1)):
            r = _make()
            result = r.render('git_status')
        self.assertIsNotNone(result)
        self.assertIn('↑2', result)
        self.assertIn('↓1', result)

    def test_staged_unstaged(self):
        porcelain = 'M  staged.py\n?? untracked.py\n'
        with patch('subprocess.run',
                   side_effect=_make_git_side_effect('main', porcelain=porcelain)):
            r = _make()
            result = r.render('git_status')
        self.assertIsNotNone(result)
        self.assertIn('+', result)
        self.assertIn('~', result)


class TestSegmentRate(unittest.TestCase):
    def test_rate_5h_none(self):
        r = _make()
        self.assertIsNone(r.render('rate_5h'))

    def test_rate_5h_bar_pct(self):
        data = {'rate_limits': {'five_hour': {'used_percentage': 30.0}}}
        r = _make(data=data, config={'RATE_STYLE': 'bar_pct', 'SHOW_TTL': False})
        result = r.render('rate_5h')
        self.assertIsNotNone(result)
        self.assertIn('▓', result)
        self.assertIn('30%', result)

    def test_rate_style_off(self):
        data = {'rate_limits': {'five_hour': {'used_percentage': 30.0}}}
        r = _make(data=data, config={'RATE_STYLE': 'off'})
        self.assertIsNone(r.render('rate_5h'))


class TestSegmentExhaust(unittest.TestCase):
    def test_exhaust_5h_none(self):
        r = _make()
        self.assertIsNone(r.render('exhaust_5h'))

    def test_exhaust_5h_renders(self):
        future_epoch = int(time.time()) + 7200  # 2h from now
        data = {'rate_limits': {'five_hour': {
            'used_percentage': 50.0,
            'resets_at': future_epoch,
        }}}
        r = _make(data=data)
        result = r.render('exhaust_5h')
        self.assertIsNotNone(result)
        self.assertIn('out in', result)


class TestSegmentDowntime(unittest.TestCase):
    def test_no_data(self):
        r = _make()
        self.assertIsNone(r.render('downtime'))

    def test_no_downtime(self):
        now = int(time.time())
        # pct=50, reset in 1h (3600s window start = now - (3600 - 1800) = now - 1800)
        # elapsed=1800s, remaining = 1800 * (50/50) = 1800s
        # time_to_reset = 3600, downtime = 3600 - 1800 = 1800 > 0 — let's use pct=1 near exhaust
        # Instead just set pct=99 so exhaust is nearly now = no downtime
        data = {'rate_limits': {'five_hour': {
            'used_percentage': 99.0,
            'resets_at': now + 100,
        }}}
        r = _make(data=data)
        result = r.render('downtime')
        self.assertIsNotNone(result)
        self.assertIn('no downtime', result)


class TestSegmentHook(unittest.TestCase):
    def test_no_session(self):
        r = _make()
        self.assertIsNone(r.render('hook'))

    def test_hook_renders(self):
        hook_data = {'hook_event': 'PostToolUse', 'tool_name': 'Bash', 'hooks_ran': []}
        r = _make(data={'session_id': 'test-sess'})
        with patch('os.path.isfile', return_value=True), \
             patch('builtins.open', mock_open(read_data=json.dumps(hook_data))):
            r._hook_loaded = False
            result = r.render('hook')
        self.assertIsNotNone(result)
        self.assertIn('Bash', result)


class TestSegmentHookifyRule(unittest.TestCase):
    def test_no_hookify(self):
        r = _make(data={'session_id': 'test-sess'})
        with patch('os.path.isfile', return_value=False):
            result = r.render('hookify_rule')
        self.assertIsNone(result)

    def test_hookify_renders(self):
        hook_data = {
            'hook_event': 'PostToolUse',
            'tool_name': 'Bash',
            'hooks_ran': [],
            'hookify_configured': True,
            'hookify_rules': [{'name': 'rule1', 'action': 'warn'}],
        }
        r = _make(data={'session_id': 'test-sess'})
        with patch('os.path.isfile', return_value=True), \
             patch('builtins.open', mock_open(read_data=json.dumps(hook_data))):
            r._hook_loaded = False
            result = r.render('hookify_rule')
        self.assertIsNotNone(result)
        self.assertIn('rule:', result)


class TestSegmentAgents(unittest.TestCase):
    def test_no_session(self):
        r = _make()
        self.assertIsNone(r.render('agents'))

    def test_active_agents(self):
        tracker_data = {'agents': [
            {'status': 'running', 'type': 'subagent'},
            {'status': 'running', 'type': 'subagent'},
        ]}
        r = _make(data={'session_id': 'test-sess'})
        with patch('os.path.isfile', return_value=True), \
             patch('builtins.open', mock_open(read_data=json.dumps(tracker_data))):
            result = r.render('agents')
        self.assertIsNotNone(result)
        self.assertIn('2', result)
        self.assertIn(BLUE, result)


class TestSegmentPlugins(unittest.TestCase):
    def test_no_plugins(self):
        r = _make()
        with patch('os.path.isfile', return_value=False):
            self.assertIsNone(r.render('plugins'))

    def test_plugins_renders(self):
        settings_data = json.dumps({'plugins': ['plugin1', 'plugin2', 'plugin3']})
        r = _make()
        with patch('builtins.open', mock_open(read_data=settings_data)):
            r._plugins_loaded = False
            result = r.render('plugins')
        self.assertIsNotNone(result)
        self.assertIn('3', result)


class TestSegmentGsdPhase(unittest.TestCase):
    def test_no_state_file(self):
        r = _make()
        with patch('os.path.isfile', return_value=False):
            result = r.render('gsd_phase')
        self.assertIsNone(result)

    def test_phase_renders(self):
        state_md = '---\nstatus: executing\ntotal_phases: 9\n---\n\n# State\n\nPhase: 4\n'
        r = _make()
        with patch('os.path.isfile', return_value=True), \
             patch('builtins.open', mock_open(read_data=state_md)):
            r._gsd_loaded = False
            result = r.render('gsd_phase')
        self.assertIsNotNone(result)
        self.assertIn('4', result)


class TestSegmentGsdProgress(unittest.TestCase):
    def test_no_state(self):
        r = _make()
        with patch('os.path.isfile', return_value=False):
            result = r.render('gsd_progress')
        self.assertIsNone(result)

    def test_progress_renders(self):
        state_md = ('---\nstatus: executing\ntotal_phases: 9\ncompleted_phases: 3\n'
                    'total_plans: 4\ncompleted_plans: 3\n---\n\n# State\n\nPhase: 4\n')
        r = _make()
        with patch('os.path.isfile', return_value=True), \
             patch('builtins.open', mock_open(read_data=state_md)):
            r._gsd_loaded = False
            result = r.render('gsd_progress')
        self.assertIsNotNone(result)
        self.assertIn('ph', result)
        self.assertIn('3/9', result)


class TestSegmentWorktree(unittest.TestCase):
    def test_not_worktree(self):
        with patch('subprocess.run',
                   side_effect=_make_git_side_effect('main')):
            r = _make()
            result = r.render('worktree')
        self.assertIsNone(result)

    def test_worktree_renders(self):
        cwd = '/some/other/worktree'
        worktree_lines = ['worktree /main/path', 'HEAD abc', 'worktree ' + cwd, 'HEAD def']
        with patch('subprocess.run',
                   side_effect=_make_git_side_effect('main', worktree_lines=worktree_lines)), \
             patch('os.path.realpath', return_value=cwd):
            r = _make(data={'cwd': cwd})
            result = r.render('worktree')
        self.assertIsNotNone(result)
        self.assertIn('wt:', result)


class TestSegmentSessionTimer(unittest.TestCase):
    def test_no_state(self):
        r = _make()
        self.assertIsNone(r.render('session_timer'))

    def test_short_session(self):
        now = int(time.time())
        r = _make(data={'session_id': 'test', 'context_window': {
            'total_input_tokens': 1000, 'total_output_tokens': 500}})
        state_data = {'total': 1500, 'msgs': 1, 'ts': now, 'first_ts': now - 30, 'history': '1500'}
        with patch('os.path.isfile', return_value=True), \
             patch('builtins.open', mock_open(read_data=json.dumps(state_data))), \
             patch('os.makedirs'), \
             patch('os.path.isdir', return_value=False), \
             patch('time.time', return_value=float(now)):
            r._session_state_loaded = False
            result = r.render('session_timer')
        self.assertIsNone(result)

    def test_long_session(self):
        now = int(time.time())
        first_ts = now - 3700
        r = _make(data={'session_id': 'test', 'context_window': {
            'total_input_tokens': 1000, 'total_output_tokens': 500}})
        state_data = {'total': 1500, 'msgs': 1, 'ts': now, 'first_ts': first_ts, 'history': '1500'}
        with patch('os.path.isfile', return_value=True), \
             patch('builtins.open', mock_open(read_data=json.dumps(state_data))), \
             patch('os.makedirs'), \
             patch('os.path.isdir', return_value=False), \
             patch('time.time', return_value=float(now)):
            r._session_state_loaded = False
            result = r.render('session_timer')
        self.assertIsNotNone(result)
        self.assertIn('1h', result)
        self.assertIn(ORANGE, result)


class TestRenderDispatch(unittest.TestCase):
    def test_unknown_segment(self):
        r = _make()
        self.assertIsNone(r.render('nonexistent'))

    def test_exception_returns_none(self):
        r = _make()
        r._seg_model = lambda: (_ for _ in ()).throw(RuntimeError('boom'))
        self.assertIsNone(r.render('model'))


class TestEstimateCost(unittest.TestCase):
    def test_opus_pricing(self):
        r = _make(data={'model': {'id': 'claude-opus-4', 'display_name': 'Opus 4'},
                        'context_window': {'total_input_tokens': 100000,
                                           'total_output_tokens': 50000}})
        result = r._estimate_cost()
        self.assertIsNotNone(result)
        self.assertIn('$', result)

    def test_sonnet_pricing(self):
        r = _make(data={'model': {'id': 'claude-sonnet-4', 'display_name': 'Sonnet'},
                        'context_window': {'total_input_tokens': 100000,
                                           'total_output_tokens': 50000}})
        result = r._estimate_cost()
        self.assertIsNotNone(result)
        self.assertIn('$', result)


if __name__ == '__main__':
    unittest.main()
