"""Admin endpoints for enterprise org, SSO, member, and audit management."""
from __future__ import annotations

import re

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity

from middleware.auth import require_auth
from middleware.rbac import require_org_role

admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")


def _slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


# ── Organizations ──────────────────────────────────────────────────────────────

@admin_bp.get("/organizations")
@require_auth
def list_organizations() -> tuple:
    """List all organizations (any authenticated user can see the list)."""
    try:
        from database.db import get_connection, list_orgs
        cnx = get_connection()
        orgs = list_orgs(cnx)
        cnx.close()
    except Exception:
        return jsonify({"error": "Service unavailable"}), 503

    safe_fields = ["id", "name", "slug", "domain", "sso_provider", "mfa_required", "created_at", "updated_at"]
    return jsonify({"organizations": [{k: str(o[k]) if o[k] is not None else None for k in safe_fields if k in o} for o in orgs]}), 200


@admin_bp.post("/organizations")
@require_auth
def create_organization() -> tuple:
    """Create a new organization. The creator is added as admin."""
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    domain = (data.get("domain") or "").strip() or None

    if not name:
        return jsonify({"error": "name is required"}), 400

    slug = _slugify(name)
    user_id = int(get_jwt_identity())

    try:
        from database.db import (
            create_org,
            get_connection,
            get_org_by_slug,
            log_identity_event,
            upsert_member,
        )
        cnx = get_connection()
        if get_org_by_slug(cnx, slug):
            slug = f"{slug}-{user_id}"
        org_id = create_org(cnx, name, slug, domain)
        upsert_member(cnx, org_id, user_id, role="admin", provisioned_by="manual")
        log_identity_event(cnx, "org_created", org_id=org_id, user_id=user_id, actor=str(user_id),
                           detail={"name": name, "slug": slug})
        cnx.close()
    except Exception:
        return jsonify({"error": "Service unavailable"}), 503

    return jsonify({"id": org_id, "name": name, "slug": slug, "domain": domain}), 201


@admin_bp.get("/organizations/<int:org_id>")
@require_org_role("admin", "member", "viewer")
def get_organization(org_id: int) -> tuple:
    try:
        from database.db import get_connection, get_org_by_id
        cnx = get_connection()
        org = get_org_by_id(cnx, org_id)
        cnx.close()
    except Exception:
        return jsonify({"error": "Service unavailable"}), 503

    if not org:
        return jsonify({"error": "Organization not found"}), 404

    safe = {k: org[k] for k in ["id", "name", "slug", "domain", "sso_provider", "mfa_required", "created_at", "updated_at"] if k in org}
    return jsonify(safe), 200


@admin_bp.patch("/organizations/<int:org_id>")
@require_org_role("admin")
def update_organization(org_id: int) -> tuple:
    data = request.get_json(silent=True) or {}
    allowed = {"name", "domain", "mfa_required"}
    fields = {k: v for k, v in data.items() if k in allowed}

    if not fields:
        return jsonify({"error": "No updatable fields provided"}), 400

    try:
        from database.db import get_connection, get_org_by_id, log_identity_event, update_org
        cnx = get_connection()
        update_org(cnx, org_id, fields)
        log_identity_event(cnx, "org_updated", org_id=org_id, actor=get_jwt_identity(), detail={"fields": list(fields)})
        org = get_org_by_id(cnx, org_id)
        cnx.close()
    except Exception:
        return jsonify({"error": "Service unavailable"}), 503

    if not org:
        return jsonify({"error": "Organization not found"}), 404
    safe = {k: org[k] for k in ["id", "name", "slug", "domain", "sso_provider", "mfa_required"] if k in org}
    return jsonify(safe), 200


@admin_bp.delete("/organizations/<int:org_id>")
@require_org_role("admin")
def delete_organization(org_id: int) -> tuple:
    try:
        from database.db import delete_org, get_connection, log_identity_event
        cnx = get_connection()
        log_identity_event(cnx, "org_deleted", org_id=org_id, actor=get_jwt_identity())
        delete_org(cnx, org_id)
        cnx.close()
    except Exception:
        return jsonify({"error": "Service unavailable"}), 503
    return jsonify({"deleted": True}), 200


# ── SSO configuration ──────────────────────────────────────────────────────────

@admin_bp.put("/organizations/<int:org_id>/sso")
@require_org_role("admin")
def configure_sso(org_id: int) -> tuple:
    """Set or replace SSO config for an organization."""
    data = request.get_json(silent=True) or {}
    provider = data.get("provider") or ""
    client_id = data.get("client_id") or ""
    client_secret = data.get("client_secret") or ""
    discovery_url = data.get("discovery_url") or ""

    valid_providers = {"okta", "azure", "google", "generic"}
    if provider not in valid_providers:
        return jsonify({"error": f"provider must be one of {sorted(valid_providers)}"}), 400
    if not client_id or not client_secret or not discovery_url:
        return jsonify({"error": "client_id, client_secret, and discovery_url are required"}), 400

    try:
        from database.db import get_connection, log_identity_event, update_org
        cnx = get_connection()
        update_org(cnx, org_id, {
            "sso_provider": provider,
            "sso_client_id": client_id,
            "sso_client_secret": client_secret,
            "sso_discovery_url": discovery_url,
        })
        log_identity_event(cnx, "sso_configured", org_id=org_id, actor=get_jwt_identity(),
                           detail={"provider": provider})
        cnx.close()
    except Exception:
        return jsonify({"error": "Service unavailable"}), 503

    return jsonify({"org_id": org_id, "provider": provider, "configured": True}), 200


@admin_bp.delete("/organizations/<int:org_id>/sso")
@require_org_role("admin")
def disable_sso(org_id: int) -> tuple:
    try:
        from database.db import get_connection, log_identity_event, update_org
        cnx = get_connection()
        update_org(cnx, org_id, {
            "sso_provider": None,
            "sso_client_id": None,
            "sso_client_secret": None,
            "sso_discovery_url": None,
        })
        log_identity_event(cnx, "sso_disabled", org_id=org_id, actor=get_jwt_identity())
        cnx.close()
    except Exception:
        return jsonify({"error": "Service unavailable"}), 503
    return jsonify({"disabled": True}), 200


# ── SCIM token management ──────────────────────────────────────────────────────

@admin_bp.post("/organizations/<int:org_id>/scim-token")
@require_org_role("admin")
def rotate_scim_token(org_id: int) -> tuple:
    """Generate a new SCIM bearer token. The raw token is returned once."""
    try:
        from database.db import get_connection, log_identity_event, update_org
        from services.identity import generate_scim_token
        raw, hashed = generate_scim_token()
        cnx = get_connection()
        update_org(cnx, org_id, {"scim_token_hash": hashed})
        log_identity_event(cnx, "scim_token_rotated", org_id=org_id, actor=get_jwt_identity())
        cnx.close()
    except Exception:
        return jsonify({"error": "Service unavailable"}), 503

    return jsonify({
        "token": raw,
        "warning": "Store this token securely. It will not be shown again.",
        "scim_base_url": f"{request.host_url.rstrip('/')}/scim/v2/{org_id}",
    }), 201


# ── Members ────────────────────────────────────────────────────────────────────

@admin_bp.get("/organizations/<int:org_id>/members")
@require_org_role("admin", "member", "viewer")
def list_members(org_id: int) -> tuple:
    try:
        from database.db import get_connection
        from database.db import list_members as db_list_members
        cnx = get_connection()
        members = db_list_members(cnx, org_id)
        cnx.close()
    except Exception:
        return jsonify({"error": "Service unavailable"}), 503

    safe_fields = ["user_id", "email", "name", "role", "provisioned_by", "is_active", "created_at"]
    return jsonify({"members": [{k: m.get(k) for k in safe_fields} for m in members]}), 200


@admin_bp.post("/organizations/<int:org_id>/members")
@require_org_role("admin")
def add_member(org_id: int) -> tuple:
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    role = data.get("role") or "member"

    if not email:
        return jsonify({"error": "email is required"}), 400
    if role not in ("admin", "member", "viewer"):
        return jsonify({"error": "role must be admin, member, or viewer"}), 400

    try:
        from database.db import get_connection, get_user_by_email, log_identity_event, upsert_member
        cnx = get_connection()
        user = get_user_by_email(cnx, email)
        if not user:
            cnx.close()
            return jsonify({"error": "User not found. Ask them to register first."}), 404
        upsert_member(cnx, org_id, user["id"], role=role, provisioned_by="manual")
        log_identity_event(cnx, "member_added", org_id=org_id, user_id=user["id"],
                           actor=get_jwt_identity(), detail={"email": email, "role": role})
        cnx.close()
    except Exception:
        return jsonify({"error": "Service unavailable"}), 503

    return jsonify({"user_id": user["id"], "email": email, "role": role}), 201


@admin_bp.patch("/organizations/<int:org_id>/members/<int:target_user_id>")
@require_org_role("admin")
def update_member_role(org_id: int, target_user_id: int) -> tuple:
    data = request.get_json(silent=True) or {}
    role = data.get("role") or ""
    if role not in ("admin", "member", "viewer"):
        return jsonify({"error": "role must be admin, member, or viewer"}), 400

    try:
        from database.db import get_connection, get_member, log_identity_event, upsert_member
        cnx = get_connection()
        if not get_member(cnx, org_id, target_user_id):
            cnx.close()
            return jsonify({"error": "Member not found"}), 404
        upsert_member(cnx, org_id, target_user_id, role=role)
        log_identity_event(cnx, "role_changed", org_id=org_id, user_id=target_user_id,
                           actor=get_jwt_identity(), detail={"new_role": role})
        cnx.close()
    except Exception:
        return jsonify({"error": "Service unavailable"}), 503

    return jsonify({"user_id": target_user_id, "role": role}), 200


@admin_bp.delete("/organizations/<int:org_id>/members/<int:target_user_id>")
@require_org_role("admin")
def remove_member(org_id: int, target_user_id: int) -> tuple:
    try:
        from database.db import get_connection, log_identity_event
        from database.db import remove_member as db_remove_member
        cnx = get_connection()
        db_remove_member(cnx, org_id, target_user_id)
        log_identity_event(cnx, "member_removed", org_id=org_id, user_id=target_user_id,
                           actor=get_jwt_identity())
        cnx.close()
    except Exception:
        return jsonify({"error": "Service unavailable"}), 503
    return jsonify({"removed": True}), 200


# ── Audit log ──────────────────────────────────────────────────────────────────

@admin_bp.get("/organizations/<int:org_id>/audit-log")
@require_org_role("admin")
def audit_log(org_id: int) -> tuple:
    limit = min(int(request.args.get("limit", 100)), 500)
    try:
        from database.db import get_connection, list_audit_events
        cnx = get_connection()
        events = list_audit_events(cnx, org_id, limit)
        cnx.close()
    except Exception:
        return jsonify({"error": "Service unavailable"}), 503

    for e in events:
        for k, v in e.items():
            if hasattr(v, "isoformat"):
                e[k] = v.isoformat()

    return jsonify({"events": events, "total": len(events)}), 200
