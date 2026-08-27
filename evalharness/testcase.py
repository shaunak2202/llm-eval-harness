"""Data model for eval test cases and suites, plus a YAML loader."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional

import yaml


@dataclass
class TestCase:
    id: str
    prompt: str
    scorer: str
    expected: Any
    threshold: Optional[float] = None
    metadata: dict = field(default_factory=dict)


@dataclass
class TestSuite:
    name: str
    cases: List[TestCase]


def load_suite(path: str) -> TestSuite:
    """Load a TestSuite from a YAML file.

    Expected format:

    name: suite-name
    cases:
      - id: some-id
        prompt: "..."
        scorer: exact_match
        expected: "..."
        threshold: 0.5   # optional, scorer-specific
    """
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    if not raw or "cases" not in raw:
        raise ValueError(f"Suite file {path} is missing a top-level 'cases' key")

    cases = []
    for c in raw["cases"]:
        for required in ("id", "prompt", "scorer", "expected"):
            if required not in c:
                raise ValueError(f"Test case missing required field '{required}': {c}")
        cases.append(
            TestCase(
                id=c["id"],
                prompt=c["prompt"],
                scorer=c["scorer"],
                expected=c["expected"],
                threshold=c.get("threshold"),
                metadata=c.get("metadata", {}),
            )
        )

    return TestSuite(name=raw.get("name", "unnamed-suite"), cases=cases)
