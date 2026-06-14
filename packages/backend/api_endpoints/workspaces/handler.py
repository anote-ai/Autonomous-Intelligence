"""Workspace management — CRUD, git clone/pull/push (hosted mode only)."""
from __future__ import annotations

import os
import subprocess
import uuid
from pathlib import Path

from flask import Blueprint, jsonify, request

workspaces_bp = Blueprint("workspaces", __name__, url_prefix="/api/workspaces")

HOSTED_MODE = os.environ.get("ANOTE_MODE", "") == "hosted"
WORKSPACES_DIR = Path(os.environ.get("WORKSPACES_DIR", "/tmp/anote_workspaces"))
WORKSPACES_DIR.mkdir(parents=True, exist_ok=True)

_workspaces: dict[str, dict] = {}


def _hosted_only() -> tuple | None:
    if not HOSTED_MODE:
        return jsonify({"error": "Workspace API only available in hosted mode"}), 501
    return None


@workspaces_bp.get("")
def list_workspaces() -> tuple:
    guard = _hosted_only()
    if guard:
        return guard  # type: ignore[return-value]
    return jsonify({"workspaces": list(_workspaces.values())}), 200


@workspaces_bp.post("")
def create_workspace() -> tuple:
    guard = _hosted_only()
    if guard:
        return guard  # type: ignore[return-value]
    data = request.get_json(silent=True) or {}
    name = data.get("name", "").strip()
    if not name:
        return jsonify({"error": "name is required"}), 400
    ws_id = str(uuid.uuid4())
    ws_path = WORKSPACES_DIR / ws_id
    ws_path.mkdir(parents=True, exist_ok=True)
    _workspaces[ws_id] = {"id": ws_id, "name": name, "path": str(ws_path)}
    return jsonify(_workspaces[ws_id]), 201


@workspaces_bp.get("/<ws_id>")
def get_workspace(ws_id: str) -> tuple:
    guard = _hosted_only()
    if guard:
        return guard  # type: ignore[return-value]
    ws = _workspaces.get(ws_id)
    if not ws:
        return jsonify({"error": "Workspace not found"}), 404
    return jsonify(ws), 200


@workspaces_bp.delete("/<ws_id>")
def delete_workspace(ws_id: str) -> tuple:
    guard = _hosted_only()
    if guard:
        return guard  # type: ignore[return-value]
    ws = _workspaces.pop(ws_id, None)
    if not ws:
        return jsonify({"error": "Workspace not found"}), 404
    import shutil
    shutil.rmtree(ws["path"], ignore_errors=True)
    return jsonify({"deleted": True}), 200


@workspaces_bp.post("/<ws_id>/clone")
def clone_workspace(ws_id: str) -> tuple:
    guard = _hosted_only()
    if guard:
        return guard  # type: ignore[return-value]
    ws = _workspaces.get(ws_id)
    if not ws:
        return jsonify({"error": "Workspace not found"}), 404
    data = request.get_json(silent=True) or {}
    repo_url = data.get("repoUrl", "").strip()
    if not repo_url:
        return jsonify({"error": "repoUrl is required"}), 400
    try:
        subprocess.run(
            ["git", "clone", repo_url, "."],
            cwd=ws["path"], capture_output=True, timeout=60, check=True,
        )
        return jsonify({"cloned": True, "workspace": ws}), 200
    except subprocess.CalledProcessError as exc:
        return jsonify({"error": exc.stderr.decode()[:500]}), 500
