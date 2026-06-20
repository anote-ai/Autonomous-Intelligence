"""Workflow / job failure-recovery engine.

This module implements the "Recovery Model" portion of GitHub issue #135
("Add failure recovery and resume-from-checkpoint for workflows and jobs"):

- Explicit checkpointing of per-step state for a workflow run.
- Tracking of which step outputs are reusable vs. invalidated after a
  failure (lineage-aware downstream invalidation).
- Recovery actions: retry the same step, retry a step with edited inputs,
  resume from the last good checkpoint, and rerun only downstream tasks.
- An auditable, append-only history of every recovery action taken on a
  run, so recovery decisions are traceable.

The engine is intentionally storage-agnostic: it operates on an in-memory
``WorkflowRun`` aggregate that callers can persist however they like (e.g.
serialize to a DB row's JSON column, or back it with the ORM models in
``database/models.py`` in a follow-up). This keeps the core recovery logic
independently testable without requiring a database, Flask app context, or
the wider agent stack to be wired up.
"""

from __future__ import annotations

import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class StepStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    INVALIDATED = "invalidated"
    SKIPPED = "skipped"


class RecoveryAction(StrEnum):
    RETRY_SAME = "retry_same"
    RETRY_WITH_EDITED_INPUT = "retry_with_edited_input"
    RESUME_FROM_CHECKPOINT = "resume_from_checkpoint"
    RERUN_DOWNSTREAM = "rerun_downstream"


class WorkflowError(Exception):
    """Base error for the workflow recovery engine."""


class StepNotFoundError(WorkflowError):
    pass


class InvalidRecoveryActionError(WorkflowError):
    pass


def _now() -> float:
    return time.time()


@dataclass
class StepCheckpoint:
    """A single recorded checkpoint for a step.

    Checkpoints accumulate over the lifetime of a step (e.g. one per
    attempt). The latest checkpoint with status SUCCEEDED is what a resume
    operation will rely on to avoid recomputing the step.
    """

    step_id: str
    status: StepStatus
    inputs: dict[str, Any] = field(default_factory=dict)
    output: Any = None
    error: str | None = None
    attempt: int = 1
    created_at: float = field(default_factory=_now)


@dataclass
class Step:
    """A node in the workflow DAG."""

    step_id: str
    name: str
    depends_on: list[str] = field(default_factory=list)
    status: StepStatus = StepStatus.PENDING
    inputs: dict[str, Any] = field(default_factory=dict)
    output: Any = None
    error: str | None = None
    attempt: int = 0
    checkpoints: list[StepCheckpoint] = field(default_factory=list)

    def latest_succeeded_checkpoint(self) -> StepCheckpoint | None:
        for checkpoint in reversed(self.checkpoints):
            if checkpoint.status == StepStatus.SUCCEEDED:
                return checkpoint
        return None


@dataclass
class AuditEntry:
    """An immutable, append-only audit record of a recovery decision."""

    entry_id: str
    run_id: str
    action: RecoveryAction
    step_id: str
    actor: str
    reason: str | None
    affected_steps: list[str]
    created_at: float = field(default_factory=_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "run_id": self.run_id,
            "action": self.action.value,
            "step_id": self.step_id,
            "actor": self.actor,
            "reason": self.reason,
            "affected_steps": list(self.affected_steps),
            "created_at": self.created_at,
        }


class WorkflowRun:
    """A single execution of a workflow, with checkpoint/recovery support.

    ``steps`` is an ordered dict-like mapping of step_id -> Step describing
    the DAG. Edges are expressed via ``Step.depends_on``.
    """

    def __init__(self, run_id: str | None = None, name: str = "") -> None:
        self.run_id = run_id or str(uuid.uuid4())
        self.name = name
        self.steps: dict[str, Step] = {}
        self.order: list[str] = []
        self.audit_log: list[AuditEntry] = []

    # ------------------------------------------------------------------
    # DAG construction
    # ------------------------------------------------------------------
    def add_step(self, step_id: str, name: str, depends_on: list[str] | None = None,
                 inputs: dict[str, Any] | None = None) -> Step:
        step = Step(
            step_id=step_id,
            name=name,
            depends_on=list(depends_on or []),
            inputs=dict(inputs or {}),
        )
        self.steps[step_id] = step
        self.order.append(step_id)
        return step

    def _get_step(self, step_id: str) -> Step:
        step = self.steps.get(step_id)
        if step is None:
            raise StepNotFoundError(f"Unknown step_id: {step_id!r}")
        return step

    def downstream_of(self, step_id: str) -> list[str]:
        """Return all step_ids transitively dependent on ``step_id`` (exclusive)."""
        self._get_step(step_id)
        downstream: list[str] = []
        frontier = {step_id}
        changed = True
        while changed:
            changed = False
            for sid in self.order:
                if sid in downstream or sid in frontier:
                    continue
                step = self.steps[sid]
                if any(dep in frontier or dep in downstream for dep in step.depends_on):
                    downstream.append(sid)
                    changed = True
        return downstream

    # ------------------------------------------------------------------
    # Execution + checkpointing
    # ------------------------------------------------------------------
    def run_step(self, step_id: str, executor: Callable[[dict[str, Any]], Any]) -> Step:
        """Execute a single step with ``executor(inputs) -> output``.

        Records a checkpoint regardless of outcome. Raises nothing — failures
        are captured on the Step/checkpoint so recovery flows can inspect
        them rather than relying on exception propagation.
        """
        step = self._get_step(step_id)

        unmet = [
            dep for dep in step.depends_on
            if self.steps[dep].status != StepStatus.SUCCEEDED
        ]
        if unmet:
            step.status = StepStatus.SKIPPED
            step.error = f"Unmet dependencies: {unmet}"
            return step

        step.status = StepStatus.RUNNING
        step.attempt += 1
        try:
            output = executor(step.inputs)
        except Exception as exc:  # noqa: BLE001 — failures are first-class data here
            step.status = StepStatus.FAILED
            step.error = str(exc)
            step.checkpoints.append(StepCheckpoint(
                step_id=step_id,
                status=StepStatus.FAILED,
                inputs=dict(step.inputs),
                error=str(exc),
                attempt=step.attempt,
            ))
            self._invalidate_downstream(step_id)
            return step

        step.status = StepStatus.SUCCEEDED
        step.output = output
        step.error = None
        step.checkpoints.append(StepCheckpoint(
            step_id=step_id,
            status=StepStatus.SUCCEEDED,
            inputs=dict(step.inputs),
            output=output,
            attempt=step.attempt,
        ))
        return step

    def _invalidate_downstream(self, step_id: str) -> list[str]:
        """Mark all downstream steps as invalidated after an upstream failure.

        Steps that have not yet run (PENDING) are left untouched — they were
        never "reusable" to begin with. Only steps that previously succeeded
        get their reusable output explicitly invalidated, since their output
        may have been derived from data that is now suspect.
        """
        invalidated: list[str] = []
        for sid in self.downstream_of(step_id):
            step = self.steps[sid]
            if step.status == StepStatus.SUCCEEDED:
                step.status = StepStatus.INVALIDATED
                invalidated.append(sid)
        return invalidated

    # ------------------------------------------------------------------
    # Recovery actions
    # ------------------------------------------------------------------
    def _record_audit(self, action: RecoveryAction, step_id: str, actor: str,
                       reason: str | None, affected_steps: list[str]) -> AuditEntry:
        entry = AuditEntry(
            entry_id=str(uuid.uuid4()),
            run_id=self.run_id,
            action=action,
            step_id=step_id,
            actor=actor,
            reason=reason,
            affected_steps=affected_steps,
        )
        self.audit_log.append(entry)
        return entry

    def retry_step(
        self,
        step_id: str,
        executor: Callable[[dict[str, Any]], Any],
        *,
        actor: str = "system",
        reason: str | None = None,
        edited_inputs: dict[str, Any] | None = None,
    ) -> Step:
        """Retry a single failed (or invalidated) step.

        If ``edited_inputs`` is supplied, the step's inputs are updated first
        (RETRY_WITH_EDITED_INPUT); otherwise the same inputs are reused
        (RETRY_SAME). On success, downstream steps that were invalidated by
        this step's prior failure are NOT automatically rerun — call
        ``rerun_downstream`` explicitly so that decision stays auditable and
        intentional.
        """
        step = self._get_step(step_id)
        if step.status not in (StepStatus.FAILED, StepStatus.INVALIDATED):
            raise InvalidRecoveryActionError(
                f"Cannot retry step {step_id!r} in status {step.status.value!r}; "
                "only FAILED or INVALIDATED steps may be retried."
            )

        action = RecoveryAction.RETRY_SAME
        if edited_inputs is not None:
            step.inputs.update(edited_inputs)
            action = RecoveryAction.RETRY_WITH_EDITED_INPUT

        self.run_step(step_id, executor)
        self._record_audit(action, step_id, actor, reason, affected_steps=[step_id])
        return step

    def resume_from_checkpoint(
        self,
        executors: dict[str, Callable[[dict[str, Any]], Any]],
        *,
        actor: str = "system",
        reason: str | None = None,
    ) -> list[Step]:
        """Resume a run, skipping any step that already has a successful
        checkpoint and is not currently invalidated.

        Returns the list of steps that were (re)executed. Steps that are
        SUCCEEDED are left untouched (no wasted recomputation); steps that
        are PENDING, FAILED, or INVALIDATED are executed in dependency
        order, reusing the last successful checkpoint's inputs when present.
        """
        executed: list[Step] = []
        for step_id in self.order:
            step = self.steps[step_id]
            if step.status == StepStatus.SUCCEEDED:
                continue  # reuse — nothing to do

            checkpoint = step.latest_succeeded_checkpoint()
            if checkpoint is not None and step.status not in (
                StepStatus.INVALIDATED, StepStatus.FAILED,
            ):
                # A prior successful checkpoint exists, nothing downstream
                # invalidated it, and the step itself isn't currently
                # failing — restore the checkpoint rather than recompute.
                step.status = StepStatus.SUCCEEDED
                step.output = checkpoint.output
                step.error = None
                continue

            executor = executors.get(step_id)
            if executor is None:
                continue
            self.run_step(step_id, executor)
            executed.append(step)

        affected = [s.step_id for s in executed]
        self._record_audit(
            RecoveryAction.RESUME_FROM_CHECKPOINT, step_id="*", actor=actor,
            reason=reason, affected_steps=affected,
        )
        return executed

    def rerun_downstream(
        self,
        step_id: str,
        executors: dict[str, Callable[[dict[str, Any]], Any]],
        *,
        actor: str = "system",
        reason: str | None = None,
    ) -> list[Step]:
        """Rerun only the steps downstream of ``step_id`` (exclusive),
        in dependency order, leaving upstream / unrelated steps untouched.

        Useful for the "edited artifact at a checkpoint" scenario: upstream
        retrieval steps stay intact while downstream drafting steps redo
        their work against the new artifact.
        """
        self._get_step(step_id)
        downstream_ids = set(self.downstream_of(step_id))
        executed: list[Step] = []
        for sid in self.order:
            if sid not in downstream_ids:
                continue
            step = self.steps[sid]
            step.status = StepStatus.PENDING
            executor = executors.get(sid)
            if executor is None:
                continue
            self.run_step(sid, executor)
            executed.append(step)

        affected = [s.step_id for s in executed]
        self._record_audit(
            RecoveryAction.RERUN_DOWNSTREAM, step_id=step_id, actor=actor,
            reason=reason, affected_steps=affected,
        )
        return executed

    # ------------------------------------------------------------------
    # Introspection / serialization (for the future failure-detail API)
    # ------------------------------------------------------------------
    def failing_steps(self) -> list[Step]:
        return [s for s in self.steps.values() if s.status == StepStatus.FAILED]

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "name": self.name,
            "steps": {
                sid: {
                    "step_id": step.step_id,
                    "name": step.name,
                    "depends_on": step.depends_on,
                    "status": step.status.value,
                    "inputs": step.inputs,
                    "output": step.output,
                    "error": step.error,
                    "attempt": step.attempt,
                    "checkpoint_count": len(step.checkpoints),
                }
                for sid, step in self.steps.items()
            },
            "audit_log": [entry.to_dict() for entry in self.audit_log],
        }

    def failure_detail(self, step_id: str) -> dict[str, Any]:
        """Build the payload the frontend failure-detail view would render:
        failing step, error summary, available recovery options, and the
        list of downstream tasks affected by this failure.
        """
        step = self._get_step(step_id)
        downstream = self.downstream_of(step_id)
        options = []
        if step.status in (StepStatus.FAILED, StepStatus.INVALIDATED):
            options = [
                RecoveryAction.RETRY_SAME.value,
                RecoveryAction.RETRY_WITH_EDITED_INPUT.value,
                RecoveryAction.RESUME_FROM_CHECKPOINT.value,
                RecoveryAction.RERUN_DOWNSTREAM.value,
            ]
        return {
            "run_id": self.run_id,
            "step_id": step.step_id,
            "step_name": step.name,
            "status": step.status.value,
            "error": step.error,
            "attempt": step.attempt,
            "recovery_options": options,
            "affected_downstream_steps": downstream,
        }
