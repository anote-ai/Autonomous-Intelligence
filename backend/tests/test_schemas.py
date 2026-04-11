"""Tests for Pydantic request validation schemas."""

from __future__ import annotations

import pytest
from api_endpoints.schemas import (
    ChatCompletionsRequest,
    ChatMessageSchema,
    CreateChatRequest,
    EvaluateRequest,
    PublicChatRequest,
    QuestionAnswerRequest,
)
from pydantic import ValidationError

# ---------------------------------------------------------------------------
# ChatMessageSchema
# ---------------------------------------------------------------------------

def test_chat_message_str_content() -> None:
    msg = ChatMessageSchema(role="user", content="Hello")
    assert msg.role == "user"
    assert msg.content == "Hello"


def test_chat_message_list_content() -> None:
    msg = ChatMessageSchema(role="user", content=[{"type": "text", "text": "Hi"}])
    assert isinstance(msg.content, list)


def test_chat_message_missing_role() -> None:
    with pytest.raises(ValidationError):
        ChatMessageSchema(content="Hello")


# ---------------------------------------------------------------------------
# ChatCompletionsRequest
# ---------------------------------------------------------------------------

def test_chat_completions_valid() -> None:
    req = ChatCompletionsRequest(
        model="gpt-4o",
        messages=[{"role": "user", "content": "Hello"}],
    )
    assert req.model == "gpt-4o"
    assert len(req.messages) == 1
    assert req.chat_id is None
    assert req.stream is False


def test_chat_completions_default_model() -> None:
    req = ChatCompletionsRequest(messages=[{"role": "user", "content": "Hi"}])
    assert req.model == "gpt-4o"


def test_chat_completions_with_chat_id() -> None:
    req = ChatCompletionsRequest(
        messages=[{"role": "user", "content": "Q"}],
        chat_id=42,
    )
    assert req.chat_id == 42


def test_chat_completions_missing_messages() -> None:
    with pytest.raises(ValidationError):
        ChatCompletionsRequest(model="gpt-4o")


def test_chat_completions_wrong_type_messages() -> None:
    with pytest.raises(ValidationError):
        ChatCompletionsRequest(model="gpt-4o", messages="not-a-list")


# ---------------------------------------------------------------------------
# PublicChatRequest
# ---------------------------------------------------------------------------

def test_public_chat_valid() -> None:
    req = PublicChatRequest(message="Hello", chat_id=1)
    assert req.message == "Hello"
    assert req.chat_id == 1
    assert req.model_key is None


def test_public_chat_missing_message() -> None:
    with pytest.raises(ValidationError):
        PublicChatRequest(chat_id=1)


def test_public_chat_missing_chat_id() -> None:
    with pytest.raises(ValidationError):
        PublicChatRequest(message="Hello")


# ---------------------------------------------------------------------------
# QuestionAnswerRequest
# ---------------------------------------------------------------------------

def test_qa_valid() -> None:
    req = QuestionAnswerRequest(question="What is this?", chat_id=5)
    assert req.question == "What is this?"
    assert req.model == "gpt-4o"


def test_qa_custom_model() -> None:
    req = QuestionAnswerRequest(question="Q?", chat_id=1, model="claude-3-5-haiku-20241022")
    assert req.model == "claude-3-5-haiku-20241022"


# ---------------------------------------------------------------------------
# EvaluateRequest
# ---------------------------------------------------------------------------

def test_evaluate_valid() -> None:
    req = EvaluateRequest(message_id=99)
    assert req.message_id == 99


def test_evaluate_missing_message_id() -> None:
    with pytest.raises(ValidationError):
        EvaluateRequest()


# ---------------------------------------------------------------------------
# CreateChatRequest
# ---------------------------------------------------------------------------

def test_create_chat_defaults() -> None:
    req = CreateChatRequest()
    assert req.chat_type == 0
    assert req.model_type == 0


def test_create_chat_custom() -> None:
    req = CreateChatRequest(chat_type=1, model_type=1)
    assert req.chat_type == 1
