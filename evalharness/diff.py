"""Run-to-run comparison logic.

Takes two `RunResult.to_dict()`-shaped dicts (typically loaded from JSON
files saved by `evalharness run --json ...`) and produces a case-by-case diff
plus overall score movement, so you can tell whether a prompt/model change
made things better or worse.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class DiffEntry:
    case_id: str
    status: str  # improved | regressed | unchanged | newly_passing | newly_failing | added | removed
    score_a: Optional[float]
    score_b: Optional[float]

    @property
    def delta(self) -> Optional[float]:
        if self.score_a is None or self.score_b is None:
            return None
        return self.score_b - self.score_a


@dataclass
class RunDiff:
    run_a_label: str
    run_b_label: str
    entries: List[DiffEntry]
    average_a: float
    average_b: float

    @property
    def average_delta(self) -> float:
        return self.average_b - self.average_a

    @property
    def regressed_count(self) -> int:
        return sum(1 for e in self.entries if e.status in ("regressed", "newly_failing"))

    @property
    def improved_count(self) -> int:
        return sum(1 for e in self.entries if e.status in ("improved", "newly_passing"))


def _score_epsilon(a: float, b: float, eps: float = 1e-9) -> bool:
    return abs(a - b) < eps


def diff_runs(data_a: dict, data_b: dict, label_a: str = "a", label_b: str = "b") -> RunDiff:
    cases_a = {c["case_id"]: c for c in data_a.get("case_results", [])}
    cases_b = {c["case_id"]: c for c in data_b.get("case_results", [])}

    all_ids = list(dict.fromkeys(list(cases_a.keys()) + list(cases_b.keys())))

    entries: List[DiffEntry] = []
    for case_id in all_ids:
        a = cases_a.get(case_id)
        b = cases_b.get(case_id)

        if a is None and b is not None:
            entries.append(DiffEntry(case_id, "added", None, b["score"]))
            continue
        if b is None and a is not None:
            entries.append(DiffEntry(case_id, "removed", a["score"], None))
            continue

        score_a, score_b = a["score"], b["score"]
        passed_a, passed_b = a["passed"], b["passed"]

        if passed_a != passed_b:
            status = "newly_passing" if passed_b else "newly_failing"
        elif _score_epsilon(score_a, score_b):
            status = "unchanged"
        elif score_b > score_a:
            status = "improved"
        else:
            status = "regressed"

        entries.append(DiffEntry(case_id, status, score_a, score_b))

    average_a = data_a.get("average_score", 0.0)
    average_b = data_b.get("average_score", 0.0)

    return RunDiff(
        run_a_label=label_a,
        run_b_label=label_b,
        entries=entries,
        average_a=average_a,
        average_b=average_b,
    )
