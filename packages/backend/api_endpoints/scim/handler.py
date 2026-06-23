"""SCIM 2.0 provisioning endpoints.

URL pattern: /scim/v2/<org_id>/Users  and  /scim/v2/<org_id>/Groups
All routes require a SCIM bearer token validated against the org's scim_token_hash.
"""
from __future__ import annotations

from flask import Blueprint, jsonify, request

from middleware.rbac import require_scim_token
from services.identity import (
    SCIM_GROUP_SCHEMA,
    SCIM_LIST_SCHEMA,
    group_name_to_role,
    scim_error,
    scim_user_from_row,
)

scim_bp = Blueprint("scim", __name__, url_prefix="/scim/v2")

_CT = {"Content-Type": "application/scim+json"}


def _base_url() -> str:
    return request.host_url.rstrip("/")


# ── Users ──────────────────────────────────────────────────────────────────────

@scim_bp.get("/<int:org_id>/Users")
@require_scim_token
def list_users(org_id: int) -> tuple:
    try:
        from database.db import get_connection, list_members
        cnx = get_connection()
        members = list_members(cnx, org_id)
        cnx.close()
    except Exception:
        return jsonify(scim_error("Service unavailable", 503)), 503, _CT

    resources = [scim_user_from_row(m, _base_url(), org_id) for m in members]
    return jsonify({
        "schemas": [SCIM_LIST_SCHEMA],
        "totalResults": len(resources),
        "Resources": resources,
    }), 200, _CT


@scim_bp.post("/<int:org_id>/Users")
@require_scim_token
def create_user(org_id: int) -> tuple:
    body = request.get_json(silent=True) or {}
    username = body.get("userName") or ""
    emails = body.get("emails") or []
    email = next((e["value"] for e in emails if e.get("primary")), username)
    name_obj = body.get("name") or {}
    name = name_obj.get("formatted") or f"{name_obj.get('givenName','')} {name_obj.get('familyName','')}".strip() or email
    external_id = body.get("externalId") or body.get("id") or ""
    active = body.get("active", True)

    if not email:
        return jsonify(scim_error("userName / emails required")), 400, _CT

    try:
        from database.db import (
            get_connection,
            get_member_by_scim_id,
            list_members,
            log_identity_event,
            upsert_member,
            upsert_sso_user,
        )
        cnx = get_connection()
        if external_id and get_member_by_scim_id(cnx, org_id, external_id):
            cnx.close()
            return jsonify(scim_error("User already exists", 409)), 409, _CT

        user_id = upsert_sso_user(cnx, email, name, "scim", external_id or email)
        if not active:
            cnx.cursor().execute("UPDATE users SET is_active = 0 WHERE id = %s", (user_id,))
        upsert_member(cnx, org_id, user_id, role="member", provisioned_by="scim", scim_external_id=external_id or str(user_id))
        log_identity_event(cnx, "scim_provision", org_id=org_id, user_id=user_id, actor="scim", detail={"email": email})
        members = list_members(cnx, org_id)
        cnx.close()
    except Exception:
        return jsonify(scim_error("Service unavailable", 503)), 503, _CT

    member = next((m for m in members if m["user_id"] == user_id), None)
    if not member:
        return jsonify(scim_error("Created but not retrievable", 500)), 500, _CT

    return jsonify(scim_user_from_row(member, _base_url(), org_id)), 201, _CT


@scim_bp.get("/<int:org_id>/Users/<string:scim_id>")
@require_scim_token
def get_user(org_id: int, scim_id: str) -> tuple:
    try:
        from database.db import get_connection, get_member_by_scim_id, list_members
        cnx = get_connection()
        mem_row = get_member_by_scim_id(cnx, org_id, scim_id)
        if not mem_row:
            cnx.close()
            return jsonify(scim_error("User not found", 404)), 404, _CT
        members = list_members(cnx, org_id)
        cnx.close()
    except Exception:
        return jsonify(scim_error("Service unavailable", 503)), 503, _CT

    member = next((m for m in members if m["user_id"] == mem_row["user_id"]), None)
    if not member:
        return jsonify(scim_error("User not found", 404)), 404, _CT
    return jsonify(scim_user_from_row(member, _base_url(), org_id)), 200, _CT


@scim_bp.put("/<int:org_id>/Users/<string:scim_id>")
@require_scim_token
def replace_user(org_id: int, scim_id: str) -> tuple:
    body = request.get_json(silent=True) or {}
    active = body.get("active", True)
    name_obj = body.get("name") or {}
    name = name_obj.get("formatted") or ""

    try:
        from database.db import (
            get_connection,
            get_member_by_scim_id,
            list_members,
            log_identity_event,
        )
        cnx = get_connection()
        mem_row = get_member_by_scim_id(cnx, org_id, scim_id)
        if not mem_row:
            cnx.close()
            return jsonify(scim_error("User not found", 404)), 404, _CT
        user_id = mem_row["user_id"]
        cur = cnx.cursor()
        if name:
            cur.execute("UPDATE users SET is_active = %s, name = %s WHERE id = %s", (1 if active else 0, name, user_id))
        else:
            cur.execute("UPDATE users SET is_active = %s WHERE id = %s", (1 if active else 0, user_id))
        log_identity_event(cnx, "scim_update", org_id=org_id, user_id=user_id, actor="scim", detail={"active": active})
        members = list_members(cnx, org_id)
        cnx.close()
    except Exception:
        return jsonify(scim_error("Service unavailable", 503)), 503, _CT

    member = next((m for m in members if m["user_id"] == user_id), None)
    if not member:
        return jsonify(scim_error("Not found", 404)), 404, _CT
    return jsonify(scim_user_from_row(member, _base_url(), org_id)), 200, _CT


@scim_bp.route("/<int:org_id>/Users/<string:scim_id>", methods=["PATCH"])
@require_scim_token
def patch_user(org_id: int, scim_id: str) -> tuple:
    body = request.get_json(silent=True) or {}
    operations = body.get("Operations") or []

    try:
        from database.db import (
            get_connection,
            get_member_by_scim_id,
            list_members,
            log_identity_event,
        )
        cnx = get_connection()
        mem_row = get_member_by_scim_id(cnx, org_id, scim_id)
        if not mem_row:
            cnx.close()
            return jsonify(scim_error("User not found", 404)), 404, _CT
        user_id = mem_row["user_id"]
        for op in operations:
            path = (op.get("path") or "").lower()
            value = op.get("value")
            if path == "active" and value is not None:
                cnx.cursor().execute("UPDATE users SET is_active = %s WHERE id = %s", (1 if value else 0, user_id))
        log_identity_event(cnx, "scim_patch", org_id=org_id, user_id=user_id, actor="scim", detail={"ops": len(operations)})
        members = list_members(cnx, org_id)
        cnx.close()
    except Exception:
        return jsonify(scim_error("Service unavailable", 503)), 503, _CT

    member = next((m for m in members if m["user_id"] == user_id), None)
    if not member:
        return jsonify(scim_error("Not found", 404)), 404, _CT
    return jsonify(scim_user_from_row(member, _base_url(), org_id)), 200, _CT


@scim_bp.delete("/<int:org_id>/Users/<string:scim_id>")
@require_scim_token
def delete_user(org_id: int, scim_id: str) -> tuple:
    try:
        from database.db import (
            get_connection,
            get_member_by_scim_id,
            log_identity_event,
            remove_member,
        )
        cnx = get_connection()
        mem_row = get_member_by_scim_id(cnx, org_id, scim_id)
        if not mem_row:
            cnx.close()
            return jsonify(scim_error("User not found", 404)), 404, _CT
        user_id = mem_row["user_id"]
        remove_member(cnx, org_id, user_id)
        cnx.cursor().execute("UPDATE users SET is_active = 0 WHERE id = %s", (user_id,))
        log_identity_event(cnx, "scim_deprovision", org_id=org_id, user_id=user_id, actor="scim")
        cnx.close()
    except Exception:
        return jsonify(scim_error("Service unavailable", 503)), 503, _CT

    return "", 204


# ── Groups (role mapping) ──────────────────────────────────────────────────────

@scim_bp.get("/<int:org_id>/Groups")
@require_scim_token
def list_groups(org_id: int) -> tuple:
    return jsonify({
        "schemas": [SCIM_LIST_SCHEMA],
        "totalResults": 3,
        "Resources": [
            _group_resource(org_id, "admin",  "Admin",   "Workspace administrators"),
            _group_resource(org_id, "member", "Members", "Regular workspace members"),
            _group_resource(org_id, "viewer", "Viewers", "Read-only workspace access"),
        ],
    }), 200, _CT


@scim_bp.post("/<int:org_id>/Groups")
@require_scim_token
def create_group(org_id: int) -> tuple:
    """
    Map an IdP group to a role by display name.
    Members in the group body are provisioned with the mapped role.
    """
    body = request.get_json(silent=True) or {}
    display_name: str = body.get("displayName") or ""
    members_raw: list[dict] = body.get("members") or []
    role = group_name_to_role(display_name)

    try:
        from database.db import get_connection, log_identity_event, upsert_member, upsert_sso_user
        cnx = get_connection()
        for m in members_raw:
            email = (m.get("value") or m.get("display") or "").lower()
            if not email:
                continue
            user_id = upsert_sso_user(cnx, email, email, "scim", email)
            upsert_member(cnx, org_id, user_id, role=role, provisioned_by="scim", scim_external_id=email)
            log_identity_event(cnx, "scim_group_sync", org_id=org_id, user_id=user_id, actor="scim",
                               detail={"group": display_name, "role": role})
        cnx.close()
    except Exception:
        return jsonify(scim_error("Service unavailable", 503)), 503, _CT

    return jsonify(_group_resource(org_id, role, display_name)), 201, _CT


@scim_bp.route("/<int:org_id>/Groups/<string:group_id>", methods=["PATCH"])
@require_scim_token
def patch_group(org_id: int, group_id: str) -> tuple:
    """Add/remove members to a role group."""
    body = request.get_json(silent=True) or {}
    operations = body.get("Operations") or []
    role = group_id  # group_id is the role name (admin/member/viewer)

    try:
        from database.db import (
            get_connection,
            log_identity_event,
            remove_member,
            upsert_member,
            upsert_sso_user,
        )
        cnx = get_connection()
        for op in operations:
            op_type = (op.get("op") or "").lower()
            members_raw: list[dict] = op.get("value") or []
            for m in members_raw:
                email = (m.get("value") or m.get("display") or "").lower()
                if not email:
                    continue
                if op_type == "add":
                    user_id = upsert_sso_user(cnx, email, email, "scim", email)
                    upsert_member(cnx, org_id, user_id, role=role, provisioned_by="scim")
                    log_identity_event(cnx, "scim_role_add", org_id=org_id, user_id=user_id, actor="scim",
                                       detail={"role": role})
                elif op_type in ("remove", "delete"):
                    cur = cnx.cursor(dictionary=True)
                    cur.execute("SELECT id FROM users WHERE email = %s LIMIT 1", (email,))
                    row = cur.fetchone()
                    if row:
                        remove_member(cnx, org_id, row["id"])
                        log_identity_event(cnx, "scim_role_remove", org_id=org_id, user_id=row["id"], actor="scim")
        cnx.close()
    except Exception:
        return jsonify(scim_error("Service unavailable", 503)), 503, _CT

    return jsonify(_group_resource(org_id, role, role.capitalize())), 200, _CT


@scim_bp.delete("/<int:org_id>/Groups/<string:group_id>")
@require_scim_token
def delete_group(org_id: int, group_id: str) -> tuple:
    return "", 204


def _group_resource(org_id: int, group_id: str, display_name: str, description: str = "") -> dict:
    return {
        "schemas": [SCIM_GROUP_SCHEMA],
        "id": group_id,
        "displayName": display_name,
        "meta": {
            "resourceType": "Group",
            "location": f"{_base_url()}/scim/v2/{org_id}/Groups/{group_id}",
        },
    }
