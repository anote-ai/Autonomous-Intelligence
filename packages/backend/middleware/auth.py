"""JWT auth middleware."""
from __future__ import annotations

import functools
from typing import Callable

from flask import jsonify
from flask_jwt_extended import verify_jwt_in_request


def require_auth(fn: Callable) -> Callable:
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):  # type: ignore[no-untyped-def]
        try:
            verify_jwt_in_request()
        except Exception as exc:
            return jsonify({"error": "Unauthorized", "detail": str(exc)}), 401
        return fn(*args, **kwargs)
    return wrapper
