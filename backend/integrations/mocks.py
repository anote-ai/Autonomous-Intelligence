"""In-memory mock connectors for connector development and testing.

These connectors implement the full :class:`~integrations.base.Connector`
contract against in-memory state instead of a real third-party API. They
let connector development, agent tool wiring, and unit tests proceed
without live credentials, per the "testable mocks/sandboxes for connector
development" requirement in issue #138.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass
from typing import Any

from .base import (
    ActionSchema,
    Connector,
    ConnectorCapability,
    ConnectorError,
    ConnectorHealth,
    ConnectorHealthStatus,
    RateLimit,
)

_PERMISSION_SEND = "email.send"
_PERMISSION_READ = "email.read"


@dataclass
class _MockMessage:
    id: int
    to: str
    subject: str
    body: str
    sender: str = "me@example.com"


class MockEmailConnector(Connector):
    """A fully functional in-memory email connector sandbox.

    Supports sending mail (write) and listing/searching the inbox (read),
    gated by the ``email.send`` / ``email.read`` permissions respectively,
    so permission-denial and partial-capability paths can be exercised in
    tests without any network access.
    """

    name = "mock_email"
    capabilities = (ConnectorCapability.EMAIL,)
    rate_limit = RateLimit(max_calls=20, window_seconds=60.0)

    def __init__(self) -> None:
        super().__init__()
        self._sent: list[_MockMessage] = []
        self._id_counter = itertools.count(1)
        self._simulated_down = False

    # -- auth -------------------------------------------------------------

    def authenticate(self, credentials: dict[str, Any]) -> None:
        token = credentials.get("token")
        if not token:
            raise ConnectorError(
                "Missing 'token' in credentials for mock_email connector.",
                retryable=False,
                fallback_hint="Provide a non-empty token to authenticate.",
            )
        scopes = credentials.get("scopes", [_PERMISSION_SEND, _PERMISSION_READ])
        self._granted_permissions = set(scopes)
        self._authenticated = True

    # -- capability discovery ---------------------------------------------

    def list_actions(self) -> list[ActionSchema]:
        return [
            ActionSchema(
                name="send_email",
                description="Send an email to a recipient.",
                capability=ConnectorCapability.EMAIL,
                parameters={
                    "to": {"type": "string", "description": "Recipient address."},
                    "subject": {"type": "string", "description": "Email subject."},
                    "body": {"type": "string", "description": "Email body text."},
                },
                required_permissions=(_PERMISSION_SEND,),
                is_write=True,
            ),
            ActionSchema(
                name="list_sent",
                description="List previously sent emails.",
                capability=ConnectorCapability.EMAIL,
                parameters={},
                required_permissions=(_PERMISSION_READ,),
                is_write=False,
            ),
            ActionSchema(
                name="search_sent",
                description="Search sent emails by subject substring.",
                capability=ConnectorCapability.EMAIL,
                parameters={
                    "query": {"type": "string", "description": "Subject substring to match."},
                },
                required_permissions=(_PERMISSION_READ,),
                is_write=False,
            ),
        ]

    # -- execution ----------------------------------------------------------

    def _execute_action(self, action_name: str, **kwargs: Any) -> Any:
        if self._simulated_down:
            raise ConnectorError(
                "mock_email connector is simulated as down.",
                retryable=True,
                fallback_hint="Wait for the connector to recover or use a fallback connector.",
            )

        if action_name == "send_email":
            return self._send_email(**kwargs)
        if action_name == "list_sent":
            return self._list_sent()
        if action_name == "search_sent":
            return self._search_sent(**kwargs)
        raise ConnectorError(f"Action '{action_name}' is not implemented.")

    def _send_email(self, to: str, subject: str, body: str) -> dict[str, Any]:
        if not to or "@" not in to:
            raise ConnectorError(
                f"Invalid recipient address: {to!r}",
                retryable=False,
                fallback_hint="Provide a valid email address for 'to'.",
            )
        message = _MockMessage(id=next(self._id_counter), to=to, subject=subject, body=body)
        self._sent.append(message)
        return {"id": message.id, "to": message.to, "subject": message.subject}

    def _list_sent(self) -> list[dict[str, Any]]:
        return [
            {"id": m.id, "to": m.to, "subject": m.subject, "body": m.body}
            for m in self._sent
        ]

    def _search_sent(self, query: str) -> list[dict[str, Any]]:
        query_lower = query.lower()
        return [
            {"id": m.id, "to": m.to, "subject": m.subject, "body": m.body}
            for m in self._sent
            if query_lower in m.subject.lower()
        ]

    # -- test/sandbox helpers ------------------------------------------------

    def simulate_outage(self, down: bool = True) -> None:
        """Toggle a simulated outage to exercise health/retry/fallback paths."""
        self._simulated_down = down

    def health_check(self) -> ConnectorHealth:
        if self._simulated_down:
            return ConnectorHealth(
                status=ConnectorHealthStatus.DOWN,
                detail="mock_email connector is simulated as down.",
            )
        return super().health_check()
