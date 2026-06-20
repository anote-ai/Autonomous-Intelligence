"""Browser/computer-use action safety policy and execution trace recording.

Part of issue #139 ("Add browser and computer-use execution for real-world
web tasks"). This module implements the *policy gating* and *execution
trace* pieces of that epic:

- ``ActionSafetyLevel``: the four safety tiers called out in the issue
  (read-only, form-fill, submit, destructive).
- ``classify_action``: maps a browser action type (e.g. ``"click"``,
  ``"submit_form"``, ``"delete_file"``) to its safety level.
- ``BrowserActionPolicy``: gates submit/destructive actions behind an
  explicit allow-list and/or an approval callback, and raises
  ``PolicyViolation`` when a disallowed action is attempted. Every
  decision (allowed or denied) is auditable via ``decisions``.
- ``BrowserSessionTrace`` / ``BrowserStepTrace``: structured, replayable
  step traces for a single browser session (run), isolated per
  workspace/project, so failed steps can be inspected and replayed.

This module intentionally has **no external dependencies** (stdlib only)
so it can be unit tested without pulling in the heavy optional deps
(langchain, anthropic, etc.) that the rest of ``agents/`` requires. Actual
browser driving (Playwright/Selenium), credential injection, and artifact
storage (screenshots to S3/disk) are out of scope for this module — see
the PR description for what's deferred.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional


class ActionSafetyLevel(str, Enum):
    """Safety tiers for browser/computer-use actions, per issue #139.

    Ordered from least to most dangerous; comparisons use this ordering.
    """

    READ_ONLY = "read_only"
    FORM_FILL = "form_fill"
    SUBMIT = "submit"
    DESTRUCTIVE = "destructive"

    @property
    def rank(self) -> int:
        return _LEVEL_RANK[self]


_LEVEL_RANK = {
    ActionSafetyLevel.READ_ONLY: 0,
    ActionSafetyLevel.FORM_FILL: 1,
    ActionSafetyLevel.SUBMIT: 2,
    ActionSafetyLevel.DESTRUCTIVE: 3,
}

# Canonical mapping of action types to safety levels. Unknown action types
# default to DESTRUCTIVE (fail closed) via classify_action's fallback.
_ACTION_SAFETY_MAP: dict[str, ActionSafetyLevel] = {
    # Read-only: navigation, observation, extraction
    "navigate": ActionSafetyLevel.READ_ONLY,
    "screenshot": ActionSafetyLevel.READ_ONLY,
    "extract_dom": ActionSafetyLevel.READ_ONLY,
    "extract_text": ActionSafetyLevel.READ_ONLY,
    "scroll": ActionSafetyLevel.READ_ONLY,
    "wait_for_selector": ActionSafetyLevel.READ_ONLY,
    "read_cookies": ActionSafetyLevel.READ_ONLY,
    "hover": ActionSafetyLevel.READ_ONLY,
    # Form-fill: populating inputs, uploading files, non-committing clicks
    "fill_field": ActionSafetyLevel.FORM_FILL,
    "select_option": ActionSafetyLevel.FORM_FILL,
    "upload_file": ActionSafetyLevel.FORM_FILL,
    "click": ActionSafetyLevel.FORM_FILL,
    "check_checkbox": ActionSafetyLevel.FORM_FILL,
    "type_text": ActionSafetyLevel.FORM_FILL,
    # Submit: actions that send data externally / commit state
    "submit_form": ActionSafetyLevel.SUBMIT,
    "click_submit_button": ActionSafetyLevel.SUBMIT,
    "send_application": ActionSafetyLevel.SUBMIT,
    "post_message": ActionSafetyLevel.SUBMIT,
    "publish": ActionSafetyLevel.SUBMIT,
    # Destructive: irreversible or account-altering actions
    "delete_file": ActionSafetyLevel.DESTRUCTIVE,
    "delete_account": ActionSafetyLevel.DESTRUCTIVE,
    "cancel_subscription": ActionSafetyLevel.DESTRUCTIVE,
    "make_payment": ActionSafetyLevel.DESTRUCTIVE,
    "change_password": ActionSafetyLevel.DESTRUCTIVE,
    "delete_post": ActionSafetyLevel.DESTRUCTIVE,
}


def classify_action(action_type: str) -> ActionSafetyLevel:
    """Classify a browser action type into a safety level.

    Unknown action types are treated as DESTRUCTIVE (fail closed) so new,
    unrecognized capabilities are gated by default rather than silently
    allowed.
    """
    return _ACTION_SAFETY_MAP.get(action_type, ActionSafetyLevel.DESTRUCTIVE)


def register_action_type(action_type: str, level: ActionSafetyLevel) -> None:
    """Register (or override) the safety level for an action type.

    Allows callers (e.g. a future Playwright tool layer) to extend the
    known action vocabulary without modifying this module.
    """
    _ACTION_SAFETY_MAP[action_type] = level


class PolicyViolation(Exception):
    """Raised when an action is attempted that the active policy denies."""

    def __init__(self, action_type: str, level: ActionSafetyLevel, reason: str):
        self.action_type = action_type
        self.level = level
        self.reason = reason
        super().__init__(
            f"Action '{action_type}' (level={level.value}) denied: {reason}"
        )


@dataclass
class PolicyDecision:
    """An auditable record of a single policy check."""

    action_type: str
    level: ActionSafetyLevel
    allowed: bool
    reason: str
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_type": self.action_type,
            "level": self.level.value,
            "allowed": self.allowed,
            "reason": self.reason,
            "timestamp": self.timestamp,
        }


ApprovalCallback = Callable[[str, ActionSafetyLevel, dict[str, Any]], bool]


class BrowserActionPolicy:
    """Gates browser actions by safety level.

    - READ_ONLY and FORM_FILL actions are always allowed.
    - SUBMIT actions are allowed only if ``allow_submit`` is True (or an
      ``approval_callback`` explicitly approves the specific call).
    - DESTRUCTIVE actions are allowed only if ``allow_destructive`` is True
      AND (no approval callback is set, or the callback approves).

    Every check — allowed or denied — is appended to ``self.decisions`` for
    later audit, satisfying the "auditable after the run" acceptance
    criterion.
    """

    def __init__(
        self,
        allow_submit: bool = False,
        allow_destructive: bool = False,
        approval_callback: Optional[ApprovalCallback] = None,
    ) -> None:
        self.allow_submit = allow_submit
        self.allow_destructive = allow_destructive
        self.approval_callback = approval_callback
        self.decisions: list[PolicyDecision] = []

    def check(self, action_type: str, params: Optional[dict[str, Any]] = None) -> PolicyDecision:
        """Evaluate whether ``action_type`` is permitted. Does not raise."""
        params = params or {}
        level = classify_action(action_type)

        if level in (ActionSafetyLevel.READ_ONLY, ActionSafetyLevel.FORM_FILL):
            decision = PolicyDecision(action_type, level, True, "auto-allowed (non-gated level)")
        elif level is ActionSafetyLevel.SUBMIT:
            if not self.allow_submit:
                decision = PolicyDecision(action_type, level, False, "submit actions disabled for this run")
            elif self.approval_callback is not None and not self.approval_callback(action_type, level, params):
                decision = PolicyDecision(action_type, level, False, "rejected by approval callback")
            else:
                decision = PolicyDecision(action_type, level, True, "submit allowed")
        else:  # DESTRUCTIVE
            if not self.allow_destructive:
                decision = PolicyDecision(action_type, level, False, "destructive actions disabled for this run")
            elif self.approval_callback is not None and not self.approval_callback(action_type, level, params):
                decision = PolicyDecision(action_type, level, False, "rejected by approval callback")
            else:
                decision = PolicyDecision(action_type, level, True, "destructive action explicitly approved")

        self.decisions.append(decision)
        return decision

    def enforce(self, action_type: str, params: Optional[dict[str, Any]] = None) -> PolicyDecision:
        """Like ``check``, but raises ``PolicyViolation`` if denied."""
        decision = self.check(action_type, params)
        if not decision.allowed:
            raise PolicyViolation(action_type, decision.level, decision.reason)
        return decision

    def audit_log(self) -> list[dict[str, Any]]:
        return [d.to_dict() for d in self.decisions]


@dataclass
class BrowserStepTrace:
    """A single recorded step within a browser session run."""

    step_id: str
    action_type: str
    level: ActionSafetyLevel
    status: str  # "pending" | "success" | "failure" | "denied"
    params: dict[str, Any] = field(default_factory=dict)
    result: Optional[dict[str, Any]] = None
    error: Optional[str] = None
    artifacts: list[dict[str, Any]] = field(default_factory=list)
    started_at: float = field(default_factory=time.time)
    ended_at: Optional[float] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_id": self.step_id,
            "action_type": self.action_type,
            "level": self.level.value,
            "status": self.status,
            "params": self.params,
            "result": self.result,
            "error": self.error,
            "artifacts": self.artifacts,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
        }


class BrowserSessionTrace:
    """Records the structured step trace for one isolated browser session.

    A session is scoped to a single (workspace_id, project_id, run_id)
    tuple so traces never leak across tenants/runs, addressing the
    "isolated per run and linked to the owning workspace/project"
    acceptance criterion. Real artifact storage (screenshots/logs to
    blob storage) is out of scope here; ``add_artifact`` only records
    structured references (e.g. a path or URI) into the trace.
    """

    def __init__(
        self,
        workspace_id: str,
        project_id: Optional[str] = None,
        run_id: Optional[str] = None,
        policy: Optional[BrowserActionPolicy] = None,
    ) -> None:
        self.session_id = str(uuid.uuid4())
        self.workspace_id = workspace_id
        self.project_id = project_id
        self.run_id = run_id or str(uuid.uuid4())
        self.policy = policy or BrowserActionPolicy()
        self.steps: list[BrowserStepTrace] = []
        self.created_at = time.time()

    def start_step(self, action_type: str, params: Optional[dict[str, Any]] = None) -> BrowserStepTrace:
        """Run the policy check for ``action_type`` and open a new step.

        If the policy denies the action, the step is recorded with
        status "denied" and ``PolicyViolation`` is re-raised so callers
        cannot silently proceed with a gated action.
        """
        params = params or {}
        level = classify_action(action_type)
        decision = self.policy.check(action_type, params)
        step = BrowserStepTrace(
            step_id=str(uuid.uuid4()),
            action_type=action_type,
            level=level,
            status="pending" if decision.allowed else "denied",
            params=params,
        )
        self.steps.append(step)
        if not decision.allowed:
            step.ended_at = time.time()
            step.error = decision.reason
            raise PolicyViolation(action_type, level, decision.reason)
        return step

    @staticmethod
    def complete_step(step: BrowserStepTrace, result: Optional[dict[str, Any]] = None) -> None:
        step.status = "success"
        step.result = result
        step.ended_at = time.time()

    @staticmethod
    def fail_step(step: BrowserStepTrace, error: str) -> None:
        step.status = "failure"
        step.error = error
        step.ended_at = time.time()

    @staticmethod
    def add_artifact(step: BrowserStepTrace, artifact_type: str, uri: str, **meta: Any) -> None:
        step.artifacts.append({"type": artifact_type, "uri": uri, **meta})

    def failed_steps(self) -> list[BrowserStepTrace]:
        return [s for s in self.steps if s.status in ("failure", "denied")]

    def replay_plan(self) -> list[dict[str, Any]]:
        """Return the ordered list of failed/denied steps with enough
        context (action_type + params) to retry them, satisfying the
        "failed steps can be replayed and debugged" acceptance criterion.
        """
        return [
            {"step_id": s.step_id, "action_type": s.action_type, "params": s.params, "status": s.status, "error": s.error}
            for s in self.failed_steps()
        ]

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "workspace_id": self.workspace_id,
            "project_id": self.project_id,
            "run_id": self.run_id,
            "created_at": self.created_at,
            "steps": [s.to_dict() for s in self.steps],
            "audit_log": self.policy.audit_log(),
        }
