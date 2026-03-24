"""Autonomous document agent using native provider tool_use + extended thinking.

The agent runs a proper agentic loop:
  1. Build a message with the user query (+ any media descriptions)
  2. Call the LLM with tool definitions and optional extended thinking
  3. Execute any tool_use blocks, collect results
  4. Feed tool results back and repeat until the model produces a final answer
  5. Persist the AI message + sources and yield a completion event

Supported providers
-------------------
- Anthropic (model_type=1): native tool_use, extended thinking on claude-3-7+
- OpenAI (model_type=0): function-calling agentic loop via openai SDK

Streaming: yields dicts compatible with the existing SSE protocol so the
frontend requires no changes.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
import traceback
from typing import Any, Generator, Optional

from agents.config import AgentConfig
from api_endpoints.financeGPT.chatbot_endpoints import (
    add_message_to_db,
    add_sources_to_db,
    get_relevant_chunks,
    retrieve_docs_from_db,
    retrieve_message_from_db,
)

# ---------------------------------------------------------------------------
# Shared tool schema (provider-agnostic)
# ---------------------------------------------------------------------------

_TOOL_SPECS = [
    {
        "name": "retrieve_documents",
        "description": (
            "Semantic search over the user's uploaded documents. "
            "Use this whenever the query could be answered by the documents. "
            "Returns the most relevant chunks with their source file names. "
            "Always prefer this over general knowledge when documents are available."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query to find relevant document chunks.",
                },
                "k": {
                    "type": "integer",
                    "description": "Number of chunks to retrieve (1–10, default 6).",
                    "default": 6,
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "list_documents",
        "description": "List all documents the user has uploaded in this chat session.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "get_chat_history",
        "description": (
            "Retrieve recent messages from this conversation. "
            "Useful for understanding what has already been discussed."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Number of recent message pairs to fetch (default 5).",
                    "default": 5,
                }
            },
            "required": [],
        },
    },
    {
        "name": "run_python",
        "description": (
            "Execute a Python code snippet and return its stdout/stderr. "
            "Use for data analysis, calculations, or any task where running "
            "real code gives a more reliable answer than pure reasoning. "
            "Standard library, numpy, pandas, and matplotlib are available."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Python code to execute. Use print() to output results.",
                }
            },
            "required": ["code"],
        },
    },
]

_SYSTEM_PROMPT = """\
You are Autonomous Intelligence — a powerful AI agent that reasons step-by-step \
and uses tools to give precise, well-grounded answers.

Guidelines:
- Always start by checking what documents are available before answering.
- Use retrieve_documents to ground your answer in the user's documents.
- Use list_documents to see what files are uploaded.
- Use get_chat_history only when the query references earlier conversation.
- Use run_python for calculations, data analysis, or tasks where code is \
  more reliable than text reasoning.
- Cite document sources (filename) when quoting from documents.
- If documents do not contain the answer, say so and answer from general \
  knowledge.
- Be thorough but concise. Do not pad with filler text.
"""


# ---------------------------------------------------------------------------
# Anthropic tool format
# ---------------------------------------------------------------------------

def _anthropic_tools() -> list[dict]:
    return [
        {
            "name": spec["name"],
            "description": spec["description"],
            "input_schema": spec["parameters"],
        }
        for spec in _TOOL_SPECS
    ]


# ---------------------------------------------------------------------------
# OpenAI tool format
# ---------------------------------------------------------------------------

def _openai_tools() -> list[dict]:
    return [
        {
            "type": "function",
            "function": {
                "name": spec["name"],
                "description": spec["description"],
                "parameters": spec["parameters"],
            },
        }
        for spec in _TOOL_SPECS
    ]


# ---------------------------------------------------------------------------
# Main agent class
# ---------------------------------------------------------------------------

class AutonomousDocumentAgent:
    """Autonomous agent that loops over tool calls until the model is done."""

    def __init__(self, model_type: int = 0, model_key: str = ""):
        self.model_type = model_type
        self.model_key = model_key

    # ------------------------------------------------------------------
    # Public entry points
    # ------------------------------------------------------------------

    def process_query_stream(
        self,
        query: str,
        chat_id: int,
        user_email: str,
        media_attachments: Optional[list] = None,
    ) -> Generator[dict, None, None]:
        """Yield SSE-compatible event dicts for an authenticated user query."""
        yield from self._run(
            query=query,
            chat_id=chat_id,
            user_email=user_email,
            is_guest=False,
            media_attachments=media_attachments or [],
        )

    def process_query_stream_guest(self, query: str) -> Generator[dict, None, None]:
        """Minimal streaming for guest users (no document access)."""
        yield {"type": "start", "message": "Processing your query...", "timestamp": _ts()}
        try:
            if self.model_type == 1:
                answer = _guest_anthropic(query, self.model_key)
            else:
                answer = _guest_openai(query, self.model_key)
        except Exception as exc:
            answer = f"I'm sorry, I encountered an error: {exc}"
        yield {
            "type": "complete",
            "answer": answer,
            "sources": [],
            "thought": "Answered from general knowledge (guest mode).",
            "timestamp": _ts(),
        }

    # ------------------------------------------------------------------
    # Core agentic loop dispatcher
    # ------------------------------------------------------------------

    def _run(
        self,
        query: str,
        chat_id: int,
        user_email: str,
        is_guest: bool,
        media_attachments: list,
    ) -> Generator[dict, None, None]:
        yield {"type": "start", "message": "Processing your query...", "timestamp": _ts()}

        # Persist user message
        add_message_to_db(query, chat_id, 1)

        if self.model_type == 1:
            yield from self._run_anthropic(query, chat_id, user_email, media_attachments)
        else:
            yield from self._run_openai(query, chat_id, user_email, media_attachments)

    # ------------------------------------------------------------------
    # Anthropic agentic loop
    # ------------------------------------------------------------------

    def _run_anthropic(
        self,
        query: str,
        chat_id: int,
        user_email: str,
        media_attachments: list,
    ) -> Generator[dict, None, None]:
        from anthropic import Anthropic

        api_key = self.model_key or os.getenv("ANTHROPIC_API_KEY")
        client = Anthropic(api_key=api_key)
        model = os.getenv("ANTHROPIC_AGENT_MODEL", AgentConfig.ANTHROPIC_VISION_MODEL)

        # Build initial user content
        user_content = _build_user_content_anthropic(query, media_attachments)
        messages: list[dict] = [{"role": "user", "content": user_content}]

        sources_found: list[dict] = []
        final_answer = ""
        final_thought = ""

        for iteration in range(AgentConfig.AGENT_MAX_ITERATIONS):
            # Build API kwargs
            api_kwargs: dict[str, Any] = {
                "model": model,
                "max_tokens": 4096,
                "system": _SYSTEM_PROMPT,
                "tools": _anthropic_tools(),
                "messages": messages,
            }
            # Extended thinking for claude-3-7+ models
            supports_thinking = "claude-3-7" in model or "claude-3-5" in model
            if supports_thinking:
                try:
                    api_kwargs["thinking"] = {
                        "type": "enabled",
                        "budget_tokens": 8000,
                    }
                    api_kwargs["max_tokens"] = 12000
                except Exception:
                    pass

            try:
                response = client.messages.create(**api_kwargs)
            except Exception as exc:
                # Retry without thinking if it caused the error
                if "thinking" in api_kwargs:
                    del api_kwargs["thinking"]
                    api_kwargs["max_tokens"] = 4096
                    try:
                        response = client.messages.create(**api_kwargs)
                    except Exception as exc2:
                        yield {"type": "error", "message": str(exc2), "timestamp": _ts()}
                        final_answer = f"Error: {exc2}"
                        break
                else:
                    yield {"type": "error", "message": str(exc), "timestamp": _ts()}
                    final_answer = f"Error: {exc}"
                    break

            # Stream thinking and text blocks
            has_tool_calls = False
            tool_calls: list[dict] = []

            for block in response.content:
                btype = getattr(block, "type", None)
                if btype == "thinking":
                    thought_text = getattr(block, "thinking", "")
                    final_thought = thought_text[:600]
                    yield {
                        "type": "thinking",
                        "content": thought_text,
                        "timestamp": _ts(),
                    }
                    yield {
                        "type": "llm_reasoning",
                        "thought": thought_text[:300],
                        "raw_output": thought_text[:500],
                        "timestamp": _ts(),
                    }
                elif btype == "text":
                    final_answer += getattr(block, "text", "")
                elif btype == "tool_use":
                    has_tool_calls = True
                    tool_calls.append({
                        "id": block.id,
                        "name": block.name,
                        "input": block.input,
                    })

            if not has_tool_calls:
                if not final_thought:
                    final_thought = "Reasoned and composed the final answer."
                break

            # Append assistant turn and execute tools
            messages.append({"role": "assistant", "content": response.content})
            tool_results = []

            for tc in tool_calls:
                yield {
                    "type": "tool_start",
                    "tool_name": tc["name"],
                    "input": str(tc["input"])[:200],
                    "timestamp": _ts(),
                }
                output, docs = _execute_tool(tc["name"], tc["input"], chat_id, user_email)
                sources_found.extend(docs)
                yield {
                    "type": "tool_end",
                    "tool_name": tc["name"],
                    "output": output[:300] + "…" if len(output) > 300 else output,
                    "timestamp": _ts(),
                }
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tc["id"],
                    "content": output,
                })

            messages.append({"role": "user", "content": tool_results})

        else:
            if not final_answer:
                final_answer = (
                    "I reached the maximum reasoning steps. Here is what I found."
                )

        yield from _finalize(final_answer, final_thought, sources_found, chat_id)

    # ------------------------------------------------------------------
    # OpenAI agentic loop
    # ------------------------------------------------------------------

    def _run_openai(
        self,
        query: str,
        chat_id: int,
        user_email: str,
        media_attachments: list,
    ) -> Generator[dict, None, None]:
        import openai as _openai

        api_key = self.model_key or os.getenv("OPENAI_API_KEY")
        client = _openai.OpenAI(api_key=api_key)
        model = os.getenv("OPENAI_AGENT_MODEL", AgentConfig.OPENAI_VISION_MODEL)

        # Build initial user content
        user_text = _build_user_content_openai(query, media_attachments)
        messages: list[dict] = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_text},
        ]

        sources_found: list[dict] = []
        final_answer = ""
        final_thought = ""

        for iteration in range(AgentConfig.AGENT_MAX_ITERATIONS):
            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    tools=_openai_tools(),
                    tool_choice="auto",
                    max_tokens=4096,
                )
            except Exception as exc:
                yield {"type": "error", "message": str(exc), "timestamp": _ts()}
                final_answer = f"Error: {exc}"
                break

            choice = response.choices[0]
            msg = choice.message

            # Stream any reasoning (not available for all OpenAI models)
            if hasattr(msg, "reasoning") and msg.reasoning:
                final_thought = msg.reasoning[:600]
                yield {
                    "type": "llm_reasoning",
                    "thought": msg.reasoning[:300],
                    "raw_output": msg.reasoning[:500],
                    "timestamp": _ts(),
                }

            tool_calls = getattr(msg, "tool_calls", None) or []

            if not tool_calls:
                final_answer = msg.content or ""
                if not final_thought:
                    final_thought = "Reasoned and composed the final answer."
                break

            # Append assistant turn
            messages.append(msg)

            for tc in tool_calls:
                fn = tc.function
                try:
                    inputs = json.loads(fn.arguments)
                except json.JSONDecodeError:
                    inputs = {}

                yield {
                    "type": "tool_start",
                    "tool_name": fn.name,
                    "input": fn.arguments[:200],
                    "timestamp": _ts(),
                }
                output, docs = _execute_tool(fn.name, inputs, chat_id, user_email)
                sources_found.extend(docs)
                yield {
                    "type": "tool_end",
                    "tool_name": fn.name,
                    "output": output[:300] + "…" if len(output) > 300 else output,
                    "timestamp": _ts(),
                }
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": output,
                })

        else:
            if not final_answer:
                final_answer = (
                    "I reached the maximum reasoning steps. Here is what I found."
                )

        yield from _finalize(final_answer, final_thought, sources_found, chat_id)


# ---------------------------------------------------------------------------
# Tool execution
# ---------------------------------------------------------------------------

def _execute_tool(
    name: str, inputs: dict, chat_id: int, user_email: str
) -> tuple[str, list[dict]]:
    """Run a named tool and return (output_string, list_of_source_dicts)."""
    docs: list[dict] = []
    try:
        if name == "retrieve_documents":
            query = inputs.get("query", "")
            k = min(int(inputs.get("k", 6)), 10)
            chunks = get_relevant_chunks(k, query, chat_id, user_email)
            if not chunks:
                return "No relevant document chunks found.", docs
            parts = []
            for chunk_text, doc_name in chunks:
                parts.append(f"**Source: {doc_name}**\n{chunk_text.strip()}")
                docs.append({"chunk_text": chunk_text, "document_name": doc_name})
            return "\n\n---\n\n".join(parts), docs

        elif name == "list_documents":
            doc_list = retrieve_docs_from_db(chat_id, user_email)
            if not doc_list:
                return "No documents uploaded in this chat.", docs
            lines = [f"- {d['document_name']} (ID: {d['id']})" for d in doc_list]
            return "Uploaded documents:\n" + "\n".join(lines), docs

        elif name == "get_chat_history":
            limit = int(inputs.get("limit", 5))
            messages = retrieve_message_from_db(user_email, chat_id, 0)
            if not messages:
                return "No chat history.", docs
            recent = messages[-(limit * 2):]
            lines = []
            for m in recent:
                role = "User" if m["sent_from_user"] == 1 else "Assistant"
                lines.append(f"{role}: {m['message_text']}")
            return "\n".join(lines), docs

        elif name == "run_python":
            code = inputs.get("code", "").strip()
            if not code:
                return "No code provided.", docs
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".py", delete=False, encoding="utf-8"
            ) as tmp:
                tmp.write(code)
                tmp_path = tmp.name
            try:
                result = subprocess.run(
                    [sys.executable, tmp_path],
                    capture_output=True, text=True, timeout=30,
                )
                out = result.stdout
                if result.stderr:
                    out += f"\n[stderr]\n{result.stderr}"
                return out.strip() or "(no output)", docs
            except subprocess.TimeoutExpired:
                return "[Error] Code execution timed out after 30 seconds.", docs
            except Exception as exc:
                return f"[Error] {exc}", docs
            finally:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass

        else:
            return f"Unknown tool: {name}", docs

    except Exception as exc:
        return f"Tool error ({name}): {exc}\n{traceback.format_exc()[:500]}", docs


# ---------------------------------------------------------------------------
# Finalization helper
# ---------------------------------------------------------------------------

def _finalize(
    answer: str,
    thought: str,
    sources: list[dict],
    chat_id: int,
) -> Generator[dict, None, None]:
    """Persist AI message + sources, then yield the completion event."""
    if not answer:
        answer = "I was unable to generate a response. Please try again."
    if not thought:
        thought = "Reasoned and composed the final answer."

    msg_id = add_message_to_db(answer, chat_id, 0)
    if sources and msg_id:
        try:
            add_sources_to_db(
                msg_id,
                [(s["chunk_text"], s["document_name"]) for s in sources],
            )
        except Exception:
            pass

    unique_sources = _deduplicate_sources(sources)

    yield {
        "type": "complete",
        "answer": answer,
        "sources": unique_sources,
        "thought": thought,
        "timestamp": _ts(),
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_user_content_anthropic(query: str, media_attachments: list) -> list:
    if not media_attachments:
        return [{"type": "text", "text": query}]

    from services.vision_service import describe_image
    import base64

    descriptions = []
    for att in media_attachments:
        if att.get("media_type") == "image":
            try:
                raw = base64.b64decode(att["data"])
                desc = describe_image(raw, mime_type=att.get("mime_type", "image/jpeg"))
                fname = att.get("original_filename", "attachment")
                descriptions.append(f"[Image: {fname}]\n{desc}")
            except Exception as exc:
                descriptions.append(f"[Image could not be described: {exc}]")

    if descriptions:
        enriched = "\n\n".join(descriptions) + "\n\n" + query
        return [{"type": "text", "text": enriched}]
    return [{"type": "text", "text": query}]


def _build_user_content_openai(query: str, media_attachments: list) -> str:
    """Build a plain text user message for OpenAI (describe images inline)."""
    if not media_attachments:
        return query

    from services.vision_service import describe_image
    import base64

    descriptions = []
    for att in media_attachments:
        if att.get("media_type") == "image":
            try:
                raw = base64.b64decode(att["data"])
                desc = describe_image(raw, mime_type=att.get("mime_type", "image/jpeg"))
                fname = att.get("original_filename", "attachment")
                descriptions.append(f"[Image: {fname}]\n{desc}")
            except Exception as exc:
                descriptions.append(f"[Image could not be described: {exc}]")

    if descriptions:
        return "\n\n".join(descriptions) + "\n\n" + query
    return query


def _deduplicate_sources(sources: list[dict]) -> list[dict]:
    seen: set[str] = set()
    out = []
    for s in sources:
        key = s["document_name"]
        if key not in seen:
            seen.add(key)
            out.append({
                "document_name": s["document_name"],
                "chunk_text": s["chunk_text"],
            })
    return out


def _ts() -> str:
    return str(int(time.time() * 1000))


def _guest_anthropic(query: str, model_key: str) -> str:
    from anthropic import Anthropic

    api_key = model_key or os.getenv("ANTHROPIC_API_KEY")
    client = Anthropic(api_key=api_key)
    response = client.messages.create(
        model=os.getenv("ANTHROPIC_AGENT_MODEL", AgentConfig.ANTHROPIC_VISION_MODEL),
        max_tokens=1024,
        system=(
            "You are a helpful AI assistant in guest mode. "
            "Answer using general knowledge. "
            "Mention that document upload and full features require an account."
        ),
        messages=[{"role": "user", "content": query}],
    )
    parts = [b.text for b in response.content if hasattr(b, "text")]
    return "\n".join(parts)


def _guest_openai(query: str, model_key: str) -> str:
    import openai as _openai

    api_key = model_key or os.getenv("OPENAI_API_KEY")
    client = _openai.OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=os.getenv("OPENAI_AGENT_MODEL", AgentConfig.OPENAI_VISION_MODEL),
        max_tokens=1024,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a helpful AI assistant in guest mode. "
                    "Answer using general knowledge. "
                    "Mention that document upload and full features require an account."
                ),
            },
            {"role": "user", "content": query},
        ],
    )
    return response.choices[0].message.content or ""
