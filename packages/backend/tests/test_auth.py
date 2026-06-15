"""Tests for authentication endpoints."""


def test_register_missing_email(client):
    resp = client.post("/auth/register", json={"password": "password123"})
    assert resp.status_code == 400
    assert "error" in resp.get_json()


def test_register_missing_password(client):
    resp = client.post("/auth/register", json={"email": "test@example.com"})
    assert resp.status_code == 400


def test_register_short_password(client):
    resp = client.post("/auth/register", json={"email": "t@e.com", "password": "short"})
    assert resp.status_code == 400


def test_register_success(client):
    resp = client.post("/auth/register", json={"email": "new@example.com", "password": "password123"})
    # 201 with DB, or 201 with fallback token in test env
    assert resp.status_code == 201
    assert "token" in resp.get_json()


def test_login_missing_credentials(client):
    resp = client.post("/auth/login", json={})
    assert resp.status_code == 400


def test_login_no_db(client):
    resp = client.post("/auth/login", json={"email": "x@x.com", "password": "password123"})
    assert resp.status_code in (401, 503)


def test_me_without_token(client):
    resp = client.get("/auth/me")
    assert resp.status_code == 401


def test_me_with_token(client, auth_headers):
    resp = client.get("/auth/me", headers=auth_headers)
    assert resp.status_code == 200
    assert "userId" in resp.get_json()
