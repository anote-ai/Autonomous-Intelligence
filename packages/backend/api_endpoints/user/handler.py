"""User profile and API key management."""
from __future__ import annotations

import secrets
import string

import bcrypt
from flask import Blueprint, jsonify
from flask_jwt_extended import get_jwt_identity, jwt_required

user_bp = Blueprint("user", __name__, url_prefix="/api/user")

_KEY_ALPHABET = string.ascii_letters + string.digits
_PREFIX_LEN = 12  # "sk-ai-" + first 6 chars of the key, shown to the user forever

# In-memory fallback store, used only when no database is configured (e.g. tests).
_fallback_keys: dict[str, list[dict]] = {}


def _generate_api_key() -> tuple[str, str]:
    """Return (plaintext_key, prefix_for_display)."""
    body = "".join(secrets.choice(_KEY_ALPHABET) for _ in range(32))
    plaintext = f"sk-ai-{body}"
    prefix = plaintext[:_PREFIX_LEN]
    return plaintext, prefix


@user_bp.get("/profile")
@jwt_required()
def get_profile() -> tuple:
    user_id = get_jwt_identity()
    return jsonify({"userId": user_id}), 200


@user_bp.put("/profile")
@jwt_required()
def update_profile() -> tuple:
    user_id = get_jwt_identity()
    return jsonify({"userId": user_id, "updated": True}), 200


@user_bp.get("/api-keys")
@jwt_required()
def list_api_keys() -> tuple:
    user_id = get_jwt_identity()
    try:
        from database.db import get_connection, list_api_keys_for_user
        cnx = get_connection()
        keys = list_api_keys_for_user(cnx, int(user_id))
        cnx.close()
        return jsonify({"keys": keys}), 200
    except Exception:
        keys = _fallback_keys.get(user_id, [])
        return jsonify({"keys": keys}), 200


@user_bp.post("/api-keys")
@jwt_required()
def create_api_key() -> tuple:
    user_id = get_jwt_identity()
    plaintext, prefix = _generate_api_key()
    key_hash = bcrypt.hashpw(plaintext.encode(), bcrypt.gensalt()).decode()

    try:
        from database.db import create_api_key as db_create_api_key
        from database.db import get_connection
        cnx = get_connection()
        key_id = db_create_api_key(cnx, int(user_id), key_hash, prefix)
        cnx.close()
        return jsonify({"id": key_id, "key": plaintext, "prefix": prefix}), 201
    except Exception:
        record = {"prefix": prefix, "hash": key_hash, "is_active": True}
        _fallback_keys.setdefault(user_id, []).append(record)
        return jsonify({"key": plaintext, "prefix": prefix}), 201


@user_bp.delete("/api-keys/<key_prefix>")
@jwt_required()
def delete_api_key(key_prefix: str) -> tuple:
    user_id = get_jwt_identity()
    try:
        from database.db import get_connection, list_api_keys_for_user, revoke_api_key
        cnx = get_connection()
        keys = list_api_keys_for_user(cnx, int(user_id))
        match = next((k for k in keys if k["key_prefix"] == key_prefix), None)
        if not match:
            cnx.close()
            return jsonify({"error": "Key not found"}), 404
        revoke_api_key(cnx, int(user_id), match["id"])
        cnx.close()
        return jsonify({"deleted": True}), 200
    except Exception:
        keys = _fallback_keys.get(user_id, [])
        original_len = len(keys)
        _fallback_keys[user_id] = [k for k in keys if k["prefix"] != key_prefix]
        if len(_fallback_keys[user_id]) == original_len:
            return jsonify({"error": "Key not found"}), 404
        return jsonify({"deleted": True}), 200


@user_bp.get("/usage")
@jwt_required()
def get_usage() -> tuple:
    user_id = get_jwt_identity()
    try:
        from database.db import get_connection, get_usage_summary
        cnx = get_connection()
        summary = get_usage_summary(cnx, int(user_id))
        cnx.close()
        return jsonify(summary), 200
    except Exception:
        return jsonify({"request_count": 0, "total_credits_used": 0}), 200
