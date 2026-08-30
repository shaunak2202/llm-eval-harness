"""Scoring functions.

Each scorer takes the raw model output and the TestCase, and returns a
ScoreResult (passed: bool, score: float in [0,1], detail: str).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable, Dict

from evalharness.providers import Provider
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


_RUBRIC_PROMPT_TEMPLATE = """You are grading a model's output against a rubric.

Rubric:
{rubric}

Model output to grade:
---
{output}
---

Respond with a line of the exact form "SCORE: <number between 0.0 and 1.0>"
followed by a one-sentence justification."""

_SCORE_RE = re.compile(r"SCORE:\s*([0-9]*\.?[0-9]+)", re.IGNORECASE)


def _parse_judge_score(judge_output: str) -> float:
    match = _SCORE_RE.search(judge_output)
    if not match:
        raise ValueError(f"Could not parse a SCORE from judge output: {judge_output!r}")
    score = float(match.group(1))
    return max(0.0, min(1.0, score))


def make_llm_rubric_scorer(judge_provider: Provider) -> Callable[[str, TestCase], ScoreResult]:
    """Build an llm_rubric scorer bound to a specific judge provider.

    `case.expected` is treated as the free-text rubric. `case.threshold`
    (default 0.7) is the minimum judge score to count as a pass.
    """

    def llm_rubric(output: str, case: TestCase) -> ScoreResult:
        rubric = str(case.expected)
        judge_prompt = _RUBRIC_PROMPT_TEMPLATE.format(rubric=rubric, output=output)
        judge_output = judge_provider.generate(judge_prompt)
        score = _parse_judge_score(judge_output)
        threshold = case.threshold if case.threshold is not None else 0.7
        passed = score >= threshold
        return ScoreResult(
            passed=passed,
            score=score,
            detail=f"judge={judge_provider.name} score={score} threshold={threshold} raw={judge_output!r}",
        )

    return llm_rubric


SCORERS: Dict[str, Callable[[str, TestCase], ScoreResult]] = {
    "exact_match": exact_match,
    "regex_match": regex_match,
    "keyword_overlap": keyword_overlap,
}


def register_scorer(name: str, fn: Callable[[str, TestCase], ScoreResult]) -> None:
    """Register (or replace) a scorer, e.g. to bind llm_rubric to a judge provider."""
    SCORERS[name] = fn


def get_scorer(name: str) -> Callable[[str, TestCase], ScoreResult]:
    if name not in SCORERS:
        raise ValueError(f"Unknown scorer '{name}'. Available: {list(SCORERS.keys())}")
    return SCORERS[name]
