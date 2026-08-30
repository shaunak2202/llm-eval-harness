from evalharness.diff import diff_runs


def make_run(scores_and_passed, average_score, name="suite"):
    return {
        "suite_name": name,
        "provider_name": "mock",
        "average_score": average_score,
        "case_results": [
            {"case_id": cid, "prompt": "p", "output": "o", "passed": passed, "score": score, "detail": "d"}
            for cid, (score, passed) in scores_and_passed.items()
        ],
    }


def test_diff_detects_improvement_and_regression():
    run_a = make_run(
        {"c1": (1.0, True), "c2": (0.5, False)},
        average_score=0.75,
    )
    run_b = make_run(
        {"c1": (0.5, False), "c2": (1.0, True)},
        average_score=0.75,
    )
    diff = diff_runs(run_a, run_b, "a", "b")

    by_id = {e.case_id: e for e in diff.entries}
    assert by_id["c1"].status == "newly_failing"
    assert by_id["c2"].status == "newly_passing"
    assert diff.regressed_count == 1
    assert diff.improved_count == 1


def test_diff_unchanged_case():
    run_a = make_run({"c1": (1.0, True)}, average_score=1.0)
    run_b = make_run({"c1": (1.0, True)}, average_score=1.0)
    diff = diff_runs(run_a, run_b, "a", "b")
    assert diff.entries[0].status == "unchanged"
    assert diff.average_delta == 0.0


def test_diff_added_and_removed_cases():
    run_a = make_run({"c1": (1.0, True)}, average_score=1.0)
    run_b = make_run({"c2": (1.0, True)}, average_score=1.0)
    diff = diff_runs(run_a, run_b, "a", "b")
    statuses = {e.case_id: e.status for e in diff.entries}
    assert statuses["c1"] == "removed"
    assert statuses["c2"] == "added"


def test_diff_score_improved_without_pass_flag_change():
    run_a = make_run({"c1": (0.4, False)}, average_score=0.4)
    run_b = make_run({"c1": (0.6, False)}, average_score=0.6)
    diff = diff_runs(run_a, run_b, "a", "b")
    assert diff.entries[0].status == "improved"
    assert round(diff.entries[0].delta, 2) == 0.2
