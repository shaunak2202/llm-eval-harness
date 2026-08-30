import textwrap

import pytest

from evalharness.sweep import load_sweep_config, run_sweep, sweep_to_dict
from evalharness.testcase import TestCase, TestSuite


def _suite():
    return TestSuite(
        name="sweep-suite",
        cases=[TestCase(id="c1", prompt="capital of France?", scorer="exact_match", expected="Paris")],
    )


def test_load_sweep_config(tmp_path):
    path = tmp_path / "sweep.yaml"
    path.write_text(
        textwrap.dedent(
            """
            configs:
              - name: cfg-a
                provider: mock
              - name: cfg-b
                provider: mock
                model: some-model
            """
        )
    )
    configs = load_sweep_config(str(path))
    assert len(configs) == 2
    assert configs[0].name == "cfg-a"
    assert configs[0].provider == "mock"
    assert configs[1].options == {"model": "some-model"}


def test_load_sweep_config_missing_key_raises(tmp_path):
    path = tmp_path / "bad.yaml"
    path.write_text("configs:\n  - name: only-name\n")
    with pytest.raises(ValueError):
        load_sweep_config(str(path))


def test_run_sweep_produces_one_result_per_config():
    configs = load_sweep_config.__wrapped__ if False else None  # placeholder no-op
    from evalharness.sweep import SweepConfig

    configs = [SweepConfig(name="a", provider="mock", options={}), SweepConfig(name="b", provider="mock", options={})]
    results = run_sweep(_suite(), configs)
    assert [r.config_name for r in results] == ["a", "b"]
    assert all(r.run_result.total_count == 1 for r in results)


def test_sweep_to_dict_keys_by_config_name():
    from evalharness.sweep import SweepConfig

    configs = [SweepConfig(name="baseline", provider="mock", options={})]
    results = run_sweep(_suite(), configs)
    data = sweep_to_dict(results)
    assert "baseline" in data
    assert data["baseline"]["suite_name"] == "sweep-suite"
