from evalharness.diff import diff_runs
from evalharness.providers import MockProvider
from evalharness.report import render_diff_html, render_run_html
from evalharness.runner import run_suite
from evalharness.testcase import TestCase, TestSuite


def _suite():
    return TestSuite(
        name="report-suite",
        cases=[
            TestCase(id="c1", prompt="capital of France?", scorer="exact_match", expected="Paris"),
            TestCase(id="c2", prompt="unknown thing", scorer="exact_match", expected="nope"),
        ],
    )


def test_render_run_html_contains_key_data():
    result = run_suite(_suite(), MockProvider())
    html = render_run_html(result)
    assert "report-suite" in html
    assert "c1" in html and "c2" in html
    assert "PASS" in html and "FAIL" in html
    assert "<html>" in html.lower() or "<!doctype" in html.lower()


def test_render_run_html_escapes_html_in_content():
    suite = TestSuite(
        name="xss-suite",
        cases=[TestCase(id="c1", prompt="<script>alert(1)</script>", scorer="exact_match", expected="x")],
    )
    result = run_suite(suite, MockProvider())
    html = render_run_html(result)
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html


def test_render_diff_html_contains_summary():
    data_a = {
        "average_score": 0.5,
        "case_results": [{"case_id": "c1", "score": 0.5, "passed": False}],
    }
    data_b = {
        "average_score": 1.0,
        "case_results": [{"case_id": "c1", "score": 1.0, "passed": True}],
    }
    diff = diff_runs(data_a, data_b, "a.json", "b.json")
    html = render_diff_html(diff)
    assert "a.json" in html and "b.json" in html
    assert "NEWLY PASSING" in html
