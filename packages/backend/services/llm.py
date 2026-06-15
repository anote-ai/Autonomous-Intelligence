"""LLM provider abstraction — Anthropic, OpenAI, Gemini, Ollama."""
from __future__ import annotations

import os


def get_provider_for_model(model: str) -> str:
    if model.startswith("claude"):
        return "anthropic"
    if model.startswith("gpt") or model.startswith("o1") or model.startswith("o3"):
        return "openai"
    if model.startswith("gemini"):
        return "google"
    return "ollama"


def complete(
    message: str,
    model: str = "claude-sonnet-4-6",
    system: str | None = None,
    max_tokens: int = 4096,
) -> str:
    """Single-turn completion across any supported provider."""
    provider = get_provider_for_model(model)
    if provider == "anthropic":
        import anthropic
        client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        kwargs: dict = {"model": model, "max_tokens": max_tokens, "messages": [{"role": "user", "content": message}]}  # type: ignore[type-arg]
        if system:
            kwargs["system"] = system
        response = client.messages.create(**kwargs)  # type: ignore[arg-type]
        block = response.content[0] if response.content else None
        return block.text if block and hasattr(block, "text") else ""  # type: ignore[union-attr]
    if provider == "openai":
        from openai import OpenAI
        client_oa = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
        msgs: list[dict] = []  # type: ignore[type-arg]
        if system:
            msgs.append({"role": "system", "content": system})
        msgs.append({"role": "user", "content": message})
        response_oa = client_oa.chat.completions.create(model=model, messages=msgs, max_tokens=max_tokens)  # type: ignore[arg-type]
        choice = response_oa.choices[0] if response_oa.choices else None
        return choice.message.content or "" if choice else ""
    if provider == "google":
        import google.generativeai as genai
        genai.configure(api_key=os.environ["GEMINI_API_KEY"])
        m = genai.GenerativeModel(model)
        return m.generate_content(message).text or ""
    import requests  # type: ignore[import-untyped]
    base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
    resp = requests.post(f"{base_url}/api/generate", json={"model": model, "prompt": message, "stream": False}, timeout=120)
    resp.raise_for_status()
    return resp.json().get("response", "")
