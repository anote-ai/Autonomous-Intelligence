"""
anote-sdk — Python SDK for the Anote AI assistant REST API.

Example::

    from anote_sdk import AnoteClient

    client = AnoteClient(api_key="ant-...", base_url="http://localhost:5000")

    result = client.chat("Explain this codebase")
    print(result.result)
"""

from .client import AnoteClient, AnoteError
from .models import (
    ChatResult,
    SessionSummary,
    Message,
    SearchResult,
    UsageSummary,
    MonthlyUsage,
    UsageQuota,
    ShareResult,
)

__all__ = [
    "AnoteClient",
    "AnoteError",
    "ChatResult",
    "SessionSummary",
    "Message",
    "SearchResult",
    "UsageSummary",
    "MonthlyUsage",
    "UsageQuota",
    "ShareResult",
]
__version__ = "1.0.0"
