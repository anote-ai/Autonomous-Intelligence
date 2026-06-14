"""Implicit RSI feedback-signal detection for document Q&A — issue #220 (slice 2).

Slice 1 (`database/qa_feedback.py`) added the `qa_feedback` table and the
`log_qa_feedback()` writer. This slice derives an **implicit** signal from chat
history with no UI change: a *rapid follow-up*. If the user asks again within a
short window of the previous answer, that answer was probably incomplete — a
soft-negative training signal for the RSI loop.

Same constraints as slice 1: opt-in (`ENABLE_RSI_FEEDBACK`) and best-effort
(detection/logging must never break a chat).

Wiring (slice 2 integration, intentionally NOT done here): call
`record_followup_if_any(user_email, chat_id, chat_type)` at the start of handling
a new user turn, before the new message is persisted. Kept out of the live
multi-agent path in this PR so the detection logic can land tested and reviewed
first; the call site is a one-liner (see PR description).
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from database.qa_feedback import log_qa_feedback, rsi_feedback_enabled

# A follow-up within this many seconds of the previous answer is treated as an
# implicit "that answer didn't fully land" signal.
FOLLOWUP_WINDOW_SECS = 30.0

# `retrieve_messages` is bound lazily from `database.db` on first use. This keeps
# the module importable (and `detect_followup_signal` unit-testable) without
# pulling the heavy DB module, and gives tests a clean seam to patch.
_retrieve_messages: Any = None


def _is_user(message: dict[str, Any]) -> bool:
    return bool(message.get("sent_from_user"))


def _age_seconds(created: Any, now: datetime) -> float | None:
    """Seconds between ``created`` and ``now``; None if ``created`` isn't a datetime."""
    if isinstance(created, datetime):
        return (now - created).total_seconds()
    return None  # unknown timestamp type → skip (best-effort)


def detect_followup_signal(
    messages: list[dict[str, Any]],
    now: datetime,
    window_secs: float = FOLLOWUP_WINDOW_SECS,
) -> dict[str, Any] | None:
    """Return a qa_feedback record for the most recent answer if the user is
    following up within ``window_secs`` of it, else ``None``.

    ``messages`` is chronological (oldest → newest), as returned by
    ``database.db.retrieve_messages`` (dicts with ``created``, ``id``,
    ``message_text``, ``sent_from_user``, ``relevant_chunks``).
    """
    if not messages:
        return None
    last = messages[-1]
    if _is_user(last):
        return None  # last turn is the user's; no answer to score yet
    age = _age_seconds(last.get("created"), now)
    if age is None or age < 0 or age > window_secs:
        return None

    question = ""
    for prev in reversed(messages[:-1]):
        if _is_user(prev):
            question = str(prev.get("message_text", ""))
            break

    return {
        "message_id": last.get("id"),
        "question": question,
        "answer": str(last.get("message_text", "")),
        "retrieved_chunks": last.get("relevant_chunks"),
        "feedback_signal": "followup",
        "source": "implicit",
    }


def record_followup_if_any(
    user_email: str,
    chat_id: int,
    chat_type: int,
    now: datetime | None = None,
) -> bool:
    """Best-effort: detect a rapid follow-up against this chat's history and log it.

    No-op (returns False) when RSI feedback is disabled. Never raises — a feedback
    side-channel must not break the chat response.
    """
    global _retrieve_messages
    if not rsi_feedback_enabled():
        return False
    try:
        if _retrieve_messages is None:
            from database.db import retrieve_messages

            _retrieve_messages = retrieve_messages
        messages = _retrieve_messages(user_email, chat_id, chat_type) or []
        record = detect_followup_signal(messages, now or datetime.now())
        if record is None:
            return False
        return log_qa_feedback(chat_id=chat_id, **record)
    except Exception as exc:  # detection must never break a chat
        print(f"[rsi] record_followup_if_any failed: {exc}")
        return False
