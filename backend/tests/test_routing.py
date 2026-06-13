"""Tests for agents/routing.py — the model-driven routing helpers (issue: 6/9
reasoning-quality direction; mirrors Research PR #26's measured trade-off)."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any


def _load_routing() -> Any:
    """Load agents/routing.py directly by file path.

    routing.py imports only the standard library, so loading it standalone avoids
    the heavy `agents` package __init__ (langchain/langgraph) and lets these tests
    run with no extra deps, no network, and no API key.
    """
    path = Path(__file__).resolve().parents[1] / "agents" / "routing.py"
    spec = importlib.util.spec_from_file_location("_agents_routing", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


routing = _load_routing()


class _FakeStructured:
    def __init__(self, result: Any, raise_on_invoke: bool = False) -> None:
        self._result = result
        self._raise = raise_on_invoke

    def invoke(self, messages: Any) -> Any:
        if self._raise:
            raise RuntimeError("model failure")
        return self._result


class _FakeLLM:
    """Records structured-output usage; returns a preset result on invoke."""

    def __init__(self, result: Any = None, raise_on_invoke: bool = False) -> None:
        self._result = result
        self._raise = raise_on_invoke
        self.structured_calls = 0

    def with_structured_output(self, schema: Any) -> _FakeStructured:
        self.structured_calls += 1
        return _FakeStructured(self._result, self._raise)


# --- llm_boolean_decision -------------------------------------------------- #

def test_llm_boolean_decision_true() -> None:
    llm = _FakeLLM(result={"decision": True, "reasoning": "needs context"})
    assert routing.llm_boolean_decision(llm, "q?", "make the earlier one shorter") is True


def test_llm_boolean_decision_false() -> None:
    llm = _FakeLLM(result={"decision": False, "reasoning": "self-contained"})
    assert routing.llm_boolean_decision(llm, "q?", "what does EBITDA mean") is False


def test_llm_boolean_decision_none_on_bad_shape() -> None:
    llm = _FakeLLM(result={"reasoning": "no decision field"})
    assert routing.llm_boolean_decision(llm, "q?", "x") is None


def test_llm_boolean_decision_none_on_exception() -> None:
    llm = _FakeLLM(raise_on_invoke=True)
    assert routing.llm_boolean_decision(llm, "q?", "x") is None


def test_llm_boolean_decision_accepts_object_result() -> None:
    class _Obj:
        decision = True

    assert routing.llm_boolean_decision(_FakeLLM(result=_Obj()), "q?", "x") is True


# --- route_boolean --------------------------------------------------------- #

def test_route_boolean_disabled_uses_keyword_and_skips_model() -> None:
    llm = _FakeLLM(result={"decision": True, "reasoning": "x"})
    decision, source, _ = routing.route_boolean(
        llm, "q?", "query", keyword_result=False, enabled=False
    )
    assert decision is False
    assert source == "keyword"
    assert llm.structured_calls == 0  # model never consulted when disabled


def test_route_boolean_enabled_uses_model() -> None:
    llm = _FakeLLM(result={"decision": True, "reasoning": "x"})
    decision, source, _ = routing.route_boolean(
        llm, "q?", "query", keyword_result=False, enabled=True
    )
    assert decision is True
    assert source == "llm"


def test_route_boolean_falls_back_to_keyword_on_model_failure() -> None:
    llm = _FakeLLM(raise_on_invoke=True)
    decision, source, _ = routing.route_boolean(
        llm, "q?", "query", keyword_result=True, enabled=True
    )
    assert decision is True
    assert source == "keyword"
