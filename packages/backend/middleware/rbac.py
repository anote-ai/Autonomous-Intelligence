"""Role-based access control decorators for org-scoped endpoints."""
from __future__ import annotations

import functools
from collections.abc import Callable
from typing import Any

from flask import jsonify, request
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request


def _get_org_id() -> int | None:
    """Extract org_id from URL path param, query string, or header."""
    from flask import g
    org_id = g.get("url_org_id")
    if org_id is not None:
        return int(org_id)
    hdr = request.headers.get("X-Org-Id")
    if hdr:
        try:
            return int(hdr)
        except ValueError:
            pass
    return None


def require_org_role(*roles: str) -> Callable:
    """Decorator: require JWT + org membership with one of the given roles."""
    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                verify_jwt_in_request()
            except Exception:
                return jsonify({"error": "Unauthorized"}), 401

            org_id = kwargs.get("org_id") or _get_org_id()
            if not org_id:
                return jsonify({"error": "org_id is required"}), 400

            user_id_str = get_jwt_identity()
            try:
                user_id = int(user_id_str)
            except (TypeError, ValueError):
                return jsonify({"error": "Unauthorized"}), 401

            try:
                from database.db import get_connection, get_member
                cnx = get_connection()
                member = get_member(cnx, org_id, user_id)
                cnx.close()
            except Exception:
                member = None

            if not member or member.get("role") not in roles:
                return jsonify({"error": "Forbidden"}), 403

            return fn(*args, **kwargs)
        return wrapper
    return decorator


def require_scim_token(fn: Callable) -> Callable:
    """Decorator: validate SCIM bearer token against scim_token_hash in org row."""
    @functools.wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        org_id = kwargs.get("org_id")
        if not org_id:
            return jsonify({"error": "org_id required"}), 400

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "SCIM bearer token required"}), 401
        token = auth_header[7:]

        try:
            import bcrypt

            from database.db import get_connection, get_org_by_id
            cnx = get_connection()
            org = get_org_by_id(cnx, org_id)
            cnx.close()
        except Exception:
            return jsonify({"error": "Service unavailable"}), 503

        if not org or not org.get("scim_token_hash"):
            return jsonify({"error": "SCIM not configured for this organization"}), 403

        if not bcrypt.checkpw(token.encode(), org["scim_token_hash"].encode()):
            return jsonify({"error": "Invalid SCIM token"}), 401

        return fn(*args, **kwargs)
    return wrapper
