"""Model-driven routing helpers for the multi-agent system.

Panacea's agents historically branch on keyword matching (e.g.
``any(kw in query.lower() for kw in [...])``). Research PR #26
(Research-OrchestrateBench) measured that this keyword routing fails on
adversarial phrasings — 0% there — where a model that reasons about intent
succeeds. These helpers provide an opt-in, model-driven alternative; callers
fall back to keyword matching whenever routing is disabled or the model call
fails, so nothing here can break a live query.

Kept dependency-light on purpose (standard library only): the chat model is
passed in as ``llm``, so this module never imports the heavy agent stack and is
unit-testable with a fake.
"""

from __future__ import annotations

from typing import Any

# JSON schema for a single yes/no routing decision. Passed to LangChain's
# ``with_structured_output`` so the model must return exactly this shape.
_DECISION_SCHEMA = {
    "title": "RoutingDecision",
    "description": "A yes/no routing decision about a user's query.",
    "type": "object",
    "properties": {
        "decision": {
            "type": "boolean",
            "description": "True if the answer to the routing question is yes.",
        },
        "reasoning": {
            "type": "string",
            "description": "One short sentence justifying the decision.",
        },
    },
    "required": ["decision", "reasoning"],
}

_SYSTEM_PROMPT = (
    "You are the router for a document Q&A assistant. Answer the yes/no question "
    "about the user's query by reasoning about its actual intent. Do NOT rely on "
    "keyword matching — the wording may omit the obvious keywords or use "
    "misleading ones. Return your answer via the structured schema."
)


def llm_boolean_decision(llm: Any, question: str, query: str) -> bool | None:
    """Ask ``llm`` a yes/no routing ``question`` about ``query``.

    Returns the boolean decision, or ``None`` if the model path is unavailable or
    the call/parse fails — callers should fall back to keyword matching on
    ``None``. Never raises.
    """
    try:
        structured = llm.with_structured_output(_DECISION_SCHEMA)
        result = structured.invoke(
            [
                ("system", _SYSTEM_PROMPT),
                ("human", f"Question: {question}\nUser query: {query!r}"),
            ]
        )
    except Exception:
        # Defensive: a routing decision must never crash a live query.
        return None
    return _extract_decision(result)


def _extract_decision(result: Any) -> bool | None:
    """Pull a bool ``decision`` out of a structured-output result, defensively."""
    if isinstance(result, dict):
        value = result.get("decision")
    else:  # pydantic model / namespace fallback
        value = getattr(result, "decision", None)
    return value if isinstance(value, bool) else None


def route_boolean(
    llm: Any,
    question: str,
    query: str,
    keyword_result: bool,
    enabled: bool,
) -> tuple[bool, str, str]:
    """Resolve a yes/no routing decision, preferring the model when enabled.

    Returns ``(decision, source, reasoning)`` where ``source`` is ``"llm"`` or
    ``"keyword"``. Falls back to ``keyword_result`` when routing is disabled or the
    model call fails, so the existing keyword behaviour is always the safety net.
    """
    if not enabled:
        return keyword_result, "keyword", "LLM routing disabled; used keyword match."
    decision = llm_boolean_decision(llm, question, query)
    if decision is None:
        return (
            keyword_result,
            "keyword",
            "LLM routing unavailable; fell back to keyword match.",
        )
    return decision, "llm", "Decided by reasoning over the query's intent."
