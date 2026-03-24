"""Autonomous document agent — native tool_use + streaming + extended thinking.

Architecture
------------
- True agentic loop: reason → pick tool → execute → observe → repeat
- Anthropic path: streaming API with real-time text/thinking tokens; extended
  thinking enabled only for claude-3-7+ models (bug fix vs v1)
- OpenAI path: function-calling loop with streaming text
- 6 tools: retrieve_documents, list_documents, get_chat_history,
           run_python, search_web, fetch_url

Streaming events emitted (SSE-compatible dicts)
-----------------------------------------------
  {"type": "start"}
  {"type": "thinking",       "content": "..."}   ← extended-thinking block
  {"type": "llm_reasoning",  "thought": "..."}   ← alias for old frontend path
  {"type": "text_token",     "content": "..."}   ← streamed text token
  {"type": "tool_start",     "tool_name": "...", "input": "..."}
  {"type": "tool_end",       "tool_name": "...", "output": "..."}
  {"type": "complete",       "answer": "...", "sources": [...], "thought": "..."}
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
# Tool registry — one canonical definition, converted per-provider below
# ---------------------------------------------------------------------------

_TOOL_SPECS: list[dict] = [
    {
        "name": "retrieve_documents",
        "description": (
            "Semantic search over the user's uploaded documents. "
            "ALWAYS call this first before answering any factual question. "
            "Returns the most relevant text chunks with their source filenames."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Natural-language search query.",
                },
                "k": {
                    "type": "integer",
                    "description": "Number of chunks to retrieve (1–10). Default 6.",
                    "default": 6,
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "list_documents",
        "description": (
            "List every document the user has uploaded in this chat session. "
            "Call this when the user asks what files are available."
        ),
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "get_chat_history",
        "description": (
            "Retrieve recent messages from this conversation. "
            "Call this only when the query explicitly references earlier context."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Number of recent message pairs (default 5).",
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
            "Use for data analysis, calculations, chart/table generation, or any "
            "task where running real code is more reliable than reasoning. "
            "Standard library + numpy, pandas, matplotlib are available."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Python code to execute. Use print() to surface results.",
                }
            },
            "required": ["code"],
        },
    },
    {
        "name": "search_web",
        "description": (
            "Search the internet for up-to-date information. "
            "Use when the user asks about current events, recent data, or facts "
            "that are unlikely to be in the uploaded documents."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query string.",
                },
                "num_results": {
                    "type": "integer",
                    "description": "Number of results to return (1–10, default 5).",
                    "default": 5,
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "fetch_url",
        "description": (
            "Fetch the readable text content of a web page. "
            "Use to read articles, documentation, or any public URL the user mentions."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "Full URL to fetch (https://...).",
                }
            },
            "required": ["url"],
        },
    },
    {
        "name": "create_note",
        "description": (
            "Save a piece of text as a new document in the user's knowledge base. "
            "Use this to: save a generated summary, create a to-do list from document content, "
            "record key findings, or produce any artifact the user can query later. "
            "The saved note is immediately searchable via retrieve_documents."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Short descriptive title for the note (used as filename).",
                },
                "content": {
                    "type": "string",
                    "description": "Full text content of the note to save.",
                },
            },
            "required": ["title", "content"],
        },
    },
    {
        "name": "retrieve_documents_multi",
        "description": (
            "Run multiple semantic searches in parallel and merge the results. "
            "Use this for broad questions that require evidence from several angles "
            "(e.g. 'compare sections A and B', 'find all mentions of X and Y'). "
            "More powerful than calling retrieve_documents once."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "queries": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of 2–5 distinct search queries.",
                },
                "k_per_query": {
                    "type": "integer",
                    "description": "Chunks per query (1–6, default 3).",
                    "default": 3,
                },
            },
            "required": ["queries"],
        },
    },
]

_SYSTEM_PROMPT = """\
You are Autonomous Intelligence — a highly capable AI agent that reasons carefully \
and uses tools to deliver precise, well-sourced answers.

Decision framework
------------------
STEP 1 — Orient:  What kind of question is this?
  • Document-based  → call retrieve_documents (or retrieve_documents_multi for complex queries)
  • "What files?"   → call list_documents
  • Needs history   → call get_chat_history
  • Current events  → call search_web, then fetch_url on the most relevant result
  • Math/data       → call run_python
  • Multi-faceted   → combine tools across multiple iterations

STEP 2 — Retrieve: Pull all necessary information before composing the answer.
  • For complex questions, call retrieve_documents_multi with 2–4 targeted queries.
  • If web results look relevant, call fetch_url to read the full content.
  • If you need data analysis, call run_python with pandas/numpy.

STEP 3 — Synthesize: Compose a clear, well-structured response.
  • Quote exact passages and cite the filename in parentheses.
  • If information came from the web, cite the URL.
  • If documents don't contain the answer, say so explicitly, then answer from knowledge.
  • Use markdown headers, bullet points, and code blocks where they help readability.

STEP 4 — Persist (optional): If the user asked for a deliverable (summary, list, report),
  call create_note to save it so they can query it later.

Do not pad responses. Be thorough on content, concise on prose.
"""

# Max characters of accumulated tool outputs to keep in context before truncating
_MAX_TOOL_OUTPUT_CHARS = 8000


# ---------------------------------------------------------------------------
# Provider-specific tool formats
# ---------------------------------------------------------------------------

def _anthropic_tools() -> list[dict]:
    return [
        {
            "name": s["name"],
            "description": s["description"],
            "input_schema": s["parameters"],
        }
        for s in _TOOL_SPECS
    ]


def _openai_tools() -> list[dict]:
    return [
        {
            "type": "function",
            "function": {
                "name": s["name"],
                "description": s["description"],
                "parameters": s["parameters"],
            },
        }
        for s in _TOOL_SPECS
    ]


# ---------------------------------------------------------------------------
# Main agent class
# ---------------------------------------------------------------------------

class AutonomousDocumentAgent:
    """Autonomous tool-calling agent with true agentic loop."""

    def __init__(self, model_type: int = 0, model_key: str = ""):
        self.model_type = model_type
        self.model_key = model_key

    def process_query_stream(
        self,
        query: str,
        chat_id: int,
        user_email: str,
        media_attachments: Optional[list] = None,
    ) -> Generator[dict, None, None]:
        yield from self._run(
            query=query,
            chat_id=chat_id,
            user_email=user_email,
            media_attachments=media_attachments or [],
        )

    def process_query_stream_guest(self, query: str) -> Generator[dict, None, None]:
        yield {"type": "start", "message": "Processing your query...", "timestamp": _ts()}
        try:
            answer = _guest_answer(query, self.model_type, self.model_key)
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
    # Core dispatcher
    # ------------------------------------------------------------------

    def _run(
        self,
        query: str,
        chat_id: int,
        user_email: str,
        media_attachments: list,
    ) -> Generator[dict, None, None]:
        yield {"type": "start", "message": "Processing your query...", "timestamp": _ts()}
        add_message_to_db(query, chat_id, 1)

        if self.model_type == 1:
            yield from _run_anthropic(query, chat_id, user_email, media_attachments, self.model_key)
        else:
            yield from _run_openai(query, chat_id, user_email, media_attachments, self.model_key)


# ---------------------------------------------------------------------------
# Anthropic agentic loop (streaming)
# ---------------------------------------------------------------------------

def _run_anthropic(
    query: str,
    chat_id: int,
    user_email: str,
    media_attachments: list,
    model_key: str,
) -> Generator[dict, None, None]:
    from anthropic import Anthropic

    client = Anthropic(api_key=model_key or os.getenv("ANTHROPIC_API_KEY"))
    model = os.getenv("ANTHROPIC_AGENT_MODEL", AgentConfig.ANTHROPIC_VISION_MODEL)

    # Extended thinking: ONLY claude-3-7 supports it (not claude-3-5!)
    use_thinking = "claude-3-7" in model

    user_content = _build_user_content_anthropic(query, media_attachments)
    messages: list[dict] = [{"role": "user", "content": user_content}]

    sources_found: list[dict] = []
    final_answer = ""
    final_thought = ""

    for _iteration in range(AgentConfig.AGENT_MAX_ITERATIONS):
        api_kwargs: dict[str, Any] = {
            "model": model,
            "max_tokens": 10000 if use_thinking else 4096,
            "system": _SYSTEM_PROMPT,
            "tools": _anthropic_tools(),
            "messages": messages,
        }
        if use_thinking:
            api_kwargs["thinking"] = {"type": "enabled", "budget_tokens": 6000}
            api_kwargs["betas"] = ["interleaved-thinking-2025-05-14"]

        # ── streaming call ─────────────────────────────────────────────
        tool_calls: list[dict] = []
        iter_answer = ""
        iter_thought = ""

        try:
            with client.messages.stream(**api_kwargs) as stream:
                current_block_type: Optional[str] = None
                current_block_id: Optional[str] = None
                current_block_name: Optional[str] = None
                current_input_json = ""
                current_thinking = ""

                for event in stream:
                    etype = event.type

                    if etype == "content_block_start":
                        cb = event.content_block
                        current_block_type = cb.type
                        current_input_json = ""
                        current_thinking = ""

                        if cb.type == "tool_use":
                            current_block_id = cb.id
                            current_block_name = cb.name
                            yield {
                                "type": "tool_start",
                                "tool_name": cb.name,
                                "input": "",
                                "timestamp": _ts(),
                            }

                    elif etype == "content_block_delta":
                        delta = event.delta
                        dtype = delta.type

                        if dtype == "text_delta":
                            iter_answer += delta.text
                            yield {"type": "text_token", "content": delta.text, "timestamp": _ts()}

                        elif dtype == "thinking_delta":
                            current_thinking += delta.thinking
                            yield {"type": "thinking", "content": delta.thinking, "timestamp": _ts()}

                        elif dtype == "input_json_delta":
                            current_input_json += delta.partial_json

                    elif etype == "content_block_stop":
                        if current_block_type == "tool_use":
                            try:
                                parsed_input = json.loads(current_input_json) if current_input_json else {}
                            except json.JSONDecodeError:
                                parsed_input = {}
                            tool_calls.append({
                                "id": current_block_id,
                                "name": current_block_name,
                                "input": parsed_input,
                            })

                        elif current_block_type == "thinking" and current_thinking:
                            iter_thought = current_thinking
                            yield {
                                "type": "llm_reasoning",
                                "thought": current_thinking[:300],
                                "raw_output": current_thinking[:500],
                                "timestamp": _ts(),
                            }

                        current_block_type = None
                        current_input_json = ""
                        current_thinking = ""

                response = stream.get_final_message()

        except Exception as exc:
            # If thinking caused the error, retry once without it
            if use_thinking:
                use_thinking = False
                del api_kwargs["thinking"]
                if "betas" in api_kwargs:
                    del api_kwargs["betas"]
                api_kwargs["max_tokens"] = 4096
                try:
                    response = client.messages.create(**api_kwargs)
                    tool_calls, iter_answer, iter_thought = _parse_response_blocks(response)
                except Exception as exc2:
                    yield {"type": "error", "message": str(exc2), "timestamp": _ts()}
                    final_answer = f"Error: {exc2}"
                    break
            else:
                yield {"type": "error", "message": str(exc), "timestamp": _ts()}
                final_answer = f"Error: {exc}"
                break

        final_answer += iter_answer
        if iter_thought:
            final_thought = iter_thought

        # ── no tool calls → model is done ─────────────────────────────
        if not tool_calls:
            if not final_thought:
                final_thought = "Reasoned and composed the final answer."
            break

        # ── execute tool calls ─────────────────────────────────────────
        messages.append({"role": "assistant", "content": response.content})
        tool_results = []

        for tc in tool_calls:
            output, docs = _execute_tool(tc["name"], tc["input"], chat_id, user_email)
            sources_found.extend(docs)
            truncated = output[:_MAX_TOOL_OUTPUT_CHARS]
            if len(output) > _MAX_TOOL_OUTPUT_CHARS:
                truncated += f"\n… [output truncated at {_MAX_TOOL_OUTPUT_CHARS} chars]"
            yield {
                "type": "tool_end",
                "tool_name": tc["name"],
                "output": output[:300] + "…" if len(output) > 300 else output,
                "timestamp": _ts(),
            }
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tc["id"],
                "content": truncated,
            })

        messages.append({"role": "user", "content": tool_results})
        # Prune old tool results to keep context window manageable
        messages = _prune_messages(messages)

    else:
        if not final_answer:
            final_answer = "I reached the maximum reasoning steps. Here is what I found so far."

    yield from _finalize(final_answer, final_thought, sources_found, chat_id)


# ---------------------------------------------------------------------------
# OpenAI agentic loop
# ---------------------------------------------------------------------------

def _run_openai(
    query: str,
    chat_id: int,
    user_email: str,
    media_attachments: list,
    model_key: str,
) -> Generator[dict, None, None]:
    import openai as _openai

    client = _openai.OpenAI(api_key=model_key or os.getenv("OPENAI_API_KEY"))
    model = os.getenv("OPENAI_AGENT_MODEL", AgentConfig.OPENAI_VISION_MODEL)

    user_text = _build_user_content_openai(query, media_attachments)
    messages: list[dict] = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": user_text},
    ]

    sources_found: list[dict] = []
    final_answer = ""
    final_thought = ""

    for _iteration in range(AgentConfig.AGENT_MAX_ITERATIONS):
        # Stream text tokens
        iter_answer = ""
        tool_calls_raw: list[dict] = []

        try:
            with client.chat.completions.create(
                model=model,
                messages=messages,
                tools=_openai_tools(),
                tool_choice="auto",
                max_tokens=4096,
                stream=True,
            ) as stream:
                current_tool_calls: dict[int, dict] = {}

                for chunk in stream:
                    delta = chunk.choices[0].delta if chunk.choices else None
                    if delta is None:
                        continue

                    # Stream text
                    if delta.content:
                        iter_answer += delta.content
                        yield {"type": "text_token", "content": delta.content, "timestamp": _ts()}

                    # Accumulate tool call chunks
                    if delta.tool_calls:
                        for tc_chunk in delta.tool_calls:
                            idx = tc_chunk.index
                            if idx not in current_tool_calls:
                                current_tool_calls[idx] = {
                                    "id": tc_chunk.id or "",
                                    "name": "",
                                    "arguments": "",
                                }
                            if tc_chunk.function:
                                if tc_chunk.function.name:
                                    current_tool_calls[idx]["name"] += tc_chunk.function.name
                                if tc_chunk.function.arguments:
                                    current_tool_calls[idx]["arguments"] += tc_chunk.function.arguments
                            if tc_chunk.id:
                                current_tool_calls[idx]["id"] = tc_chunk.id

                tool_calls_raw = list(current_tool_calls.values())

        except Exception as exc:
            yield {"type": "error", "message": str(exc), "timestamp": _ts()}
            final_answer = f"Error: {exc}"
            break

        final_answer += iter_answer

        if not tool_calls_raw:
            if not final_thought:
                final_thought = "Reasoned and composed the final answer."
            break

        # Build assistant message with tool_calls
        parsed_tool_calls = []
        for tc in tool_calls_raw:
            parsed_tool_calls.append({
                "id": tc["id"],
                "type": "function",
                "function": {"name": tc["name"], "arguments": tc["arguments"]},
            })
        messages.append({"role": "assistant", "content": None, "tool_calls": parsed_tool_calls})

        for tc in tool_calls_raw:
            try:
                inputs = json.loads(tc["arguments"]) if tc["arguments"] else {}
            except json.JSONDecodeError:
                inputs = {}

            yield {
                "type": "tool_start",
                "tool_name": tc["name"],
                "input": tc["arguments"][:200],
                "timestamp": _ts(),
            }
            output, docs = _execute_tool(tc["name"], inputs, chat_id, user_email)
            sources_found.extend(docs)
            yield {
                "type": "tool_end",
                "tool_name": tc["name"],
                "output": output[:300] + "…" if len(output) > 300 else output,
                "timestamp": _ts(),
            }
            truncated = output[:_MAX_TOOL_OUTPUT_CHARS]
            messages.append({
                "role": "tool",
                "tool_call_id": tc["id"],
                "content": truncated,
            })

        messages = _prune_messages(messages)

    else:
        if not final_answer:
            final_answer = "I reached the maximum reasoning steps. Here is what I found so far."

    yield from _finalize(final_answer, final_thought, sources_found, chat_id)


# ---------------------------------------------------------------------------
# Tool execution
# ---------------------------------------------------------------------------

def _execute_tool(
    name: str, inputs: dict, chat_id: int, user_email: str
) -> tuple[str, list[dict]]:
    docs: list[dict] = []
    try:
        if name == "retrieve_documents":
            return _tool_retrieve(inputs, chat_id, user_email, docs)
        elif name == "list_documents":
            return _tool_list_docs(chat_id, user_email), docs
        elif name == "get_chat_history":
            return _tool_chat_history(inputs, chat_id, user_email), docs
        elif name == "run_python":
            return _tool_run_python(inputs), docs
        elif name == "search_web":
            return _tool_search_web(inputs), docs
        elif name == "fetch_url":
            return _tool_fetch_url(inputs), docs
        elif name == "create_note":
            return _tool_create_note(inputs, chat_id), docs
        elif name == "retrieve_documents_multi":
            return _tool_retrieve_multi(inputs, chat_id, user_email, docs)
        else:
            return f"Unknown tool: {name}", docs
    except Exception as exc:
        return f"Tool error ({name}): {exc}\n{traceback.format_exc()[:400]}", docs


def _tool_retrieve(inputs: dict, chat_id: int, user_email: str, docs: list) -> tuple[str, list]:
    query = inputs.get("query", "")
    k = min(int(inputs.get("k", 6)), 10)
    chunks = get_relevant_chunks(k, query, chat_id, user_email)
    if not chunks:
        return "No relevant document chunks found for this query.", docs
    parts = []
    for chunk_text, doc_name in chunks:
        parts.append(f"**Source: {doc_name}**\n{chunk_text.strip()}")
        docs.append({"chunk_text": chunk_text, "document_name": doc_name})
    return "\n\n---\n\n".join(parts), docs


def _tool_list_docs(chat_id: int, user_email: str) -> str:
    doc_list = retrieve_docs_from_db(chat_id, user_email)
    if not doc_list:
        return "No documents uploaded in this chat."
    lines = [f"- {d['document_name']} (ID: {d['id']})" for d in doc_list]
    return "Uploaded documents:\n" + "\n".join(lines)


def _tool_chat_history(inputs: dict, chat_id: int, user_email: str) -> str:
    limit = max(1, min(int(inputs.get("limit", 5)), 20))
    messages = retrieve_message_from_db(user_email, chat_id, 0)
    if not messages:
        return "No chat history."
    recent = messages[-(limit * 2):]
    lines = []
    for m in recent:
        role = "User" if m["sent_from_user"] == 1 else "Assistant"
        lines.append(f"{role}: {m['message_text'][:500]}")
    return "\n".join(lines)


def _tool_run_python(inputs: dict) -> str:
    code = inputs.get("code", "").strip()
    if not code:
        return "No code provided."
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, encoding="utf-8"
    ) as tmp:
        tmp.write(code)
        tmp_path = tmp.name
    try:
        result = subprocess.run(
            [sys.executable, tmp_path],
            capture_output=True,
            text=True,
            timeout=30,
        )
        out = result.stdout
        if result.stderr:
            out += f"\n[stderr]\n{result.stderr}"
        return out.strip() or "(no output)"
    except subprocess.TimeoutExpired:
        return "[Error] Code execution timed out (30s limit)."
    except Exception as exc:
        return f"[Error] {exc}"
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def _tool_search_web(inputs: dict) -> str:
    """Search the web using DuckDuckGo HTML search (no API key needed)."""
    import re
    import urllib.parse

    import requests
    from bs4 import BeautifulSoup

    query = inputs.get("query", "").strip()
    num = min(int(inputs.get("num_results", 5)), 10)
    if not query:
        return "No query provided."

    url = "https://html.duckduckgo.com/html/"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
    }
    try:
        resp = requests.post(url, data={"q": query}, headers=headers, timeout=10)
        resp.raise_for_status()
    except Exception as exc:
        return f"[Web search failed: {exc}]"

    soup = BeautifulSoup(resp.text, "html.parser")
    results = []
    for result in soup.select(".result__body")[:num]:
        title_el = result.select_one(".result__title a")
        snippet_el = result.select_one(".result__snippet")
        link_el = result.select_one(".result__url")

        title = title_el.get_text(strip=True) if title_el else "No title"
        snippet = snippet_el.get_text(strip=True) if snippet_el else "No description"
        href = title_el.get("href", "") if title_el else ""

        # DuckDuckGo wraps links; extract the real URL from the uddg param
        if "uddg=" in href:
            match = re.search(r"uddg=([^&]+)", href)
            if match:
                href = urllib.parse.unquote(match.group(1))

        results.append(f"**{title}**\n{snippet}\nURL: {href}")

    if not results:
        return f"No web results found for: {query}"

    return f"Web search results for '{query}':\n\n" + "\n\n---\n\n".join(results)


def _tool_fetch_url(inputs: dict) -> str:
    """Fetch and extract readable text from a URL."""
    import requests
    from bs4 import BeautifulSoup

    url = inputs.get("url", "").strip()
    if not url:
        return "No URL provided."
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
    }
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
    except Exception as exc:
        return f"[Failed to fetch URL: {exc}]"

    soup = BeautifulSoup(resp.text, "html.parser")

    # Remove boilerplate
    for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
        tag.decompose()

    # Try <article> first, fall back to <main>, then <body>
    content = soup.find("article") or soup.find("main") or soup.find("body")
    if not content:
        return "[Could not extract readable content from this URL.]"

    text = content.get_text(separator="\n", strip=True)
    # Collapse excessive blank lines
    lines = [l for l in text.splitlines() if l.strip()]
    clean = "\n".join(lines)

    # Limit output size
    if len(clean) > 6000:
        clean = clean[:6000] + "\n… [content truncated]"

    return f"Content from {url}:\n\n{clean}"


def _tool_create_note(inputs: dict, chat_id: int) -> str:
    """Save a generated note/summary as a searchable document."""
    from api_endpoints.financeGPT.chatbot_endpoints import (
        add_document_to_db,
        chunk_document,
    )

    title = inputs.get("title", "Agent Note").strip()
    content = inputs.get("content", "").strip()
    if not content:
        return "No content provided to save."

    # Wrap in a simple header for readability
    full_text = f"# {title}\n\n{content}"

    try:
        doc_id, already_exists = add_document_to_db(full_text, title, chat_id)
        if not already_exists:
            chunk_document.remote(full_text, 1000, doc_id)
        return (
            f"Note '{title}' saved as document ID {doc_id}. "
            "It is now searchable via retrieve_documents."
        )
    except Exception as exc:
        return f"Failed to save note: {exc}"


def _tool_retrieve_multi(
    inputs: dict, chat_id: int, user_email: str, docs: list
) -> tuple[str, list]:
    """Run multiple retrieval queries and merge deduplicated results."""
    queries = inputs.get("queries") or []
    if not queries:
        return "No queries provided.", docs

    k_per = min(int(inputs.get("k_per_query", 3)), 6)
    seen_texts: set[str] = set()
    all_parts: list[str] = []

    for query in queries[:5]:  # cap at 5 queries
        chunks = get_relevant_chunks(k_per, query, chat_id, user_email)
        for chunk_text, doc_name in (chunks or []):
            key = chunk_text[:80]  # deduplicate by prefix
            if key not in seen_texts:
                seen_texts.add(key)
                all_parts.append(f"**Source: {doc_name}** (query: '{query}')\n{chunk_text.strip()}")
                docs.append({"chunk_text": chunk_text, "document_name": doc_name})

    if not all_parts:
        return "No relevant chunks found across all queries.", docs

    return (
        f"Multi-query retrieval ({len(queries)} queries, {len(all_parts)} unique chunks):\n\n"
        + "\n\n---\n\n".join(all_parts),
        docs,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_response_blocks(response) -> tuple[list[dict], str, str]:
    """Parse a non-streaming response into (tool_calls, text, thought)."""
    tool_calls = []
    text = ""
    thought = ""
    for block in response.content:
        btype = getattr(block, "type", None)
        if btype == "tool_use":
            tool_calls.append({"id": block.id, "name": block.name, "input": block.input})
        elif btype == "text":
            text += getattr(block, "text", "")
        elif btype == "thinking":
            thought = getattr(block, "thinking", "")[:600]
    return tool_calls, text, thought


def _prune_messages(messages: list[dict]) -> list[dict]:
    """Trim old tool_result messages to prevent context window overflow.

    Keeps the first user message, all assistant turns, and the last 3 rounds
    of tool results. This prevents runaway context growth on long agent loops.
    """
    if len(messages) <= 6:
        return messages

    # Always keep the initial user message
    first = messages[0]
    rest = messages[1:]

    # Keep only the last 4 assistant+tool-result pairs
    # Each round = 2 messages (assistant with tool_use, user with tool_result)
    keep_rounds = 4
    if len(rest) > keep_rounds * 2:
        rest = rest[-(keep_rounds * 2):]

    return [first] + rest


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
        return [{"type": "text", "text": "\n\n".join(descriptions) + "\n\n" + query}]
    return [{"type": "text", "text": query}]


def _build_user_content_openai(query: str, media_attachments: list) -> str:
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


def _finalize(
    answer: str,
    thought: str,
    sources: list[dict],
    chat_id: int,
) -> Generator[dict, None, None]:
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


def _deduplicate_sources(sources: list[dict]) -> list[dict]:
    seen: set[str] = set()
    out = []
    for s in sources:
        key = s["document_name"]
        if key not in seen:
            seen.add(key)
            out.append({"document_name": s["document_name"], "chunk_text": s["chunk_text"]})
    return out


def _guest_answer(query: str, model_type: int, model_key: str) -> str:
    system = (
        "You are a helpful AI assistant in guest mode. "
        "Answer using general knowledge. "
        "For document analysis and full features, a user account is required."
    )
    if model_type == 1:
        from anthropic import Anthropic
        client = Anthropic(api_key=model_key or os.getenv("ANTHROPIC_API_KEY"))
        resp = client.messages.create(
            model=os.getenv("ANTHROPIC_AGENT_MODEL", AgentConfig.ANTHROPIC_VISION_MODEL),
            max_tokens=1024,
            system=system,
            messages=[{"role": "user", "content": query}],
        )
        return "".join(b.text for b in resp.content if hasattr(b, "text"))
    else:
        import openai as _openai
        client = _openai.OpenAI(api_key=model_key or os.getenv("OPENAI_API_KEY"))
        resp = client.chat.completions.create(
            model=os.getenv("OPENAI_AGENT_MODEL", AgentConfig.OPENAI_VISION_MODEL),
            max_tokens=1024,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": query}],
        )
        return resp.choices[0].message.content or ""


def _ts() -> str:
    return str(int(time.time() * 1000))
