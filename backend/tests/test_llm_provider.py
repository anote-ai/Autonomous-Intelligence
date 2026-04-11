"""Tests for the centralized LLM provider module."""
import os
from unittest.mock import MagicMock, patch

from services.llm_provider import (
    DEFAULT_ANTHROPIC_MODEL,
    DEFAULT_OPENAI_MODEL,
    LLMProvider,
    get_anthropic_client,
    get_chat_completion,
    get_openai_client,
    resolve_model,
)


def test_default_models_defined():
    assert DEFAULT_OPENAI_MODEL == "gpt-4o"
    assert DEFAULT_ANTHROPIC_MODEL == "claude-3-5-haiku-20241022"


def test_llm_provider_enum_values():
    assert LLMProvider.OPENAI.value == "openai"
    assert LLMProvider.ANTHROPIC.value == "anthropic"
    assert LLMProvider.LOCAL.value == "local"


def test_resolve_model_openai():
    assert resolve_model(0) == DEFAULT_OPENAI_MODEL


def test_resolve_model_anthropic():
    assert resolve_model(1) == DEFAULT_ANTHROPIC_MODEL


def test_resolve_model_unknown_defaults_to_openai():
    assert resolve_model(99) == DEFAULT_OPENAI_MODEL


def test_get_openai_client_returns_client():
    with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
        client = get_openai_client()
        assert client is not None


def test_get_anthropic_client_returns_client():
    with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
        client = get_anthropic_client()
        assert client is not None


def test_get_chat_completion_openai():
    mock_resp = MagicMock()
    mock_resp.choices[0].message.content = "Hello!"

    with patch("services.llm_provider.get_openai_client") as mock_factory:
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_resp
        mock_factory.return_value = mock_client

        result = get_chat_completion(
            messages=[{"role": "user", "content": "Hi"}],
            model="gpt-4o",
        )
        assert result == "Hello!"
        mock_client.chat.completions.create.assert_called_once()


def test_get_chat_completion_anthropic():
    mock_resp = MagicMock()
    mock_resp.content = [MagicMock(text="Bonjour!")]

    with patch("services.llm_provider.get_anthropic_client") as mock_factory:
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_resp
        mock_factory.return_value = mock_client

        result = get_chat_completion(
            messages=[{"role": "user", "content": "Hi"}],
            model="claude-3-5-haiku-20241022",
        )
        assert result == "Bonjour!"
        mock_client.messages.create.assert_called_once()


def test_get_chat_completion_strips_system_from_anthropic_messages():
    mock_resp = MagicMock()
    mock_resp.content = [MagicMock(text="ok")]

    with patch("services.llm_provider.get_anthropic_client") as mock_factory:
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_resp
        mock_factory.return_value = mock_client

        get_chat_completion(
            messages=[
                {"role": "system", "content": "You are helpful"},
                {"role": "user", "content": "Hi"},
            ],
            model="claude-3-5-haiku-20241022",
        )
        call_kwargs = mock_client.messages.create.call_args.kwargs
        # System messages must NOT appear in the messages list for Anthropic
        for msg in call_kwargs["messages"]:
            assert msg["role"] != "system"
