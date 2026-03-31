"""Centralized LLM provider configuration and factory utilities.

This module is the single source of truth for all LLM client construction and
model dispatch.  Every part of the backend that needs to call OpenAI or
Anthropic should use the helpers defined here instead of creating clients
inline.
"""

from __future__ import annotations

import os
from enum import Enum
from typing import Any

import anthropic
import openai

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_OPENAI_MODEL: str = "gpt-4o"
DEFAULT_ANTHROPIC_MODEL: str = "claude-3-5-haiku-20241022"


# ---------------------------------------------------------------------------
# Provider enum
# ---------------------------------------------------------------------------


class LLMProvider(Enum):
    """Supported LLM providers."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    LOCAL = "local"
    OLLAMA = "ollama"


# ---------------------------------------------------------------------------
# Client factories
# ---------------------------------------------------------------------------


def get_openai_client() -> openai.OpenAI:
    """Return a configured :class:`openai.OpenAI` instance.

    Reads ``OPENAI_API_KEY`` from the environment.  The base URL defaults to
    the Docker-internal Ollama proxy so that local models work transparently
    when the variable ``OPENAI_BASE_URL`` is set; otherwise the official
    OpenAI endpoint is used.
    """
    api_key = os.getenv("OPENAI_API_KEY", "")
    base_url = os.getenv("OPENAI_BASE_URL", "http://host.docker.internal:11434/v1")
    return openai.OpenAI(api_key=api_key, base_url=base_url)


def get_anthropic_client() -> anthropic.Anthropic:
    """Return a configured :class:`anthropic.Anthropic` instance.

    Reads ``ANTHROPIC_API_KEY`` from the environment.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    return anthropic.Anthropic(api_key=api_key)


# ---------------------------------------------------------------------------
# Model resolution helper
# ---------------------------------------------------------------------------


def resolve_model(model_type_int: int) -> str:
    """Translate the legacy ``model_type`` integer flag to a model name.

    Args:
        model_type_int: ``0`` for OpenAI/local, ``1`` for Anthropic.

    Returns:
        The default model name string for the given provider.
    """
    if model_type_int == 1:
        return DEFAULT_ANTHROPIC_MODEL
    return DEFAULT_OPENAI_MODEL


# ---------------------------------------------------------------------------
# Unified completion helper
# ---------------------------------------------------------------------------


def get_chat_completion(
    messages: list[dict[str, Any]],
    model: str,
    system_prompt: str | None = None,
    max_tokens: int = 1024,
) -> str:
    """Dispatch a chat completion request to the correct provider.

    The provider is inferred from the *model* name: models whose name starts
    with ``"claude"`` are routed to Anthropic; everything else goes to OpenAI.

    Args:
        messages: List of ``{"role": ..., "content": ...}`` dicts.  For
            Anthropic these must not contain ``"system"`` entries – pass a
            system message via *system_prompt* instead.
        model: Model identifier string.
        system_prompt: Optional system prompt text.  When provided it is
            forwarded as the ``system`` parameter for Anthropic requests and
            prepended as a ``{"role": "system"}`` message for OpenAI requests.
        max_tokens: Maximum number of tokens in the completion (Anthropic only;
            OpenAI uses its own default when this is not set).

    Returns:
        The text content of the first choice/message returned by the provider.
    """
    is_anthropic = model.startswith("claude")

    if is_anthropic:
        client = get_anthropic_client()
        # Filter out any system messages that may have been inadvertently
        # included; pass them through the dedicated system parameter.
        system_msgs = [m["content"] for m in messages if m.get("role") == "system"]
        conv_msgs = [m for m in messages if m.get("role") != "system"]
        if system_prompt:
            effective_system = system_prompt
        elif system_msgs:
            effective_system = "\n".join(system_msgs)
        else:
            effective_system = "You are a helpful assistant."

        resp = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=effective_system,
            messages=conv_msgs,
        )
        return resp.content[0].text  # type: ignore[index]

    else:
        client = get_openai_client()
        openai_messages: list[dict[str, Any]] = []
        if system_prompt:
            openai_messages.append({"role": "system", "content": system_prompt})
        openai_messages.extend(messages)
        resp = client.chat.completions.create(
            model=model,
            messages=openai_messages,  # type: ignore[arg-type]
        )
        return resp.choices[0].message.content or ""
