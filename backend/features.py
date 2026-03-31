"""
Feature flags for the Anote AI backend.

Each flag reads from an environment variable and defaults to ``True`` so that
the full-featured deployment works out of the box.  Set the variable to
``"false"`` (case-insensitive) to disable the feature.
"""

import os


def _flag(env_var: str, default: bool = True) -> bool:
    raw = os.getenv(env_var, "true" if default else "false")
    return raw.strip().lower() not in ("false", "0", "no", "off")


def is_finance_gpt_enabled() -> bool:
    """Return True when the FinanceGPT / RAG chatbot feature is active.

    Controlled by the ``ENABLE_FINANCE_GPT`` environment variable (default: enabled).
    Disable to run as a plain chat-completion API server without document Q&A.
    """
    return _flag("ENABLE_FINANCE_GPT", default=True)


def is_agent_enabled() -> bool:
    """Return True when the autonomous-agent system is active.

    This mirrors :py:meth:`agents.config.AgentConfig.is_agent_enabled` but is
    accessible without importing the full agent stack.  Controlled by the
    ``ENABLE_AGENTS`` environment variable (default: enabled).
    """
    return _flag("ENABLE_AGENTS", default=True)
