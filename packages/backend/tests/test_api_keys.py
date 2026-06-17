"""Tests for API key management and usage endpoints (issue #221)."""
from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import bcrypt


def test_create_api_key_requires_auth(client):
    resp = client.post("/api/user/api-keys")
    assert resp.status_code == 401


def test_create_and_list_api_key(client, auth_headers):
    resp = client.post("/api/user/api-keys", headers=auth_headers)
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["key"].startswith("sk-ai-")
    assert len(body["key"]) == len("sk-ai-") + 32
    prefix = body["prefix"]

    list_resp = client.get("/api/user/api-keys", headers=auth_headers)
    assert list_resp.status_code == 200
    keys = list_resp.get_json()["keys"]
    assert any(k["prefix"] == prefix for k in keys)


def test_delete_api_key(client, auth_headers):
    create_resp = client.post("/api/user/api-keys", headers=auth_headers)
    prefix = create_resp.get_json()["prefix"]

    delete_resp = client.delete(f"/api/user/api-keys/{prefix}", headers=auth_headers)
    assert delete_resp.status_code == 200
    assert delete_resp.get_json()["deleted"] is True


def test_delete_unknown_api_key(client, auth_headers):
    resp = client.delete("/api/user/api-keys/sk-ai-nope", headers=auth_headers)
    assert resp.status_code == 404


def test_get_usage_requires_auth(client):
    resp = client.get("/api/user/usage")
    assert resp.status_code == 401


def test_get_usage_with_auth(client, auth_headers):
    resp = client.get("/api/user/usage", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.get_json()
    assert "request_count" in body
    assert "total_credits_used" in body


def test_require_api_key_missing_header(app):
    from middleware.auth import require_api_key

    @require_api_key
    def dummy():
        return "ok"

    with app.test_request_context():
        resp = dummy()
        assert resp[1] == 401


def test_require_api_key_invalid_format(app):
    from middleware.auth import require_api_key

    @require_api_key
    def dummy():
        return "ok"

    with app.test_request_context(headers={"Authorization": "Bearer not-a-key"}):
        resp = dummy()
        assert resp[1] == 401


def test_require_api_key_no_db(app):
    from middleware.auth import require_api_key

    @require_api_key
    def dummy():
        return "ok"

    with app.test_request_context(headers={"Authorization": "Bearer sk-ai-" + "a" * 32}):
        resp = dummy()
        assert resp[1] in (401, 503)


def _mock_cnx_for_keys(candidates):
    cnx = MagicMock()
    cursor = MagicMock()
    cursor.fetchall.return_value = candidates
    cnx.cursor.return_value = cursor
    return cnx


def test_require_api_key_valid(app):
    from middleware.auth import require_api_key

    plaintext = "sk-ai-" + "b" * 32
    key_hash = bcrypt.hashpw(plaintext.encode(), bcrypt.gensalt()).decode()
    candidates = [{"id": 1, "user_id": 7, "key_hash": key_hash,
                   "key_prefix": plaintext[:12], "rate_limit_per_minute": 60,
                   "expires_at": None}]

    @require_api_key
    def dummy():
        from flask import g
        return {"user_id": g.user_id, "api_key_id": g.api_key_id}, 200

    with patch("database.db.get_connection", return_value=_mock_cnx_for_keys(candidates)):
        with app.test_request_context(headers={"Authorization": f"Bearer {plaintext}"}):
            resp = dummy()
            assert resp[1] == 200
            assert resp[0]["user_id"] == 7
            assert resp[0]["api_key_id"] == 1


def test_require_api_key_expired(app):
    from middleware.auth import require_api_key

    plaintext = "sk-ai-" + "c" * 32
    key_hash = bcrypt.hashpw(plaintext.encode(), bcrypt.gensalt()).decode()
    candidates = [{"id": 2, "user_id": 8, "key_hash": key_hash,
                   "key_prefix": plaintext[:12], "rate_limit_per_minute": 60,
                   "expires_at": datetime.utcnow() - timedelta(days=1)}]

    @require_api_key
    def dummy():
        return "ok", 200

    with patch("database.db.get_connection", return_value=_mock_cnx_for_keys(candidates)):
        with app.test_request_context(headers={"Authorization": f"Bearer {plaintext}"}):
            resp = dummy()
            assert resp[1] == 401


def test_require_api_key_wrong_key(app):
    from middleware.auth import require_api_key

    plaintext = "sk-ai-" + "d" * 32
    other_hash = bcrypt.hashpw(("sk-ai-" + "e" * 32).encode(), bcrypt.gensalt()).decode()
    candidates = [{"id": 3, "user_id": 9, "key_hash": other_hash,
                   "key_prefix": "sk-ai-eeeeee", "rate_limit_per_minute": 60,
                   "expires_at": None}]

    @require_api_key
    def dummy():
        return "ok", 200

    with patch("database.db.get_connection", return_value=_mock_cnx_for_keys(candidates)):
        with app.test_request_context(headers={"Authorization": f"Bearer {plaintext}"}):
            resp = dummy()
            assert resp[1] == 401


def test_require_api_key_rate_limited(app):
    from middleware.auth import _rate_limiter, require_api_key

    plaintext = "sk-ai-" + "f" * 32
    key_hash = bcrypt.hashpw(plaintext.encode(), bcrypt.gensalt()).decode()
    candidates = [{"id": 4, "user_id": 10, "key_hash": key_hash,
                   "key_prefix": plaintext[:12], "rate_limit_per_minute": 60,
                   "expires_at": None}]

    @require_api_key
    def dummy():
        return "ok", 200

    with patch("database.db.get_connection", return_value=_mock_cnx_for_keys(candidates)):
        with app.test_request_context(headers={"Authorization": f"Bearer {plaintext}"}):
            for _ in range(60):
                _rate_limiter.is_allowed("key:4")
            resp = dummy()
            assert resp[1] == 429


def test_db_api_key_helpers():
    from database import db

    cnx = MagicMock()
    cursor = MagicMock()
    cursor.lastrowid = 42
    cursor.rowcount = 1
    cursor.fetchone.return_value = {"request_count": 3, "total_credits_used": 9}
    cursor.fetchall.return_value = [{"id": 1, "key_prefix": "sk-ai-aaaaaa"}]
    cnx.cursor.return_value = cursor

    assert db.create_api_key(cnx, 1, "hash", "sk-ai-aaaaaa") == 42
    assert db.list_api_keys_for_user(cnx, 1) == [{"id": 1, "key_prefix": "sk-ai-aaaaaa"}]
    assert db.get_active_api_keys(cnx) == [{"id": 1, "key_prefix": "sk-ai-aaaaaa"}]
    assert db.revoke_api_key(cnx, 1, 1) is True
    db.touch_api_key(cnx, 1)
    db.log_api_usage(cnx, 1, 1, "/api/chat", 200, credits_used=2)
    assert db.get_usage_summary(cnx, 1) == {"request_count": 3, "total_credits_used": 9}
    assert db.deduct_credits(cnx, 1, 5) is True
    db.add_credits(cnx, 1, 5)
