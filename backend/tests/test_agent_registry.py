"""Tests for agents/registry.py — registry agent metadata, lookup, lifecycle,
and pre-run compatibility validation (issue #136: runtime integration of
registry agents into live workflows)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

import pytest


def _load_registry() -> Any:
    """Load agents/registry.py directly by file path.

    registry.py imports only the standard library, so loading it standalone
    avoids the heavy `agents` package __init__ (langchain/langgraph) and lets
    these tests run with no extra deps, no network, and no API key.

    The module is registered in sys.modules under its real name before
    exec'ing, because dataclasses' field-type resolution looks the defining
    module up via sys.modules[cls.__module__].
    """
    path = Path(__file__).resolve().parents[1] / "agents" / "registry.py"
    spec = importlib.util.spec_from_file_location("_agents_registry", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["_agents_registry"] = module
    spec.loader.exec_module(module)
    return module


registry_mod = _load_registry()


def _make_descriptor(**overrides: Any):
    defaults = dict(
        agent_id="lead-research-agent",
        name="Lead Research Agent",
        description="Sources and qualifies prospects for outreach workflows.",
        version="1.0.0",
        task_categories=("outreach", "lead-research"),
        required_tools=("web_search",),
        supported_providers=("openai", "anthropic"),
        required_permissions=("network.read",),
    )
    defaults.update(overrides)
    return registry_mod.AgentDescriptor(**defaults)


# -- AgentDescriptor validation -------------------------------------------- #


def test_descriptor_round_trips_to_dict() -> None:
    descriptor = _make_descriptor()
    as_dict = descriptor.to_dict()
    assert as_dict["agent_id"] == "lead-research-agent"
    assert as_dict["task_categories"] == ["outreach", "lead-research"]
    assert as_dict["status"] == registry_mod.AgentLifecycleStatus.ACTIVE


def test_descriptor_rejects_malformed_version() -> None:
    with pytest.raises(ValueError):
        _make_descriptor(version="not-a-version")


def test_descriptor_rejects_missing_agent_id() -> None:
    with pytest.raises(ValueError):
        _make_descriptor(agent_id="")


def test_descriptor_rejects_invalid_status() -> None:
    with pytest.raises(ValueError):
        _make_descriptor(status="archived")


def test_descriptor_version_tuple() -> None:
    descriptor = _make_descriptor(version="2.3.4")
    assert descriptor.version_tuple == (2, 3, 4)


# -- AgentRegistry: install / update / disable / deprecate ----------------- #


def test_install_and_get_agent() -> None:
    reg = registry_mod.AgentRegistry()
    descriptor = _make_descriptor()
    reg.install(descriptor)
    assert reg.get("lead-research-agent") == descriptor


def test_install_conflicting_redefinition_raises() -> None:
    reg = registry_mod.AgentRegistry()
    reg.install(_make_descriptor())
    with pytest.raises(ValueError):
        reg.install(_make_descriptor(description="A different description"))


def test_install_idempotent_for_identical_descriptor() -> None:
    reg = registry_mod.AgentRegistry()
    descriptor = _make_descriptor()
    reg.install(descriptor)
    reg.install(descriptor)  # no error
    assert reg.list_versions("lead-research-agent") == [descriptor]


def test_update_requires_existing_agent() -> None:
    reg = registry_mod.AgentRegistry()
    with pytest.raises(registry_mod.AgentNotFoundError):
        reg.update(_make_descriptor())


def test_update_publishes_new_version_and_keeps_old() -> None:
    reg = registry_mod.AgentRegistry()
    v1 = _make_descriptor(version="1.0.0")
    reg.install(v1)
    v2 = _make_descriptor(version="2.0.0", description="Improved sourcing logic.")
    reg.update(v2)

    assert reg.get("lead-research-agent") == v2  # latest resolves by default
    assert reg.get("lead-research-agent", version="1.0.0") == v1  # pinned still works
    assert len(reg.list_versions("lead-research-agent")) == 2


def test_get_unknown_agent_raises() -> None:
    reg = registry_mod.AgentRegistry()
    with pytest.raises(registry_mod.AgentNotFoundError):
        reg.get("does-not-exist")


def test_get_unknown_version_raises() -> None:
    reg = registry_mod.AgentRegistry()
    reg.install(_make_descriptor(version="1.0.0"))
    with pytest.raises(registry_mod.AgentNotFoundError):
        reg.get("lead-research-agent", version="9.9.9")


def test_disable_excludes_from_default_resolution() -> None:
    reg = registry_mod.AgentRegistry()
    reg.install(_make_descriptor(version="1.0.0"))
    reg.disable("lead-research-agent", "1.0.0")

    with pytest.raises(registry_mod.AgentNotFoundError):
        reg.get("lead-research-agent")  # no enabled versions left

    # Pinned lookup still finds it (so callers can introspect status / error nicely).
    pinned = reg.get("lead-research-agent", version="1.0.0")
    assert pinned.status == registry_mod.AgentLifecycleStatus.DISABLED


def test_deprecate_keeps_resolvable() -> None:
    reg = registry_mod.AgentRegistry()
    reg.install(_make_descriptor(version="1.0.0"))
    reg.deprecate("lead-research-agent", "1.0.0")

    resolved = reg.get("lead-research-agent")
    assert resolved.status == registry_mod.AgentLifecycleStatus.DEPRECATED


def test_default_resolution_prefers_active_over_deprecated_even_if_older() -> None:
    reg = registry_mod.AgentRegistry()
    v1 = _make_descriptor(version="1.0.0")
    v2 = _make_descriptor(version="2.0.0")
    reg.install(v1)
    reg.install(v2)
    reg.deprecate("lead-research-agent", "2.0.0")

    # v2 is newer but deprecated; v1 is active -> v1 should win.
    resolved = reg.get("lead-research-agent")
    assert resolved.version == "1.0.0"


def test_find_by_task_category() -> None:
    reg = registry_mod.AgentRegistry()
    reg.install(_make_descriptor(agent_id="lead-research-agent", task_categories=("outreach",)))
    reg.install(
        _make_descriptor(
            agent_id="code-review-agent",
            name="Code Review Agent",
            task_categories=("coding", "code-review"),
        )
    )

    matches = reg.find_by_task_category("outreach")
    assert [d.agent_id for d in matches] == ["lead-research-agent"]

    matches = reg.find_by_task_category("code-review")
    assert [d.agent_id for d in matches] == ["code-review-agent"]

    assert reg.find_by_task_category("nonexistent-category") == []


def test_list_agents() -> None:
    reg = registry_mod.AgentRegistry()
    reg.install(_make_descriptor(agent_id="b-agent"))
    reg.install(_make_descriptor(agent_id="a-agent"))
    assert reg.list_agents() == ["a-agent", "b-agent"]


# -- compatibility validation ------------------------------------------------ #


def test_compatibility_ok_when_all_requirements_met() -> None:
    descriptor = _make_descriptor()
    result = registry_mod.check_compatibility(
        descriptor,
        available_tools=["web_search"],
        available_providers=["openai"],
        granted_permissions=["network.read"],
    )
    assert result.ok
    assert result.issues == ()


def test_compatibility_reports_missing_tools() -> None:
    descriptor = _make_descriptor()
    result = registry_mod.check_compatibility(
        descriptor,
        available_tools=[],
        available_providers=["openai"],
        granted_permissions=["network.read"],
    )
    assert not result.ok
    assert any(issue.code == "missing_tools" for issue in result.issues)
    assert "web_search" in result.issues[0].message


def test_compatibility_reports_unsupported_provider() -> None:
    descriptor = _make_descriptor(supported_providers=("anthropic",))
    result = registry_mod.check_compatibility(
        descriptor,
        available_tools=["web_search"],
        available_providers=["openai"],
        granted_permissions=["network.read"],
    )
    assert not result.ok
    assert any(issue.code == "no_supported_provider" for issue in result.issues)


def test_compatibility_reports_missing_permissions() -> None:
    descriptor = _make_descriptor()
    result = registry_mod.check_compatibility(
        descriptor,
        available_tools=["web_search"],
        available_providers=["openai"],
        granted_permissions=[],
    )
    assert not result.ok
    assert any(issue.code == "missing_permissions" for issue in result.issues)


def test_compatibility_disabled_agent_is_blocking() -> None:
    descriptor = _make_descriptor(status=registry_mod.AgentLifecycleStatus.DISABLED)
    result = registry_mod.check_compatibility(
        descriptor,
        available_tools=["web_search"],
        available_providers=["openai"],
        granted_permissions=["network.read"],
    )
    assert not result.ok
    assert any(issue.code == "agent_disabled" for issue in result.issues)


def test_compatibility_deprecated_agent_is_advisory_not_blocking() -> None:
    descriptor = _make_descriptor(status=registry_mod.AgentLifecycleStatus.DEPRECATED)
    result = registry_mod.check_compatibility(
        descriptor,
        available_tools=["web_search"],
        available_providers=["openai"],
        granted_permissions=["network.read"],
    )
    assert result.ok  # deprecated alone shouldn't block a run
    assert any(issue.code == "agent_deprecated" for issue in result.issues)


def test_compatibility_result_raise_if_incompatible() -> None:
    descriptor = _make_descriptor()
    result = registry_mod.check_compatibility(
        descriptor, available_tools=[], available_providers=[], granted_permissions=[]
    )
    with pytest.raises(registry_mod.AgentCompatibilityError):
        result.raise_if_incompatible()


def test_compatibility_result_ok_does_not_raise() -> None:
    descriptor = _make_descriptor()
    result = registry_mod.check_compatibility(
        descriptor,
        available_tools=["web_search"],
        available_providers=["openai"],
        granted_permissions=["network.read"],
    )
    result.raise_if_incompatible()  # should not raise


def test_default_available_providers_reads_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert registry_mod._default_available_providers() == ["openai"]


# -- resolve_agent_for_run (the workflow-facing entry point) ---------------- #


def test_resolve_agent_for_run_success_records_resolved_version() -> None:
    reg = registry_mod.AgentRegistry()
    reg.install(_make_descriptor(version="1.0.0"))
    reg.install(_make_descriptor(version="2.0.0"))

    resolved = registry_mod.resolve_agent_for_run(
        reg,
        "lead-research-agent",
        version="1.0.0",
        available_tools=["web_search"],
        available_providers=["openai"],
        granted_permissions=["network.read"],
    )
    assert resolved.descriptor.version == "1.0.0"
    assert resolved.compatibility.ok


def test_resolve_agent_for_run_unknown_agent_raises_not_found() -> None:
    reg = registry_mod.AgentRegistry()
    with pytest.raises(registry_mod.AgentNotFoundError):
        registry_mod.resolve_agent_for_run(reg, "ghost-agent")


def test_resolve_agent_for_run_incompatible_raises_with_actionable_message() -> None:
    reg = registry_mod.AgentRegistry()
    reg.install(_make_descriptor())

    with pytest.raises(registry_mod.AgentCompatibilityError) as excinfo:
        registry_mod.resolve_agent_for_run(
            reg,
            "lead-research-agent",
            available_tools=[],
            available_providers=[],
            granted_permissions=[],
        )
    message = str(excinfo.value)
    assert "missing_tools" in message
    assert "web_search" in message


def test_resolve_agent_for_run_pins_older_version_after_workspace_update() -> None:
    """Mirrors the issue's example scenario: a workspace updates to a newer
    agent version, but a run pinned to the prior stable version keeps working."""
    reg = registry_mod.AgentRegistry()
    v1 = _make_descriptor(version="1.0.0")
    reg.install(v1)
    reg.update(_make_descriptor(version="2.0.0"))

    pinned_run = registry_mod.resolve_agent_for_run(
        reg,
        "lead-research-agent",
        version="1.0.0",
        available_tools=["web_search"],
        available_providers=["openai"],
        granted_permissions=["network.read"],
    )
    assert pinned_run.descriptor.version == "1.0.0"

    latest_run = registry_mod.resolve_agent_for_run(
        reg,
        "lead-research-agent",
        available_tools=["web_search"],
        available_providers=["openai"],
        granted_permissions=["network.read"],
    )
    assert latest_run.descriptor.version == "2.0.0"
