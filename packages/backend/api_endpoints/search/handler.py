"""Semantic search endpoint."""
from __future__ import annotations

import os

from flask import Blueprint, jsonify, request

from services.search import has_index, search_index

search_bp = Blueprint("search", __name__, url_prefix="/api/search")


@search_bp.get("")
def search() -> tuple:
    """Search the codebase index."""
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"error": "q parameter is required"}), 400

    cwd = request.args.get("cwd", os.getcwd())
    top = int(request.args.get("top", "10"))

    if not has_index(cwd):
        return jsonify({"error": "No index found. Run `anote index` in your project."}), 404

    try:
        results = search_index(query=query, cwd=cwd, top_k=top)
        return jsonify({"results": results, "query": query, "cwd": cwd}), 200
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500
