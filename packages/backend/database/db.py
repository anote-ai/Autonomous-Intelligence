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


# ---------------------------------------------------------------------------
# Folders
# ---------------------------------------------------------------------------

def create_folder(cnx: Any, user_id: int, name: str) -> int:
    cursor = cnx.cursor()
    cursor.execute(
        "INSERT INTO folders (user_id, name) VALUES (%s, %s)",
        (user_id, name),
    )
    folder_id: int = cursor.lastrowid
    cursor.close()
    return folder_id


def get_folders(cnx: Any, user_id: int) -> list[dict]:
    cursor = cnx.cursor(dictionary=True)
    cursor.execute(
        "SELECT id, name, created_at FROM folders WHERE user_id = %s ORDER BY name",
        (user_id,),
    )
    rows = cursor.fetchall()
    cursor.close()
    return rows  # type: ignore[return-value]


def rename_folder(cnx: Any, folder_id: int, user_id: int, name: str) -> bool:
    cursor = cnx.cursor()
    cursor.execute(
        "UPDATE folders SET name = %s WHERE id = %s AND user_id = %s",
        (name, folder_id, user_id),
    )
    updated = cursor.rowcount > 0
    cursor.close()
    return updated


def delete_folder(cnx: Any, folder_id: int, user_id: int) -> bool:
    cursor = cnx.cursor()
    cursor.execute(
        "DELETE FROM folders WHERE id = %s AND user_id = %s",
        (folder_id, user_id),
    )
    deleted = cursor.rowcount > 0
    cursor.close()
    return deleted


# ---------------------------------------------------------------------------
# Documents
# ---------------------------------------------------------------------------

def create_document(cnx: Any, user_id: int, doc_uuid: str, filename: str,
                    chunk_count: int, folder_id: int | None = None) -> int:
    cursor = cnx.cursor()
    cursor.execute(
        "INSERT INTO documents (user_id, folder_id, doc_uuid, filename, chunk_count) "
        "VALUES (%s, %s, %s, %s, %s)",
        (user_id, folder_id, doc_uuid, filename, chunk_count),
    )
    doc_id: int = cursor.lastrowid
    cursor.close()
    return doc_id


def get_documents(cnx: Any, user_id: int, folder_id: int | None = None) -> list[dict]:
    cursor = cnx.cursor(dictionary=True)
    if folder_id is None:
        cursor.execute(
            "SELECT doc_uuid as id, filename, chunk_count, folder_id, created_at "
            "FROM documents WHERE user_id = %s ORDER BY created_at DESC",
            (user_id,),
        )
    else:
        cursor.execute(
            "SELECT doc_uuid as id, filename, chunk_count, folder_id, created_at "
            "FROM documents WHERE user_id = %s AND folder_id = %s ORDER BY created_at DESC",
            (user_id, folder_id),
        )
    rows = cursor.fetchall()
    cursor.close()
    return rows  # type: ignore[return-value]


def get_document_by_uuid(cnx: Any, user_id: int, doc_uuid: str) -> dict | None:
    cursor = cnx.cursor(dictionary=True)
    cursor.execute(
        "SELECT doc_uuid as id, filename, chunk_count, folder_id, created_at "
        "FROM documents WHERE user_id = %s AND doc_uuid = %s",
        (user_id, doc_uuid),
    )
    row = cursor.fetchone()
    cursor.close()
    return row  # type: ignore[return-value]


def delete_document(cnx: Any, user_id: int, doc_uuid: str) -> bool:
    cursor = cnx.cursor()
    cursor.execute(
        "DELETE FROM documents WHERE user_id = %s AND doc_uuid = %s",
        (user_id, doc_uuid),
    )
    deleted = cursor.rowcount > 0
    cursor.close()
    return deleted


def move_document(cnx: Any, user_id: int, doc_uuid: str, folder_id: int | None) -> bool:
    cursor = cnx.cursor()
    cursor.execute(
        "UPDATE documents SET folder_id = %s WHERE user_id = %s AND doc_uuid = %s",
        (folder_id, user_id, doc_uuid),
    )
    updated = cursor.rowcount > 0
    cursor.close()
    return updated
