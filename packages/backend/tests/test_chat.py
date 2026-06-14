"""Tests for chat endpoints."""


def test_chat_stream_missing_message(client):
    resp = client.post("/api/chat/stream", json={})
    assert resp.status_code == 400


def test_chat_missing_message(client):
    resp = client.post("/api/chat", json={})
    assert resp.status_code == 400


def test_chat_no_api_key(client):
    resp = client.post("/api/chat", json={"message": "hello"})
    assert resp.status_code in (200, 500)


def test_list_sessions(client):
    resp = client.get("/api/chat/sessions")
    assert resp.status_code == 200
    assert "sessions" in resp.get_json()


def test_create_session(client):
    resp = client.post("/api/chat/sessions")
    assert resp.status_code == 201
    assert "sessionId" in resp.get_json()


def test_get_session(client):
    sid = client.post("/api/chat/sessions").get_json()["sessionId"]
    resp = client.get(f"/api/chat/sessions/{sid}")
    assert resp.status_code == 200
    assert resp.get_json()["sessionId"] == sid


def test_get_session_not_found(client):
    resp = client.get("/api/chat/sessions/does-not-exist")
    assert resp.status_code == 404


def test_delete_session(client):
    sid = client.post("/api/chat/sessions").get_json()["sessionId"]
    resp = client.delete(f"/api/chat/sessions/{sid}")
    assert resp.status_code == 200
