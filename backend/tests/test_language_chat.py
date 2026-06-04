from __future__ import annotations

from typing import Any

from api_endpoints.languages import language_chat


def test_language_chat_openai_client_is_lazy(monkeypatch: Any) -> None:
    created_clients: list[dict[str, Any]] = []

    class FakeOpenAI:
        def __init__(self, **kwargs: Any) -> None:
            created_clients.append(kwargs)

    monkeypatch.setattr(language_chat, "client", None)
    monkeypatch.setattr(language_chat, "OpenAI", FakeOpenAI)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    assert language_chat.client is None

    client = language_chat.get_client()

    assert client is language_chat.client
    assert created_clients == [{"api_key": "test-key"}]
