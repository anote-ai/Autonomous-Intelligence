"""Anote API client — synchronous and async."""

from __future__ import annotations

from typing import Any, Optional
import httpx

from .models import (
    ChatResult,
    SessionSummary,
    Message,
    SearchResult,
    UsageSummary,
    ShareResult,
    HealthResult,
)


class AnoteError(Exception):
    """Raised when the Anote API returns a non-2xx response."""

    def __init__(self, message: str, status: int, body: Any) -> None:
        super().__init__(message)
        self.status = status
        self.body = body


def _raise_for_status(response: httpx.Response) -> dict:
    data: dict = {}
    try:
        data = response.json()
    except Exception:
        pass
    if response.is_error:
        msg = data.get("error") or f"HTTP {response.status_code}"
        raise AnoteError(msg, response.status_code, data)
    return data


_DEFAULT_BASE = "https://api.anote.ai"
_USER_AGENT = "anote-sdk-python/1.0.0"


class AnoteClient:
    """Synchronous Anote API client.

    Args:
        api_key: Your Anote API key.
        base_url: Server base URL. Defaults to ``https://api.anote.ai``.
        timeout: Request timeout in seconds. Defaults to 60.
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = _DEFAULT_BASE,
        timeout: float = 60.0,
    ) -> None:
        if not api_key:
            raise ValueError("api_key is required")
        self._base = base_url.rstrip("/") + "/api/v1"
        self._headers = {
            "Authorization": f"Bearer {api_key}",
            "User-Agent": _USER_AGENT,
        }
        self._timeout = timeout

    def _get(self, path: str, params: Optional[dict] = None) -> dict:
        with httpx.Client(timeout=self._timeout) as http:
            r = http.get(f"{self._base}{path}", headers=self._headers, params=params)
            return _raise_for_status(r)

    def _post(self, path: str, body: Optional[dict] = None) -> dict:
        with httpx.Client(timeout=self._timeout) as http:
            r = http.post(f"{self._base}{path}", headers=self._headers, json=body or {})
            return _raise_for_status(r)

    def _delete(self, path: str) -> dict:
        with httpx.Client(timeout=self._timeout) as http:
            r = http.delete(f"{self._base}{path}", headers=self._headers)
            return _raise_for_status(r)

    def chat(
        self,
        message: str,
        *,
        cwd: Optional[str] = None,
        model: str = "claude-sonnet-4-6",
        tools: Optional[list[str]] = None,
    ) -> ChatResult:
        """Send a message and receive a complete AI response."""
        payload: dict = {"message": message, "model": model}
        if cwd:
            payload["cwd"] = cwd
        if tools:
            payload["tools"] = tools
        return ChatResult.model_validate(self._post("/chat", payload))

    def list_sessions(self) -> list[SessionSummary]:
        """List all chat sessions."""
        data = self._get("/sessions")
        return [SessionSummary.model_validate(s) for s in data]

    def get_session_messages(self, session_id: str) -> list[Message]:
        """Get full message history for a session."""
        data = self._get(f"/sessions/{session_id}/messages")
        return [Message.model_validate(m) for m in data.get("history", [])]

    def delete_session(self, session_id: str) -> bool:
        """Delete a session. Returns True on success."""
        data = self._delete(f"/sessions/{session_id}")
        return bool(data.get("ok"))

    def share_session(self, session_id: str) -> ShareResult:
        """Mint a shareable read-only link for a session."""
        return ShareResult.model_validate(self._post(f"/sessions/{session_id}/share"))

    def search(self, query: str, limit: int = 20) -> list[SearchResult]:
        """Full-text search across all session histories."""
        data = self._get("/search", params={"q": query, "limit": limit})
        return [SearchResult.model_validate(r) for r in data.get("results", [])]

    def get_usage(self) -> UsageSummary:
        """Get current month usage and remaining quota."""
        return UsageSummary.model_validate(self._get("/usage"))

    def health(self) -> HealthResult:
        """Check server liveness. Does not require authentication."""
        with httpx.Client(timeout=self._timeout) as http:
            r = http.get(f"{self._base}/health", headers={"User-Agent": _USER_AGENT})
            return HealthResult.model_validate(r.json())


class AsyncAnoteClient:
    """Async Anote API client for use with asyncio / anyio."""

    def __init__(
        self,
        api_key: str,
        base_url: str = _DEFAULT_BASE,
        timeout: float = 60.0,
    ) -> None:
        if not api_key:
            raise ValueError("api_key is required")
        self._base = base_url.rstrip("/") + "/api/v1"
        self._headers = {
            "Authorization": f"Bearer {api_key}",
            "User-Agent": _USER_AGENT,
        }
        self._timeout = timeout
        self._http: Optional[httpx.AsyncClient] = None

    async def __aenter__(self) -> "AsyncAnoteClient":
        self._http = httpx.AsyncClient(timeout=self._timeout)
        return self

    async def __aexit__(self, *_: Any) -> None:
        if self._http:
            await self._http.aclose()

    def _client(self) -> httpx.AsyncClient:
        if not self._http:
            raise RuntimeError("Use 'async with AsyncAnoteClient(...) as client'")
        return self._http

    async def _get(self, path: str, params: Optional[dict] = None) -> dict:
        r = await self._client().get(f"{self._base}{path}", headers=self._headers, params=params)
        return _raise_for_status(r)

    async def _post(self, path: str, body: Optional[dict] = None) -> dict:
        r = await self._client().post(f"{self._base}{path}", headers=self._headers, json=body or {})
        return _raise_for_status(r)

    async def _delete(self, path: str) -> dict:
        r = await self._client().delete(f"{self._base}{path}", headers=self._headers)
        return _raise_for_status(r)

    async def chat(self, message: str, *, cwd: Optional[str] = None, model: str = "claude-sonnet-4-6", tools: Optional[list[str]] = None) -> ChatResult:
        payload: dict = {"message": message, "model": model}
        if cwd:
            payload["cwd"] = cwd
        if tools:
            payload["tools"] = tools
        return ChatResult.model_validate(await self._post("/chat", payload))

    async def list_sessions(self) -> list[SessionSummary]:
        return [SessionSummary.model_validate(s) for s in await self._get("/sessions")]

    async def get_session_messages(self, session_id: str) -> list[Message]:
        data = await self._get(f"/sessions/{session_id}/messages")
        return [Message.model_validate(m) for m in data.get("history", [])]

    async def delete_session(self, session_id: str) -> bool:
        return bool((await self._delete(f"/sessions/{session_id}")).get("ok"))

    async def share_session(self, session_id: str) -> ShareResult:
        return ShareResult.model_validate(await self._post(f"/sessions/{session_id}/share"))

    async def search(self, query: str, limit: int = 20) -> list[SearchResult]:
        data = await self._get("/search", params={"q": query, "limit": limit})
        return [SearchResult.model_validate(r) for r in data.get("results", [])]

    async def get_usage(self) -> UsageSummary:
        return UsageSummary.model_validate(await self._get("/usage"))

    async def health(self) -> HealthResult:
        r = await self._client().get(f"{self._base}/health", headers={"User-Agent": _USER_AGENT})
        return HealthResult.model_validate(r.json())
