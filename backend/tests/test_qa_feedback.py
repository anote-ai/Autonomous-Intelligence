"""Tests for database/qa_feedback.py — RSI feedback logging (issue #220, slice 1).

No real DB: get_db_connection is monkeypatched with a fake connection, so these
run offline under the conftest mysql stub.
"""

from __future__ import annotations

from typing import Any

from database import qa_feedback


class _FakeCursor:
    def __init__(self) -> None:
        self.executed: list[tuple[str, Any]] = []

    def execute(self, sql: str, params: Any = None) -> None:
        self.executed.append((sql, params))


class _FakeConn:
    def __init__(self) -> None:
        self.cursor_obj = _FakeCursor()
        self.committed = False
        self.closed = False

    def commit(self) -> None:
        self.committed = True

    def close(self) -> None:
        self.closed = True


def _install_fake(monkeypatch: Any) -> _FakeConn:
    conn = _FakeConn()
    monkeypatch.setattr(qa_feedback, "get_db_connection", lambda: (conn, conn.cursor_obj))
    return conn


def test_disabled_is_noop(monkeypatch: Any) -> None:
    monkeypatch.setenv("ENABLE_RSI_FEEDBACK", "false")
    conn = _install_fake(monkeypatch)
    assert qa_feedback.log_qa_feedback(
        chat_id=1, question="q", answer="a", feedback_signal="copy"
    ) is False
    assert conn.cursor_obj.executed == []  # no DB write when the flag is off


def test_enabled_writes_row(monkeypatch: Any) -> None:
    monkeypatch.setenv("ENABLE_RSI_FEEDBACK", "true")
    conn = _install_fake(monkeypatch)
    ok = qa_feedback.log_qa_feedback(
        chat_id=7,
        question="what is EBITDA",
        answer="earnings before...",
        feedback_signal="thumbs_up",
        message_id=42,
        retrieved_chunks=["c1", "c2"],
        session_id="s1",
        source="explicit",
    )
    assert ok is True
    assert conn.committed is True and conn.closed is True
    assert len(conn.cursor_obj.executed) == 1
    sql, params = conn.cursor_obj.executed[0]
    assert "INSERT INTO qa_feedback" in sql
    assert params[0] == 7
    assert params[5] == "thumbs_up"
    assert params[3] == '["c1", "c2"]'  # retrieved_chunks serialized to JSON


def test_invalid_signal_rejected(monkeypatch: Any) -> None:
    monkeypatch.setenv("ENABLE_RSI_FEEDBACK", "true")
    conn = _install_fake(monkeypatch)
    assert qa_feedback.log_qa_feedback(
        chat_id=1, question="q", answer="a", feedback_signal="bogus"
    ) is False
    assert conn.cursor_obj.executed == []


def test_db_failure_is_swallowed(monkeypatch: Any) -> None:
    monkeypatch.setenv("ENABLE_RSI_FEEDBACK", "true")

    def _boom() -> Any:
        raise RuntimeError("db down")

    monkeypatch.setattr(qa_feedback, "get_db_connection", _boom)
    # Must not raise — feedback logging can never break a chat response.
    assert qa_feedback.log_qa_feedback(
        chat_id=1, question="q", answer="a", feedback_signal="copy"
    ) is False
