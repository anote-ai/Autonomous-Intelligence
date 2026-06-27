"""MySQL database connection and query helpers."""
from __future__ import annotations

import os
from typing import Any

try:
    import mysql.connector
    MYSQL_AVAILABLE = True
except ImportError:
    MYSQL_AVAILABLE = False


def get_connection() -> Any:
    if not MYSQL_AVAILABLE:
        raise RuntimeError("mysql-connector-python not installed")
    return mysql.connector.connect(
        host=os.environ.get("DB_HOST", "localhost"),
        database=os.environ.get("DB_NAME", "anote"),
        user=os.environ.get("DB_USER", "root"),
        password=os.environ.get("DB_PASSWORD", ""),
        autocommit=True,
    )


def get_user_by_email(cnx: Any, email: str) -> dict | None:
    cursor = cnx.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE email = %s LIMIT 1", (email,))
    row = cursor.fetchone()
    cursor.close()
    return row


def create_user(cnx: Any, email: str, password_hash: str, name: str = "") -> int:
    cursor = cnx.cursor()
    cursor.execute(
        "INSERT INTO users (email, password_hash, name, created_at) VALUES (%s, %s, %s, NOW())",
        (email, password_hash, name),
    )
    user_id: int = cursor.lastrowid
    cursor.close()
    return user_id


# ── Chat / message persistence (foundation for #210 / RSI #220) ──────────────


def create_chat(cnx: Any, user_id: int, name: str = "New Chat", mode: str = "chat") -> int:
    """Create a chat row and return its id."""
    cursor = cnx.cursor()
    cursor.execute(
        "INSERT INTO chats (user_id, name, mode, created_at) VALUES (%s, %s, %s, NOW())",
        (user_id, name, mode),
    )
    chat_id: int = cursor.lastrowid
    cursor.close()
    return chat_id


def add_message(
    cnx: Any,
    chat_id: int,
    role: str,
    content: str,
    model: str | None = None,
    tokens: int = 0,
) -> int:
    """Append a message to a chat and return its id. ``role`` is user/assistant/system."""
    cursor = cnx.cursor()
    cursor.execute(
        "INSERT INTO messages (chat_id, role, content, model, tokens, created_at) "
        "VALUES (%s, %s, %s, %s, %s, NOW())",
        (chat_id, role, content, model, tokens),
    )
    message_id: int = cursor.lastrowid
    cursor.close()
    return message_id


def get_messages(cnx: Any, chat_id: int) -> list[dict]:
    """Return a chat's messages in chronological order (oldest first)."""
    cursor = cnx.cursor(dictionary=True)
    cursor.execute(
        "SELECT id, role, content, model, tokens, created_at "
        "FROM messages WHERE chat_id = %s ORDER BY id ASC",
        (chat_id,),
    )
    rows = cursor.fetchall()
    cursor.close()
    return rows


def get_chats(cnx: Any, user_id: int) -> list[dict]:
    """Return a user's chats, most recent first."""
    cursor = cnx.cursor(dictionary=True)
    cursor.execute(
        "SELECT id, name, mode, created_at FROM chats WHERE user_id = %s ORDER BY id DESC",
        (user_id,),
    )
    rows = cursor.fetchall()
    cursor.close()
    return rows
