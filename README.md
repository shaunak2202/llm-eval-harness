# LLM Eval Harness

A small, provider-agnostic toolkit for regression-testing LLM prompts. Instead of
manually eyeballing outputs every time a prompt changes, define test cases once and
run them through scorers that give you a pass/fail + numeric score, plus a diff
against a previous run.

## Why

Working on LLM pipelines (document QA, speech-to-text post-processing, etc.) it's
easy to tweak a prompt, glance at 2-3 outputs, and ship it. This harness makes that
process repeatable: same test suite, same scoring rules, every time -- so a prompt
or model change can be evaluated objectively before it goes out.

## Status

**In progress.** Working so far:

- Core data model for test cases and suites (`evalharness/testcase.py`)
- Pluggable provider interface with a mock provider for offline dev
  (`evalharness/providers.py`)
- Scorers: exact match, regex match, keyword overlap (`evalharness/scorers.py`)
- Runner that executes a suite against a provider + config and produces a
  structured `RunResult` (`evalharness/runner.py`)
- CLI entrypoint (`evalharness/cli.py`) to run a suite and print a report
- Example test suite (`examples/qa_suite.yaml`)
- Unit tests for scorers and runner (`tests/`)

Not yet built (planned for follow-up sessions):

- OpenAI-compatible HTTP provider (currently only the mock provider is wired up)
- LLM-graded rubric scorer (using a second model call to grade subjective outputs)
- Run-to-run diff report (`evalharness compare run1.json run2.json`)
- JSON/HTML report export

## Install

```bash
git clone https://github.com/shaunak2202/llm-eval-harness
cd llm-eval-harness
pip install -r requirements.txt
```

Requires Python 3.10+.

## Usage

Run the example suite against the built-in mock provider (no API key needed):

```bash
python -m evalharness.cli run examples/qa_suite.yaml --provider mock
```

This prints a per-case pass/fail report and an overall score summary.

### Writing a test suite

```yaml
name: qa-basic
cases:
  - id: capital-of-france
    prompt: "What is the capital of France? Answer with just the city name."
    scorer: exact_match
    expected: "Paris"

  - id: contains-keywords
    prompt: "List three primary colors."
    scorer: keyword_overlap
    expected: ["red", "blue", "yellow"]
    threshold: 0.66

  - id: format-check
    prompt: "Return today's date in YYYY-MM-DD format."
    scorer: regex_match
    expected: "^\\d{4}-\\d{2}-\\d{2}$"
```

### Scorers

| Scorer | What it does |
|---|---|
| `exact_match` | Case-insensitive exact string match after stripping whitespace |
| `regex_match` | Passes if the model output matches the given regex |
| `keyword_overlap` | Fraction of expected keywords present in output, pass if >= threshold |

## Project layout

```
evalharness/
  testcase.py    # TestCase / TestSuite data model + YAML loader
  providers.py    # Provider interface + MockProvider
  scorers.py       # Scoring functions
  runner.py         # Executes a suite, returns structured results
  cli.py             # Command-line entrypoint
examples/
  qa_suite.yaml
tests/
  test_scorers.py
  test_runner.py
```

## Design notes

- Providers are a simple `generate(prompt: str, **kwargs) -> str` interface so
  adding a real API-backed provider later is a small, isolated change.
- Scorers are plain functions `(output: str, case: TestCase) -> ScoreResult`,
  registered in a dict, so new scoring strategies are easy to add without
  touching the runner.
- Results are returned as plain dataclasses (JSON-serializable) rather than
  printed directly, so future work (diffing, HTML export) can consume the
  same structure the CLI does.

---

Built by a personal automation project Shaunak set up: it uses Claude to design and write real, working code within his actual skill set, and pushes it here on a regular schedule as an ongoing practice/portfolio project.
