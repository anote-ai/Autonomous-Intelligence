"""Benchmark runner — loads fixtures, replays scenarios, records metrics.

Designed to run offline (no API keys) when a fake ``llm_fn`` is provided,
or against a real model in staging by passing the actual client.

Usage:
    from benchmarks.runner import BenchmarkRunner, LLMCallable

    # Offline / CI:
    runner = BenchmarkRunner(llm_fn=lambda prompt, ctx: "mock answer")
    results = runner.run_workflow("coding")

    # Staging (real model):
    import anthropic
    client = anthropic.Anthropic()
    def real_llm(prompt: str, context: str) -> str:
        msg = client.messages.create(
            model="claude-sonnet-4-6", max_tokens=1024,
            messages=[{"role": "user", "content": f"{context}\n\n{prompt}"}]
        )
        return msg.content[0].text
    runner = BenchmarkRunner(llm_fn=real_llm)
    results = runner.run_workflow("coding")
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC
from pathlib import Path
from typing import Any

FIXTURES_DIR = Path(__file__).parent / "fixtures"

# All supported workflow names (must match fixture file stems)
WORKFLOWS = ["coding", "outreach", "proposals", "jobs", "social"]

LLMCallable = Callable[[str, str], str]


@dataclass
class ScenarioResult:
    scenario_id: str
    workflow: str
    tags: list[str]
    description: str
    passed: bool
    score: float            # 0.0 – 1.0
    latency_ms: float
    estimated_tokens: int
    failure_reason: str     # empty string when passed
    answer: str
    assertions: dict[str, bool]  # per-assertion pass/fail


@dataclass
class WorkflowBenchmarkResult:
    workflow: str
    model: str
    timestamp: str
    scenarios: list[ScenarioResult] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.scenarios)

    @property
    def passed(self) -> int:
        return sum(1 for s in self.scenarios if s.passed)

    @property
    def pass_rate(self) -> float:
        return self.passed / self.total if self.total else 0.0

    @property
    def mean_score(self) -> float:
        return sum(s.score for s in self.scenarios) / self.total if self.total else 0.0

    @property
    def mean_latency_ms(self) -> float:
        return sum(s.latency_ms for s in self.scenarios) / self.total if self.total else 0.0

    @property
    def total_tokens(self) -> int:
        return sum(s.estimated_tokens for s in self.scenarios)

    def to_dict(self) -> dict[str, Any]:
        return {
            "workflow": self.workflow,
            "model": self.model,
            "timestamp": self.timestamp,
            "summary": {
                "total": self.total,
                "passed": self.passed,
                "pass_rate": round(self.pass_rate, 4),
                "mean_score": round(self.mean_score, 4),
                "mean_latency_ms": round(self.mean_latency_ms, 1),
                "total_tokens": self.total_tokens,
            },
            "scenarios": [
                {
                    "id": s.scenario_id,
                    "tags": s.tags,
                    "description": s.description,
                    "passed": s.passed,
                    "score": round(s.score, 4),
                    "latency_ms": round(s.latency_ms, 1),
                    "estimated_tokens": s.estimated_tokens,
                    "failure_reason": s.failure_reason,
                    "assertions": s.assertions,
                }
                for s in self.scenarios
            ],
        }

    def save(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(self.to_dict(), indent=2))


@dataclass
class BenchmarkSuiteResult:
    """Result across all workflows in a full suite run."""
    model: str
    timestamp: str
    workflows: list[WorkflowBenchmarkResult] = field(default_factory=list)

    @property
    def total_scenarios(self) -> int:
        return sum(w.total for w in self.workflows)

    @property
    def total_passed(self) -> int:
        return sum(w.passed for w in self.workflows)

    @property
    def overall_pass_rate(self) -> float:
        return self.total_passed / self.total_scenarios if self.total_scenarios else 0.0

    @property
    def total_tokens(self) -> int:
        return sum(w.total_tokens for w in self.workflows)

    def to_dict(self) -> dict[str, Any]:
        return {
            "model": self.model,
            "timestamp": self.timestamp,
            "summary": {
                "total_scenarios": self.total_scenarios,
                "total_passed": self.total_passed,
                "overall_pass_rate": round(self.overall_pass_rate, 4),
                "total_tokens": self.total_tokens,
            },
            "workflows": [w.to_dict() for w in self.workflows],
        }

    def save(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(self.to_dict(), indent=2))


class BenchmarkRunner:
    """Replays benchmark fixtures through a provided LLM callable.

    Parameters
    ----------
    llm_fn:
        Callable that takes (prompt: str, context: str) and returns
        the model's answer as a plain string.  In CI this is a fast fake;
        in staging it wraps a real API client.
    model_name:
        Human-readable label recorded in results (default "mock").
    """

    def __init__(self, llm_fn: LLMCallable, model_name: str = "mock") -> None:
        self._llm_fn = llm_fn
        self._model_name = model_name

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def run_workflow(self, workflow: str) -> WorkflowBenchmarkResult:
        """Run all scenarios in one workflow. Returns a WorkflowBenchmarkResult."""
        if workflow not in WORKFLOWS:
            raise ValueError(f"Unknown workflow {workflow!r}. Choose from {WORKFLOWS}.")

        fixture_path = FIXTURES_DIR / f"{workflow}.json"
        if not fixture_path.exists():
            raise FileNotFoundError(f"Fixture file not found: {fixture_path}")

        data = json.loads(fixture_path.read_text())
        timestamp = _utc_now()
        result = WorkflowBenchmarkResult(
            workflow=workflow,
            model=self._model_name,
            timestamp=timestamp,
        )

        for scenario in data.get("scenarios", []):
            result.scenarios.append(self._run_scenario(scenario, workflow))

        return result

    def run_all(self) -> BenchmarkSuiteResult:
        """Run every workflow fixture. Returns an aggregate BenchmarkSuiteResult."""
        timestamp = _utc_now()
        suite = BenchmarkSuiteResult(model=self._model_name, timestamp=timestamp)
        for workflow in WORKFLOWS:
            suite.workflows.append(self.run_workflow(workflow))
        return suite

    # ------------------------------------------------------------------ #
    # Internal
    # ------------------------------------------------------------------ #

    def _run_scenario(self, scenario: dict[str, Any], workflow: str) -> ScenarioResult:
        scenario_id: str = scenario["id"]
        tags: list[str] = scenario.get("tags", [])
        description: str = scenario.get("description", "")
        inputs: dict[str, Any] = scenario.get("inputs", {})
        expected: dict[str, Any] = scenario.get("expected", {})

        prompt = inputs.get("query", "")
        context = _build_context(inputs)

        t0 = time.perf_counter()
        try:
            answer = self._llm_fn(prompt, context)
        except Exception as exc:
            answer = f"[ERROR] {exc}"
        latency_ms = (time.perf_counter() - t0) * 1000

        estimated_tokens = _estimate_tokens(prompt + context + answer)

        assertions, score, failure_reason = _evaluate(answer, expected)
        threshold = expected.get("quality_threshold", 0.0)
        passed = score >= threshold and not failure_reason.startswith("POLICY")

        return ScenarioResult(
            scenario_id=scenario_id,
            workflow=workflow,
            tags=tags,
            description=description,
            passed=passed,
            score=score,
            latency_ms=latency_ms,
            estimated_tokens=estimated_tokens,
            failure_reason=failure_reason,
            answer=answer,
            assertions=assertions,
        )


# ------------------------------------------------------------------ #
# Helpers
# ------------------------------------------------------------------ #

def _build_context(inputs: dict[str, Any]) -> str:
    """Concatenate context_documents into a single context string."""
    docs = inputs.get("context_documents", [])
    if not docs:
        return ""
    parts = [f"Document {i + 1}:\n{doc}" for i, doc in enumerate(docs)]
    return "\n\n".join(parts)


def _evaluate(
    answer: str,
    expected: dict[str, Any],
) -> tuple[dict[str, bool], float, str]:
    """Check answer against expected spec.

    Returns (assertions_dict, score_0_to_1, failure_reason).
    """
    answer_lower = answer.lower()
    assertions: dict[str, bool] = {}
    failure_parts: list[str] = []

    must_refuse: bool = expected.get("must_refuse", False)
    must_not_fabricate: bool = expected.get("must_not_fabricate", False)

    # --- contains checks ---
    for phrase in expected.get("contains", []):
        key = f"contains:{phrase}"
        ok = phrase.lower() in answer_lower
        assertions[key] = ok
        if not ok:
            failure_parts.append(f"missing '{phrase}'")

    # --- not_contains checks ---
    for phrase in expected.get("not_contains", []):
        key = f"not_contains:{phrase}"
        ok = phrase.lower() not in answer_lower
        assertions[key] = ok
        if not ok:
            if must_refuse:
                failure_parts.append(f"POLICY VIOLATION: produced forbidden content '{phrase}'")
            elif must_not_fabricate:
                failure_parts.append(f"POLICY VIOLATION: fabricated content '{phrase}'")
            else:
                failure_parts.append(f"contains forbidden phrase '{phrase}'")

    # --- policy short-circuits: any policy violation → score = 0 ---
    any_policy_violation = any("POLICY" in f for f in failure_parts)
    if any_policy_violation:
        return assertions, 0.0, "; ".join(failure_parts)

    # --- score = fraction of assertions passed ---
    total = len(assertions)
    passed_count = sum(1 for v in assertions.values() if v)
    score = passed_count / total if total else 1.0  # no assertions → full score

    failure_reason = "; ".join(failure_parts) if failure_parts else ""
    return assertions, score, failure_reason


def _estimate_tokens(text: str) -> int:
    """Rough token estimate: ~4 characters per token (GPT/Claude approximation)."""
    return max(1, len(text) // 4)


def _utc_now() -> str:
    from datetime import datetime
    return datetime.now(UTC).isoformat()


# ------------------------------------------------------------------ #
# CLI entry point
# ------------------------------------------------------------------ #

def _main() -> None:
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Run Panacea workflow benchmarks")
    parser.add_argument("--workflow", choices=WORKFLOWS + ["all"], default="all")
    parser.add_argument("--model", default="claude-sonnet-4-6")
    parser.add_argument("--out", default=None, help="Write JSON report to this path")
    parser.add_argument("--provider", choices=["anthropic", "openai", "mock"], default="mock")
    args = parser.parse_args()

    llm_fn = _build_real_llm(args.provider, args.model)
    runner = BenchmarkRunner(llm_fn=llm_fn, model_name=args.model)

    if args.workflow == "all":
        result = runner.run_all()
        report_dict = result.to_dict()
        if args.out:
            result.save(args.out)
    else:
        wf_result = runner.run_workflow(args.workflow)
        report_dict = wf_result.to_dict()
        if args.out:
            wf_result.save(args.out)

    # Always print to stdout
    import json as _json
    print(_json.dumps(report_dict, indent=2))

    # Exit non-zero on any failure
    if args.workflow == "all":
        total = report_dict["summary"]["total_scenarios"]
        passed = report_dict["summary"]["total_passed"]
    else:
        total = report_dict["summary"]["total"]
        passed = report_dict["summary"]["passed"]
    sys.exit(0 if passed == total else 1)


def _build_real_llm(provider: str, model: str) -> LLMCallable:
    """Build a real LLM callable for staging runs. Falls back to mock."""
    if provider == "mock":
        return lambda prompt, context: f"[MOCK] prompt={prompt[:60]}"

    if provider == "anthropic":
        import os
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            raise OSError("ANTHROPIC_API_KEY not set")
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)

        def anthropic_llm(prompt: str, context: str) -> str:
            content = f"{context}\n\n{prompt}".strip() if context else prompt
            msg = client.messages.create(
                model=model,
                max_tokens=1024,
                messages=[{"role": "user", "content": content}],
            )
            block = msg.content[0] if msg.content else None
            return block.text if block and hasattr(block, "text") else ""

        return anthropic_llm

    if provider == "openai":
        import os
        api_key = os.environ.get("OPENAI_API_KEY", "")
        if not api_key:
            raise OSError("OPENAI_API_KEY not set")
        import openai
        client = openai.OpenAI(api_key=api_key)

        def openai_llm(prompt: str, context: str) -> str:
            content = f"{context}\n\n{prompt}".strip() if context else prompt
            resp = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": content}],
                max_tokens=1024,
            )
            return resp.choices[0].message.content or ""

        return openai_llm

    raise ValueError(f"Unknown provider: {provider}")


if __name__ == "__main__":
    _main()
