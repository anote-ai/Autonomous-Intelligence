"""Chat endpoints — SSE streaming agent chat and session management."""
from __future__ import annotations

import os
import uuid
from collections.abc import Generator

from flask import Blueprint, Response, jsonify, request, stream_with_context

from services.streaming import stream_agent_response, stream_llm_response

chat_bp = Blueprint("chat", __name__, url_prefix="/api/chat")

_sessions: dict[str, list[dict]] = {}


@chat_bp.post("/stream")
def chat_stream() -> Response:
    """SSE endpoint: stream an agent response to the client."""
    data = request.get_json(silent=True) or {}
    message: str = data.get("message", "").strip()
    cwd: str = data.get("cwd", os.getcwd())
    model: str = data.get("model", "claude-sonnet-4-6")

    if not message:
        return jsonify({"error": "message is required"}), 400  # type: ignore[return-value]

    def generate() -> Generator[str, None, None]:
        yield from stream_agent_response(message=message, cwd=cwd, model=model)

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@chat_bp.post("")
def chat() -> tuple:
    """Non-streaming chat completion."""
    data = request.get_json(silent=True) or {}
    message: str = data.get("message", "").strip()
    model: str = data.get("model", "claude-sonnet-4-6")
    history: list[dict] = data.get("history", [])

    if not message:
        return jsonify({"error": "message is required"}), 400

    try:
        response_text = stream_llm_response(message=message, model=model, history=history)
        return jsonify({"response": response_text, "model": model}), 200
    except Exception as exc:
        print(f"Chat error: {exc}")
        return jsonify({"error": "Internal server error"}), 500


@chat_bp.get("/sessions")
def list_sessions() -> tuple:
    return jsonify({"sessions": list(_sessions.keys())}), 200


@chat_bp.post("/sessions")
def create_session() -> tuple:
    session_id = str(uuid.uuid4())
    _sessions[session_id] = []
    return jsonify({"sessionId": session_id}), 201


@chat_bp.get("/sessions/<session_id>")
def get_session(session_id: str) -> tuple:
    if session_id not in _sessions:
        return jsonify({"error": "Session not found"}), 404
    return jsonify({"sessionId": session_id, "messages": _sessions[session_id]}), 200


@chat_bp.delete("/sessions/<session_id>")
def delete_session(session_id: str) -> tuple:
    _sessions.pop(session_id, None)
    return jsonify({"deleted": True}), 200
