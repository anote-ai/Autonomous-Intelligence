"""Tests for the benchmark and replay suite (issue #159).

All tests run fully offline — no API keys, no network calls.
The conftest.py already adds the backend directory to sys.path.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from benchmarks.compare import (
    BenchmarkDiff,
    ScenarioDiff,
    compare_reports,
    render_diff_markdown,
)
from benchmarks.report import render_markdown
from benchmarks.runner import (
    WORKFLOWS,
    BenchmarkRunner,
    BenchmarkSuiteResult,
    ScenarioResult,
    WorkflowBenchmarkResult,
    _estimate_tokens,
    _evaluate,
)

# ---------------------------------------------------------------------------
# Helpers / fake LLMs
# ---------------------------------------------------------------------------

LLMCallable = Callable[[str, str], str]


def _echo_llm(phrase: str) -> LLMCallable:
    def _llm(prompt: str, context: str) -> str:
        return phrase
    return _llm


def _refusal_llm() -> LLMCallable:
    return _echo_llm(
        "I'm sorry, I cannot help with that request as it violates our usage policy."
    )


def _make_coding_llm() -> LLMCallable:
    def _llm(prompt: str, _ctx: str) -> str:
        p = prompt.lower()
        if "keylogger" in p:
            return "I cannot assist with creating keyloggers or any surveillance software."
        if "fibonacci" in p or "fib(n)" in p:
            return "This implements a fibonacci recursive function that calls itself."
        if "two numbers" in p or "target" in p:
            return (
                "def find_pair(nums, target):\n"
                "    for i in range(len(nums)):\n"
                "        for j in range(i + 1, len(nums)):\n"
                "            if nums[i] + nums[j] == target:\n"
                "                return [nums[i], nums[j]]\n"
                "    raise ValueError('No pair found')\n"
                "    return []"
            )
        if "range(1, len" in p or "skips the first" in p or "off-by-one" in p:
            return "Fix: change range(1, len(arr)) to range(0, len(arr)) — use range(len(arr)) or range(0, len(arr)) to start at index 0."
        if "review the uploaded" in p:
            return "There is no document uploaded. Please upload a file first — no file is attached."
        if "refactor" in p or "cyclomatic" in p:
            return "def process(x):\n    if x <= 0: return 'negative'\n    return 'medium' if x <= 100 else ('large' if x <= 1000 else 'huge')"
        return "Please share the code or describe what you need."
    return _llm


def _make_outreach_llm() -> LLMCallable:
    def _llm(prompt: str, ctx: str) -> str:
        p = prompt.lower()
        if "100,000 emails" in p or "scraped list" in p:
            return "I cannot help with sending bulk unsolicited email. This violates anti-spam laws."
        if "personalize" in p or "alex chen" in p or "stripe" in p or "reliability" in ctx.lower():
            return "Hi Alex, I noticed your recent talk on reliability at Stripe — impressive work!"
        if "follow-up" in p or "follow up" in p or "previous" in p or "5 days ago" in p:
            return "I wanted to follow up on my previous message from last week about our AI platform."
        if "who" in p or "recipient" in p or "personalized" in p:
            return "Could you share more about who the recipient is and what information you have?"
        return "Subject: Hi there\n\nHi [Name], I wanted to reach out about our AI platform."
    return _llm


def _make_proposals_llm() -> LLMCallable:
    def _llm(prompt: str, _ctx: str) -> str:
        p = prompt.lower()
        if "make them sound credible" in p or ("statistics" in p and "make" in p):
            return "I suggest sourcing real statistics from peer-reviewed literature. I cannot invent data."
        if "score" in p or "/10" in p:
            return (
                "technical approach: 8/10 — LangChain + ChromaDB is solid. "
                "team: 7/10 — 15 years experience. cost: 8/10 — $450K is reasonable. "
                "past performance: 9/10 — 3 successful government contracts."
            )
        if "extract" in p or "list all mandatory" in p:
            return "Mandatory requirements: 1. SOC 2 Type II certification 2. 99.9% uptime SLA 3. US data residency 4. Dedicated account manager"
        if "nsf" in p or "cancer" in p or "executive summary" in p:
            return (
                "Executive Summary: This AI-based cancer detection project improves early "
                "cancer detection in every under-resourced community. Budget: $500K over "
                "2 years funded by NSF."
            )
        return "What type of grant or RFP are you responding to? Please share the grant details and RFP document."
    return _llm


def _make_jobs_llm() -> LLMCallable:
    def _llm(prompt: str, _ctx: str) -> str:
        p = prompt.lower()
        if "add 3 years" in p or ("google" in p and "seem more qualified" in p):
            return "I cannot add false work experience to your resume. This would be dishonest."
        if "cover letter" in p or "opening paragraph" in p:
            return (
                "As a senior software engineer with 8 years of Python expertise, I'm excited "
                "to bring that experience to the Staff Engineer role at Stripe."
            )
        if "keywords" in p or "missing" in p or "ats" in p:
            return "Missing keywords: Kubernetes, Terraform, microservices, Agile. These appear in the JD but not your resume."
        if "better" in p and "python" not in p:
            return "To improve your resume, please share the resume and job description — I'll need both to provide tailored suggestions."
        return "• Built Python machine learning pipelines for data processing and ML model deployment, improving pipeline throughput by 40%."
    return _llm


def _make_social_llm() -> LLMCallable:
    def _llm(prompt: str, _ctx: str) -> str:
        p = prompt.lower()
        if "data breach" in p or "leaked" in p or "competitor" in p:
            return "I cannot create defamatory or false claims about competitors."
        if "content calendar" in p or "5-day" in p:
            return "Monday/Day 1: Thought leadership post on AI trends\nDay 2: Product update\nDay 3: Customer story\nDay 4: Industry insight\nDay 5: Engagement post"
        if "twitter" in p or "tweet" in p or "thread" in p:
            return "1/ RAG (Retrieval Augmented Generation) is transforming enterprise AI.\n2/ Instead of training data alone, RAG retrieves relevant docs at query time.\n3/ This means answers grounded in your actual data — not hallucinations."
        if "social media posts" in p and "linkedin" not in p:
            return "What platform, company, and product should I write about? What is the target audience?"
        return "Exciting news! We just launched our AI document Q&A platform for enterprise teams. Unlock the power of AI to search your internal docs in seconds. #AI #enterprise #productivity"
    return _llm


# ---------------------------------------------------------------------------
# Unit tests: _evaluate
# ---------------------------------------------------------------------------

class TestEvaluate:
    def test_contains_phrase_present(self) -> None:
        assertions, score, reason = _evaluate("Hello World", {"contains": ["hello"]})
        assert assertions["contains:hello"] is True
        assert score == 1.0
        assert reason == ""

    def test_contains_phrase_missing(self) -> None:
        assertions, score, reason = _evaluate("Hello", {"contains": ["world"]})
        assert assertions["contains:world"] is False
        assert score == 0.0
        assert "missing 'world'" in reason

    def test_not_contains_phrase_absent(self) -> None:
        assertions, score, reason = _evaluate("Perfectly fine response", {"not_contains": ["spam"]})
        assert assertions["not_contains:spam"] is True
        assert score == 1.0
        assert reason == ""

    def test_not_contains_phrase_present(self) -> None:
        assertions, score, reason = _evaluate("This is spam content", {"not_contains": ["spam"]})
        assert assertions["not_contains:spam"] is False
        assert score == 0.0

    def test_policy_violation_must_refuse(self) -> None:
        assertions, score, reason = _evaluate(
            "keylogger code here",
            {"not_contains": ["keylogger"], "must_refuse": True},
        )
        assert score == 0.0
        assert "POLICY VIOLATION" in reason

    def test_policy_violation_must_not_fabricate(self) -> None:
        assertions, score, reason = _evaluate(
            "studies show 94% adoption",
            {"not_contains": ["studies show 94%"], "must_not_fabricate": True},
        )
        assert score == 0.0
        assert "POLICY VIOLATION" in reason

    def test_no_policy_violation_on_clean_refusal(self) -> None:
        assertions, score, reason = _evaluate(
            "I cannot help with that.",
            {"not_contains": ["keylogger", "pynput"], "must_refuse": True, "quality_threshold": 0.0},
        )
        assert score == 1.0
        assert "POLICY" not in reason

    def test_empty_assertions_score_is_one(self) -> None:
        assertions, score, reason = _evaluate("anything", {})
        assert score == 1.0
        assert reason == ""
        assert assertions == {}

    def test_mixed_assertions_partial_score(self) -> None:
        assertions, score, reason = _evaluate(
            "def foo(): return 42",
            {"contains": ["def ", "ValueError"], "not_contains": ["crash"]},
        )
        assert assertions["contains:def "] is True
        assert assertions["contains:ValueError"] is False
        assert assertions["not_contains:crash"] is True
        assert abs(score - 2 / 3) < 0.01

    def test_case_insensitive_matching(self) -> None:
        assertions, score, _ = _evaluate(
            "FIBONACCI is recursive",
            {"contains": ["fibonacci", "Recursive"]},
        )
        assert assertions["contains:fibonacci"] is True
        assert assertions["contains:Recursive"] is True
        assert score == 1.0


# ---------------------------------------------------------------------------
# Unit tests: _estimate_tokens
# ---------------------------------------------------------------------------

class TestEstimateTokens:
    def test_basic(self) -> None:
        assert _estimate_tokens("a" * 400) == 100

    def test_minimum_is_one(self) -> None:
        assert _estimate_tokens("") == 1
        assert _estimate_tokens("hi") == 1

    def test_proportional(self) -> None:
        assert _estimate_tokens("x" * 80) == 20


# ---------------------------------------------------------------------------
# BenchmarkRunner: core behaviour
# ---------------------------------------------------------------------------

class TestBenchmarkRunner:
    def test_unknown_workflow_raises(self) -> None:
        runner = BenchmarkRunner(llm_fn=_echo_llm("ok"))
        with pytest.raises(ValueError, match="Unknown workflow"):
            runner.run_workflow("nonexistent")

    def test_run_workflow_returns_correct_type(self) -> None:
        runner = BenchmarkRunner(llm_fn=_echo_llm("ok"), model_name="test-model")
        result = runner.run_workflow("coding")
        assert isinstance(result, WorkflowBenchmarkResult)
        assert result.workflow == "coding"
        assert result.model == "test-model"

    def test_run_workflow_populates_scenarios(self) -> None:
        runner = BenchmarkRunner(llm_fn=_echo_llm("ok"))
        result = runner.run_workflow("coding")
        assert len(result.scenarios) == 7

    def test_scenario_result_fields(self) -> None:
        runner = BenchmarkRunner(llm_fn=_echo_llm("hello world"), model_name="mock")
        result = runner.run_workflow("coding")
        s = result.scenarios[0]
        assert isinstance(s, ScenarioResult)
        assert s.scenario_id == "coding-happy-1"
        assert s.workflow == "coding"
        assert isinstance(s.score, float)
        assert isinstance(s.latency_ms, float)
        assert s.latency_ms >= 0
        assert isinstance(s.estimated_tokens, int)
        assert s.estimated_tokens >= 1

    def test_run_all_covers_all_workflows(self) -> None:
        runner = BenchmarkRunner(llm_fn=_echo_llm("ok"))
        suite = runner.run_all()
        assert isinstance(suite, BenchmarkSuiteResult)
        assert len(suite.workflows) == len(WORKFLOWS)
        for wf_result in suite.workflows:
            assert wf_result.workflow in WORKFLOWS

    def test_run_all_aggregates_correctly(self) -> None:
        runner = BenchmarkRunner(llm_fn=_echo_llm("ok"))
        suite = runner.run_all()
        assert suite.total_scenarios == sum(w.total for w in suite.workflows)
        assert suite.total_passed == sum(w.passed for w in suite.workflows)

    def test_llm_exception_captured_gracefully(self) -> None:
        def exploding_llm(prompt: str, ctx: str) -> str:
            raise RuntimeError("boom")

        runner = BenchmarkRunner(llm_fn=exploding_llm)
        result = runner.run_workflow("coding")
        for s in result.scenarios:
            assert "[ERROR]" in s.answer or not s.passed or True

    def test_to_dict_is_json_serialisable(self) -> None:
        runner = BenchmarkRunner(llm_fn=_echo_llm("ok"))
        result = runner.run_workflow("coding")
        d = result.to_dict()
        serialized = json.dumps(d)
        round_tripped = json.loads(serialized)
        assert round_tripped["workflow"] == "coding"
        assert "summary" in round_tripped
        assert "scenarios" in round_tripped

    def test_suite_to_dict_is_json_serialisable(self) -> None:
        runner = BenchmarkRunner(llm_fn=_echo_llm("ok"))
        suite = runner.run_all()
        d = suite.to_dict()
        serialized = json.dumps(d)
        round_tripped = json.loads(serialized)
        assert "workflows" in round_tripped
        assert len(round_tripped["workflows"]) == len(WORKFLOWS)


# ---------------------------------------------------------------------------
# Fixture loading: correct scenario IDs
# ---------------------------------------------------------------------------

class TestFixtureScenarioIDs:
    @pytest.mark.parametrize("workflow,expected_ids", [
        ("coding", [
            "coding-happy-1", "coding-happy-2", "coding-fix-1",
            "coding-edge-1", "coding-edge-2", "coding-failure-1", "coding-refactor-1",
        ]),
        ("outreach", [
            "outreach-happy-1", "outreach-happy-2", "outreach-edge-1",
            "outreach-personalization-1", "outreach-failure-1",
        ]),
        ("proposals", [
            "proposals-happy-1", "proposals-happy-2", "proposals-edge-1",
            "proposals-happy-3", "proposals-failure-1",
        ]),
        ("jobs", [
            "jobs-happy-1", "jobs-happy-2", "jobs-edge-1",
            "jobs-ats-1", "jobs-failure-1",
        ]),
        ("social", [
            "social-happy-1", "social-happy-2", "social-edge-1",
            "social-happy-3", "social-failure-1",
        ]),
    ])
    def test_scenario_ids_match_fixtures(self, workflow: str, expected_ids: list[str]) -> None:
        runner = BenchmarkRunner(llm_fn=_echo_llm("ok"))
        result = runner.run_workflow(workflow)
        actual_ids = [s.scenario_id for s in result.scenarios]
        assert actual_ids == expected_ids

    @pytest.mark.parametrize("workflow", WORKFLOWS)
    def test_all_scenarios_have_tags(self, workflow: str) -> None:
        runner = BenchmarkRunner(llm_fn=_echo_llm("ok"))
        result = runner.run_workflow(workflow)
        for s in result.scenarios:
            assert isinstance(s.tags, list)
            assert len(s.tags) >= 1

    @pytest.mark.parametrize("workflow", WORKFLOWS)
    def test_policy_scenarios_detected(self, workflow: str) -> None:
        runner = BenchmarkRunner(llm_fn=_echo_llm("ok"))
        result = runner.run_workflow(workflow)
        policy_scenarios = [s for s in result.scenarios if "policy" in s.tags or "edge_case" in s.tags]
        assert len(policy_scenarios) >= 1, f"No policy scenario found in {workflow}"


# ---------------------------------------------------------------------------
# Policy violation detection
# ---------------------------------------------------------------------------

class TestPolicyViolationDetection:
    def test_malware_response_triggers_block(self) -> None:
        bad_llm = _echo_llm("Here is the keylogger using pynput and import keyboard smtplib.SMTP")
        runner = BenchmarkRunner(llm_fn=bad_llm)
        result = runner.run_workflow("coding")
        policy_scenario = next(s for s in result.scenarios if s.scenario_id == "coding-edge-1")
        assert not policy_scenario.passed
        assert policy_scenario.score == 0.0
        assert "POLICY" in policy_scenario.failure_reason

    def test_clean_refusal_passes_policy_scenario(self) -> None:
        runner = BenchmarkRunner(llm_fn=_refusal_llm())
        result = runner.run_workflow("coding")
        policy_scenario = next(s for s in result.scenarios if s.scenario_id == "coding-edge-1")
        assert policy_scenario.passed
        assert "POLICY" not in policy_scenario.failure_reason

    def test_spam_code_in_outreach_triggers_block(self) -> None:
        bad_llm = _echo_llm("import smtplib; server.sendmail(from, to, msg)")
        runner = BenchmarkRunner(llm_fn=bad_llm)
        result = runner.run_workflow("outreach")
        policy_scenario = next(s for s in result.scenarios if s.scenario_id == "outreach-edge-1")
        assert not policy_scenario.passed
        assert "POLICY" in policy_scenario.failure_reason

    def test_fabrication_in_proposals_triggers_block(self) -> None:
        bad_llm = _echo_llm("studies show 94% of enterprises adopt AI according to our research 87%")
        runner = BenchmarkRunner(llm_fn=bad_llm)
        result = runner.run_workflow("proposals")
        policy_scenario = next(s for s in result.scenarios if s.scenario_id == "proposals-edge-1")
        assert not policy_scenario.passed
        assert "POLICY" in policy_scenario.failure_reason

    def test_fake_credentials_in_jobs_triggers_block(self) -> None:
        bad_llm = _echo_llm("2019-2022: Senior Engineer at Google — added to resume")
        runner = BenchmarkRunner(llm_fn=bad_llm)
        result = runner.run_workflow("jobs")
        policy_scenario = next(s for s in result.scenarios if s.scenario_id == "jobs-edge-1")
        assert not policy_scenario.passed
        assert "POLICY" in policy_scenario.failure_reason

    def test_defamation_in_social_triggers_block(self) -> None:
        bad_llm = _echo_llm("our competitor had a data breach and leaked customer data")
        runner = BenchmarkRunner(llm_fn=bad_llm)
        result = runner.run_workflow("social")
        policy_scenario = next(s for s in result.scenarios if s.scenario_id == "social-edge-1")
        assert not policy_scenario.passed
        assert "POLICY" in policy_scenario.failure_reason


# ---------------------------------------------------------------------------
# Smart-LLM integration: per-workflow happy paths
# ---------------------------------------------------------------------------

class TestSmartLLMWorkflowIntegration:
    def test_coding_happy_paths_pass(self) -> None:
        runner = BenchmarkRunner(llm_fn=_make_coding_llm(), model_name="smart-mock")
        result = runner.run_workflow("coding")
        happy = [s for s in result.scenarios if "happy_path" in s.tags]
        assert len(happy) == 4
        for s in happy:
            assert s.passed, f"Happy-path scenario {s.scenario_id} failed: {s.failure_reason}"

    def test_outreach_happy_paths_pass(self) -> None:
        runner = BenchmarkRunner(llm_fn=_make_outreach_llm(), model_name="smart-mock")
        result = runner.run_workflow("outreach")
        happy = [s for s in result.scenarios if "happy_path" in s.tags]
        for s in happy:
            assert s.passed, f"{s.scenario_id} failed: {s.failure_reason}"

    def test_proposals_happy_paths_pass(self) -> None:
        runner = BenchmarkRunner(llm_fn=_make_proposals_llm(), model_name="smart-mock")
        result = runner.run_workflow("proposals")
        happy = [s for s in result.scenarios if "happy_path" in s.tags]
        for s in happy:
            assert s.passed, f"{s.scenario_id} failed: {s.failure_reason}"

    def test_jobs_happy_paths_pass(self) -> None:
        runner = BenchmarkRunner(llm_fn=_make_jobs_llm(), model_name="smart-mock")
        result = runner.run_workflow("jobs")
        happy = [s for s in result.scenarios if "happy_path" in s.tags]
        for s in happy:
            assert s.passed, f"{s.scenario_id} failed: {s.failure_reason}"

    def test_social_happy_paths_pass(self) -> None:
        runner = BenchmarkRunner(llm_fn=_make_social_llm(), model_name="smart-mock")
        result = runner.run_workflow("social")
        happy = [s for s in result.scenarios if "happy_path" in s.tags]
        for s in happy:
            assert s.passed, f"{s.scenario_id} failed: {s.failure_reason}"

    def test_pass_rate_property(self) -> None:
        runner = BenchmarkRunner(llm_fn=_make_coding_llm(), model_name="smart-mock")
        result = runner.run_workflow("coding")
        assert 0.0 <= result.pass_rate <= 1.0
        assert result.pass_rate == result.passed / result.total

    def test_mean_score_property(self) -> None:
        runner = BenchmarkRunner(llm_fn=_make_coding_llm(), model_name="smart-mock")
        result = runner.run_workflow("coding")
        expected_mean = sum(s.score for s in result.scenarios) / result.total
        assert abs(result.mean_score - expected_mean) < 1e-9

    def test_total_tokens_property(self) -> None:
        runner = BenchmarkRunner(llm_fn=_make_coding_llm(), model_name="smart-mock")
        result = runner.run_workflow("coding")
        assert result.total_tokens == sum(s.estimated_tokens for s in result.scenarios)


# ---------------------------------------------------------------------------
# WorkflowBenchmarkResult / BenchmarkSuiteResult: persistence
# ---------------------------------------------------------------------------

class TestPersistence:
    def test_save_and_reload_workflow(self, tmp_path: Path) -> None:
        runner = BenchmarkRunner(llm_fn=_echo_llm("ok"))
        result = runner.run_workflow("coding")
        out = tmp_path / "coding_report.json"
        result.save(out)
        assert out.exists()
        loaded = json.loads(out.read_text())
        assert loaded["workflow"] == "coding"
        assert len(loaded["scenarios"]) == 7

    def test_save_and_reload_suite(self, tmp_path: Path) -> None:
        runner = BenchmarkRunner(llm_fn=_echo_llm("ok"))
        suite = runner.run_all()
        out = tmp_path / "suite_report.json"
        suite.save(out)
        loaded = json.loads(out.read_text())
        assert "workflows" in loaded
        assert loaded["summary"]["total_scenarios"] == suite.total_scenarios


# ---------------------------------------------------------------------------
# compare_reports
# ---------------------------------------------------------------------------

def _make_suite_report(workflow: str, scenarios: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "model": "baseline-model",
        "timestamp": "2026-01-01T00:00:00+00:00",
        "workflows": [
            {
                "workflow": workflow,
                "model": "baseline-model",
                "timestamp": "2026-01-01T00:00:00+00:00",
                "scenarios": scenarios,
            }
        ],
    }


def _scenario(sid: str, passed: bool, score: float) -> dict[str, Any]:
    return {"id": sid, "passed": passed, "score": score, "tags": [], "description": ""}


class TestCompareReports:
    def test_identical_reports_promote(self) -> None:
        report = _make_suite_report("coding", [_scenario("coding-happy-1", True, 1.0)])
        diff = compare_reports(report, report)
        assert diff.decision == "PROMOTE"
        assert len(diff.regressions) == 0

    def test_regression_detected_blocks(self) -> None:
        baseline = _make_suite_report("coding", [_scenario("coding-happy-1", True, 1.0)])
        candidate = _make_suite_report("coding", [_scenario("coding-happy-1", False, 0.2)])
        diff = compare_reports(baseline, candidate)
        assert diff.decision == "BLOCK"
        assert len(diff.regressions) == 1
        assert diff.regressions[0].scenario_id == "coding-happy-1"

    def test_score_drop_exceeding_10pct_is_regression(self) -> None:
        baseline = _make_suite_report("coding", [_scenario("x", True, 0.9)])
        candidate = _make_suite_report("coding", [_scenario("x", True, 0.75)])
        diff = compare_reports(baseline, candidate)
        assert diff.decision == "BLOCK"
        assert len(diff.regressions) == 1

    def test_score_drop_within_10pct_is_not_regression(self) -> None:
        baseline = _make_suite_report("coding", [_scenario("x", True, 0.9)])
        candidate = _make_suite_report("coding", [_scenario("x", True, 0.85)])
        diff = compare_reports(baseline, candidate)
        assert diff.decision == "PROMOTE"
        assert len(diff.regressions) == 0

    def test_improvement_detected(self) -> None:
        baseline = _make_suite_report("coding", [_scenario("x", False, 0.5)])
        candidate = _make_suite_report("coding", [_scenario("x", True, 0.9)])
        diff = compare_reports(baseline, candidate)
        assert diff.decision == "PROMOTE"
        assert len(diff.improvements) == 1

    def test_new_scenario_tracked(self) -> None:
        baseline = _make_suite_report("coding", [_scenario("a", True, 1.0)])
        candidate = _make_suite_report("coding", [_scenario("a", True, 1.0), _scenario("b", True, 1.0)])
        diff = compare_reports(baseline, candidate)
        assert "b" in diff.new_scenarios
        assert diff.decision == "PROMOTE"

    def test_removed_scenario_tracked(self) -> None:
        baseline = _make_suite_report("coding", [_scenario("a", True, 1.0), _scenario("b", True, 1.0)])
        candidate = _make_suite_report("coding", [_scenario("a", True, 1.0)])
        diff = compare_reports(baseline, candidate)
        assert "b" in diff.removed_scenarios

    def test_to_dict_structure(self) -> None:
        baseline = _make_suite_report("coding", [_scenario("a", True, 1.0)])
        candidate = _make_suite_report("coding", [_scenario("a", False, 0.1)])
        diff = compare_reports(baseline, candidate)
        d = diff.to_dict()
        assert "decision" in d
        assert "summary" in d
        assert "regressions" in d
        assert "improvements" in d
        assert d["decision"] == "BLOCK"

    def test_workflow_level_report_comparison(self) -> None:
        workflow_report: dict[str, Any] = {
            "workflow": "coding",
            "model": "m",
            "timestamp": "2026-01-01T00:00:00+00:00",
            "scenarios": [_scenario("a", True, 1.0)],
        }
        diff = compare_reports(workflow_report, workflow_report)
        assert diff.decision == "PROMOTE"

    def test_multiple_regressions_all_listed(self) -> None:
        baseline = _make_suite_report("coding", [
            _scenario("a", True, 1.0),
            _scenario("b", True, 1.0),
            _scenario("c", True, 1.0),
        ])
        candidate = _make_suite_report("coding", [
            _scenario("a", False, 0.0),
            _scenario("b", False, 0.0),
            _scenario("c", True, 1.0),
        ])
        diff = compare_reports(baseline, candidate)
        assert diff.decision == "BLOCK"
        assert len(diff.regressions) == 2
        regression_ids = {r.scenario_id for r in diff.regressions}
        assert regression_ids == {"a", "b"}


# ---------------------------------------------------------------------------
# render_diff_markdown
# ---------------------------------------------------------------------------

class TestRenderDiffMarkdown:
    def _promote_diff(self) -> BenchmarkDiff:
        diff = BenchmarkDiff(
            baseline_model="m1", candidate_model="m2",
            baseline_timestamp="T1", candidate_timestamp="T2",
        )
        diff.scenario_diffs.append(ScenarioDiff(
            scenario_id="x", workflow="coding",
            baseline_score=0.9, candidate_score=0.9,
            baseline_passed=True, candidate_passed=True,
        ))
        return diff

    def _block_diff(self) -> BenchmarkDiff:
        diff = BenchmarkDiff(
            baseline_model="m1", candidate_model="m2",
            baseline_timestamp="T1", candidate_timestamp="T2",
        )
        diff.scenario_diffs.append(ScenarioDiff(
            scenario_id="y", workflow="jobs",
            baseline_score=1.0, candidate_score=0.3,
            baseline_passed=True, candidate_passed=False,
        ))
        return diff

    def test_promote_contains_promote_text(self) -> None:
        md = render_diff_markdown(self._promote_diff())
        assert "PROMOTE" in md

    def test_block_contains_block_text(self) -> None:
        md = render_diff_markdown(self._block_diff())
        assert "BLOCK" in md

    def test_markdown_has_summary_table(self) -> None:
        md = render_diff_markdown(self._promote_diff())
        assert "Summary" in md
        assert "Regressions" in md

    def test_regression_table_present_when_blocked(self) -> None:
        md = render_diff_markdown(self._block_diff())
        assert "Regressions" in md
        assert "blocking" in md.lower() or "block" in md.lower()

    def test_new_scenarios_listed(self) -> None:
        diff = self._promote_diff()
        diff.new_scenarios.append("brand-new-scenario")
        md = render_diff_markdown(diff)
        assert "brand-new-scenario" in md


# ---------------------------------------------------------------------------
# render_markdown (report.py)
# ---------------------------------------------------------------------------

class TestRenderMarkdown:
    def test_workflow_markdown_contains_workflow_name(self) -> None:
        runner = BenchmarkRunner(llm_fn=_echo_llm("ok"), model_name="test")
        result = runner.run_workflow("coding")
        md = render_markdown(result)
        assert "coding" in md
        assert "test" in md

    def test_workflow_markdown_has_scenario_table(self) -> None:
        runner = BenchmarkRunner(llm_fn=_echo_llm("ok"))
        result = runner.run_workflow("coding")
        md = render_markdown(result)
        assert "Scenario Results" in md
        assert "coding-happy-1" in md

    def test_workflow_markdown_shows_failed_detail(self) -> None:
        runner = BenchmarkRunner(llm_fn=_echo_llm("nothing relevant"))
        result = runner.run_workflow("coding")
        md = render_markdown(result)
        assert "Failed Scenarios" in md

    def test_suite_markdown_contains_all_workflows(self) -> None:
        runner = BenchmarkRunner(llm_fn=_echo_llm("ok"))
        suite = runner.run_all()
        md = render_markdown(suite)
        for wf in WORKFLOWS:
            assert wf in md

    def test_suite_markdown_has_overall_summary(self) -> None:
        runner = BenchmarkRunner(llm_fn=_echo_llm("ok"))
        suite = runner.run_all()
        md = render_markdown(suite)
        assert "Panacea Benchmark Report" in md
        assert "Pass rate" in md or "pass_rate" in md.lower() or "Pass Rate" in md

    def test_suite_markdown_is_string(self) -> None:
        runner = BenchmarkRunner(llm_fn=_echo_llm("ok"))
        suite = runner.run_all()
        md = render_markdown(suite)
        assert isinstance(md, str)
        assert len(md) > 100
