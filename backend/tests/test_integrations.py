"""Tests for the connector/integration framework (see GitHub issue #138)."""

from __future__ import annotations

import time

import pytest
from integrations.base import (
    ActionSchema,
    Connector,
    ConnectorAuthError,
    ConnectorCapability,
    ConnectorError,
    ConnectorHealthStatus,
    ConnectorPermissionError,
    ConnectorRateLimitError,
    RateLimit,
)
from integrations.mocks import MockEmailConnector
from integrations.registry import ConnectorRegistry, get_registry

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def connector() -> MockEmailConnector:
    c = MockEmailConnector()
    c.authenticate({"token": "abc123"})
    return c


@pytest.fixture()
def registry() -> ConnectorRegistry:
    return ConnectorRegistry()


# ---------------------------------------------------------------------------
# Capability discovery / typed tool definitions
# ---------------------------------------------------------------------------


def test_list_actions_returns_typed_schemas(connector: MockEmailConnector) -> None:
    actions = connector.list_actions()
    names = {a.name for a in actions}
    assert names == {"send_email", "list_sent", "search_sent"}
    assert all(isinstance(a, ActionSchema) for a in actions)
    send = next(a for a in actions if a.name == "send_email")
    assert send.capability == ConnectorCapability.EMAIL
    assert send.is_write is True
    assert "email.send" in send.required_permissions


def test_get_tool_definitions_renders_llm_tool_shape(connector: MockEmailConnector) -> None:
    tools = connector.get_tool_definitions()
    send_tool = next(t for t in tools if t["name"] == "send_email")
    assert send_tool["input_schema"]["type"] == "object"
    assert set(send_tool["input_schema"]["required"]) == {"to", "subject", "body"}


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


def test_unauthenticated_connector_rejects_execute() -> None:
    c = MockEmailConnector()
    result = c.execute("send_email", to="a@example.com", subject="hi", body="hello")
    assert result.success is False
    assert isinstance(result.error, ConnectorAuthError)


def test_authenticate_requires_token() -> None:
    c = MockEmailConnector()
    with pytest.raises(ConnectorError):
        c.authenticate({})


def test_authenticate_grants_default_scopes() -> None:
    c = MockEmailConnector()
    c.authenticate({"token": "tok"})
    assert c.is_authenticated
    assert "email.send" in c.granted_permissions
    assert "email.read" in c.granted_permissions


# ---------------------------------------------------------------------------
# Execution: success paths
# ---------------------------------------------------------------------------


def test_send_email_success(connector: MockEmailConnector) -> None:
    result = connector.execute(
        "send_email", to="alice@example.com", subject="Hello", body="Hi Alice"
    )
    assert result.success is True
    assert result.data["to"] == "alice@example.com"
    assert result.data["subject"] == "Hello"


def test_list_sent_after_send(connector: MockEmailConnector) -> None:
    connector.execute("send_email", to="bob@example.com", subject="Re: project", body="...")
    result = connector.execute("list_sent")
    assert result.success is True
    assert len(result.data) == 1
    assert result.data[0]["to"] == "bob@example.com"


def test_search_sent_matches_subject(connector: MockEmailConnector) -> None:
    connector.execute("send_email", to="a@example.com", subject="Invoice #1", body="x")
    connector.execute("send_email", to="b@example.com", subject="Meeting notes", body="y")
    result = connector.execute("search_sent", query="invoice")
    assert result.success is True
    assert len(result.data) == 1
    assert result.data[0]["subject"] == "Invoice #1"


# ---------------------------------------------------------------------------
# Execution: failure paths (actionable errors)
# ---------------------------------------------------------------------------


def test_unknown_action_returns_connector_error(connector: MockEmailConnector) -> None:
    result = connector.execute("delete_everything")
    assert result.success is False
    assert isinstance(result.error, ConnectorError)
    assert "Unknown action" in result.error.message


def test_invalid_recipient_returns_actionable_error(connector: MockEmailConnector) -> None:
    result = connector.execute("send_email", to="not-an-email", subject="x", body="y")
    assert result.success is False
    assert result.error.retryable is False
    assert result.error.fallback_hint is not None


def test_missing_permission_blocks_action() -> None:
    c = MockEmailConnector()
    c.authenticate({"token": "tok", "scopes": ["email.read"]})
    result = c.execute("send_email", to="a@example.com", subject="x", body="y")
    assert result.success is False
    assert isinstance(result.error, ConnectorPermissionError)
    assert "email.send" in result.error.missing_permissions


def test_simulated_outage_is_retryable(connector: MockEmailConnector) -> None:
    connector.simulate_outage(True)
    result = connector.execute("list_sent")
    assert result.success is False
    assert result.error.retryable is True
    health = connector.health_check()
    assert health.status == ConnectorHealthStatus.DOWN


def test_outage_recovers_after_toggle(connector: MockEmailConnector) -> None:
    connector.simulate_outage(True)
    connector.simulate_outage(False)
    result = connector.execute("list_sent")
    assert result.success is True


# ---------------------------------------------------------------------------
# Rate limiting
# ---------------------------------------------------------------------------


def test_rate_limit_blocks_after_threshold() -> None:
    c = MockEmailConnector()
    c.rate_limit = RateLimit(max_calls=2, window_seconds=60.0)
    c._limiter = type(c._limiter)(c.rate_limit)
    c.authenticate({"token": "tok"})

    assert c.execute("list_sent").success is True
    assert c.execute("list_sent").success is True
    third = c.execute("list_sent")
    assert third.success is False
    assert isinstance(third.error, ConnectorRateLimitError)
    assert third.error.retryable is True


def test_rate_limit_window_resets(monkeypatch: pytest.MonkeyPatch) -> None:
    c = MockEmailConnector()
    c.rate_limit = RateLimit(max_calls=1, window_seconds=0.05)
    c._limiter = type(c._limiter)(c.rate_limit)
    c.authenticate({"token": "tok"})

    assert c.execute("list_sent").success is True
    assert c.execute("list_sent").success is False
    time.sleep(0.06)
    assert c.execute("list_sent").success is True


# ---------------------------------------------------------------------------
# Health checks
# ---------------------------------------------------------------------------


def test_health_check_healthy_when_fully_authorized(connector: MockEmailConnector) -> None:
    health = connector.health_check()
    assert health.status == ConnectorHealthStatus.HEALTHY


def test_health_check_degraded_with_partial_permissions() -> None:
    c = MockEmailConnector()
    c.authenticate({"token": "tok", "scopes": ["email.read"]})
    health = c.health_check()
    assert health.status == ConnectorHealthStatus.DEGRADED
    assert "email.send" in health.missing_permissions


def test_health_check_unauthorized_before_auth() -> None:
    c = MockEmailConnector()
    health = c.health_check()
    assert health.status == ConnectorHealthStatus.UNAUTHORIZED


# ---------------------------------------------------------------------------
# Registry: discovery and dependency reporting
# ---------------------------------------------------------------------------


def test_registry_register_and_get(registry: ConnectorRegistry, connector: MockEmailConnector) -> None:
    registry.register(connector)
    assert registry.get("mock_email") is connector
    assert registry.get("nonexistent") is None


def test_registry_require_raises_for_missing(registry: ConnectorRegistry) -> None:
    with pytest.raises(KeyError):
        registry.require("nope")


def test_registry_find_by_capability(registry: ConnectorRegistry, connector: MockEmailConnector) -> None:
    registry.register(connector)
    found = registry.find_by_capability(ConnectorCapability.EMAIL)
    assert connector in found
    assert registry.find_by_capability(ConnectorCapability.CRM) == []


def test_registry_namespaced_tool_definitions(registry: ConnectorRegistry, connector: MockEmailConnector) -> None:
    registry.register(connector)
    tools = registry.get_tool_definitions()
    names = {t["name"] for t in tools}
    assert "mock_email.send_email" in names


def test_registry_describe_dependencies_reports_health(
    registry: ConnectorRegistry, connector: MockEmailConnector
) -> None:
    registry.register(connector)
    report = registry.describe_dependencies()
    assert len(report) == 1
    assert report[0]["name"] == "mock_email"
    assert report[0]["capabilities"] == ["email"]
    assert report[0]["health"]["status"] == "healthy"


def test_registry_describe_dependencies_surfaces_unhealthy_connector(
    registry: ConnectorRegistry, connector: MockEmailConnector
) -> None:
    connector.simulate_outage(True)
    registry.register(connector)
    report = registry.describe_dependencies()
    assert report[0]["health"]["status"] == "down"


def test_default_registry_singleton_is_shared() -> None:
    a = get_registry()
    b = get_registry()
    assert a is b


# ---------------------------------------------------------------------------
# Custom connector smoke test (verifies the abstract contract is reusable)
# ---------------------------------------------------------------------------


class _EchoConnector(Connector):
    name = "echo"
    capabilities = (ConnectorCapability.CRM,)

    def authenticate(self, credentials: dict) -> None:
        self._authenticated = True
        self._granted_permissions = {"crm.read"}

    def list_actions(self) -> list[ActionSchema]:
        return [
            ActionSchema(
                name="echo",
                description="Echo back the input.",
                capability=ConnectorCapability.CRM,
                parameters={"value": {"type": "string"}},
                required_permissions=("crm.read",),
            )
        ]

    def _execute_action(self, action_name: str, **kwargs):
        return kwargs.get("value")


def test_custom_connector_implements_shared_contract() -> None:
    c = _EchoConnector()
    c.authenticate({})
    result = c.execute("echo", value="hi")
    assert result.success is True
    assert result.data == "hi"
