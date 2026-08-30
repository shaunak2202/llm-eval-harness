# LLM Eval Harness

A small, provider-agnostic toolkit for regression-testing LLM prompts. Instead of
manually eyeballing outputs every time a prompt changes, define test cases once and
run them through scorers that give you a pass/fail + numeric score, plus a diff
against a previous run.

## Why

Working on LLM pipelines (document QA, speech-to-text post-processing, etc.) it's
easy to tweak a prompt, glance at 2-3 outputs, and ship it. This harness makes that
process repeatable: same test suite, same scoring rules, every time -- so a prompt
or model change can be evaluated objectively before it goes out, and you can diff
two runs to see exactly which cases got better or worse.

## Status

**In progress**, but the core loop -- write cases, run against mock or a real
OpenAI-compatible endpoint, score, save JSON, diff two runs -- works end to end.

Working so far:

- Core data model for test cases and suites (`evalharness/testcase.py`)
- Pluggable provider interface (`evalharness/providers.py`) with:
  - `MockProvider` for offline dev (deterministic, no API key needed)
  - `OpenAIProvider` for any OpenAI-compatible chat-completions API (real
    OpenAI, or self-hosted / third-party endpoints that speak the same
    protocol, e.g. many local inference servers)
- Scorers (`evalharness/scorers.py`):
  - `exact_match`, `regex_match`, `keyword_overlap`
  - `llm_rubric` -- uses a second ("judge") model call to grade subjective
    outputs against a free-text rubric, parsing a `SCORE: 0.0-1.0` line back
    out of the judge's response
- Runner that executes a suite against a provider + config and produces a
  structured `RunResult` (`evalharness/runner.py`)
- CLI (`evalharness/cli.py`):
  - `run` -- run a suite, print a report, optionally save JSON
  - `compare` -- diff two saved JSON runs, case by case, and report
    regressions/improvements
- Example test suites (`examples/qa_suite.yaml`, `examples/rubric_suite.yaml`)
- Unit tests for scorers, providers, runner, and diffing (`tests/`)

Not yet built (planned for follow-up session):

- HTML report export
- Multi-config comparison in a single `run` invocation (currently you run
  twice and `compare` the two JSON files)
- Retry/backoff + rate-limit handling for the HTTP provider

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
python -m evalharness.cli run examples/qa_suite.yaml --provider mock --json runs/baseline.json
```

This prints a per-case pass/fail report and an overall score summary, and
saves the structured results to `runs/baseline.json`.

### Using a real OpenAI-compatible API

```bash
export OPENAI_API_KEY=sk-...
python -m evalharness.cli run examples/qa_suite.yaml \
  --provider openai --model gpt-4o-mini --json runs/gpt4o-mini.json
```

Optional flags: `--base-url` (defaults to `https://api.openai.com/v1`, so you
can point it at any compatible endpoint), `--temperature` (default `0.0`).

### LLM-graded rubric scoring

For subjective outputs where exact-match/regex/keyword scoring doesn't cut
it, use `llm_rubric`. It sends the model's output plus your rubric to a
*judge* model (by default the same provider, or override with
`--judge-provider` / `--judge-model`) and asks for a score:

```yaml
- id: helpful-explanation
  prompt: "Explain what a hash map is, in 2 sentences, to a beginner."
  scorer: llm_rubric
  expected: |
    Score 1.0 if the explanation is correct, uses no undefined jargon, and
    is 1-3 sentences. Score 0.0 if it's wrong or way too long. Partial
    credit for partially meeting these criteria.
  threshold: 0.7
```

```bash
python -m evalharness.cli run examples/rubric_suite.yaml --provider mock \
  --judge-provider mock
```

(With `--provider mock`/`--judge-provider mock` this is fully offline and
deterministic, useful for testing the plumbing; swap in `openai` for real
grading.)

### Comparing two runs

After saving two JSON runs (e.g. before/after a prompt edit), diff them:

```bash
python -m evalharness.cli compare runs/baseline.json runs/gpt4o-mini.json
```

This prints, per case: unchanged / improved / regressed / newly-passing /
newly-failing, plus an overall score delta, and exits non-zero if any case
regressed (handy in CI).

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
| `llm_rubric` | A judge model scores the output 0.0-1.0 against a free-text rubric, pass if >= threshold (default 0.7) |

## Project layout

```
evalharness/
  testcase.py    # TestCase / TestSuite data model + YAML loader
  providers.py    # Provider interface + MockProvider + OpenAIProvider
  scorers.py       # Scoring functions incl. llm_rubric
  runner.py         # Executes a suite, returns structured results
  diff.py            # Run-to-run comparison logic
  cli.py             # Command-line entrypoint (run, compare)
examples/
  qa_suite.yaml
  rubric_suite.yaml
tests/
  test_scorers.py
  test_runner.py
  test_providers.py
  test_diff.py
```

## Design notes

- Providers are a simple `generate(prompt: str, **kwargs) -> str` interface so
  adding a new backend is a small, isolated change -- `OpenAIProvider` in this
  session was added without touching the runner, scorers, or CLI's core flow.
- Scorers are plain functions `(output: str, case: TestCase) -> ScoreResult`,
  registered in a dict. `llm_rubric` takes an optional `judge_provider` via
  functools.partial binding so it fits the same signature the runner expects.
- Results are plain dataclasses (JSON-serializable) rather than printed
  directly, which is what makes `compare` possible: it just loads two
  `RunResult.to_dict()` blobs and matches cases by `case_id`.
- The HTTP provider has no retry/backoff logic yet and is intentionally
  minimal (uses `urllib` from the stdlib, no extra HTTP dependency) -- fine
  for a small eval suite, called out in README as a known limitation rather
  than pretending it's production-grade.

---

Built by a personal automation project Shaunak set up: it uses Claude to design and write real, working code within his actual skill set, and pushes it here on a regular schedule as an ongoing practice/portfolio project.

---

Built by a personal automation project Shaunak set up: it uses Claude to design and write real, working code within his actual skill set, and pushes it here on a regular schedule as an ongoing practice/portfolio project.
