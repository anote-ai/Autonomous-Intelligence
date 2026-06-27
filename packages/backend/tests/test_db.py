"""Unit tests for chat/message persistence helpers in database.db.

The helpers take a connection object, so we mock it — no real MySQL needed.
"""
from unittest.mock import MagicMock

from database import db


def _mock_cnx(lastrowid=None, fetchall=None):
    cnx = MagicMock()
    cursor = MagicMock()
    cursor.lastrowid = lastrowid
    cursor.fetchall.return_value = fetchall if fetchall is not None else []
    cnx.cursor.return_value = cursor
    return cnx, cursor


def test_create_chat_inserts_and_returns_id():
    cnx, cursor = _mock_cnx(lastrowid=42)
    chat_id = db.create_chat(cnx, user_id=7, name="My Chat", mode="document")
    assert chat_id == 42
    sql, params = cursor.execute.call_args[0]
    assert "INSERT INTO chats" in sql
    assert params == (7, "My Chat", "document")
    cursor.close.assert_called_once()


def test_create_chat_defaults():
    cnx, cursor = _mock_cnx(lastrowid=1)
    db.create_chat(cnx, user_id=5)
    _, params = cursor.execute.call_args[0]
    assert params == (5, "New Chat", "chat")


def test_add_message_inserts_and_returns_id():
    cnx, cursor = _mock_cnx(lastrowid=99)
    msg_id = db.add_message(
        cnx, chat_id=42, role="user", content="hi", model="claude-sonnet-4-6", tokens=3
    )
    assert msg_id == 99
    sql, params = cursor.execute.call_args[0]
    assert "INSERT INTO messages" in sql
    assert params == (42, "user", "hi", "claude-sonnet-4-6", 3)


def test_add_message_defaults_model_and_tokens():
    cnx, cursor = _mock_cnx(lastrowid=2)
    db.add_message(cnx, chat_id=42, role="assistant", content="hello")
    _, params = cursor.execute.call_args[0]
    assert params == (42, "assistant", "hello", None, 0)


def test_get_messages_chronological():
    rows = [{"id": 1, "role": "user", "content": "hi"}]
    cnx, cursor = _mock_cnx(fetchall=rows)
    result = db.get_messages(cnx, chat_id=42)
    assert result == rows
    sql, params = cursor.execute.call_args[0]
    assert "FROM messages WHERE chat_id" in sql
    assert "ORDER BY id ASC" in sql
    assert params == (42,)
    cnx.cursor.assert_called_with(dictionary=True)


def test_get_chats_most_recent_first():
    rows = [{"id": 2, "name": "B"}, {"id": 1, "name": "A"}]
    cnx, cursor = _mock_cnx(fetchall=rows)
    result = db.get_chats(cnx, user_id=7)
    assert result == rows
    sql, params = cursor.execute.call_args[0]
    assert "FROM chats WHERE user_id" in sql
    assert "ORDER BY id DESC" in sql
    assert params == (7,)
