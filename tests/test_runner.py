from evalharness.providers import MockProvider
from evalharness.runner import run_suite
from evalharness.testcase import TestCase, TestSuite


def test_run_suite_all_pass():
    suite = TestSuite(
        name="test-suite",
        cases=[
            TestCase(
                id="c1",
                prompt="What is the capital of France?",
                scorer="exact_match",
                expected="Paris",
            ),
            TestCase(
                id="c2",
                prompt="List three primary colors.",
                scorer="keyword_overlap",
                expected=["red", "blue", "yellow"],
                threshold=0.5,
            ),
        ],
    )
    provider = MockProvider()
    result = run_suite(suite, provider)

    assert result.total_count == 2
    assert result.pass_count == 2
    assert result.average_score == 1.0


def test_run_suite_unknown_prompt_uses_placeholder():
    suite = TestSuite(
        name="test-suite",
        cases=[
            TestCase(
                id="c1",
                prompt="Something totally unrelated to canned answers",
                scorer="exact_match",
                expected="Paris",
            )
        ],
    )
    provider = MockProvider()
    result = run_suite(suite, provider)

    assert result.total_count == 1
    assert result.pass_count == 0
    assert result.case_results[0].output.startswith("<mock-response-")
