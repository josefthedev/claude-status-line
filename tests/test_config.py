"""Tests for lib/config.py — config file parser."""

import os
import tempfile
import unittest
import unittest.mock as mock

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

    def test_bool_yes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write(tmp, 'FLAG=yes\n')
            self.assertIs(_parse_file(path)['FLAG'], True)

    def test_bool_no(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write(tmp, 'FLAG=no\n')
            self.assertIs(_parse_file(path)['FLAG'], False)


class TestLoadConfig(unittest.TestCase):
    def test_no_files_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch('lib.config.os.path.expanduser', return_value='/nonexistent/base.conf'):
                result = load_config(cwd=tmp)
            self.assertEqual(result, {})

    def test_base_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            base_conf = os.path.join(tmp, 'base.conf')
            with open(base_conf, 'w') as f:
                f.write('BAR_WIDTH=6\nSHOW_LABELS=true\n')
            with mock.patch('lib.config.os.path.expanduser', return_value=base_conf):
                result = load_config(cwd='/nonexistent_project')
            self.assertEqual(result['BAR_WIDTH'], 6)
            self.assertIs(result['SHOW_LABELS'], True)

    def test_project_override_wins(self):
        with tempfile.TemporaryDirectory() as base_tmp:
            with tempfile.TemporaryDirectory() as project_tmp:
                base_conf = os.path.join(base_tmp, 'base.conf')
                with open(base_conf, 'w') as f:
                    f.write('BAR_WIDTH=6\nSHOW_LABELS=true\n')

                dot_claude = os.path.join(project_tmp, '.claude')
                os.makedirs(dot_claude)
                override_conf = os.path.join(dot_claude, 'statusline.conf')
                with open(override_conf, 'w') as f:
                    f.write('BAR_WIDTH=10\n')

                with mock.patch('lib.config.os.path.expanduser', return_value=base_conf):
                    result = load_config(cwd=project_tmp)

                self.assertEqual(result['BAR_WIDTH'], 10)
                self.assertIs(result['SHOW_LABELS'], True)

    def test_project_only(self):
        with tempfile.TemporaryDirectory() as project_tmp:
            dot_claude = os.path.join(project_tmp, '.claude')
            os.makedirs(dot_claude)
            override_conf = os.path.join(dot_claude, 'statusline.conf')
            with open(override_conf, 'w') as f:
                f.write('BAR_WIDTH=8\n')

            with mock.patch('lib.config.os.path.expanduser', return_value='/nonexistent/base.conf'):
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
