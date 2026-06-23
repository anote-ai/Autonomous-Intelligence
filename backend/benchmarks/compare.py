"""Benchmark comparison — diff two runs to detect regressions.

Compares a *candidate* JSON report against a *baseline* JSON report and
produces a structured diff that CI can use to block or allow promotion.

Usage (CLI):
    python -m benchmarks.compare baseline.json candidate.json

Usage (programmatic):
    from benchmarks.compare import compare_reports, render_diff_markdown
    diff = compare_reports(baseline_dict, candidate_dict)
    print(render_diff_markdown(diff))
    if diff["decision"] == "BLOCK":
        sys.exit(1)
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ScenarioDiff:
    scenario_id: str
    workflow: str
    baseline_score: float
    candidate_score: float
    baseline_passed: bool
    candidate_passed: bool

    @property
    def delta(self) -> float:
        return self.candidate_score - self.baseline_score

    @property
    def is_regression(self) -> bool:
        # A scenario regresses if it was passing and now fails, or score dropped > 10%
        return (self.baseline_passed and not self.candidate_passed) or self.delta < -0.10

    @property
    def is_improvement(self) -> bool:
        return (not self.baseline_passed and self.candidate_passed) or self.delta > 0.10


@dataclass
class BenchmarkDiff:
    baseline_model: str
    candidate_model: str
    baseline_timestamp: str
    candidate_timestamp: str
    scenario_diffs: list[ScenarioDiff] = field(default_factory=list)
    new_scenarios: list[str] = field(default_factory=list)   # in candidate but not baseline
    removed_scenarios: list[str] = field(default_factory=list)  # in baseline but not candidate

    @property
    def regressions(self) -> list[ScenarioDiff]:
        return [d for d in self.scenario_diffs if d.is_regression]

    @property
    def improvements(self) -> list[ScenarioDiff]:
        return [d for d in self.scenario_diffs if d.is_improvement]

    @property
    def decision(self) -> str:
        """PROMOTE if no regressions; BLOCK otherwise."""
        return "BLOCK" if self.regressions else "PROMOTE"

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision": self.decision,
            "baseline_model": self.baseline_model,
            "candidate_model": self.candidate_model,
            "baseline_timestamp": self.baseline_timestamp,
            "candidate_timestamp": self.candidate_timestamp,
            "summary": {
                "total_compared": len(self.scenario_diffs),
                "regressions": len(self.regressions),
                "improvements": len(self.improvements),
                "new_scenarios": len(self.new_scenarios),
                "removed_scenarios": len(self.removed_scenarios),
            },
            "regressions": [
                {
                    "id": d.scenario_id,
                    "workflow": d.workflow,
                    "baseline_score": round(d.baseline_score, 4),
                    "candidate_score": round(d.candidate_score, 4),
                    "delta": round(d.delta, 4),
                    "baseline_passed": d.baseline_passed,
                    "candidate_passed": d.candidate_passed,
                }
                for d in self.regressions
            ],
            "improvements": [
                {
                    "id": d.scenario_id,
                    "workflow": d.workflow,
                    "baseline_score": round(d.baseline_score, 4),
                    "candidate_score": round(d.candidate_score, 4),
                    "delta": round(d.delta, 4),
                }
                for d in self.improvements
            ],
            "new_scenarios": self.new_scenarios,
            "removed_scenarios": self.removed_scenarios,
        }


def compare_reports(baseline: dict[str, Any], candidate: dict[str, Any]) -> BenchmarkDiff:
    """Compare two benchmark report dicts (as produced by runner.to_dict())."""
    diff = BenchmarkDiff(
        baseline_model=baseline.get("model", "unknown"),
        candidate_model=candidate.get("model", "unknown"),
        baseline_timestamp=baseline.get("timestamp", ""),
        candidate_timestamp=candidate.get("timestamp", ""),
    )

    # Index scenarios from both reports
    baseline_scenarios = _index_scenarios(baseline)
    candidate_scenarios = _index_scenarios(candidate)

    all_ids = set(baseline_scenarios) | set(candidate_scenarios)
    for sid in sorted(all_ids):
        if sid not in baseline_scenarios:
            diff.new_scenarios.append(sid)
        elif sid not in candidate_scenarios:
            diff.removed_scenarios.append(sid)
        else:
            b = baseline_scenarios[sid]
            c = candidate_scenarios[sid]
            diff.scenario_diffs.append(ScenarioDiff(
                scenario_id=sid,
                workflow=b.get("workflow", c.get("workflow", "unknown")),
                baseline_score=b["score"],
                candidate_score=c["score"],
                baseline_passed=b["passed"],
                candidate_passed=c["passed"],
            ))

    return diff


def render_diff_markdown(diff: BenchmarkDiff) -> str:
    decision_icon = "✅" if diff.decision == "PROMOTE" else "🚫"
    lines: list[str] = [
        "# Benchmark Comparison Report",
        "",
        f"**Decision:** {decision_icon} **{diff.decision}**",
        "",
        "| | Baseline | Candidate |",
        "|--|----------|-----------|",
        f"| Model | `{diff.baseline_model}` | `{diff.candidate_model}` |",
        f"| Timestamp | {diff.baseline_timestamp} | {diff.candidate_timestamp} |",
        "",
        "## Summary",
        "",
        "| Metric | Count |",
        "|--------|-------|",
        f"| Scenarios compared | {len(diff.scenario_diffs)} |",
        f"| Regressions | {len(diff.regressions)} |",
        f"| Improvements | {len(diff.improvements)} |",
        f"| New scenarios | {len(diff.new_scenarios)} |",
        f"| Removed scenarios | {len(diff.removed_scenarios)} |",
        "",
    ]

    if diff.regressions:
        lines += [
            "## 🚨 Regressions (blocking)",
            "",
            "| Scenario | Workflow | Baseline Score | Candidate Score | Δ |",
            "|----------|----------|----------------|-----------------|---|",
        ]
        for r in diff.regressions:
            delta_str = f"{r.delta:+.2f}"
            lines.append(
                f"| `{r.scenario_id}` | {r.workflow} | {r.baseline_score:.2f} "
                f"| {r.candidate_score:.2f} | {delta_str} |"
            )
        lines.append("")

    if diff.improvements:
        lines += [
            "## 🎉 Improvements",
            "",
            "| Scenario | Workflow | Baseline Score | Candidate Score | Δ |",
            "|----------|----------|----------------|-----------------|---|",
        ]
        for i in diff.improvements:
            delta_str = f"{i.delta:+.2f}"
            lines.append(
                f"| `{i.scenario_id}` | {i.workflow} | {i.baseline_score:.2f} "
                f"| {i.candidate_score:.2f} | {delta_str} |"
            )
        lines.append("")

    if diff.new_scenarios:
        lines += [
            "## New scenarios (not in baseline)",
            "",
            *[f"- `{s}`" for s in diff.new_scenarios],
            "",
        ]

    if diff.removed_scenarios:
        lines += [
            "## Removed scenarios (were in baseline)",
            "",
            *[f"- `{s}`" for s in diff.removed_scenarios],
            "",
        ]

    return "\n".join(lines)


def _index_scenarios(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Build a flat dict of scenario_id → scenario dict from a suite or workflow report."""
    index: dict[str, dict[str, Any]] = {}
    # Suite-level report has "workflows" → each has "scenarios"
    if "workflows" in report:
        for wf in report["workflows"]:
            for s in wf.get("scenarios", []):
                s["workflow"] = wf["workflow"]
                index[s["id"]] = s
    # Workflow-level report has "scenarios" directly
    elif "scenarios" in report:
        for s in report.get("scenarios", []):
            s["workflow"] = report.get("workflow", "unknown")
            index[s["id"]] = s
    return index


def _main() -> None:
    if len(sys.argv) < 3:
        print("Usage: python -m benchmarks.compare <baseline.json> <candidate.json> [--out diff.json]")
        sys.exit(2)

    baseline_path = Path(sys.argv[1])
    candidate_path = Path(sys.argv[2])
    out_path = Path(sys.argv[4]) if len(sys.argv) > 4 and sys.argv[3] == "--out" else None

    baseline = json.loads(baseline_path.read_text())
    candidate = json.loads(candidate_path.read_text())

    diff = compare_reports(baseline, candidate)
    diff_dict = diff.to_dict()

    print(render_diff_markdown(diff))

    if out_path:
        out_path.write_text(json.dumps(diff_dict, indent=2))
        print(f"\nDiff written to {out_path}")

    sys.exit(0 if diff.decision == "PROMOTE" else 1)


if __name__ == "__main__":
    _main()
