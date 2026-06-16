"""Tests for AnoteClient — uses respx to mock HTTP, no live server needed."""
from __future__ import annotations

import pytest
import respx
import httpx

from anote_sdk import AnoteClient, AnoteError
from anote_sdk.models import ChatResult, HealthResult


BASE = "http://localhost:5000"


@pytest.fixture
def client():
    return AnoteClient(api_key="ant-test", base_url=BASE)


def test_constructor_requires_api_key():
    with pytest.raises(ValueError, match="api_key is required"):
        AnoteClient(api_key="")


def test_health(client):
    with respx.mock:
        respx.get(f"{BASE}/api/v1/health").mock(
            return_value=httpx.Response(200, json={"status": "ok", "version": "1.0.0"})
        )
        result = client.health()
    assert result.status == "ok"


def test_chat(client):
    with respx.mock:
        respx.post(f"{BASE}/api/v1/chat").mock(
            return_value=httpx.Response(200, json={
                "result": "Hello world",
                "usage": {"inputTokens": 10, "outputTokens": 5},
            })
        )
        result = client.chat("say hello")
    assert result.result == "Hello world"
    assert isinstance(result, ChatResult)


def test_chat_with_cwd_and_tools(client):
    with respx.mock:
        route = respx.post(f"{BASE}/api/v1/chat").mock(
            return_value=httpx.Response(200, json={
                "result": "done",
                "usage": {"inputTokens": 1, "outputTokens": 1},
            })
        )
        result = client.chat("fix bug", cwd="/project", tools=["bash"])
    assert result.result == "done"
    assert route.called


def test_error_raises_anote_error(client):
    with respx.mock:
        respx.post(f"{BASE}/api/v1/chat").mock(
            return_value=httpx.Response(401, json={"error": "Unauthorized"})
        )
        with pytest.raises(AnoteError) as exc_info:
            client.chat("hello")
    assert exc_info.value.status == 401


def test_list_sessions_empty(client):
    with respx.mock:
        respx.get(f"{BASE}/api/v1/sessions").mock(
            return_value=httpx.Response(200, json=[])
        )
        sessions = client.list_sessions()
    assert sessions == []


def test_delete_session(client):
    with respx.mock:
        respx.delete(f"{BASE}/api/v1/sessions/abc123").mock(
            return_value=httpx.Response(200, json={"ok": True})
        )
        ok = client.delete_session("abc123")
    assert ok is True


def test_search(client):
    with respx.mock:
        respx.get(f"{BASE}/api/v1/search").mock(
            return_value=httpx.Response(200, json={"results": []})
        )
        results = client.search("hello")
    assert results == []
