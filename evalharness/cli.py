"""Command-line entrypoint.

Usage:
    python -m evalharness.cli run <suite.yaml> [--provider mock] [--json out.json]
"""
from __future__ import annotations

import argparse
import json
import sys

from evalharness.providers import get_provider
from evalharness.runner import run_suite
from evalharness.testcase import load_suite


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="evalharness", description="LLM prompt eval harness")
    sub = parser.add_subparsers(dest="command", required=True)

    run_p = sub.add_parser("run", help="Run a test suite")
    run_p.add_argument("suite_path", help="Path to a YAML suite file")
    run_p.add_argument("--provider", default="mock", help="Provider name (default: mock)")
    run_p.add_argument("--json", dest="json_out", default=None, help="Write results to this JSON file")

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


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "run":
        suite = load_suite(args.suite_path)
        provider = get_provider(args.provider)
        result = run_suite(suite, provider)
        print_report(result)

        if args.json_out:
            with open(args.json_out, "w", encoding="utf-8") as f:
                json.dump(result.to_dict(), f, indent=2)
            print(f"Wrote JSON results to {args.json_out}")

        return 0 if result.pass_count == result.total_count else 1

    return 1


if __name__ == "__main__":
    sys.exit(main())
