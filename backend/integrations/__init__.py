"""Integration / connector framework for external systems.

This package provides a first-class connector layer so that agents can act
on external systems (email, calendar, ATS, CRM, cloud storage, social
platforms, ...) through a shared, typed interface instead of bespoke
provider calls embedded directly in workflows.

Scope of this initial implementation (see GitHub issue #138):

* ``base.py`` defines the shared connector contract: auth, capability
  discovery, typed action schemas, health checks and structured errors.
* ``registry.py`` provides a process-wide registry so agents/tools can look
  up connectors by name and discover which external systems a project
  depends on before a run starts.
* ``mocks.py`` ships a fully working in-memory email connector that
  implements the contract, suitable for tests and connector development
  sandboxes.

Follow-up work (out of scope here): real OAuth-backed connectors for
calendar/ATS/CRM/storage/social platforms, retry/fallback policy execution,
and an operator-console UI for connector health/permission state.
"""

from .base import (
    ActionSchema,
    Connector,
    ConnectorAction,
    ConnectorCapability,
    ConnectorError,
    ConnectorHealth,
    ConnectorHealthStatus,
    ConnectorPermissionError,
    ConnectorRateLimitError,
    RateLimit,
)
from .registry import ConnectorRegistry, get_registry

__all__ = [
    "ActionSchema",
    "Connector",
    "ConnectorAction",
    "ConnectorCapability",
    "ConnectorError",
    "ConnectorHealth",
    "ConnectorHealthStatus",
    "ConnectorPermissionError",
    "ConnectorRateLimitError",
    "ConnectorRegistry",
    "RateLimit",
    "get_registry",
]
