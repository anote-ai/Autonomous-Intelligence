"""User profile and API key management."""
from __future__ import annotations

import secrets

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

user_bp = Blueprint("user", __name__, url_prefix="/api/user")

_api_keys: dict[str, list[str]] = {}


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
    keys = _api_keys.get(user_id, [])
    masked = [f"{k[:8]}...{k[-4:]}" for k in keys]
    return jsonify({"keys": masked}), 200


@user_bp.post("/api-keys")
@jwt_required()
def create_api_key() -> tuple:
    user_id = get_jwt_identity()
    key = f"ak-{secrets.token_urlsafe(32)}"
    _api_keys.setdefault(user_id, []).append(key)
    return jsonify({"key": key}), 201


@user_bp.delete("/api-keys/<key_prefix>")
@jwt_required()
def delete_api_key(key_prefix: str) -> tuple:
    user_id = get_jwt_identity()
    keys = _api_keys.get(user_id, [])
    original_len = len(keys)
    _api_keys[user_id] = [k for k in keys if not k.startswith(key_prefix)]
    deleted = original_len - len(_api_keys.get(user_id, []))
    if not deleted:
        return jsonify({"error": "Key not found"}), 404
    return jsonify({"deleted": deleted}), 200
