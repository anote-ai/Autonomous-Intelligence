"""Tests for database/feedback_signals.py — implicit RSI signals (issue #220, slice 2).

Pure logic + best-effort orchestration; deps (retrieve_messages, log_qa_feedback)
are monkeypatched, so these run offline under the conftest mysql stub.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from database import feedback_signals as fs

NOW = datetime(2026, 6, 14, 12, 0, 0)


def _msg(
    text: str,
    is_user: bool,
    created: Any,
    mid: int | None = None,
    chunks: Any = None,
) -> dict[str, Any]:
    return {
        "message_text": text,
        "sent_from_user": 1 if is_user else 0,
        "created": created,
        "id": mid,
        "relevant_chunks": chunks,
    }


# --- detect_followup_signal ------------------------------------------------ #

def test_detect_followup_within_window() -> None:
    msgs = [
        _msg("what is EBITDA?", True, NOW - timedelta(seconds=40)),
        _msg("EBITDA is ...", False, NOW - timedelta(seconds=5), mid=99, chunks="c1|c2"),
    ]
    rec = fs.detect_followup_signal(msgs, NOW)
    assert rec is not None
    assert rec["feedback_signal"] == "followup"
    assert rec["message_id"] == 99
    assert rec["question"] == "what is EBITDA?"
    assert rec["answer"] == "EBITDA is ..."
    assert rec["retrieved_chunks"] == "c1|c2"


def test_detect_none_when_answer_too_old() -> None:
    msgs = [
        _msg("q", True, NOW - timedelta(seconds=120)),
        _msg("a", False, NOW - timedelta(seconds=60), mid=1),  # 60s > 30s window
    ]
    assert fs.detect_followup_signal(msgs, NOW) is None


def test_detect_none_when_last_is_user() -> None:
    msgs = [
        _msg("a", False, NOW - timedelta(seconds=5), mid=1),
        _msg("q2", True, NOW),
    ]
    assert fs.detect_followup_signal(msgs, NOW) is None


def test_detect_none_empty() -> None:
    assert fs.detect_followup_signal([], NOW) is None


def test_detect_none_non_datetime_created() -> None:
    msgs = [_msg("q", True, "2026-06-14"), _msg("a", False, "2026-06-14", mid=1)]
    assert fs.detect_followup_signal(msgs, NOW) is None


# --- record_followup_if_any ------------------------------------------------ #

def test_record_disabled_is_noop(monkeypatch: Any) -> None:
    monkeypatch.setenv("ENABLE_RSI_FEEDBACK", "false")

    def _fail(*a: Any, **k: Any) -> Any:
        raise AssertionError("must not be called when disabled")

    monkeypatch.setattr(fs, "_retrieve_messages", _fail)
    monkeypatch.setattr(fs, "log_qa_feedback", _fail)
    assert fs.record_followup_if_any("u@x", 1, 0) is False


def test_record_enabled_logs_followup(monkeypatch: Any) -> None:
    monkeypatch.setenv("ENABLE_RSI_FEEDBACK", "true")
    msgs = [
        _msg("q", True, NOW - timedelta(seconds=40)),
        _msg("a", False, NOW - timedelta(seconds=3), mid=7, chunks="c"),
    ]
    monkeypatch.setattr(fs, "_retrieve_messages", lambda *a, **k: msgs)
    logged: dict[str, Any] = {}

    def _fake_log(**kw: Any) -> bool:
        logged.update(kw)
        return True

    monkeypatch.setattr(fs, "log_qa_feedback", _fake_log)
    assert fs.record_followup_if_any("u@x", 5, 0, now=NOW) is True
    assert logged["chat_id"] == 5
    assert logged["feedback_signal"] == "followup"
    assert logged["message_id"] == 7


def test_record_no_followup_returns_false(monkeypatch: Any) -> None:
    monkeypatch.setenv("ENABLE_RSI_FEEDBACK", "true")
    msgs = [_msg("a", False, NOW - timedelta(seconds=300), mid=1)]  # too old
    monkeypatch.setattr(fs, "_retrieve_messages", lambda *a, **k: msgs)
    monkeypatch.setattr(fs, "log_qa_feedback", lambda **k: True)
    assert fs.record_followup_if_any("u@x", 5, 0, now=NOW) is False


def test_record_swallows_exception(monkeypatch: Any) -> None:
    monkeypatch.setenv("ENABLE_RSI_FEEDBACK", "true")

    def _boom(*a: Any, **k: Any) -> Any:
        raise RuntimeError("db down")

    monkeypatch.setattr(fs, "_retrieve_messages", _boom)
    assert fs.record_followup_if_any("u@x", 5, 0) is False
