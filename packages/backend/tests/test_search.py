"""Tests for search, user, and misc endpoints."""
import json


def test_search_missing_query(client):
    resp = client.get("/api/search")
    assert resp.status_code == 400


def test_search_no_index(client, tmp_path):
    resp = client.get(f"/api/search?q=test&cwd={tmp_path}")
    assert resp.status_code == 404


def test_search_with_index(client, tmp_path):
    idx_dir = tmp_path / ".anote" / "index"
    idx_dir.mkdir(parents=True)
    chunks = [
        {"file": "src/auth.ts", "startLine": 1, "endLine": 20, "content": "JWT authentication middleware"},
        {"file": "src/db.ts", "startLine": 1, "endLine": 30, "content": "MySQL database connection pool"},
    ]
    (idx_dir / "chunks.json").write_text(json.dumps(chunks))
    resp = client.get(f"/api/search?q=authentication&cwd={tmp_path}&top=5")
    assert resp.status_code == 200
    assert "results" in resp.get_json()


def test_user_profile(client, auth_headers):
    resp = client.get("/api/user/profile", headers=auth_headers)
    assert resp.status_code == 200
    assert "userId" in resp.get_json()


def test_user_update_profile(client, auth_headers):
    resp = client.put("/api/user/profile", json={"name": "New Name"}, headers=auth_headers)
    assert resp.status_code == 200


def test_api_keys_list(client, auth_headers):
    resp = client.get("/api/user/api-keys", headers=auth_headers)
    assert resp.status_code == 200
    assert "keys" in resp.get_json()


def test_api_keys_create(client, auth_headers):
    resp = client.post("/api/user/api-keys", headers=auth_headers)
    assert resp.status_code == 201
    assert resp.get_json()["key"].startswith("ak-")


def test_api_keys_delete_not_found(client, auth_headers):
    resp = client.delete("/api/user/api-keys/nonexistent-prefix", headers=auth_headers)
    assert resp.status_code == 404


def test_workspaces_non_hosted(client):
    resp = client.get("/api/workspaces")
    assert resp.status_code == 501


def test_payments_no_stripe(client):
    resp = client.post("/api/payments/checkout", json={"priceId": "price_test"})
    assert resp.status_code == 503


def test_payments_portal_no_stripe(client):
    resp = client.post("/api/payments/portal", json={"customerId": "cus_test"})
    assert resp.status_code == 503


def test_rate_limiter():
    from middleware.rate_limit import RateLimiter
    limiter = RateLimiter(max_calls=3, period=60.0)
    assert limiter.is_allowed("user1") is True
    assert limiter.is_allowed("user1") is True
    assert limiter.is_allowed("user1") is True
    assert limiter.is_allowed("user1") is False
    assert limiter.is_allowed("user2") is True


def test_llm_provider_detection():
    from services.llm import get_provider_for_model
    assert get_provider_for_model("claude-sonnet-4-6") == "anthropic"
    assert get_provider_for_model("gpt-4o") == "openai"
    assert get_provider_for_model("gemini-2.0-flash") == "google"
    assert get_provider_for_model("llama3") == "ollama"


def test_search_service_no_index(tmp_path):
    from services.search import has_index, search_index
    assert has_index(str(tmp_path)) is False
    assert search_index("query", str(tmp_path)) == []


def test_rag_chunk_text():
    from services.rag import _chunk_text
    chunks = _chunk_text("a" * 2500, chunk_size=1000, overlap=100)
    assert len(chunks) > 1


def test_rag_empty_text():
    from services.rag import _chunk_text
    assert _chunk_text("") == []
    assert _chunk_text("   ") == []
