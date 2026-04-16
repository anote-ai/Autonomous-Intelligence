from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest
from database import db


@pytest.fixture()
def db_connection(monkeypatch: pytest.MonkeyPatch) -> tuple[MagicMock, MagicMock]:
    connection = MagicMock()
    cursor = MagicMock()
    monkeypatch.setattr(db, "get_db_connection", lambda: (connection, cursor))
    return connection, cursor


def test_add_chat_inserts_chat_and_name(db_connection: tuple[MagicMock, MagicMock]) -> None:
    connection, cursor = db_connection
    cursor.fetchone.return_value = {"id": 3}
    cursor.lastrowid = 11
    chat_id = db.add_chat("user@example.com", 0, 1)
    assert chat_id == 11
    assert cursor.execute.call_count == 3
    connection.commit.assert_called_once()


def test_update_chat_name_updates_owned_chat(db_connection: tuple[MagicMock, MagicMock]) -> None:
    connection, cursor = db_connection
    db.update_chat_name("user@example.com", 11, "Renamed")
    connection.commit.assert_called_once()
    assert "UPDATE chats" in cursor.execute.call_args.args[0]


def test_retrieve_chats_returns_dict_rows(db_connection: tuple[MagicMock, MagicMock]) -> None:
    _, cursor = db_connection
    cursor.fetchall.return_value = [{"id": 1, "chat_name": "Chat 1"}]
    assert db.retrieve_chats("user@example.com") == [{"id": 1, "chat_name": "Chat 1"}]


def test_find_most_recent_chat_returns_single_row(db_connection: tuple[MagicMock, MagicMock]) -> None:
    _, cursor = db_connection
    cursor.fetchone.return_value = {"id": 9, "chat_name": "Recent"}
    assert db.find_most_recent_chat("user@example.com") == {"id": 9, "chat_name": "Recent"}


def test_retrieve_messages_normalizes_reasoning(db_connection: tuple[MagicMock, MagicMock]) -> None:
    _, cursor = db_connection
    cursor.fetchall.return_value = [
        {
            "created": "2024-01-01",
            "id": 6,
            "message_text": "Answer",
            "reasoning": '[{"thought": "step 1"}]',
            "sent_from_user": 0,
            "relevant_chunks": None,
        }
    ]
    messages = db.retrieve_messages("user@example.com", 1, 0)
    assert messages is not None
    assert messages[0]["reasoning"][0]["thought"] == "step 1"
    assert messages[0]["reasoning"][-1]["type"] == "complete"


def test_retrieve_messages_handles_invalid_reasoning_json(db_connection: tuple[MagicMock, MagicMock]) -> None:
    _, cursor = db_connection
    cursor.fetchall.return_value = [
        {
            "created": "2024-01-01",
            "id": 6,
            "message_text": "Answer",
            "reasoning": "not-json",
            "sent_from_user": 0,
            "relevant_chunks": None,
        }
    ]
    messages = db.retrieve_messages("user@example.com", 1, 0)
    assert messages == [
        {
            "created": "2024-01-01",
            "id": 6,
            "message_text": "Answer",
            "reasoning": [],
            "sent_from_user": 0,
            "relevant_chunks": None,
        }
    ]


@pytest.mark.parametrize(
    ("function", "expected"),
    [
        (db.delete_chat, "Successfully deleted"),
        (db.reset_chat, "Successfully deleted"),
    ],
)
def test_delete_and_reset_chat_return_success(
    db_connection: tuple[MagicMock, MagicMock],
    function: Any,
    expected: str,
) -> None:
    connection, cursor = db_connection
    cursor.rowcount = 1
    assert function(5, "user@example.com") == expected
    connection.commit.assert_called_once()


def test_reset_uploaded_docs_deletes_chunks_and_documents(db_connection: tuple[MagicMock, MagicMock]) -> None:
    connection, cursor = db_connection
    db.reset_uploaded_docs(5, "user@example.com")
    assert cursor.execute.call_count == 2
    connection.commit.assert_called_once()


def test_change_chat_mode_updates_model(db_connection: tuple[MagicMock, MagicMock]) -> None:
    connection, cursor = db_connection
    db.change_chat_mode(1, 5, "user@example.com")
    connection.commit.assert_called_once()
    assert "SET chats.model_type" in cursor.execute.call_args.args[0]


def test_add_document_returns_existing_document(db_connection: tuple[MagicMock, MagicMock]) -> None:
    connection, cursor = db_connection
    cursor.fetchone.return_value = {"id": 99}
    assert db.add_document("text", "file.pdf", chat_id=1) == (99, True)
    connection.commit.assert_not_called()


def test_add_document_inserts_new_document(db_connection: tuple[MagicMock, MagicMock]) -> None:
    connection, cursor = db_connection
    cursor.fetchone.return_value = None
    cursor.lastrowid = 12
    assert db.add_document("text", "file.pdf", chat_id=1) == (12, False)
    connection.commit.assert_called_once()


def test_add_message_skips_guest_chat() -> None:
    assert db.add_message("hello", 0, 1) is None


def test_add_message_inserts_row(db_connection: tuple[MagicMock, MagicMock]) -> None:
    connection, cursor = db_connection
    cursor.lastrowid = 22
    assert db.add_message("hello", 1, 1, reasoning="[]") == 22
    connection.commit.assert_called_once()


def test_retrieve_docs_and_delete_doc(db_connection: tuple[MagicMock, MagicMock]) -> None:
    connection, cursor = db_connection
    cursor.fetchall.return_value = [{"id": 4, "document_name": "file.pdf"}]
    assert db.retrieve_docs(1, "user@example.com") == [{"id": 4, "document_name": "file.pdf"}]

    cursor.fetchone.return_value = {"id": 4}
    assert db.delete_doc(4, "user@example.com") == "success"
    connection.commit.assert_called()


def test_add_model_key_updates_chat(db_connection: tuple[MagicMock, MagicMock]) -> None:
    connection, cursor = db_connection
    db.add_model_key("custom", 1, "user@example.com")
    connection.commit.assert_called_once()
    assert "custom_model_key" in cursor.execute.call_args.args[0]


def test_get_chat_info_returns_expected_tuple(db_connection: tuple[MagicMock, MagicMock]) -> None:
    _, cursor = db_connection
    cursor.fetchone.return_value = {"model_type": 0, "associated_task": 2, "chat_name": "Chat 1"}
    assert db.get_chat_info(1) == (0, 2, "Chat 1")


def test_get_chat_info_returns_nones_when_missing(db_connection: tuple[MagicMock, MagicMock]) -> None:
    _, cursor = db_connection
    cursor.fetchone.return_value = None
    assert db.get_chat_info(1) == (None, None, None)
