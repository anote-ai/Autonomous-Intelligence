"""Tests for the browser/computer-use action safety policy (issue #139).

Loaded by file path the same way ``test_config.py`` loads
``agents/config.py`` — ``agents/browser_policy.py`` only imports the
standard library, so it can be unit tested without pulling in the heavy
optional deps (langchain, anthropic, etc.) required by ``agents/__init__``.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

import pytest


def _load_browser_policy() -> Any:
    path = Path(__file__).resolve().parents[1] / "agents" / "browser_policy.py"
    spec = importlib.util.spec_from_file_location("_real_browser_policy", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    # dataclass() needs the module registered in sys.modules to resolve
    # forward-referenced type annotations.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


bp = _load_browser_policy()


# ---------------------------------------------------------------------------
# classify_action
# ---------------------------------------------------------------------------


def test_classify_known_actions() -> None:
    assert bp.classify_action("navigate") == bp.ActionSafetyLevel.READ_ONLY
    assert bp.classify_action("screenshot") == bp.ActionSafetyLevel.READ_ONLY
    assert bp.classify_action("fill_field") == bp.ActionSafetyLevel.FORM_FILL
    assert bp.classify_action("click") == bp.ActionSafetyLevel.FORM_FILL
    assert bp.classify_action("submit_form") == bp.ActionSafetyLevel.SUBMIT
    assert bp.classify_action("send_application") == bp.ActionSafetyLevel.SUBMIT
    assert bp.classify_action("delete_account") == bp.ActionSafetyLevel.DESTRUCTIVE
    assert bp.classify_action("make_payment") == bp.ActionSafetyLevel.DESTRUCTIVE


def test_classify_unknown_action_fails_closed() -> None:
    assert bp.classify_action("totally_unknown_action") == bp.ActionSafetyLevel.DESTRUCTIVE


def test_register_action_type_overrides_mapping() -> None:
    bp.register_action_type("custom_read_action", bp.ActionSafetyLevel.READ_ONLY)
    assert bp.classify_action("custom_read_action") == bp.ActionSafetyLevel.READ_ONLY


def test_safety_level_rank_ordering() -> None:
    assert bp.ActionSafetyLevel.READ_ONLY.rank < bp.ActionSafetyLevel.FORM_FILL.rank
    assert bp.ActionSafetyLevel.FORM_FILL.rank < bp.ActionSafetyLevel.SUBMIT.rank
    assert bp.ActionSafetyLevel.SUBMIT.rank < bp.ActionSafetyLevel.DESTRUCTIVE.rank


# ---------------------------------------------------------------------------
# BrowserActionPolicy
# ---------------------------------------------------------------------------


def test_read_only_and_form_fill_always_allowed() -> None:
    policy = bp.BrowserActionPolicy()  # no submit/destructive allowed
    assert policy.check("navigate").allowed is True
    assert policy.check("fill_field").allowed is True


def test_submit_denied_by_default() -> None:
    policy = bp.BrowserActionPolicy()
    decision = policy.check("submit_form")
    assert decision.allowed is False
    assert "disabled" in decision.reason


def test_submit_allowed_when_enabled() -> None:
    policy = bp.BrowserActionPolicy(allow_submit=True)
    decision = policy.check("submit_form")
    assert decision.allowed is True


def test_destructive_denied_by_default_even_if_submit_allowed() -> None:
    policy = bp.BrowserActionPolicy(allow_submit=True)
    decision = policy.check("delete_account")
    assert decision.allowed is False


def test_destructive_allowed_when_enabled() -> None:
    policy = bp.BrowserActionPolicy(allow_destructive=True)
    decision = policy.check("delete_account")
    assert decision.allowed is True


def test_approval_callback_can_reject_otherwise_allowed_action() -> None:
    policy = bp.BrowserActionPolicy(allow_submit=True, approval_callback=lambda *_: False)
    decision = policy.check("submit_form")
    assert decision.allowed is False
    assert "approval callback" in decision.reason


def test_approval_callback_can_approve_destructive_action() -> None:
    policy = bp.BrowserActionPolicy(allow_destructive=True, approval_callback=lambda *_: True)
    decision = policy.check("delete_account")
    assert decision.allowed is True


def test_enforce_raises_policy_violation_when_denied() -> None:
    policy = bp.BrowserActionPolicy()
    with pytest.raises(bp.PolicyViolation):
        policy.enforce("submit_form")


def test_enforce_returns_decision_when_allowed() -> None:
    policy = bp.BrowserActionPolicy()
    decision = policy.enforce("navigate")
    assert decision.allowed is True


def test_audit_log_records_every_decision() -> None:
    policy = bp.BrowserActionPolicy(allow_submit=True)
    policy.check("navigate")
    policy.check("submit_form")
    policy.check("delete_account")
    log = policy.audit_log()
    assert len(log) == 3
    assert [entry["allowed"] for entry in log] == [True, True, False]


# ---------------------------------------------------------------------------
# BrowserSessionTrace
# ---------------------------------------------------------------------------


def test_session_trace_is_scoped_to_workspace_and_run() -> None:
    trace = bp.BrowserSessionTrace(workspace_id="ws-1", project_id="proj-9", run_id="run-42")
    assert trace.workspace_id == "ws-1"
    assert trace.project_id == "proj-9"
    assert trace.run_id == "run-42"
    assert trace.session_id  # auto-generated, unique per session


def test_two_sessions_have_distinct_session_ids() -> None:
    t1 = bp.BrowserSessionTrace(workspace_id="ws-1")
    t2 = bp.BrowserSessionTrace(workspace_id="ws-1")
    assert t1.session_id != t2.session_id


def test_start_step_records_pending_step_on_allowed_action() -> None:
    trace = bp.BrowserSessionTrace(workspace_id="ws-1")
    step = trace.start_step("navigate", {"url": "https://example.com"})
    assert step.status == "pending"
    assert step.level == bp.ActionSafetyLevel.READ_ONLY
    assert len(trace.steps) == 1


def test_start_step_raises_and_records_denied_step_for_gated_action() -> None:
    trace = bp.BrowserSessionTrace(workspace_id="ws-1")
    with pytest.raises(bp.PolicyViolation):
        trace.start_step("submit_form", {"form_id": "apply"})
    assert len(trace.steps) == 1
    assert trace.steps[0].status == "denied"


def test_complete_step_and_fail_step() -> None:
    trace = bp.BrowserSessionTrace(workspace_id="ws-1")
    step = trace.start_step("navigate")
    trace.complete_step(step, result={"title": "Example"})
    assert step.status == "success"
    assert step.result == {"title": "Example"}
    assert step.ended_at is not None

    step2 = trace.start_step("fill_field")
    trace.fail_step(step2, error="selector not found")
    assert step2.status == "failure"
    assert step2.error == "selector not found"


def test_add_artifact_attaches_to_step() -> None:
    trace = bp.BrowserSessionTrace(workspace_id="ws-1")
    step = trace.start_step("screenshot")
    trace.add_artifact(step, "screenshot", "file:///tmp/shot.png", page="apply-form")
    assert step.artifacts == [{"type": "screenshot", "uri": "file:///tmp/shot.png", "page": "apply-form"}]


def test_failed_steps_and_replay_plan() -> None:
    policy = bp.BrowserActionPolicy()  # submit disabled -> will be denied
    trace = bp.BrowserSessionTrace(workspace_id="ws-1", policy=policy)

    step1 = trace.start_step("navigate")
    trace.complete_step(step1)

    step2 = trace.start_step("fill_field", {"field": "email"})
    trace.fail_step(step2, error="timeout")

    with pytest.raises(bp.PolicyViolation):
        trace.start_step("submit_form", {"form_id": "apply"})

    failed = trace.failed_steps()
    assert len(failed) == 2
    assert {s.status for s in failed} == {"failure", "denied"}

    plan = trace.replay_plan()
    assert len(plan) == 2
    assert plan[0]["action_type"] == "fill_field"
    assert plan[1]["action_type"] == "submit_form"


def test_to_dict_is_json_serializable_shape() -> None:
    trace = bp.BrowserSessionTrace(workspace_id="ws-1", project_id="proj-1")
    step = trace.start_step("navigate")
    trace.complete_step(step, result={"ok": True})

    data = trace.to_dict()
    assert data["workspace_id"] == "ws-1"
    assert data["project_id"] == "proj-1"
    assert len(data["steps"]) == 1
    assert data["steps"][0]["status"] == "success"
    assert isinstance(data["audit_log"], list)
