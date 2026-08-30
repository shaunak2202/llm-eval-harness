from evalharness.providers import MockProvider
from evalharness.scorers import (
    exact_match,
    regex_match,
    keyword_overlap,
    make_llm_rubric_scorer,
)
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


class FixedJudge:
    name = "fixed-judge"

    def __init__(self, response):
        self.response = response

    def generate(self, prompt, **kwargs):
        return self.response


def test_llm_rubric_pass_above_threshold():
    judge = FixedJudge("SCORE: 0.9\nGood, concise, correct.")
    scorer = make_llm_rubric_scorer(judge)
    case = make_case(scorer="llm_rubric", expected="Be correct and concise.", threshold=0.7)
    result = scorer("A hash map maps keys to values.", case)
    assert result.passed
    assert result.score == 0.9


def test_llm_rubric_fail_below_threshold():
    judge = FixedJudge("SCORE: 0.3\nToo vague.")
    scorer = make_llm_rubric_scorer(judge)
    case = make_case(scorer="llm_rubric", expected="Be correct and concise.", threshold=0.7)
    result = scorer("stuff", case)
    assert not result.passed
    assert result.score == 0.3


def test_llm_rubric_clamps_out_of_range_scores():
    judge = FixedJudge("SCORE: 1.5\nOver-generous judge.")
    scorer = make_llm_rubric_scorer(judge)
    case = make_case(scorer="llm_rubric", expected="rubric text")
    result = scorer("output", case)
    assert result.score == 1.0


def test_llm_rubric_raises_on_unparseable_judge_output():
    judge = FixedJudge("I refuse to give a numeric score.")
    scorer = make_llm_rubric_scorer(judge)
    case = make_case(scorer="llm_rubric", expected="rubric text")
    try:
        scorer("output", case)
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_llm_rubric_with_mock_provider_is_deterministic():
    judge = MockProvider()
    scorer = make_llm_rubric_scorer(judge)
    case = make_case(scorer="llm_rubric", expected="rubric text", threshold=0.0)
    r1 = scorer("some output", case)
    r2 = scorer("some output", case)
    assert r1.score == r2.score
