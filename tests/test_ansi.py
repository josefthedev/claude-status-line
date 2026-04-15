import sys, os; sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from lib.ansi import strip_ansi, visible_width, truncate_ansi

def test_strip_plain():
    assert strip_ansi("hello") == "hello"

def test_strip_color():
    assert strip_ansi("\033[31mhello\033[0m") == "hello"

def test_strip_rgb():
    assert strip_ansi("\033[38;2;0;153;255mhello\033[0m") == "hello"

def test_strip_dim():
    assert strip_ansi("\033[2mhello\033[22m") == "hello"

def test_strip_256():
    assert strip_ansi("\033[38;5;208mhello\033[0m") == "hello"

def test_visible_width_plain():
    assert visible_width("hello") == 5

def test_visible_width_colored():
    assert visible_width("\033[31mhello\033[0m") == 5

def test_visible_width_unicode():
    assert visible_width("│") == 1

def test_truncate_ansi_no_cut():
    s = "\033[31mhi\033[0m"
    assert truncate_ansi(s, 10) == s

def test_truncate_ansi_cuts_at_visible():
    s = "\033[31mhello world\033[0m"
    result = truncate_ansi(s, 5)
    assert visible_width(result) <= 5
    assert "\033[0m" in result  # reset appended

def test_truncate_ansi_mid_escape():
    # Must not cut in the middle of an escape sequence
    s = "abc\033[38;2;0;153;255mdef\033[0m"
    result = truncate_ansi(s, 4)
    assert visible_width(result) <= 4

if __name__ == "__main__":
    import unittest
    # Run tests defined above using manual discovery
    tests = [v for k, v in globals().items() if k.startswith("test_")]
    passed = failed = 0
    for t in tests:
        try:
            t()
            print(f"  PASS {t.__name__}")
            passed += 1
        except Exception as e:
            print(f"  FAIL {t.__name__}: {e}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)
