"""
Autonomous Intelligence Reactive Agent System

This package provides reactive agents that replace direct LLM calls with
intelligent agent workflows using LangChain and MCP servers.
"""

from .reactive_agent import ReactiveDocumentAgent, WorkflowReactiveAgent
from .config import AgentConfig
from .registry import (
    AgentCompatibilityError,
    AgentDescriptor,
    AgentLifecycleStatus,
    AgentNotFoundError,
    AgentRegistry,
    CompatibilityIssue,
    CompatibilityResult,
    ResolvedAgentRun,
    check_compatibility,
    default_registry,
    resolve_agent_for_run,
)

__all__ = [
    "ReactiveDocumentAgent",
    "WorkflowReactiveAgent",
    "AgentConfig",
    "AgentCompatibilityError",
    "AgentDescriptor",
    "AgentLifecycleStatus",
    "AgentNotFoundError",
    "AgentRegistry",
    "CompatibilityIssue",
    "CompatibilityResult",
    "ResolvedAgentRun",
    "check_compatibility",
    "default_registry",
    "resolve_agent_for_run",
]