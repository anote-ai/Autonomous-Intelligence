"""Data governance endpoints: retention policies, legal holds, exports, classifications."""
from __future__ import annotations

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity

from middleware.rbac import require_org_role
from services.governance import (
    VALID_DATA_TYPES,
    VALID_EXPORT_STATUSES,
    validate_classification,
    validate_hold,
    validate_policy,
)

governance_bp = Blueprint("governance", __name__, url_prefix="/api/admin/organizations")


def _actor() -> int:
    try:
        return int(get_jwt_identity())
    except (TypeError, ValueError):
        return 0


# ── Retention policies ─────────────────────────────────────────────────────────

@governance_bp.get("/<int:org_id>/governance/policies")
@require_org_role("admin", "member", "viewer")
def list_policies(org_id: int) -> tuple:
    try:
        from database.db import get_connection, list_data_policies
        cnx = get_connection()
        rows = list_data_policies(cnx, org_id)
        cnx.close()
    except Exception:
        return jsonify({"error": "Service unavailable"}), 503
    return jsonify({"policies": rows, "defaults": {"retention_days": 365, "auto_delete": False, "classification": "internal"}}), 200


@governance_bp.put("/<int:org_id>/governance/policies/<string:data_type>")
@require_org_role("admin")
def set_policy(org_id: int, data_type: str) -> tuple:
    body = request.get_json(silent=True) or {}
    retention_days = body.get("retention_days", 365)
    auto_delete = bool(body.get("auto_delete", False))
    classification = (body.get("classification") or "internal").strip()

    err = validate_policy(data_type, retention_days, classification)
    if err:
        return jsonify({"error": err}), 400

    try:
        from database.db import (
            get_connection,
            log_governance_event,
            upsert_data_policy,
        )
        actor = _actor()
        cnx = get_connection()
        upsert_data_policy(cnx, org_id, data_type, retention_days, auto_delete, classification, actor)
        log_governance_event(cnx, org_id, "policy_set", actor_id=actor, resource=data_type,
                             detail={"retention_days": retention_days, "auto_delete": auto_delete,
                                     "classification": classification})
        cnx.close()
    except Exception:
        return jsonify({"error": "Service unavailable"}), 503

    return jsonify({"org_id": org_id, "data_type": data_type, "retention_days": retention_days,
                    "auto_delete": auto_delete, "classification": classification}), 200


@governance_bp.delete("/<int:org_id>/governance/policies/<string:data_type>")
@require_org_role("admin")
def reset_policy(org_id: int, data_type: str) -> tuple:
    if data_type not in VALID_DATA_TYPES:
        return jsonify({"error": f"Unknown data_type: {data_type}"}), 400
    try:
        from database.db import delete_data_policy, get_connection, log_governance_event
        actor = _actor()
        cnx = get_connection()
        delete_data_policy(cnx, org_id, data_type)
        log_governance_event(cnx, org_id, "policy_reset", actor_id=actor, resource=data_type)
        cnx.close()
    except Exception:
        return jsonify({"error": "Service unavailable"}), 503
    return jsonify({"reset": True, "data_type": data_type}), 200


# ── Legal holds ────────────────────────────────────────────────────────────────

@governance_bp.get("/<int:org_id>/governance/holds")
@require_org_role("admin", "member")
def list_holds(org_id: int) -> tuple:
    include_released = request.args.get("include_released", "").lower() in ("1", "true", "yes")
    try:
        from database.db import get_connection, list_legal_holds
        cnx = get_connection()
        holds = list_legal_holds(cnx, org_id, include_released=include_released)
        cnx.close()
    except Exception:
        return jsonify({"error": "Service unavailable"}), 503

    for h in holds:
        for k, v in h.items():
            if hasattr(v, "isoformat"):
                h[k] = v.isoformat()
    return jsonify({"holds": holds, "total": len(holds)}), 200


@governance_bp.post("/<int:org_id>/governance/holds")
@require_org_role("admin")
def place_hold(org_id: int) -> tuple:
    body = request.get_json(silent=True) or {}
    resource_type = (body.get("resource_type") or "").strip()
    resource_id = (body.get("resource_id") or "").strip()
    reason = (body.get("reason") or "").strip()
    expires_at = body.get("expires_at") or None

    err = validate_hold(resource_type, resource_id, reason)
    if err:
        return jsonify({"error": err}), 400

    try:
        from database.db import create_legal_hold, get_connection, log_governance_event
        actor = _actor()
        cnx = get_connection()
        hold_id = create_legal_hold(cnx, org_id, resource_type, resource_id, reason, actor, expires_at)
        log_governance_event(cnx, org_id, "hold_placed", actor_id=actor,
                             resource=f"{resource_type}/{resource_id}",
                             detail={"hold_id": hold_id, "reason": reason})
        cnx.close()
    except Exception:
        return jsonify({"error": "Service unavailable"}), 503

    return jsonify({"hold_id": hold_id, "org_id": org_id, "resource_type": resource_type,
                    "resource_id": resource_id, "reason": reason, "expires_at": expires_at}), 201


@governance_bp.delete("/<int:org_id>/governance/holds/<int:hold_id>")
@require_org_role("admin")
def release_hold(org_id: int, hold_id: int) -> tuple:
    try:
        from database.db import (
            get_connection,
            get_legal_hold,
            log_governance_event,
            release_legal_hold,
        )
        actor = _actor()
        cnx = get_connection()
        hold = get_legal_hold(cnx, hold_id)
        if not hold or hold.get("org_id") != org_id:
            cnx.close()
            return jsonify({"error": "Hold not found"}), 404
        if hold.get("released_at") is not None:
            cnx.close()
            return jsonify({"error": "Hold is already released"}), 409
        release_legal_hold(cnx, hold_id, actor)
        log_governance_event(cnx, org_id, "hold_released", actor_id=actor,
                             resource=f"{hold['resource_type']}/{hold['resource_id']}",
                             detail={"hold_id": hold_id})
        cnx.close()
    except Exception:
        return jsonify({"error": "Service unavailable"}), 503
    return jsonify({"released": True, "hold_id": hold_id}), 200


# ── Export requests ────────────────────────────────────────────────────────────

@governance_bp.get("/<int:org_id>/governance/exports")
@require_org_role("admin", "member")
def list_exports(org_id: int) -> tuple:
    try:
        from database.db import get_connection, list_export_requests
        cnx = get_connection()
        reqs = list_export_requests(cnx, org_id)
        cnx.close()
    except Exception:
        return jsonify({"error": "Service unavailable"}), 503

    for r in reqs:
        for k, v in r.items():
            if hasattr(v, "isoformat"):
                r[k] = v.isoformat()
    return jsonify({"exports": reqs, "total": len(reqs)}), 200


@governance_bp.post("/<int:org_id>/governance/exports")
@require_org_role("admin", "member")
def request_export(org_id: int) -> tuple:
    body = request.get_json(silent=True) or {}
    data_types = body.get("data_types") or []
    scope = body.get("scope") or None

    if not isinstance(data_types, list) or not data_types:
        return jsonify({"error": "data_types must be a non-empty list"}), 400
    invalid = [dt for dt in data_types if dt not in VALID_DATA_TYPES]
    if invalid:
        return jsonify({"error": f"Invalid data_types: {invalid}"}), 400

    try:
        from database.db import create_export_request, get_connection, log_governance_event
        actor = _actor()
        cnx = get_connection()
        req_id = create_export_request(cnx, org_id, actor, data_types, scope)
        log_governance_event(cnx, org_id, "export_requested", actor_id=actor,
                             detail={"req_id": req_id, "data_types": data_types})
        cnx.close()
    except Exception:
        return jsonify({"error": "Service unavailable"}), 503

    return jsonify({"req_id": req_id, "org_id": org_id, "status": "pending",
                    "data_types": data_types}), 201


@governance_bp.get("/<int:org_id>/governance/exports/<int:req_id>")
@require_org_role("admin", "member", "viewer")
def get_export(org_id: int, req_id: int) -> tuple:
    try:
        from database.db import get_connection, get_export_request
        cnx = get_connection()
        req = get_export_request(cnx, req_id)
        cnx.close()
    except Exception:
        return jsonify({"error": "Service unavailable"}), 503

    if not req or req.get("org_id") != org_id:
        return jsonify({"error": "Export request not found"}), 404
    for k, v in req.items():
        if hasattr(v, "isoformat"):
            req[k] = v.isoformat()
    return jsonify(req), 200


@governance_bp.post("/<int:org_id>/governance/exports/<int:req_id>/fulfill")
@require_org_role("admin")
def fulfill_export(org_id: int, req_id: int) -> tuple:
    body = request.get_json(silent=True) or {}
    status = (body.get("status") or "fulfilled").strip()
    download_url = (body.get("download_url") or "").strip() or None

    if status not in VALID_EXPORT_STATUSES:
        return jsonify({"error": f"status must be one of: {sorted(VALID_EXPORT_STATUSES)}"}), 400

    try:
        from database.db import (
            get_connection,
            get_export_request,
            log_governance_event,
            update_export_status,
        )
        actor = _actor()
        cnx = get_connection()
        req = get_export_request(cnx, req_id)
        if not req or req.get("org_id") != org_id:
            cnx.close()
            return jsonify({"error": "Export request not found"}), 404
        update_export_status(cnx, req_id, status, download_url, actor)
        log_governance_event(cnx, org_id, "export_fulfilled", actor_id=actor,
                             detail={"req_id": req_id, "status": status})
        cnx.close()
    except Exception:
        return jsonify({"error": "Service unavailable"}), 503

    return jsonify({"req_id": req_id, "status": status, "download_url": download_url}), 200


# ── Data classifications ───────────────────────────────────────────────────────

@governance_bp.get("/<int:org_id>/governance/classifications")
@require_org_role("admin", "member", "viewer")
def list_classifications(org_id: int) -> tuple:
    try:
        from database.db import get_connection, list_resource_classifications
        cnx = get_connection()
        rows = list_resource_classifications(cnx, org_id)
        cnx.close()
    except Exception:
        return jsonify({"error": "Service unavailable"}), 503
    return jsonify({"classifications": rows, "total": len(rows)}), 200


@governance_bp.post("/<int:org_id>/governance/classifications")
@require_org_role("admin", "member")
def tag_resource(org_id: int) -> tuple:
    body = request.get_json(silent=True) or {}
    resource_type = (body.get("resource_type") or "").strip()
    resource_id = (body.get("resource_id") or "").strip()
    classification = (body.get("classification") or "").strip()

    err = validate_classification(resource_type, resource_id, classification)
    if err:
        return jsonify({"error": err}), 400

    try:
        from database.db import (
            get_connection,
            log_governance_event,
            upsert_resource_classification,
        )
        actor = _actor()
        cnx = get_connection()
        cls_id = upsert_resource_classification(cnx, org_id, resource_type, resource_id, classification, actor)
        log_governance_event(cnx, org_id, "classification_set", actor_id=actor,
                             resource=f"{resource_type}/{resource_id}",
                             detail={"classification": classification})
        cnx.close()
    except Exception:
        return jsonify({"error": "Service unavailable"}), 503

    return jsonify({"id": cls_id, "org_id": org_id, "resource_type": resource_type,
                    "resource_id": resource_id, "classification": classification}), 201


@governance_bp.delete("/<int:org_id>/governance/classifications/<int:cls_id>")
@require_org_role("admin")
def remove_classification(org_id: int, cls_id: int) -> tuple:
    try:
        from database.db import delete_resource_classification, get_connection, log_governance_event
        actor = _actor()
        cnx = get_connection()
        delete_resource_classification(cnx, cls_id, org_id)
        log_governance_event(cnx, org_id, "classification_removed", actor_id=actor,
                             detail={"cls_id": cls_id})
        cnx.close()
    except Exception:
        return jsonify({"error": "Service unavailable"}), 503
    return jsonify({"removed": True, "id": cls_id}), 200


# ── Deletion eligibility check ─────────────────────────────────────────────────

@governance_bp.get("/<int:org_id>/governance/deletion-check")
@require_org_role("admin", "member")
def deletion_check(org_id: int) -> tuple:
    resource_type = request.args.get("resource_type", "").strip()
    resource_id = request.args.get("resource_id", "").strip()

    if not resource_type or not resource_id:
        return jsonify({"error": "resource_type and resource_id query params are required"}), 400

    try:
        from database.db import get_connection
        from services.governance import evaluate_deletion_allowed
        cnx = get_connection()
        result = evaluate_deletion_allowed(cnx, org_id, resource_type, resource_id)
        cnx.close()
    except Exception:
        return jsonify({"error": "Service unavailable"}), 503

    return jsonify(result), 200


# ── Governance audit log ───────────────────────────────────────────────────────

@governance_bp.get("/<int:org_id>/governance/audit")
@require_org_role("admin")
def governance_audit(org_id: int) -> tuple:
    limit = min(int(request.args.get("limit", 100)), 500)
    try:
        from database.db import get_connection, list_governance_audit
        cnx = get_connection()
        events = list_governance_audit(cnx, org_id, limit)
        cnx.close()
    except Exception:
        return jsonify({"error": "Service unavailable"}), 503

    for e in events:
        for k, v in e.items():
            if hasattr(v, "isoformat"):
                e[k] = v.isoformat()
    return jsonify({"events": events, "total": len(events)}), 200
