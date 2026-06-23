"""Benchmark report formatter — produces Markdown and JSON summaries.

Usage:
    from benchmarks.report import render_markdown
    md = render_markdown(workflow_result)
    print(md)
"""

from __future__ import annotations

from benchmarks.runner import BenchmarkSuiteResult, WorkflowBenchmarkResult, ScenarioResult


def render_markdown(result: WorkflowBenchmarkResult | BenchmarkSuiteResult) -> str:
    if isinstance(result, BenchmarkSuiteResult):
        return _render_suite(result)
    return _render_workflow(result)


def _render_suite(suite: BenchmarkSuiteResult) -> str:
    lines: list[str] = [
        f"# Panacea Benchmark Report",
        f"",
        f"**Model:** `{suite.model}`  ",
        f"**Timestamp:** {suite.timestamp}",
        f"",
        f"## Summary",
        f"",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Total scenarios | {suite.total_scenarios} |",
        f"| Passed | {suite.total_passed} |",
        f"| Pass rate | {suite.overall_pass_rate:.1%} |",
        f"| Total tokens (est.) | {suite.total_tokens:,} |",
        f"",
        f"## Workflow Results",
        f"",
        f"| Workflow | Scenarios | Passed | Pass Rate | Mean Score | Avg Latency |",
        f"|----------|-----------|--------|-----------|------------|-------------|",
    ]
    for wf in suite.workflows:
        icon = "✅" if wf.pass_rate == 1.0 else ("⚠️" if wf.pass_rate >= 0.7 else "❌")
        lines.append(
            f"| {icon} {wf.workflow} | {wf.total} | {wf.passed} "
            f"| {wf.pass_rate:.1%} | {wf.mean_score:.2f} | {wf.mean_latency_ms:.0f} ms |"
        )
    lines.append("")

    for wf in suite.workflows:
        lines.append(_render_workflow(wf))

    return "\n".join(lines)


def _render_workflow(result: WorkflowBenchmarkResult) -> str:
    lines: list[str] = [
        f"## Workflow: `{result.workflow}`",
        f"",
        f"**Model:** `{result.model}` | **Timestamp:** {result.timestamp}",
        f"",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Total | {result.total} |",
        f"| Passed | {result.passed} |",
        f"| Pass rate | {result.pass_rate:.1%} |",
        f"| Mean score | {result.mean_score:.2f} |",
        f"| Mean latency | {result.mean_latency_ms:.0f} ms |",
        f"| Total tokens (est.) | {result.total_tokens:,} |",
        f"",
        f"### Scenario Results",
        f"",
        f"| ID | Tags | Passed | Score | Latency | Failure |",
        f"|----|------|--------|-------|---------|---------|",
    ]
    for s in result.scenarios:
        icon = "✅" if s.passed else "❌"
        tags = ", ".join(s.tags)
        failure = s.failure_reason[:60] + "…" if len(s.failure_reason) > 60 else s.failure_reason
        lines.append(
            f"| {icon} `{s.scenario_id}` | {tags} | {s.passed} "
            f"| {s.score:.2f} | {s.latency_ms:.0f} ms | {failure} |"
        )

    failing = [s for s in result.scenarios if not s.passed]
    if failing:
        lines += ["", "### Failed Scenarios (detail)", ""]
        for s in failing:
            lines += [
                f"#### `{s.scenario_id}`",
                f"",
                f"**Description:** {s.description}  ",
                f"**Score:** {s.score:.2f}  ",
                f"**Failure:** {s.failure_reason}  ",
                f"**Answer (first 300 chars):** `{s.answer[:300]}`",
                f"",
            ]

    lines.append("")
    return "\n".join(lines)
