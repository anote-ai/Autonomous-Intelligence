"""HTTP handlers for the operator console — issue #140 (slice 1).

These handlers back a small REST surface for autonomous "runs": list/create,
fetch a single run, fetch its audit trail, and apply an operator
intervention (pause/resume/cancel/retry/message). The Flask routes in
``app.py`` resolve the authenticated user and delegate to these functions,
mirroring the pattern used by ``api_endpoints/documents/handler.py``.

Scope: this slice ships the persisted data model + control API only. The
dashboard UI (project list, live run view, daily/overnight summary screens)
is explicitly out of scope here — see the PR description for the rest of
the epic.
"""

from __future__ import annotations

from typing import Any

from database.agent_runs import (
    apply_intervention,
    create_run,
    get_run,
    list_run_events,
    list_runs,
)
from database.db_auth import user_id_for_email
from flask import Request, jsonify
from flask.typing import ResponseReturnValue

_VALID_INTERVENTIONS = {"pause", "resume", "cancel", "retry", "message"}


def _resolve_user_id(user_email: str) -> int | None:
    return user_id_for_email(user_email)


def CreateRunHandler(request: Request, user_email: str) -> ResponseReturnValue:
    """POST /api/agent-runs — queue a new autonomous run."""
    body = request.get_json(silent=True) or {}
    project_name = (body.get("project_name") or "").strip()
    chat_id = body.get("chat_id")

    if not project_name:
        return jsonify({"error": "project_name is required"}), 400

    user_id = _resolve_user_id(user_email)
    if user_id is None:
        return jsonify({"error": "User not found"}), 404

    run_id = create_run(user_id, project_name, chat_id=chat_id)
    run = get_run(run_id, user_id)
    return jsonify(_serialize_run(run)), 201


def ListRunsHandler(request: Request, user_email: str) -> ResponseReturnValue:
    """GET /api/agent-runs — list runs for the operator console's queue/history views."""
    user_id = _resolve_user_id(user_email)
    if user_id is None:
        return jsonify({"error": "User not found"}), 404

    status = request.args.get("status")
    try:
        limit = int(request.args.get("limit", 50))
    except (TypeError, ValueError):
        limit = 50

    runs = list_runs(user_id, status=status, limit=limit)
    return jsonify({"runs": [_serialize_run(r) for r in runs]}), 200


def GetRunHandler(request: Request, user_email: str, run_id: int) -> ResponseReturnValue:
    """GET /api/agent-runs/<run_id> — live run detail view."""
    user_id = _resolve_user_id(user_email)
    if user_id is None:
        return jsonify({"error": "User not found"}), 404

    run = get_run(run_id, user_id)
    if run is None:
        return jsonify({"error": "Run not found"}), 404
    return jsonify(_serialize_run(run)), 200


def GetRunEventsHandler(request: Request, user_email: str, run_id: int) -> ResponseReturnValue:
    """GET /api/agent-runs/<run_id>/events — audit trail of interventions."""
    user_id = _resolve_user_id(user_email)
    if user_id is None:
        return jsonify({"error": "User not found"}), 404

    run = get_run(run_id, user_id)
    if run is None:
        return jsonify({"error": "Run not found"}), 404

    events = list_run_events(run_id, user_id)
    return jsonify({"events": [_serialize_event(e) for e in events]}), 200


def InterventionHandler(request: Request, user_email: str, run_id: int) -> ResponseReturnValue:
    """POST /api/agent-runs/<run_id>/intervene — pause/resume/cancel/retry/message.

    Body: {"action": "pause" | "resume" | "cancel" | "retry" | "message",
           "message": "..."}  (message only required/used for action=message)
    """
    user_id = _resolve_user_id(user_email)
    if user_id is None:
        return jsonify({"error": "User not found"}), 404

    body = request.get_json(silent=True) or {}
    action = (body.get("action") or "").strip()
    message = body.get("message")

    if action not in _VALID_INTERVENTIONS:
        return jsonify({
            "error": f"Invalid action {action!r}. Must be one of {sorted(_VALID_INTERVENTIONS)}."
        }), 400

    if action == "message" and not message:
        return jsonify({"error": "message is required for action=message"}), 400

    try:
        result = apply_intervention(run_id, user_id, action, actor=user_email, message=message)
    except ValueError as exc:
        msg = str(exc)
        status_code = 404 if "not found" in msg.lower() else 400
        return jsonify({"error": msg}), status_code

    return jsonify(result), 200


def _serialize_run(run: dict[str, Any] | None) -> dict[str, Any] | None:
    if run is None:
        return None
    out = dict(run)
    for key in ("created", "updated", "started_at", "finished_at"):
        value = out.get(key)
        if hasattr(value, "isoformat"):
            out[key] = value.isoformat()
    if out.get("cost_usd") is not None:
        out["cost_usd"] = float(out["cost_usd"])
    return out


def _serialize_event(event: dict[str, Any]) -> dict[str, Any]:
    out = dict(event)
    value = out.get("created")
    if hasattr(value, "isoformat"):
        out["created"] = value.isoformat()
    return out
