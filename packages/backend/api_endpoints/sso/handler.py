"""SSO endpoints — OIDC authorization code flow."""
from __future__ import annotations

import os
import secrets

from flask import Blueprint, jsonify, redirect, request
from flask_jwt_extended import create_access_token

sso_bp = Blueprint("sso", __name__, url_prefix="/auth/sso")

_SSO_STATE_STORE: dict[str, int] = {}


def _redirect_uri() -> str:
    base = os.environ.get("APP_BASE_URL", "http://localhost:5000")
    return f"{base}/auth/sso/callback"


@sso_bp.get("/init")
def sso_init() -> tuple:
    """
    Initiate SSO for an organization.
    Query params: org_id (int)
    Redirects to the IdP authorization URL.
    """
    org_id_str = request.args.get("org_id", "")
    if not org_id_str or not org_id_str.isdigit():
        return jsonify({"error": "org_id is required"}), 400
    org_id = int(org_id_str)

    try:
        from database.db import get_connection, get_org_by_id
        cnx = get_connection()
        org = get_org_by_id(cnx, org_id)
        cnx.close()
    except Exception:
        return jsonify({"error": "Service unavailable"}), 503

    if not org:
        return jsonify({"error": "Organization not found"}), 404
    if not org.get("sso_discovery_url"):
        return jsonify({"error": "SSO not configured for this organization"}), 422

    state = secrets.token_urlsafe(24)
    _SSO_STATE_STORE[state] = org_id

    try:
        from services.identity import get_authorization_url
        url = get_authorization_url(org, state, _redirect_uri())
    except Exception as exc:
        return jsonify({"error": str(exc)}), 502

    return redirect(url), 302  # type: ignore[return-value]


@sso_bp.get("/callback")
def sso_callback() -> tuple:
    """
    Handle the OIDC callback from the IdP.
    Query params: code, state
    Returns a JWT on success.
    """
    code = request.args.get("code", "")
    state = request.args.get("state", "")
    error = request.args.get("error", "")

    if error:
        return jsonify({"error": f"IdP error: {error}"}), 400
    if not code or not state:
        return jsonify({"error": "code and state are required"}), 400

    org_id = _SSO_STATE_STORE.pop(state, None)
    if org_id is None:
        return jsonify({"error": "Invalid or expired state"}), 400

    try:
        from database.db import get_connection, get_org_by_id
        cnx = get_connection()
        org = get_org_by_id(cnx, org_id)
    except Exception:
        return jsonify({"error": "Service unavailable"}), 503

    if not org:
        return jsonify({"error": "Organization not found"}), 404

    try:
        from services.identity import exchange_code_for_tokens, provision_sso_user
        claims = exchange_code_for_tokens(org, code, _redirect_uri())
        user_id = provision_sso_user(cnx, org_id, claims, org["sso_provider"])
        cnx.close()
    except Exception as exc:
        return jsonify({"error": str(exc)}), 502

    token = create_access_token(identity=str(user_id))
    return jsonify({"token": token, "userId": user_id, "org_id": org_id}), 200


@sso_bp.get("/providers")
def sso_providers() -> tuple:
    """Return the list of supported SSO providers."""
    return jsonify({
        "providers": [
            {"id": "okta",    "name": "Okta",             "protocol": "OIDC"},
            {"id": "azure",   "name": "Microsoft Entra",  "protocol": "OIDC"},
            {"id": "google",  "name": "Google Workspace", "protocol": "OIDC"},
            {"id": "generic", "name": "Generic OIDC",     "protocol": "OIDC"},
        ]
    }), 200
