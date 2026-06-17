"""JWT and API-key auth middleware."""
from __future__ import annotations

import functools
from collections.abc import Callable
from datetime import datetime

import bcrypt
from flask import g, jsonify, request
from flask_jwt_extended import verify_jwt_in_request

from middleware.rate_limit import RateLimiter

_rate_limiter = RateLimiter(max_calls=60, period=60.0)


def require_auth(fn: Callable) -> Callable:
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):  # type: ignore[no-untyped-def]
        try:
            verify_jwt_in_request()
        except Exception:
            return jsonify({"error": "Unauthorized"}), 401
        return fn(*args, **kwargs)
    return wrapper


def require_api_key(fn: Callable) -> Callable:
    """Authenticate requests via the `Authorization: Bearer sk-ai-...` header.

    Looks up the key against all active API keys (comparing bcrypt hashes),
    enforces expiry and a per-key rate limit, and stamps `g.api_key_id` /
    `g.user_id` for downstream usage logging.
    """

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):  # type: ignore[no-untyped-def]
        header = request.headers.get("Authorization", "")
        if not header.startswith("Bearer ") or not header[7:].startswith("sk-ai-"):
            return jsonify({"error": "Missing or invalid API key"}), 401
        plaintext = header[7:]

        try:
            from database.db import get_active_api_keys, get_connection
            cnx = get_connection()
            candidates = get_active_api_keys(cnx)
            cnx.close()
        except Exception:
            return jsonify({"error": "API key authentication unavailable"}), 503

        matched = None
        for candidate in candidates:
            if bcrypt.checkpw(plaintext.encode(), candidate["key_hash"].encode()):
                matched = candidate
                break

        if not matched:
            return jsonify({"error": "Invalid API key"}), 401

        if matched.get("expires_at") and matched["expires_at"] < datetime.utcnow():
            return jsonify({"error": "API key expired"}), 401

        if not _rate_limiter.is_allowed(f"key:{matched['id']}"):
            return jsonify({"error": "Rate limit exceeded"}), 429

        g.api_key_id = matched["id"]
        g.user_id = matched["user_id"]
        return fn(*args, **kwargs)

    return wrapper
