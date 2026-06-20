"""Shared connector contract for external system integrations.

Every connector (email, calendar, ATS, CRM, cloud storage, social platform,
...) implements the :class:`Connector` abstract base class defined here so
that agents can discover capabilities and invoke actions through a single,
typed interface rather than bespoke, provider-specific code paths.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

# ---------------------------------------------------------------------------
# Capability / action schema model
# ---------------------------------------------------------------------------


class ConnectorCapability(StrEnum):
    """Coarse-grained capability categories a connector may support.

    These map to the integration priorities called out in issue #138:
    email, calendar, ATS/job boards, CRM, cloud storage, and social
    platforms.
    """

    EMAIL = "email"
    CALENDAR = "calendar"
    ATS = "ats"
    CRM = "crm"
    STORAGE = "storage"
    SOCIAL = "social"


@dataclass(frozen=True)
class ActionSchema:
    """Typed description of a single action a connector exposes.

    This is the unit agents use for tool discovery: rather than hardcoding
    a bespoke function signature per provider, agents enumerate
    ``Connector.list_actions()`` and get back a list of these schemas which
    can be converted directly into LLM tool/function definitions.
    """

    name: str
    description: str
    capability: ConnectorCapability
    parameters: dict[str, Any] = field(default_factory=dict)
    required_permissions: tuple[str, ...] = field(default_factory=tuple)
    is_write: bool = False

    def to_tool_definition(self) -> dict[str, Any]:
        """Render this schema as an OpenAI/Anthropic-style tool definition."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": {
                "type": "object",
                "properties": self.parameters,
                "required": list(self.parameters.keys()),
            },
        }


@dataclass(frozen=True)
class RateLimit:
    """Simple fixed-window rate limit description for a connector."""

    max_calls: int
    window_seconds: float

    def __post_init__(self) -> None:
        if self.max_calls <= 0:
            raise ValueError("max_calls must be positive")
        if self.window_seconds <= 0:
            raise ValueError("window_seconds must be positive")


class ConnectorHealthStatus(StrEnum):
    """Operational state of a connector, surfaced to operator tooling."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAUTHORIZED = "unauthorized"
    DOWN = "down"
    UNKNOWN = "unknown"


@dataclass
class ConnectorHealth:
    """Health/permission snapshot for a connector instance."""

    status: ConnectorHealthStatus
    detail: str = ""
    missing_permissions: tuple[str, ...] = field(default_factory=tuple)
    checked_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "detail": self.detail,
            "missing_permissions": list(self.missing_permissions),
            "checked_at": self.checked_at,
        }


@dataclass
class ConnectorAction:
    """The result of invoking an action on a connector."""

    success: bool
    data: Any = None
    error: ConnectorError | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error.to_dict() if self.error else None,
        }


# ---------------------------------------------------------------------------
# Structured errors
# ---------------------------------------------------------------------------


class ConnectorError(Exception):
    """Base class for actionable connector errors.

    Carries enough structure (``retryable``, ``fallback_hint``) for the
    runtime to decide whether to retry, fall back to another connector, or
    surface the failure to the operator.
    """

    def __init__(
        self,
        message: str,
        *,
        retryable: bool = False,
        fallback_hint: str | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.retryable = retryable
        self.fallback_hint = fallback_hint

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": type(self).__name__,
            "message": self.message,
            "retryable": self.retryable,
            "fallback_hint": self.fallback_hint,
        }


class ConnectorPermissionError(ConnectorError):
    """Raised when the connector lacks permission to perform an action."""

    def __init__(self, message: str, *, missing_permissions: tuple[str, ...] = ()) -> None:
        super().__init__(
            message,
            retryable=False,
            fallback_hint="Reconnect or re-authorize the connector with the required scopes.",
        )
        self.missing_permissions = missing_permissions

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        data["missing_permissions"] = list(self.missing_permissions)
        return data


class ConnectorRateLimitError(ConnectorError):
    """Raised when a connector's rate limit has been exceeded."""

    def __init__(self, message: str, *, retry_after_seconds: float) -> None:
        super().__init__(
            message,
            retryable=True,
            fallback_hint="Retry after the cooldown window or route to a fallback connector.",
        )
        self.retry_after_seconds = retry_after_seconds

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        data["retry_after_seconds"] = self.retry_after_seconds
        return data


class ConnectorAuthError(ConnectorError):
    """Raised when authentication with the external system fails."""

    def __init__(self, message: str) -> None:
        super().__init__(
            message,
            retryable=False,
            fallback_hint="Refresh credentials and retry the connection.",
        )


# ---------------------------------------------------------------------------
# Rate limiter helper (simple fixed-window counter, in-process)
# ---------------------------------------------------------------------------


class _FixedWindowLimiter:
    def __init__(self, rate_limit: RateLimit | None) -> None:
        self._rate_limit = rate_limit
        self._window_start = time.time()
        self._calls_in_window = 0

    def check(self) -> None:
        if self._rate_limit is None:
            return
        now = time.time()
        elapsed = now - self._window_start
        if elapsed >= self._rate_limit.window_seconds:
            self._window_start = now
            self._calls_in_window = 0
        if self._calls_in_window >= self._rate_limit.max_calls:
            retry_after = self._rate_limit.window_seconds - elapsed
            raise ConnectorRateLimitError(
                f"Rate limit of {self._rate_limit.max_calls} calls per "
                f"{self._rate_limit.window_seconds}s exceeded.",
                retry_after_seconds=max(retry_after, 0.0),
            )
        self._calls_in_window += 1


# ---------------------------------------------------------------------------
# Connector base class
# ---------------------------------------------------------------------------


class Connector(ABC):
    """Shared interface every connector implementation must satisfy.

    Subclasses provide:
      * ``name`` / ``capabilities`` describing what the connector is and does.
      * ``authenticate()`` to establish/validate credentials.
      * ``list_actions()`` for capability discovery (typed tool definitions).
      * ``execute(action_name, **kwargs)`` to perform a read/write action.
      * ``health_check()`` to report operational + permission state.
    """

    #: Human-readable connector name, e.g. "gmail", "google_calendar".
    name: str = "connector"

    #: Capabilities this connector exposes (email, calendar, crm, ...).
    capabilities: tuple[ConnectorCapability, ...] = ()

    #: Optional rate limit applied to every ``execute`` call.
    rate_limit: RateLimit | None = None

    def __init__(self) -> None:
        self._authenticated = False
        self._granted_permissions: set[str] = set()
        self._limiter = _FixedWindowLimiter(self.rate_limit)

    # -- auth -----------------------------------------------------------

    @abstractmethod
    def authenticate(self, credentials: dict[str, Any]) -> None:
        """Validate and store credentials for this connector instance.

        Implementations should set ``self._authenticated`` and populate
        ``self._granted_permissions`` based on the scopes present in
        *credentials*.
        """

    @property
    def is_authenticated(self) -> bool:
        return self._authenticated

    @property
    def granted_permissions(self) -> frozenset[str]:
        return frozenset(self._granted_permissions)

    # -- capability discovery --------------------------------------------

    @abstractmethod
    def list_actions(self) -> list[ActionSchema]:
        """Return the typed action schemas this connector supports."""

    def get_tool_definitions(self) -> list[dict[str, Any]]:
        """Convenience wrapper: actions rendered as LLM tool definitions."""
        return [action.to_tool_definition() for action in self.list_actions()]

    def _find_action(self, action_name: str) -> ActionSchema:
        for action in self.list_actions():
            if action.name == action_name:
                return action
        raise ConnectorError(
            f"Unknown action '{action_name}' for connector '{self.name}'.",
            retryable=False,
            fallback_hint="Call list_actions() to discover supported actions.",
        )

    # -- execution --------------------------------------------------------

    def execute(self, action_name: str, **kwargs: Any) -> ConnectorAction:
        """Validate, rate-limit, and dispatch *action_name* with *kwargs*.

        Wraps :meth:`_execute_action` so that every connector gets
        permission checks, rate limiting, and structured error handling for
        free.
        """
        try:
            action = self._find_action(action_name)
        except ConnectorError as exc:
            return ConnectorAction(success=False, error=exc)

        if not self.is_authenticated:
            auth_error = ConnectorAuthError(
                f"Connector '{self.name}' is not authenticated."
            )
            return ConnectorAction(success=False, error=auth_error)

        missing = [
            perm for perm in action.required_permissions
            if perm not in self._granted_permissions
        ]
        if missing:
            permission_error = ConnectorPermissionError(
                f"Connector '{self.name}' is missing permissions for "
                f"action '{action_name}': {', '.join(missing)}.",
                missing_permissions=tuple(missing),
            )
            return ConnectorAction(success=False, error=permission_error)

        try:
            self._limiter.check()
        except ConnectorRateLimitError as exc:
            return ConnectorAction(success=False, error=exc)

        try:
            result = self._execute_action(action_name, **kwargs)
            return ConnectorAction(success=True, data=result)
        except ConnectorError as exc:
            return ConnectorAction(success=False, error=exc)
        except Exception as exc:  # pragma: no cover - defensive catch-all
            wrapped = ConnectorError(
                f"Unexpected error executing '{action_name}' on "
                f"'{self.name}': {exc}",
                retryable=True,
                fallback_hint="Retry once; escalate to operator if it recurs.",
            )
            return ConnectorAction(success=False, error=wrapped)

    @abstractmethod
    def _execute_action(self, action_name: str, **kwargs: Any) -> Any:
        """Subclass hook implementing the actual side effect for an action."""

    # -- health -------------------------------------------------------------

    def health_check(self) -> ConnectorHealth:
        """Default health check; subclasses may override for richer checks."""
        if not self.is_authenticated:
            return ConnectorHealth(
                status=ConnectorHealthStatus.UNAUTHORIZED,
                detail=f"Connector '{self.name}' has not authenticated.",
            )
        required = {
            perm
            for action in self.list_actions()
            for perm in action.required_permissions
        }
        missing = tuple(sorted(required - self._granted_permissions))
        if missing:
            return ConnectorHealth(
                status=ConnectorHealthStatus.DEGRADED,
                detail="Some actions are unavailable due to missing permissions.",
                missing_permissions=missing,
            )
        return ConnectorHealth(status=ConnectorHealthStatus.HEALTHY, detail="OK")
