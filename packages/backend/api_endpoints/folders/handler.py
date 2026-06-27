"""Folder endpoints — create, list, rename, delete."""
from __future__ import annotations

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity

from database.db import (
    create_folder,
    delete_folder,
    get_connection,
    get_folders,
    rename_folder,
)
from middleware.auth import require_auth

folders_bp = Blueprint("folders", __name__, url_prefix="/api/folders")


@folders_bp.post("")
@require_auth
def create() -> tuple:  # type: ignore[type-arg]
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "name is required"}), 400
    try:
        cnx = get_connection()
        folder_id = create_folder(cnx, int(get_jwt_identity()), name)
        cnx.close()
        return jsonify({"id": folder_id, "name": name}), 201
    except Exception:
        return jsonify({"error": "Internal server error"}), 500


@folders_bp.get("")
@require_auth
def list_folders() -> tuple:  # type: ignore[type-arg]
    try:
        cnx = get_connection()
        folders = get_folders(cnx, int(get_jwt_identity()))
        cnx.close()
        return jsonify({"folders": folders}), 200
    except Exception:
        return jsonify({"error": "Internal server error"}), 500


@folders_bp.patch("/<int:folder_id>")
@require_auth
def rename(folder_id: int) -> tuple:  # type: ignore[type-arg]
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "name is required"}), 400
    try:
        cnx = get_connection()
        updated = rename_folder(cnx, folder_id, int(get_jwt_identity()), name)
        cnx.close()
        if not updated:
            return jsonify({"error": "Folder not found"}), 404
        return jsonify({"id": folder_id, "name": name}), 200
    except Exception:
        return jsonify({"error": "Internal server error"}), 500


@folders_bp.delete("/<int:folder_id>")
@require_auth
def remove(folder_id: int) -> tuple:  # type: ignore[type-arg]
    try:
        cnx = get_connection()
        deleted = delete_folder(cnx, folder_id, int(get_jwt_identity()))
        cnx.close()
        if not deleted:
            return jsonify({"error": "Folder not found"}), 404
        return jsonify({"deleted": True}), 200
    except Exception:
        return jsonify({"error": "Internal server error"}), 500
