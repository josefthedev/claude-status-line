"""Tests for lib/packer.py — adaptive line packer."""

import unittest

from lib.packer import pack_lines


class MockRenderer:
    def __init__(self, segments: dict):
        self._segments = segments

    def render(self, name: str):
        return self._segments.get(name)


class TestPackLines(unittest.TestCase):

    def test_two_segments_fit(self):
        """Two short segments both appear in output separated by separator."""
        renderer = MockRenderer({'seg_a': 'hello', 'seg_b': 'world'})
        result = pack_lines([['seg_a', 'seg_b']], renderer, budget=40)
        self.assertEqual(len(result), 1)
        self.assertIn('hello', result[0])
        self.assertIn('world', result[0])
        # separator character should be present
        self.assertIn('│', result[0])

    def test_segment_dropped_over_budget(self):
        """Second segment dropped when it would exceed budget."""
        # seg_a = 10 chars, seg_b = 10 chars; sep = 3 visible chars (' │ ')
        # combined would be 10 + 3 + 10 = 23, exceeds budget=15
        renderer = MockRenderer({'seg_a': 'a' * 10, 'seg_b': 'b' * 10})
        result = pack_lines([['seg_a', 'seg_b']], renderer, budget=15)
        self.assertEqual(len(result), 1)
        self.assertIn('a' * 10, result[0])
        self.assertNotIn('b', result[0])

    def test_git_status_attachment(self):
        """git_status after git_branch joined with space, not dim separator."""
        renderer = MockRenderer({'git_branch': 'main', 'git_status': '+1~2'})
        result = pack_lines([['git_branch', 'git_status']], renderer, budget=40)
        self.assertEqual(len(result), 1)
        # Should be "main +1~2" with space, not "main │ +1~2"
        self.assertIn('main +1~2', result[0])
        self.assertNotIn('│', result[0])

    def test_all_none(self):
        """All segments return None, result is empty string."""
        renderer = MockRenderer({})
        result = pack_lines([['seg_a', 'seg_b', 'seg_c']], renderer, budget=80)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], '')

    def test_empty_line_def(self):
        """Empty names list produces empty string."""
        renderer = MockRenderer({'seg_a': 'hello'})
        result = pack_lines([[]], renderer, budget=80)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], '')

    def test_none_skipped(self):
        """None segment between two valid segments doesn't break packing."""
        renderer = MockRenderer({'seg_a': None, 'seg_b': 'foo', 'seg_c': 'bar'})
        result = pack_lines([['seg_a', 'seg_b', 'seg_c']], renderer, budget=80)
        self.assertEqual(len(result), 1)
        self.assertIn('foo', result[0])
        self.assertIn('bar', result[0])
        self.assertNotIn('None', result[0])

    def test_multiple_lines(self):
        """Two line_defs returns list of length 2."""
        renderer = MockRenderer({'seg_a': 'line1', 'seg_b': 'line2'})
        result = pack_lines([['seg_a'], ['seg_b']], renderer, budget=40)
        self.assertEqual(len(result), 2)
        self.assertIn('line1', result[0])
        self.assertIn('line2', result[1])

    def test_first_segment_exceeds_budget(self):
        """Single segment wider than budget, line is empty string."""
        renderer = MockRenderer({'seg_a': 'x' * 20})
        result = pack_lines([['seg_a']], renderer, budget=10)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], '')

    def test_ansi_width_ignored(self):
        """ANSI escape codes don't count toward visible width."""
        # ANSI color + reset adds invisible bytes; visible text is 5 chars
        ansi_str = '\033[38;2;0;153;255mhello\033[0m'  # "hello" in blue = 5 visible chars
        renderer = MockRenderer({'seg_a': ansi_str, 'seg_b': 'world'})
        # budget=14: "hello" (5) + " │ " (3) + "world" (5) = 13 — fits
        result = pack_lines([['seg_a', 'seg_b']], renderer, budget=14)
        self.assertEqual(len(result), 1)
        self.assertIn('hello', result[0])
        self.assertIn('world', result[0])


if __name__ == '__main__':
    unittest.main()
