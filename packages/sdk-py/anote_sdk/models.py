"""Pydantic v2 models for Anote API responses (camelCase JSON → snake_case Python)."""

from __future__ import annotations
from typing import Literal, Union
from pydantic import BaseModel, ConfigDict


def _camel(s: str) -> str:
    parts = s.split("_")
    return parts[0] + "".join(p.capitalize() for p in parts[1:])


class _Base(BaseModel):
    model_config = ConfigDict(populate_by_name=True, alias_generator=_camel)


class TokenUsage(_Base):
    input_tokens: int = 0
    output_tokens: int = 0


class ChatResult(_Base):
    result: str
    usage: TokenUsage


class SessionSummary(_Base):
    session_id: str
    cwd: str = ""
    message_count: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    model: str = ""
    created_at: int = 0
    updated_at: int = 0


class Message(_Base):
    role: Literal["user", "assistant"]
    content: str
    ts: int = 0


class SearchResult(_Base):
    session_id: str = ""
    role: str = ""
    snippet: str = ""
    ts: int = 0


class MonthlyUsage(_Base):
    month: str = ""
    request_count: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    updated_at: int = 0


class UsageQuota(_Base):
    plan: Literal["free", "pro"] = "free"
    max_requests: int = 0
    max_input_tokens: int = 0
    max_output_tokens: int = 0


class UsageRemaining(_Base):
    requests: Union[int, Literal["unlimited"]] = 0
    input_tokens: Union[int, Literal["unlimited"]] = 0
    output_tokens: Union[int, Literal["unlimited"]] = 0


class UsageSummary(_Base):
    current: MonthlyUsage = MonthlyUsage()
    quota: UsageQuota = UsageQuota()
    remaining: UsageRemaining = UsageRemaining()
    history: list[MonthlyUsage] = []


class ShareResult(_Base):
    token: str = ""
    share_url: str = ""


class HealthResult(_Base):
    status: str = "ok"
    version: str = ""
