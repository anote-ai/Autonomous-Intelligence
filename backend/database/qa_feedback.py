"""RSI feedback logging for document Q&A — issue #220 (slice 1: foundation).

Persists implicit/explicit feedback signals on Q&A answers to the `qa_feedback`
table (migration 0002), so the RSI loop in later slices (re-ranker training,
answer self-consistency) has a training signal.

Design constraints:
- **Opt-in**: collection is OFF unless ``ENABLE_RSI_FEEDBACK`` is truthy, so
  production behaviour is unchanged until enabled.
- **Best-effort**: a logging failure must never break a chat response — every
  path is wrapped and returns a bool instead of raising (mirrors
  ``database/db_auth.py:touch_api_key_last_used``).
"""
from __future__ import annotations

import json
import os
from collections.abc import Sequence
from typing import Any

from database.db_pool import get_db_connection

# Implicit signals are derived from user behaviour; explicit ones from UI.
VALID_SIGNALS = frozenset(
    {
        "positive",
        "negative",
        "followup",  # follow-up question within a short window (implicit negative)
        "reask",  # same/similar question re-asked (implicit negative)
        "copy",  # copy-to-clipboard (implicit positive)
        "thumbs_up",
        "thumbs_down",
    }
)


def rsi_feedback_enabled() -> bool:
    """Whether RSI feedback collection is turned on (default off)."""
    return os.getenv("ENABLE_RSI_FEEDBACK", "false").lower() == "true"


def log_qa_feedback(
    *,
    chat_id: int,
    question: str,
    answer: str,
    feedback_signal: str,
    message_id: int | None = None,
    retrieved_chunks: str | Sequence[Any] | None = None,
    session_id: str | None = None,
    source: str = "implicit",
) -> bool:
    """Persist one feedback row. Returns True if written, False otherwise.

    No-op (returns False) when ``ENABLE_RSI_FEEDBACK`` is off or the signal is
    unknown. Never raises — a feedback-logging failure must not break the chat.
    """
    if not rsi_feedback_enabled():
        return False
    if feedback_signal not in VALID_SIGNALS:
        return False

    # retrieved_chunks may be a pre-serialized string (e.g. messages.relevant_chunks
    # from the DB) or a fresh sequence of chunks — handle both.
    if retrieved_chunks is None:
        chunks_json = None
    elif isinstance(retrieved_chunks, str):
        chunks_json = retrieved_chunks
    else:
        chunks_json = json.dumps(list(retrieved_chunks))
    conn = None
    try:
        conn, cursor = get_db_connection()
        cursor.execute(
            """
            INSERT INTO qa_feedback
                (chat_id, message_id, question, retrieved_chunks, answer,
                 feedback_signal, session_id, source)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            [
                chat_id,
                message_id,
                question,
                chunks_json,
                answer,
                feedback_signal,
                session_id,
                source,
            ],
        )
        conn.commit()
        return True
    except Exception as exc:  # never break a chat on feedback logging
        print(f"[rsi] log_qa_feedback failed: {exc}")
        return False
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass
