"""Multi-config sweep: run the same suite against several provider/model
configs in one invocation and summarize results side by side.

A sweep config file looks like:

    configs:
      - name: gpt-4o-mini
        provider: openai
        model: gpt-4o-mini
      - name: gpt-4o
        provider: openai
        model: gpt-4o

Each entry's `name` is used as the label in output/JSON; `provider` plus any
of `model`, `base_url`, `temperature`, `retries` are forwarded to
`get_provider`.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List

import yaml

from evalharness.providers import get_provider
from evalharness.runner import RunResult, run_suite
from evalharness.testcase import TestSuite


@dataclass
class SweepConfig:
    name: str
    provider: str
    options: dict


def load_sweep_config(path: str) -> List[SweepConfig]:
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    if not raw or "configs" not in raw:
        raise ValueError(f"Sweep file {path} is missing a top-level 'configs' key")

    configs = []
    for entry in raw["configs"]:
        for required in ("name", "provider"):
            if required not in entry:
                raise ValueError(f"Sweep config entry missing required field '{required}': {entry}")
        options = {k: v for k, v in entry.items() if k not in ("name", "provider")}
        configs.append(SweepConfig(name=entry["name"], provider=entry["provider"], options=options))

    return configs


@dataclass
class SweepResult:
    config_name: str
    run_result: RunResult


def run_sweep(suite: TestSuite, configs: List[SweepConfig]) -> List[SweepResult]:
    results = []
    for cfg in configs:
        provider = get_provider(cfg.provider, **cfg.options)
        result = run_suite(suite, provider)
        results.append(SweepResult(config_name=cfg.name, run_result=result))
    return results


def sweep_to_dict(results: List[SweepResult]) -> dict:
    return {r.config_name: r.run_result.to_dict() for r in results}
