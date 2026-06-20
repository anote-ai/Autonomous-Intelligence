"""Process-wide registry for connector instances.

The registry lets agents look up connectors by name (typed tool selection
instead of bespoke code paths) and lets the runtime/operator console ask
"which external systems does this project depend on, and are they
healthy?" before a run starts.
"""

from __future__ import annotations

from typing import Any

from .base import Connector, ConnectorCapability, ConnectorHealth


class ConnectorRegistry:
    """In-memory registry mapping connector names to instances."""

    def __init__(self) -> None:
        self._connectors: dict[str, Connector] = {}

    def register(self, connector: Connector) -> None:
        """Register *connector*, keyed by its ``name`` attribute."""
        if not connector.name:
            raise ValueError("Connector must have a non-empty 'name'.")
        self._connectors[connector.name] = connector

    def unregister(self, name: str) -> None:
        self._connectors.pop(name, None)

    def get(self, name: str) -> Connector | None:
        return self._connectors.get(name)

    def require(self, name: str) -> Connector:
        connector = self.get(name)
        if connector is None:
            raise KeyError(f"No connector registered under name '{name}'.")
        return connector

    def list_connectors(self) -> list[Connector]:
        return list(self._connectors.values())

    def find_by_capability(self, capability: ConnectorCapability) -> list[Connector]:
        """Return all registered connectors that support *capability*.

        This is how agents discover a connector for a task ("I need an
        email connector") without hardcoding a specific provider.
        """
        return [
            connector
            for connector in self._connectors.values()
            if capability in connector.capabilities
        ]

    def get_tool_definitions(self) -> list[dict[str, Any]]:
        """Aggregate tool definitions across every registered connector.

        Each tool definition is namespaced with the connector name so
        agents can disambiguate identical action names across providers
        (e.g. ``gmail.send_email`` vs ``outlook.send_email``).
        """
        definitions: list[dict[str, Any]] = []
        for connector in self._connectors.values():
            for tool in connector.get_tool_definitions():
                namespaced = dict(tool)
                namespaced["name"] = f"{connector.name}.{tool['name']}"
                definitions.append(namespaced)
        return definitions

    def describe_dependencies(self) -> list[dict[str, Any]]:
        """Report which external systems are registered and their health.

        Intended to back a "pre-run dependency check": before an agent run
        starts, the runtime can call this to surface unhealthy or
        unauthorized connectors to the operator.
        """
        report: list[dict[str, Any]] = []
        for connector in self._connectors.values():
            health: ConnectorHealth = connector.health_check()
            report.append(
                {
                    "name": connector.name,
                    "capabilities": [c.value for c in connector.capabilities],
                    "health": health.to_dict(),
                }
            )
        return report

    def clear(self) -> None:
        """Remove all registered connectors. Primarily for test isolation."""
        self._connectors.clear()


_default_registry = ConnectorRegistry()


def get_registry() -> ConnectorRegistry:
    """Return the process-wide default :class:`ConnectorRegistry`."""
    return _default_registry
