"""Executes a TestSuite against a Provider and produces structured results."""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import List

from evalharness.providers import Provider
from evalharness.scorers import get_scorer, ScoreResult
from evalharness.testcase import TestCase, TestSuite


@dataclass
class CaseResult:
    case_id: str
    prompt: str
    output: str
    passed: bool
    score: float
    detail: str


@dataclass
class RunResult:
    suite_name: str
    provider_name: str
    case_results: List[CaseResult]

    @property
    def pass_count(self) -> int:
        return sum(1 for c in self.case_results if c.passed)

    @property
    def total_count(self) -> int:
        return len(self.case_results)

    @property
    def average_score(self) -> float:
        if not self.case_results:
            return 0.0
        return sum(c.score for c in self.case_results) / len(self.case_results)

    def to_dict(self) -> dict:
        return {
            "suite_name": self.suite_name,
            "provider_name": self.provider_name,
            "pass_count": self.pass_count,
            "total_count": self.total_count,
            "average_score": self.average_score,
            "case_results": [asdict(c) for c in self.case_results],
        }


def run_case(provider: Provider, case: TestCase) -> CaseResult:
    output = provider.generate(case.prompt)
    scorer = get_scorer(case.scorer)
    result: ScoreResult = scorer(output, case)
    return CaseResult(
        case_id=case.id,
        prompt=case.prompt,
        output=output,
        passed=result.passed,
        score=result.score,
        detail=result.detail,
    )


def run_suite(suite: TestSuite, provider: Provider) -> RunResult:
    case_results = [run_case(provider, case) for case in suite.cases]
    return RunResult(
        suite_name=suite.name,
        provider_name=provider.name,
        case_results=case_results,
    )
