"""HTML report rendering for runs and diffs.

Produces a single, self-contained HTML file (inline CSS, no external
assets/CDN) so reports are easy to open locally or attach to a CI artifact.
Deliberately dependency-free -- just string templating with manual
escaping of any model/user-controlled content via `html.escape`.
"""
from __future__ import annotations

from html import escape
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from evalharness.diff import RunDiff
    from evalharness.runner import RunResult

_STYLE = """
body { font-family: -apple-system, Segoe UI, Helvetica, Arial, sans-serif; margin: 2rem; color: #1a1a1a; background: #fafafa; }
h1 { margin-bottom: 0.25rem; }
.subtitle { color: #666; margin-top: 0; }
table { border-collapse: collapse; width: 100%; margin-top: 1rem; background: #fff; }
th, td { border: 1px solid #ddd; padding: 0.5rem 0.75rem; text-align: left; vertical-align: top; }
th { background: #f0f0f0; }
tr.pass, tr.improved, tr.newly_passing { background: #eafbea; }
tr.fail, tr.regressed, tr.newly_failing { background: #fdecea; }
tr.unchanged, tr.added, tr.removed { background: #fff; }
.badge { display: inline-block; padding: 0.1rem 0.5rem; border-radius: 0.25rem; font-size: 0.8rem; font-weight: 600; }
.badge.pass, .badge.improved, .badge.newly_passing { background: #2e7d32; color: #fff; }
.badge.fail, .badge.regressed, .badge.newly_failing { background: #c62828; color: #fff; }
.badge.unchanged, .badge.added, .badge.removed { background: #757575; color: #fff; }
.summary { background: #fff; border: 1px solid #ddd; padding: 1rem; border-radius: 0.5rem; display: inline-block; }
pre.detail { white-space: pre-wrap; word-break: break-word; margin: 0; font-size: 0.85rem; }
"""


def render_run_html(result: "RunResult") -> str:
    rows = []
    for c in result.case_results:
        css_class = "pass" if c.passed else "fail"
        badge_text = "PASS" if c.passed else "FAIL"
        rows.append(
            f"<tr class='{css_class}'>"
            f"<td>{escape(c.case_id)}</td>"
            f"<td><span class='badge {css_class}'>{badge_text}</span></td>"
            f"<td>{c.score:.2f}</td>"
            f"<td><pre class='detail'>{escape(c.prompt)}</pre></td>"
            f"<td><pre class='detail'>{escape(c.output)}</pre></td>"
            f"<td><pre class='detail'>{escape(c.detail)}</pre></td>"
            f"</tr>"
        )

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset='utf-8'>
<title>Eval report: {escape(result.suite_name)}</title>
<style>{_STYLE}</style>
</head>
<body>
<h1>{escape(result.suite_name)}</h1>
<p class='subtitle'>Provider: {escape(result.provider_name)}</p>
<div class='summary'>
  <strong>{result.pass_count}/{result.total_count}</strong> cases passed &mdash;
  average score <strong>{result.average_score:.2f}</strong>
</div>
<table>
<thead><tr><th>Case</th><th>Status</th><th>Score</th><th>Prompt</th><th>Output</th><th>Detail</th></tr></thead>
<tbody>
{''.join(rows)}
</tbody>
</table>
</body>
</html>
"""


def render_diff_html(diff: "RunDiff") -> str:
    rows = []
    for e in diff.entries:
        score_a = "-" if e.score_a is None else f"{e.score_a:.2f}"
        score_b = "-" if e.score_b is None else f"{e.score_b:.2f}"
        delta = "-" if e.delta is None else f"{e.delta:+.2f}"
        rows.append(
            f"<tr class='{e.status}'>"
            f"<td>{escape(e.case_id)}</td>"
            f"<td><span class='badge {e.status}'>{escape(e.status.replace('_', ' ').upper())}</span></td>"
            f"<td>{score_a}</td>"
            f"<td>{score_b}</td>"
            f"<td>{delta}</td>"
            f"</tr>"
        )

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset='utf-8'>
<title>Eval diff: {escape(diff.run_a_label)} vs {escape(diff.run_b_label)}</title>
<style>{_STYLE}</style>
</head>
<body>
<h1>Run comparison</h1>
<p class='subtitle'>{escape(diff.run_a_label)} &rarr; {escape(diff.run_b_label)}</p>
<div class='summary'>
  Overall avg score: <strong>{diff.average_a:.2f} &rarr; {diff.average_b:.2f}</strong>
  ({diff.average_delta:+.2f})<br>
  Regressions: <strong>{diff.regressed_count}</strong> &nbsp;
  Improvements: <strong>{diff.improved_count}</strong>
</div>
<table>
<thead><tr><th>Case</th><th>Status</th><th>Score A</th><th>Score B</th><th>Delta</th></tr></thead>
<tbody>
{''.join(rows)}
</tbody>
</table>
</body>
</html>
"""


def write_html(html: str, path: str) -> None:
    import os

    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
