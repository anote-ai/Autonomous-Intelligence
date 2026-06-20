"""
Agent Registry — runtime integration for registry-backed agents.

This module gives registry agents structured, machine-checkable metadata and a
resolution/compatibility-validation layer so that workflows and crews can
reference an agent by a stable ``(agent_id, version)`` pair and have the
runtime verify — before a run starts — that the agent can actually execute in
the current environment (required tools present, model/provider available,
permissions satisfied).

This is the foundation piece of the larger "registry agents in live
workflows" effort (see GitHub issue #136). It intentionally does not attempt
the entire epic (install/update/disable/deprecate lifecycle HTTP endpoints,
the frontend builder UI, etc.) — see the PR description for what is
explicitly out of scope.
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


_VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")


class AgentLifecycleStatus:
    """Lifecycle states a registry agent version can be in."""

    ACTIVE = "active"
    DEPRECATED = "deprecated"
    DISABLED = "disabled"

    ALL = (ACTIVE, DEPRECATED, DISABLED)


def _parse_version(version: str) -> Tuple[int, int, int]:
    if not _VERSION_RE.match(version or ""):
        raise ValueError(
            f"Invalid agent version '{version}'. Expected semantic version 'MAJOR.MINOR.PATCH'."
        )
    major, minor, patch = (int(part) for part in version.split("."))
    return major, minor, patch


@dataclass(frozen=True)
class AgentDescriptor:
    """Structured metadata describing one version of a registry agent.

    This is the descriptor referenced in the issue's "Agent Metadata" scope:
    name, description, version, supported task categories, tool
    requirements, model/provider requirements, input/output expectations,
    and permission requirements.
    """

    agent_id: str
    name: str
    description: str
    version: str
    task_categories: Tuple[str, ...] = field(default_factory=tuple)
    required_tools: Tuple[str, ...] = field(default_factory=tuple)
    supported_providers: Tuple[str, ...] = field(default_factory=tuple)
    required_permissions: Tuple[str, ...] = field(default_factory=tuple)
    input_schema: Dict[str, Any] = field(default_factory=dict)
    output_schema: Dict[str, Any] = field(default_factory=dict)
    status: str = AgentLifecycleStatus.ACTIVE

    def __post_init__(self) -> None:
        if not self.agent_id:
            raise ValueError("agent_id is required")
        if not self.name:
            raise ValueError("name is required")
        _parse_version(self.version)  # raises ValueError if malformed
        if self.status not in AgentLifecycleStatus.ALL:
            raise ValueError(
                f"Invalid status '{self.status}'. Must be one of {AgentLifecycleStatus.ALL}."
            )

    @property
    def version_tuple(self) -> Tuple[int, int, int]:
        return _parse_version(self.version)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "task_categories": list(self.task_categories),
            "required_tools": list(self.required_tools),
            "supported_providers": list(self.supported_providers),
            "required_permissions": list(self.required_permissions),
            "input_schema": self.input_schema,
            "output_schema": self.output_schema,
            "status": self.status,
        }


@dataclass(frozen=True)
class CompatibilityIssue:
    """A single actionable compatibility failure."""

    code: str
    message: str


@dataclass(frozen=True)
class CompatibilityResult:
    """Outcome of validating an agent descriptor against a runtime environment."""

    ok: bool
    issues: Tuple[CompatibilityIssue, ...] = field(default_factory=tuple)

    def raise_if_incompatible(self) -> None:
        if not self.ok:
            details = "; ".join(f"[{issue.code}] {issue.message}" for issue in self.issues)
            raise AgentCompatibilityError(details, self.issues)


class AgentCompatibilityError(RuntimeError):
    """Raised when a resolved agent fails a pre-run compatibility check."""

    def __init__(self, message: str, issues: Tuple[CompatibilityIssue, ...] = ()):
        super().__init__(message)
        self.issues = issues


class AgentNotFoundError(LookupError):
    """Raised when a workflow references an agent_id/version that does not exist."""


class AgentRegistry:
    """In-memory registry of versioned agent descriptors.

    Supports the lifecycle operations called out in the issue: install,
    update (publish a new version), disable, and deprecate. Multiple
    versions of the same agent_id may coexist so that runs pinned to an
    older version keep working after a workspace updates to a newer one.
    """

    def __init__(self) -> None:
        # agent_id -> version -> descriptor
        self._agents: Dict[str, Dict[str, AgentDescriptor]] = {}

    # -- lifecycle -----------------------------------------------------
    def install(self, descriptor: AgentDescriptor) -> None:
        """Install (register) a new agent version. Idempotent re-install of
        the same agent_id/version with identical metadata is allowed; a
        conflicting redefinition is rejected."""
        versions = self._agents.setdefault(descriptor.agent_id, {})
        existing = versions.get(descriptor.version)
        if existing is not None and existing != descriptor:
            raise ValueError(
                f"Agent '{descriptor.agent_id}' version '{descriptor.version}' is already "
                "installed with different metadata. Publish a new version instead."
            )
        versions[descriptor.version] = descriptor
        logger.info("Installed agent %s@%s", descriptor.agent_id, descriptor.version)

    def update(self, descriptor: AgentDescriptor) -> None:
        """Publish a new version of an existing agent. Older versions remain
        installed and resolvable so pinned runs are unaffected."""
        if descriptor.agent_id not in self._agents:
            raise AgentNotFoundError(
                f"Cannot update unknown agent '{descriptor.agent_id}'. Install it first."
            )
        self.install(descriptor)

    def disable(self, agent_id: str, version: str) -> None:
        """Mark a specific version as disabled. Disabled versions fail
        compatibility checks at resolution time but are not deleted."""
        descriptor = self._require(agent_id, version)
        self._agents[agent_id][version] = AgentDescriptor(
            **{**descriptor.to_dict(), "status": AgentLifecycleStatus.DISABLED}
        )

    def deprecate(self, agent_id: str, version: str) -> None:
        """Mark a specific version as deprecated. Deprecated versions still
        resolve and run (so existing pinned workflows are not broken) but
        compatibility checks will return a warning-level issue callers can
        surface to users."""
        descriptor = self._require(agent_id, version)
        self._agents[agent_id][version] = AgentDescriptor(
            **{**descriptor.to_dict(), "status": AgentLifecycleStatus.DEPRECATED}
        )

    # -- lookup ----------------------------------------------------------
    def _require(self, agent_id: str, version: str) -> AgentDescriptor:
        versions = self._agents.get(agent_id)
        if not versions or version not in versions:
            raise AgentNotFoundError(f"Agent '{agent_id}' version '{version}' not found in registry.")
        return versions[version]

    def get(self, agent_id: str, version: Optional[str] = None) -> AgentDescriptor:
        """Resolve an agent by id and (optional) version. When version is
        omitted, resolves to the highest installed version that is not
        disabled (preferring active over deprecated)."""
        versions = self._agents.get(agent_id)
        if not versions:
            raise AgentNotFoundError(f"Agent '{agent_id}' is not in the registry.")
        if version is not None:
            return self._require(agent_id, version)

        candidates = [d for d in versions.values() if d.status != AgentLifecycleStatus.DISABLED]
        if not candidates:
            raise AgentNotFoundError(
                f"Agent '{agent_id}' has no enabled versions installed."
            )
        candidates.sort(
            key=lambda d: (d.status == AgentLifecycleStatus.ACTIVE, d.version_tuple),
            reverse=True,
        )
        return candidates[0]

    def list_versions(self, agent_id: str) -> List[AgentDescriptor]:
        versions = self._agents.get(agent_id, {})
        return sorted(versions.values(), key=lambda d: d.version_tuple)

    def list_agents(self) -> List[str]:
        return sorted(self._agents.keys())

    def find_by_task_category(self, task_category: str) -> List[AgentDescriptor]:
        """Orchestration-time routing helper: return the best (highest
        version, enabled) descriptor per agent_id that supports the given
        task category."""
        matches = []
        for agent_id in self._agents:
            try:
                descriptor = self.get(agent_id)
            except AgentNotFoundError:
                continue
            if task_category in descriptor.task_categories:
                matches.append(descriptor)
        return matches


# -- compatibility validation --------------------------------------------

def check_compatibility(
    descriptor: AgentDescriptor,
    *,
    available_tools: Optional[List[str]] = None,
    available_providers: Optional[List[str]] = None,
    granted_permissions: Optional[List[str]] = None,
) -> CompatibilityResult:
    """Validate that ``descriptor`` can run given the current runtime
    environment. Mirrors the issue's acceptance criterion: "Compatibility
    failures are caught before or at run startup with actionable errors."

    Environment values default to reading from the process (env vars / a
    static capability list) when not explicitly supplied, so callers can
    either pass exact values (e.g. in tests) or rely on defaults in
    production call sites.
    """
    issues: List[CompatibilityIssue] = []

    if descriptor.status == AgentLifecycleStatus.DISABLED:
        issues.append(
            CompatibilityIssue(
                code="agent_disabled",
                message=(
                    f"Agent '{descriptor.agent_id}'@{descriptor.version} has been disabled "
                    "and cannot be used in new runs."
                ),
            )
        )

    if descriptor.status == AgentLifecycleStatus.DEPRECATED:
        issues.append(
            CompatibilityIssue(
                code="agent_deprecated",
                message=(
                    f"Agent '{descriptor.agent_id}'@{descriptor.version} is deprecated. "
                    "Consider migrating to a newer version."
                ),
            )
        )

    tools = set(available_tools if available_tools is not None else _default_available_tools())
    missing_tools = [tool for tool in descriptor.required_tools if tool not in tools]
    if missing_tools:
        issues.append(
            CompatibilityIssue(
                code="missing_tools",
                message=(
                    f"Agent '{descriptor.agent_id}' requires tool(s) {missing_tools} "
                    "which are not registered in this environment."
                ),
            )
        )

    providers = set(
        available_providers if available_providers is not None else _default_available_providers()
    )
    if descriptor.supported_providers and not (set(descriptor.supported_providers) & providers):
        issues.append(
            CompatibilityIssue(
                code="no_supported_provider",
                message=(
                    f"Agent '{descriptor.agent_id}' supports provider(s) "
                    f"{list(descriptor.supported_providers)}, but none are configured "
                    f"(available: {sorted(providers)})."
                ),
            )
        )

    permissions = set(granted_permissions if granted_permissions is not None else [])
    missing_permissions = [
        perm for perm in descriptor.required_permissions if perm not in permissions
    ]
    if missing_permissions:
        issues.append(
            CompatibilityIssue(
                code="missing_permissions",
                message=(
                    f"Agent '{descriptor.agent_id}' requires permission(s) "
                    f"{missing_permissions} that have not been granted to this run."
                ),
            )
        )

    # "disabled"/"deprecated" issues are advisory for deprecated but blocking for disabled.
    blocking = [i for i in issues if i.code != "agent_deprecated"]
    return CompatibilityResult(ok=not blocking, issues=tuple(issues))


def _default_available_tools() -> List[str]:
    return []


def _default_available_providers() -> List[str]:
    providers = []
    if os.getenv("OPENAI_API_KEY"):
        providers.append("openai")
    if os.getenv("ANTHROPIC_API_KEY"):
        providers.append("anthropic")
    return providers


# -- workflow-facing resolution -------------------------------------------

@dataclass(frozen=True)
class ResolvedAgentRun:
    """Result of resolving + validating a registry agent reference for a run.

    ``descriptor`` carries the exact agent version that participated, which
    callers should persist alongside the run record (acceptance criterion:
    "Runs record the specific agent version used.").
    """

    descriptor: AgentDescriptor
    compatibility: CompatibilityResult


def resolve_agent_for_run(
    registry: AgentRegistry,
    agent_id: str,
    version: Optional[str] = None,
    *,
    available_tools: Optional[List[str]] = None,
    available_providers: Optional[List[str]] = None,
    granted_permissions: Optional[List[str]] = None,
) -> ResolvedAgentRun:
    """Resolve a registry agent reference (id + optional pinned version) and
    run its pre-flight compatibility check. Raises ``AgentNotFoundError`` if
    the agent/version is unknown, or ``AgentCompatibilityError`` if it fails
    a blocking compatibility check. On success, returns the resolved
    descriptor (including the exact version) for the caller to record on
    the run.
    """
    descriptor = registry.get(agent_id, version)
    compatibility = check_compatibility(
        descriptor,
        available_tools=available_tools,
        available_providers=available_providers,
        granted_permissions=granted_permissions,
    )
    compatibility.raise_if_incompatible()
    return ResolvedAgentRun(descriptor=descriptor, compatibility=compatibility)


# A module-level default registry instance that the rest of the backend
# (multi_agent_system, future API endpoints) can import and populate.
default_registry = AgentRegistry()
