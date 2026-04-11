"""Tests for SQLAlchemy ORM models."""
from database.models import (
    ApiKey,
    Base,
    Chat,
    Chunk,
    Document,
    Message,
    MessageAttachment,
    User,
)


def _cols(model):
    return {c.name for c in model.__table__.columns}


def test_user_columns():
    cols = _cols(User)
    assert {"id", "email", "credits", "password_hash", "session_token"}.issubset(cols)


def test_chat_columns():
    cols = _cols(Chat)
    assert {"id", "user_id", "model_type", "associated_task"}.issubset(cols)


def test_message_columns():
    cols = _cols(Message)
    assert {"id", "chat_id", "message_text", "sent_from_user"}.issubset(cols)


def test_document_columns():
    cols = _cols(Document)
    assert {"id", "chat_id", "document_name", "media_type"}.issubset(cols)


def test_chunk_columns():
    cols = _cols(Chunk)
    assert {"id", "document_id", "start_index", "end_index"}.issubset(cols)


def test_api_key_columns():
    cols = _cols(ApiKey)
    assert {"id", "user_id", "api_key", "key_name"}.issubset(cols)


def test_message_attachment_columns():
    cols = _cols(MessageAttachment)
    assert {"id", "message_id", "media_type", "storage_key"}.issubset(cols)


def test_relationships_defined():
    assert hasattr(User, "chats")
    assert hasattr(Chat, "messages")
    assert hasattr(Chat, "documents")
    assert hasattr(Document, "chunks")
    assert hasattr(Message, "attachments")


def test_base_has_all_tables():
    table_names = set(Base.metadata.tables.keys())
    expected = {"users", "chats", "messages", "documents", "chunks", "apiKeys"}
    assert expected.issubset(table_names)
