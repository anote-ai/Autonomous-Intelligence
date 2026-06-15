"""Semantic search endpoint."""
from __future__ import annotations

import os
import re
from pathlib import Path

from flask import Blueprint, jsonify, request

from services.search import has_index, search_index

search_bp = Blueprint("search", __name__, url_prefix="/api/search")

# Only allow cwd values that look like absolute Unix/Windows paths with no shell metacharacters
_SAFE_PATH_RE = re.compile(r'^[a-zA-Z0-9/_\-. ]+$')


@search_bp.get("")
def search() -> tuple:  # type: ignore[type-arg]
    """Search the codebase index."""
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"error": "q parameter is required"}), 400

    raw_cwd = request.args.get("cwd", os.getcwd())

    # Validate cwd: must be an absolute path containing only safe characters
    if not raw_cwd.startswith("/") or not _SAFE_PATH_RE.match(raw_cwd):
        return jsonify({"error": "Invalid cwd parameter"}), 400

    # Resolve symlinks and reject any remaining traversal
    try:
        cwd = str(Path(raw_cwd).resolve())
    except Exception:
        return jsonify({"error": "Invalid cwd parameter"}), 400

    if ".." in Path(cwd).parts:
        return jsonify({"error": "Invalid cwd parameter"}), 400

    top = int(request.args.get("top", "10"))

    if not has_index(cwd):
        return jsonify({"error": "No index found. Run `anote index` in your project."}), 404

    try:
        results = search_index(query=query, cwd=cwd, top_k=top)
        return jsonify({"results": results, "query": query, "cwd": cwd}), 200
    except Exception as exc:
        print(f"Search error: {exc}")
        return jsonify({"error": "Internal server error"}), 500
