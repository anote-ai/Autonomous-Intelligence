"""Semantic search endpoint."""
from __future__ import annotations

import re

from flask import Blueprint, jsonify, request

from services.search import has_index, search_index, search_root

search_bp = Blueprint("search", __name__, url_prefix="/api/search")

# Only allow cwd values that look like absolute Unix/Windows paths with no shell metacharacters
_SAFE_PATH_RE = re.compile(r'^[a-zA-Z0-9/_\-. ]+$')


@search_bp.get("")
def search() -> tuple:  # type: ignore[type-arg]
    """Search the codebase index."""
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"error": "q parameter is required"}), 400

    cwd = str(search_root())
    raw_cwd = request.args.get("cwd")
    if raw_cwd is not None:
        # cwd is only a validation hint. Filesystem access always uses the server-controlled root.
        if raw_cwd != cwd or not _SAFE_PATH_RE.match(raw_cwd):
            return jsonify({"error": "Invalid cwd parameter"}), 400

    top = int(request.args.get("top", "10"))

    if not has_index():
        return jsonify({"error": "No index found. Run `anote index` in your project."}), 404

    try:
        results = search_index(query=query, top_k=top)
        return jsonify({"results": results, "query": query, "cwd": cwd}), 200
    except Exception as exc:
        print(f"Search error: {exc}")
        return jsonify({"error": "Internal server error"}), 500
