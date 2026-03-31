"""OpenAI-compatible client for the Anote AI API.

This thin wrapper lets you swap ``openai.OpenAI(...)`` for
``AnoteOpenAI(api_key=..., base_url=...)`` with zero other code changes.

Example
-------
.. code-block:: python

    from anoteai.openai_compat import AnoteOpenAI

    client = AnoteOpenAI(
        api_key="your-anote-api-key",
        base_url="http://localhost:5000",   # or https://api.anote.ai
    )

    # Plain chat (no documents):
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": "What is the capital of France?"}],
    )
    print(response.choices[0].message.content)

    # Document-grounded Q&A:
    #   1. Upload documents and get a chat_id
    upload_resp = client.documents.upload("path/to/report.pdf")
    chat_id = upload_resp["chat_id"]

    #   2. Ask questions
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": "Summarise the key findings."}],
        extra_body={"chat_id": chat_id},
    )
    print(response.choices[0].message.content)
    print("Sources:", response.anote_sources)
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

import requests


# ---------------------------------------------------------------------------
# Simple data classes that mirror the OpenAI SDK response objects
# ---------------------------------------------------------------------------

@dataclass
class Message:
    role: str
    content: str


@dataclass
class Choice:
    index: int
    message: Message
    finish_reason: str


@dataclass
class Usage:
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


@dataclass
class ChatCompletion:
    id: str
    object: str
    created: int
    model: str
    choices: list[Choice]
    usage: Usage
    # Anote extension
    anote_message_id: int | None = None
    anote_sources: list[dict] = field(default_factory=list)


@dataclass
class Model:
    id: str
    object: str
    created: int
    owned_by: str


@dataclass
class ModelList:
    object: str
    data: list[Model]


# ---------------------------------------------------------------------------
# Sub-clients
# ---------------------------------------------------------------------------

class CompletionsClient:
    def __init__(self, http: "_HTTPClient") -> None:
        self._http = http

    def create(
        self,
        *,
        model: str,
        messages: list[dict],
        stream: bool = False,
        extra_body: dict | None = None,
        **kwargs: Any,
    ) -> ChatCompletion:
        """Call ``POST /v1/chat/completions`` and return a :class:`ChatCompletion`."""
        body: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": stream,
            **(extra_body or {}),
            **kwargs,
        }
        data = self._http.post("/v1/chat/completions", body)
        choices = [
            Choice(
                index=c["index"],
                message=Message(
                    role=c["message"]["role"],
                    content=c["message"]["content"],
                ),
                finish_reason=c.get("finish_reason", "stop"),
            )
            for c in data.get("choices", [])
        ]
        usage_raw = data.get("usage", {})
        anote = data.get("anote", {})
        return ChatCompletion(
            id=data.get("id", ""),
            object=data.get("object", "chat.completion"),
            created=data.get("created", 0),
            model=data.get("model", model),
            choices=choices,
            usage=Usage(
                prompt_tokens=usage_raw.get("prompt_tokens", -1),
                completion_tokens=usage_raw.get("completion_tokens", -1),
                total_tokens=usage_raw.get("total_tokens", -1),
            ),
            anote_message_id=anote.get("message_id"),
            anote_sources=anote.get("sources", []),
        )


class ChatClient:
    def __init__(self, http: "_HTTPClient") -> None:
        self.completions = CompletionsClient(http)


class ModelsClient:
    def __init__(self, http: "_HTTPClient") -> None:
        self._http = http

    def list(self) -> ModelList:
        """Call ``GET /v1/models`` and return a :class:`ModelList`."""
        data = self._http.get("/v1/models")
        models = [
            Model(
                id=m["id"],
                object=m["object"],
                created=m["created"],
                owned_by=m["owned_by"],
            )
            for m in data.get("data", [])
        ]
        return ModelList(object=data.get("object", "list"), data=models)


class DocumentsClient:
    """Helper client for Anote document upload (not part of the OpenAI spec)."""

    def __init__(self, http: "_HTTPClient") -> None:
        self._http = http

    def upload(self, *file_paths: str, task_type: int = 0, model_type: int = 1) -> dict:
        """Upload one or more documents and return ``{"chat_id": <int>}``."""
        files = [
            ("files[]", (os.path.basename(p), open(p, "rb"), "application/octet-stream"))
            for p in file_paths
        ]
        data = {"task_type": task_type, "model_type": model_type}
        resp = requests.post(
            f"{self._http.base_url}/public/upload",
            headers={"Authorization": f"Bearer {self._http.api_key}"},
            files=files,
            data=data,
        )
        resp.raise_for_status()
        for _, fobj in files:
            fobj[1].close()
        return resp.json()

    def question_answer(self, question: str, chat_id: int, model: str = "gpt-4o") -> dict:
        """Simple stateless Q&A against previously-uploaded documents."""
        return self._http.post(
            "/v1/question-answer",
            {"question": question, "chat_id": chat_id, "model": model},
        )


# ---------------------------------------------------------------------------
# Internal HTTP client
# ---------------------------------------------------------------------------

class _HTTPClient:
    def __init__(self, api_key: str, base_url: str) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def post(self, path: str, body: dict) -> dict:
        resp = requests.post(
            f"{self.base_url}{path}",
            headers=self._headers(),
            json=body,
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json()

    def get(self, path: str) -> dict:
        resp = requests.get(
            f"{self.base_url}{path}",
            headers=self._headers(),
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()


# ---------------------------------------------------------------------------
# Main public class
# ---------------------------------------------------------------------------

class AnoteOpenAI:
    """Drop-in replacement for ``openai.OpenAI`` that targets the Anote API.

    Parameters
    ----------
    api_key:
        Your Anote API key (or set ``ANOTE_API_KEY`` env var).
    base_url:
        The Anote server base URL, e.g. ``"http://localhost:5000"`` or
        ``"https://api.anote.ai"``.  Defaults to ``http://localhost:5000``.
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = "http://localhost:5000",
    ) -> None:
        resolved_key = api_key or os.environ.get("ANOTE_API_KEY", "")
        if not resolved_key:
            raise ValueError(
                "api_key must be supplied or ANOTE_API_KEY env var must be set."
            )
        self._http = _HTTPClient(api_key=resolved_key, base_url=base_url)
        self.chat = ChatClient(self._http)
        self.models = ModelsClient(self._http)
        self.documents = DocumentsClient(self._http)
