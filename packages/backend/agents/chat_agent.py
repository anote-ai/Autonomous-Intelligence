"""General-purpose LangChain chat agent."""
from __future__ import annotations

import os
from typing import Any


def run_chat_agent(
    message: str,
    history: list[dict] | None = None,
    model: str = "claude-sonnet-4-6",
) -> str:
    """Run a chat agent with conversation history."""
    history = history or []
    try:
        from langchain_anthropic import ChatAnthropic
        from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
        llm = ChatAnthropic(model=model, api_key=os.environ.get("ANTHROPIC_API_KEY", ""))
        messages: list[Any] = [SystemMessage(content="You are Anote, a helpful AI assistant.")]
        for h in history:
            if h.get("role") == "user":
                messages.append(HumanMessage(content=h["content"]))
            elif h.get("role") == "assistant":
                messages.append(AIMessage(content=h["content"]))
        messages.append(HumanMessage(content=message))
        response = llm.invoke(messages)
        return str(response.content)
    except Exception as exc:
        return f"Error: {exc}"
