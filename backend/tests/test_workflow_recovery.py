"""Tests for the workflow/job failure-recovery engine (issue #135).

Covers the acceptance criteria from the issue:
  * A failed run can resume from a checkpoint rather than restarting.
  * Completed unaffected steps are not recomputed.
  * Users can retry a failed step with corrected input.
  * Recovery actions show up in run history / audit trail.
  * Downstream invalidation behaves correctly after an upstream failure.
"""
from __future__ import annotations

import pytest
from services.workflow_recovery import (
    InvalidRecoveryActionError,
    RecoveryAction,
    StepNotFoundError,
    StepStatus,
    WorkflowRun,
)


def _ok(value):
    def _executor(_inputs):
        return value
    return _executor


def _fail(message="boom"):
    def _executor(_inputs):
        raise RuntimeError(message)
    return _executor


def _build_linear_run() -> WorkflowRun:
    """ingest -> transform -> publish"""
    run = WorkflowRun(name="linear")
    run.add_step("ingest", "Ingest", inputs={"source": "s3://bucket/file"})
    run.add_step("transform", "Transform", depends_on=["ingest"], inputs={"mode": "default"})
    run.add_step("publish", "Publish", depends_on=["transform"], inputs={"target": "webhook"})
    return run


# ---------------------------------------------------------------------------
# Basic execution + checkpointing
# ---------------------------------------------------------------------------


def test_run_step_records_checkpoint_on_success():
    run = _build_linear_run()
    step = run.run_step("ingest", _ok("ingested-data"))
    assert step.status == StepStatus.SUCCEEDED
    assert step.output == "ingested-data"
    assert len(step.checkpoints) == 1
    assert step.checkpoints[0].status == StepStatus.SUCCEEDED


def test_run_step_records_checkpoint_on_failure():
    run = _build_linear_run()
    step = run.run_step("ingest", _fail("network error"))
    assert step.status == StepStatus.FAILED
    assert step.error == "network error"
    assert len(step.checkpoints) == 1
    assert step.checkpoints[0].status == StepStatus.FAILED


def test_step_with_unmet_dependency_is_skipped():
    run = _build_linear_run()
    # transform depends on ingest, which has not run yet.
    step = run.run_step("transform", _ok("should-not-run"))
    assert step.status == StepStatus.SKIPPED
    assert step.output is None


def test_unknown_step_raises():
    run = _build_linear_run()
    with pytest.raises(StepNotFoundError):
        run.run_step("does-not-exist", _ok("x"))


# ---------------------------------------------------------------------------
# Downstream invalidation
# ---------------------------------------------------------------------------


def test_downstream_of_returns_transitive_dependents():
    run = _build_linear_run()
    assert run.downstream_of("ingest") == ["transform", "publish"]
    assert run.downstream_of("transform") == ["publish"]
    assert run.downstream_of("publish") == []


def test_failure_invalidates_downstream_succeeded_steps():
    run = _build_linear_run()
    run.run_step("ingest", _ok("data"))
    run.run_step("transform", _ok("transformed"))
    assert run.steps["transform"].status == StepStatus.SUCCEEDED

    # Re-running ingest (e.g. with a fixed config) but it fails again.
    run.run_step("ingest", _fail("still broken"))
    assert run.steps["ingest"].status == StepStatus.FAILED
    # transform had succeeded based on now-suspect upstream data -> invalidated
    assert run.steps["transform"].status == StepStatus.INVALIDATED
    # publish never ran, so it stays PENDING rather than being marked invalid.
    assert run.steps["publish"].status == StepStatus.PENDING


# ---------------------------------------------------------------------------
# Recovery action: retry same step / with edited inputs
# ---------------------------------------------------------------------------


def test_retry_same_step_after_failure():
    run = _build_linear_run()
    run.run_step("ingest", _fail("timeout"))
    assert run.steps["ingest"].status == StepStatus.FAILED

    step = run.retry_step("ingest", _ok("recovered"), reason="transient timeout")
    assert step.status == StepStatus.SUCCEEDED
    assert step.output == "recovered"

    audit = run.audit_log[-1]
    assert audit.action == RecoveryAction.RETRY_SAME
    assert audit.step_id == "ingest"
    assert audit.reason == "transient timeout"


def test_retry_with_edited_inputs_updates_step_inputs_and_audit():
    run = _build_linear_run()
    run.run_step("ingest", _fail("bad endpoint"))

    captured_inputs = {}

    def executor(inputs):
        captured_inputs.update(inputs)
        return "ok"

    run.retry_step(
        "ingest",
        executor,
        edited_inputs={"source": "s3://bucket/fixed-file"},
        actor="user-42",
        reason="fixed the webhook endpoint config",
    )

    assert run.steps["ingest"].inputs["source"] == "s3://bucket/fixed-file"
    assert captured_inputs["source"] == "s3://bucket/fixed-file"

    audit = run.audit_log[-1]
    assert audit.action == RecoveryAction.RETRY_WITH_EDITED_INPUT
    assert audit.actor == "user-42"


def test_cannot_retry_a_step_that_has_not_failed():
    run = _build_linear_run()
    run.run_step("ingest", _ok("data"))
    with pytest.raises(InvalidRecoveryActionError):
        run.retry_step("ingest", _ok("data-again"))


# ---------------------------------------------------------------------------
# Recovery action: resume from checkpoint
# ---------------------------------------------------------------------------


def test_resume_from_checkpoint_skips_completed_steps():
    run = _build_linear_run()
    run.run_step("ingest", _ok("data"))
    run.run_step("transform", _ok("transformed"))
    # publish fails first time.
    run.run_step("publish", _fail("webhook down"))

    call_counts = {"ingest": 0, "transform": 0, "publish": 0}

    def make_tracker(step_id, value):
        def _executor(_inputs):
            call_counts[step_id] += 1
            return value
        return _executor

    executed = run.resume_from_checkpoint({
        "ingest": make_tracker("ingest", "data"),
        "transform": make_tracker("transform", "transformed"),
        "publish": make_tracker("publish", "published"),
    })

    # Only the failed step should have actually been re-executed.
    assert call_counts == {"ingest": 0, "transform": 0, "publish": 1}
    assert [s.step_id for s in executed] == ["publish"]
    assert run.steps["publish"].status == StepStatus.SUCCEEDED
    assert run.steps["ingest"].status == StepStatus.SUCCEEDED
    assert run.steps["transform"].status == StepStatus.SUCCEEDED

    audit = run.audit_log[-1]
    assert audit.action == RecoveryAction.RESUME_FROM_CHECKPOINT
    assert audit.affected_steps == ["publish"]


def test_resume_from_checkpoint_reruns_invalidated_steps():
    run = _build_linear_run()
    run.run_step("ingest", _ok("v1"))
    run.run_step("transform", _ok("transformed-v1"))
    # ingest re-run fails -> invalidates transform.
    run.run_step("ingest", _fail("broke"))
    assert run.steps["transform"].status == StepStatus.INVALIDATED

    executed = run.resume_from_checkpoint({
        "ingest": _ok("v2"),
        "transform": _ok("transformed-v2"),
        "publish": _ok("published"),
    })

    executed_ids = {s.step_id for s in executed}
    assert "ingest" in executed_ids
    assert "transform" in executed_ids
    assert run.steps["transform"].output == "transformed-v2"
    assert run.steps["publish"].status == StepStatus.SUCCEEDED


# ---------------------------------------------------------------------------
# Recovery action: rerun downstream only
# ---------------------------------------------------------------------------


def test_rerun_downstream_leaves_upstream_intact():
    run = _build_linear_run()
    run.run_step("ingest", _ok("retrieved-doc"))
    run.run_step("transform", _ok("draft-v1"))
    run.run_step("publish", _ok("published-v1"))

    ingest_calls = {"count": 0}

    def ingest_executor(_inputs):
        ingest_calls["count"] += 1
        return "retrieved-doc"

    executed = run.rerun_downstream(
        "ingest",
        {
            "ingest": ingest_executor,  # should not be called — ingest is upstream of itself
            "transform": _ok("draft-v2"),
            "publish": _ok("published-v2"),
        },
        reason="checkpoint artifact edited",
    )

    # ingest itself is not downstream of itself, so it must not be touched.
    assert ingest_calls["count"] == 0
    assert run.steps["ingest"].output == "retrieved-doc"
    assert run.steps["transform"].output == "draft-v2"
    assert run.steps["publish"].output == "published-v2"
    assert {s.step_id for s in executed} == {"transform", "publish"}

    audit = run.audit_log[-1]
    assert audit.action == RecoveryAction.RERUN_DOWNSTREAM
    assert audit.step_id == "ingest"
    assert set(audit.affected_steps) == {"transform", "publish"}


# ---------------------------------------------------------------------------
# Failure detail view payload (for the future frontend integration)
# ---------------------------------------------------------------------------


def test_failure_detail_includes_options_and_downstream_for_failed_step():
    run = _build_linear_run()
    run.run_step("ingest", _ok("data"))
    run.run_step("transform", _ok("transformed"))
    run.run_step("publish", _fail("webhook 500"))

    detail = run.failure_detail("publish")
    assert detail["status"] == StepStatus.FAILED.value
    assert detail["error"] == "webhook 500"
    assert set(detail["recovery_options"]) == {
        RecoveryAction.RETRY_SAME.value,
        RecoveryAction.RETRY_WITH_EDITED_INPUT.value,
        RecoveryAction.RESUME_FROM_CHECKPOINT.value,
        RecoveryAction.RERUN_DOWNSTREAM.value,
    }
    assert detail["affected_downstream_steps"] == []


def test_failure_detail_has_no_recovery_options_for_healthy_step():
    run = _build_linear_run()
    run.run_step("ingest", _ok("data"))
    detail = run.failure_detail("ingest")
    assert detail["status"] == StepStatus.SUCCEEDED.value
    assert detail["recovery_options"] == []


def test_to_dict_serializes_run_state_and_audit_log():
    run = _build_linear_run()
    run.run_step("ingest", _fail("oops"))
    run.retry_step("ingest", _ok("fixed"))

    payload = run.to_dict()
    assert payload["run_id"] == run.run_id
    assert payload["steps"]["ingest"]["status"] == StepStatus.SUCCEEDED.value
    assert payload["steps"]["ingest"]["checkpoint_count"] == 2
    assert len(payload["audit_log"]) == 1
    assert payload["audit_log"][0]["action"] == RecoveryAction.RETRY_SAME.value
