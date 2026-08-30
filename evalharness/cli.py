"""Command-line entrypoint.

Usage:
    python -m evalharness.cli run <suite.yaml> [options]
    python -m evalharness.cli compare <run_a.json> <run_b.json> [options]
    python -m evalharness.cli sweep <suite.yaml> <sweep.yaml> [options]
"""
from __future__ import annotations

import argparse
import json
import sys

from evalharness.diff import diff_runs
from evalharness.providers import get_provider
from evalharness.report import render_diff_html, render_run_html, write_html
from evalharness.runner import run_suite
from evalharness.scorers import make_llm_rubric_scorer, register_scorer
from evalharness.sweep import load_sweep_config, run_sweep, sweep_to_dict
from evalharness.testcase import load_suite


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="evalharness", description="LLM prompt eval harness")
    sub = parser.add_subparsers(dest="command", required=True)

    run_p = sub.add_parser("run", help="Run a test suite")
    run_p.add_argument("suite_path", help="Path to a YAML suite file")
    run_p.add_argument("--provider", default="mock", help="Provider name (default: mock)")
    run_p.add_argument("--model", default=None, help="Model name to pass to the provider")
    run_p.add_argument("--base-url", default=None, help="Base URL for HTTP-backed providers")
    run_p.add_argument("--temperature", type=float, default=0.0, help="Sampling temperature (default: 0.0)")
    run_p.add_argument("--retries", type=int, default=3, help="Max attempts for HTTP providers on transient errors (default: 3)")
    run_p.add_argument("--judge-provider", default=None, help="Provider to use for llm_rubric grading (default: same as --provider)")
    run_p.add_argument("--judge-model", default=None, help="Model name for the judge provider")
    run_p.add_argument("--json", dest="json_out", default=None, help="Write results to this JSON file")
    run_p.add_argument("--html", dest="html_out", default=None, help="Write an HTML report to this file")

    cmp_p = sub.add_parser("compare", help="Compare two saved JSON run results")
    cmp_p.add_argument("run_a", help="Path to earlier/baseline run JSON")
    cmp_p.add_argument("run_b", help="Path to later/candidate run JSON")
    cmp_p.add_argument("--html", dest="html_out", default=None, help="Write an HTML diff report to this file")

    sweep_p = sub.add_parser("sweep", help="Run a suite against multiple configs in one go")
    sweep_p.add_argument("suite_path", help="Path to a YAML suite file")
    sweep_p.add_argument("sweep_path", help="Path to a YAML sweep config file (list of provider configs)")
    sweep_p.add_argument("--json", dest="json_out", default=None, help="Write combined results to this JSON file")

    return parser


def print_report(result) -> None:
    print(f"Suite: {result.suite_name}  Provider: {result.provider_name}")
    print("-" * 60)
    for c in result.case_results:
        status = "PASS" if c.passed else "FAIL"
        print(f"[{status}] {c.case_id}  score={c.score:.2f}")
        print(f"        {c.detail}")
    print("-" * 60)
    print(
        f"Result: {result.pass_count}/{result.total_count} passed "
        f"(avg score {result.average_score:.2f})"
    )


def print_diff(diff) -> None:
    print(f"Comparing runs -- {diff.run_a_label} -> {diff.run_b_label}")
    print("-" * 60)
    for entry in diff.entries:
        marker = {
            "improved": "UP",
            "regressed": "DOWN",
            "unchanged": "==",
            "newly_passing": "NEW-PASS",
            "newly_failing": "NEW-FAIL",
            "added": "ADDED",
            "removed": "REMOVED",
        }[entry.status]
        print(
            f"[{marker:>9}] {entry.case_id}  "
            f"{entry.score_a} -> {entry.score_b}"
        )
    print("-" * 60)
    print(
        f"Overall avg score: {diff.average_a:.2f} -> {diff.average_b:.2f} "
        f"({diff.average_delta:+.2f})"
    )
    print(
        f"Regressions: {diff.regressed_count}  Improvements: {diff.improved_count}"
    )


def print_sweep(sweep_results) -> None:
    print(f"{'Config':<20} {'Provider':<12} {'Pass':<10} {'Avg score':<10}")
    print("-" * 60)
    for r in sweep_results:
        rr = r.run_result
        pass_str = f"{rr.pass_count}/{rr.total_count}"
        print(f"{r.config_name:<20} {rr.provider_name:<12} {pass_str:<10} {rr.average_score:<10.2f}")
    print("-" * 60)


def _build_provider(name, model, base_url, temperature, retries=None):
    kwargs = {}
    if model is not None:
        kwargs["model"] = model
    if base_url is not None:
        kwargs["base_url"] = base_url
    kwargs["temperature"] = temperature
    if retries is not None and name == "openai":
        kwargs["retries"] = retries
    return get_provider(name, **kwargs)


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "run":
        suite = load_suite(args.suite_path)
        provider = _build_provider(args.provider, args.model, args.base_url, args.temperature, args.retries)

        judge_provider_name = args.judge_provider or args.provider
        judge_provider = _build_provider(
            judge_provider_name, args.judge_model, args.base_url, args.temperature, args.retries
        )
        register_scorer("llm_rubric", make_llm_rubric_scorer(judge_provider))

        result = run_suite(suite, provider)
        print_report(result)

        if args.json_out:
            import os

            os.makedirs(os.path.dirname(args.json_out) or ".", exist_ok=True)
            with open(args.json_out, "w", encoding="utf-8") as f:
                json.dump(result.to_dict(), f, indent=2)
            print(f"Wrote JSON results to {args.json_out}")

        if args.html_out:
            write_html(render_run_html(result), args.html_out)
            print(f"Wrote HTML report to {args.html_out}")

        return 0 if result.pass_count == result.total_count else 1

    if args.command == "compare":
        with open(args.run_a, "r", encoding="utf-8") as f:
            data_a = json.load(f)
        with open(args.run_b, "r", encoding="utf-8") as f:
            data_b = json.load(f)

        diff = diff_runs(data_a, data_b, label_a=args.run_a, label_b=args.run_b)
        print_diff(diff)

        if args.html_out:
            write_html(render_diff_html(diff), args.html_out)
            print(f"Wrote HTML diff report to {args.html_out}")

        return 1 if diff.regressed_count > 0 else 0

    if args.command == "sweep":
        suite = load_suite(args.suite_path)
        configs = load_sweep_config(args.sweep_path)
        results = run_sweep(suite, configs)
        print_sweep(results)

        if args.json_out:
            import os

            os.makedirs(os.path.dirname(args.json_out) or ".", exist_ok=True)
            with open(args.json_out, "w", encoding="utf-8") as f:
                json.dump(sweep_to_dict(results), f, indent=2)
            print(f"Wrote combined JSON results to {args.json_out}")

        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
