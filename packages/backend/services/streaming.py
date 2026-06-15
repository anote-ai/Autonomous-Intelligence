"""SSE streaming helpers for agent and LLM responses."""
from __future__ import annotations

import json
import os
from collections.abc import Generator


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def stream_agent_response(
    message: str,
    cwd: str = ".",
    model: str = "claude-sonnet-4-6",
) -> Generator[str, None, None]:
    """Stream an agent response via SSE using the Anthropic SDK."""
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        yield _sse("error", {"message": "ANTHROPIC_API_KEY not configured"})
        return
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        with client.messages.stream(
            model=model,
            max_tokens=4096,
            messages=[{"role": "user", "content": message}],
        ) as stream:
            for text in stream.text_stream:
                yield _sse("text", {"text": text})
        yield _sse("done", {})
    except Exception as exc:
        yield _sse("error", {"message": str(exc)})


def stream_llm_response(
    message: str,
    model: str = "claude-sonnet-4-6",
    history: list[dict] | None = None,
) -> str:
    """Non-streaming LLM completion."""
    history = history or []
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not configured")
    import anthropic
    client = anthropic.Anthropic(api_key=api_key)
    messages = [*history, {"role": "user", "content": message}]
    response = client.messages.create(model=model, max_tokens=4096, messages=messages)
    return response.content[0].text if response.content else ""
