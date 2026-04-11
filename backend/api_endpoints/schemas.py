"""Pydantic v2 request validation schemas for key API endpoints.

Usage
-----
Import the schema class and call ``model_validate`` on the raw JSON body::

    from api_endpoints.schemas import ChatCompletionsRequest

    try:
        req = ChatCompletionsRequest.model_validate(request.get_json(force=True) or {})
    except ValidationError as exc:
        return jsonify({"error": {"message": str(exc), "type": "validation_error"}}), 422

Or use the ``validate_request`` decorator to handle this automatically.
"""

from __future__ import annotations

from functools import wraps
from typing import Any, Union

from flask import jsonify, request
from pydantic import BaseModel, ValidationError


# ---------------------------------------------------------------------------
# Sub-schemas
# ---------------------------------------------------------------------------


class ChatMessageSchema(BaseModel):
    """A single message in a chat conversation."""

    role: str
    content: Union[str, list[Any]]


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


class ChatCompletionsRequest(BaseModel):
    """Body for POST /v1/chat/completions (OpenAI-compatible)."""

    model: str = "gpt-4o"
    messages: list[ChatMessageSchema]
    chat_id: Union[int, None] = None
    stream: bool = False


class PublicChatRequest(BaseModel):
    """Body for POST /public/chat."""

    message: str
    chat_id: int
    model_key: Union[str, None] = None


class QuestionAnswerRequest(BaseModel):
    """Body for POST /v1/question-answer."""

    question: str
    chat_id: int
    model: str = "gpt-4o"


class CreateChatRequest(BaseModel):
    """Body for POST /create-new-chat."""

    chat_type: int = 0
    model_type: int = 0


class EvaluateRequest(BaseModel):
    """Body for POST /public/evaluate."""

    message_id: int


# ---------------------------------------------------------------------------
# Helper decorator
# ---------------------------------------------------------------------------


def validate_request(schema_class: type[BaseModel]):
    """Decorator that validates ``request.get_json()`` against *schema_class*.

    If validation succeeds, the parsed model is stored as ``request.validated``
    so the view function can access it.  On failure a 422 JSON response is
    returned before the view function is called.

    Example::

        @app.route("/example", methods=["POST"])
        @validate_request(ChatCompletionsRequest)
        def example():
            req = request.validated  # type: ChatCompletionsRequest
            ...
    """

    def decorator(fn):  # type: ignore[no-untyped-def]
        @wraps(fn)
        def wrapper(*args, **kwargs):  # type: ignore[no-untyped-def]
            try:
                body = request.get_json(force=True) or {}
                request.validated = schema_class.model_validate(body)  # type: ignore[attr-defined]
            except ValidationError as exc:
                return jsonify(
                    {"error": {"message": str(exc), "type": "validation_error"}}
                ), 422
            return fn(*args, **kwargs)

        return wrapper

    return decorator
