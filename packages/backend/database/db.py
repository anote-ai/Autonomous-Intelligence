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
