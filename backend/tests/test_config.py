"""Tests for AgentConfig API-key validation (issue #217)."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any


def _load_real_agent_config() -> Any:
    """Load the real agents/config.py directly by file path.

    conftest injects a lightweight FakeAgentConfig into sys.modules for
    `agents.config` so importing app.py does not pull the heavy `agents`
    package (langchain et al.). These unit tests exercise the *real* key-check
    logic, so we load config.py by path, bypassing both that stub and the
    package __init__. config.py only imports the standard library, so loading
    it standalone is safe.
    """
    path = Path(__file__).resolve().parents[1] / "agents" / "config.py"
    spec = importlib.util.spec_from_file_location("_real_agents_config", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.AgentConfig


AgentConfig = _load_real_agent_config()


def test_check_api_keys_openai_always_required(monkeypatch: Any) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "x")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr(AgentConfig, "DEFAULT_AGENT_MODEL_TYPE", 0)
    status = AgentConfig.check_api_keys()
    assert status["required"] == ["OPENAI_API_KEY"]
    assert status["ok"] is True
    assert status["missing"] == []


def test_check_api_keys_requires_anthropic_when_model_type_anthropic(
    monkeypatch: Any,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "x")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr(AgentConfig, "DEFAULT_AGENT_MODEL_TYPE", 1)
    status = AgentConfig.check_api_keys()
    assert "ANTHROPIC_API_KEY" in status["required"]
    assert status["ok"] is False
    assert status["missing"] == ["ANTHROPIC_API_KEY"]


def test_check_api_keys_flags_missing_openai(monkeypatch: Any) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(AgentConfig, "DEFAULT_AGENT_MODEL_TYPE", 0)
    status = AgentConfig.check_api_keys()
    assert status["ok"] is False
    assert "OPENAI_API_KEY" in status["missing"]
    assert status["present"]["OPENAI_API_KEY"] is False


def test_log_api_key_status_does_not_raise_and_returns_status(
    monkeypatch: Any,
) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(AgentConfig, "DEFAULT_AGENT_MODEL_TYPE", 0)
    # Non-blocking: logging a missing key must never raise.
    status = AgentConfig.log_api_key_status()
    assert status["ok"] is False


def test_health_keys_endpoint_exposes_only_ok_flag(client: Any) -> None:
    # Public endpoint: only an ok flag is exposed; details stay in logs.
    response = client.get("/health/keys")
    assert response.status_code == 200
    data = response.get_json()
    assert set(data) == {"ok"}
    assert isinstance(data["ok"], bool)
