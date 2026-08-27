"""Scoring functions.

Each scorer takes the raw model output and the TestCase, and returns a
ScoreResult (passed: bool, score: float in [0,1], detail: str).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable, Dict

from evalharness.testcase import TestCase


@dataclass
class ScoreResult:
    passed: bool
    score: float
    detail: str


def exact_match(output: str, case: TestCase) -> ScoreResult:
    normalized_out = output.strip().lower()
    normalized_exp = str(case.expected).strip().lower()
    passed = normalized_out == normalized_exp
    return ScoreResult(
        passed=passed,
        score=1.0 if passed else 0.0,
        detail=f"expected={case.expected!r} got={output!r}",
    )


def regex_match(output: str, case: TestCase) -> ScoreResult:
    pattern = case.expected
    match = re.search(pattern, output.strip())
    passed = match is not None
    return ScoreResult(
        passed=passed,
        score=1.0 if passed else 0.0,
        detail=f"pattern={pattern!r} got={output!r}",
    )


def keyword_overlap(output: str, case: TestCase) -> ScoreResult:
    keywords = case.expected
    if isinstance(keywords, str):
        keywords = [keywords]

    lowered_out = output.lower()
    hits = sum(1 for kw in keywords if str(kw).lower() in lowered_out)
    score = hits / len(keywords) if keywords else 0.0
    threshold = case.threshold if case.threshold is not None else 1.0
    passed = score >= threshold

    return ScoreResult(
        passed=passed,
        score=score,
        detail=f"{hits}/{len(keywords)} keywords found (threshold={threshold})",
    )


SCORERS: Dict[str, Callable[[str, TestCase], ScoreResult]] = {
    "exact_match": exact_match,
    "regex_match": regex_match,
    "keyword_overlap": keyword_overlap,
}


def get_scorer(name: str) -> Callable[[str, TestCase], ScoreResult]:
    if name not in SCORERS:
        raise ValueError(f"Unknown scorer '{name}'. Available: {list(SCORERS.keys())}")
    return SCORERS[name]
