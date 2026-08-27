from evalharness.scorers import exact_match, regex_match, keyword_overlap
from evalharness.testcase import TestCase


def make_case(**kwargs):
    defaults = dict(id="t", prompt="p", scorer="exact_match", expected="x")
    defaults.update(kwargs)
    return TestCase(**defaults)


def test_exact_match_pass():
    case = make_case(expected="Paris")
    result = exact_match("  paris ", case)
    assert result.passed
    assert result.score == 1.0


def test_exact_match_fail():
    case = make_case(expected="Paris")
    result = exact_match("London", case)
    assert not result.passed
    assert result.score == 0.0


def test_regex_match_pass():
    case = make_case(expected=r"^\d{4}-\d{2}-\d{2}$")
    result = regex_match("2024-01-01", case)
    assert result.passed


def test_regex_match_fail():
    case = make_case(expected=r"^\d{4}-\d{2}-\d{2}$")
    result = regex_match("not a date", case)
    assert not result.passed


def test_keyword_overlap_full():
    case = make_case(expected=["red", "blue", "yellow"], threshold=1.0)
    result = keyword_overlap("red, blue, and yellow are primary colors", case)
    assert result.passed
    assert result.score == 1.0


def test_keyword_overlap_partial_below_threshold():
    case = make_case(expected=["red", "blue", "yellow"], threshold=0.9)
    result = keyword_overlap("red and blue", case)
    assert not result.passed
    assert round(result.score, 2) == 0.67


def test_keyword_overlap_partial_meets_threshold():
    case = make_case(expected=["red", "blue", "yellow"], threshold=0.5)
    result = keyword_overlap("red and blue", case)
    assert result.passed
