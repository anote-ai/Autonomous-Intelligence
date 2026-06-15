"""API key creation, lookup, and lifecycle helpers."""

from __future__ import annotations

import secrets
import string
from datetime import datetime
from typing import Any

import bcrypt

from database.db_pool import get_db_connection

KEY_PREFIX = "sk-ai-"
KEY_RANDOM_LENGTH = 32
DISPLAY_PREFIX_LENGTH = len(KEY_PREFIX) + 8
DEFAULT_RATE_LIMIT_PER_MINUTE = 60


def generate_plaintext_api_key() -> str:
    alphabet = string.ascii_letters + string.digits
    return KEY_PREFIX + "".join(secrets.choice(alphabet) for _ in range(KEY_RANDOM_LENGTH))


def hash_api_key(api_key: str) -> str:
    return bcrypt.hashpw(api_key.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_api_key(api_key: str, key_hash: str | bytes | None) -> bool:
    if not api_key or not key_hash:
        return False
    if isinstance(key_hash, str):
        key_hash = key_hash.encode("utf-8")
    try:
        return bcrypt.checkpw(api_key.encode("utf-8"), key_hash)
    except ValueError:
        return False


def _status_for_key(row: dict[str, Any]) -> str:
    if row.get("is_active") in (0, False):
        return "revoked"
    expires_at = row.get("expires_at")
    if expires_at and expires_at < datetime.now():
        return "expired"
    return "active"


def create_api_key(
    email: str,
    *,
    name: str | None = None,
    expires_at: str | None = None,
    rate_limit_per_minute: int | None = None,
) -> dict[str, Any]:
    conn, cursor = get_db_connection()
    try:
        cursor.execute("SELECT id FROM users WHERE email = %s", [email])
        user = cursor.fetchone()
        if user is None:
            raise ValueError(f"User with email {email} not found")

        plaintext = generate_plaintext_api_key()
        key_prefix = plaintext[:DISPLAY_PREFIX_LENGTH]
        key_hash = hash_api_key(plaintext)
        now = datetime.now()
        name = name or "Untitled Key"
        rate_limit = int(rate_limit_per_minute or DEFAULT_RATE_LIMIT_PER_MINUTE)
        rate_limit = max(1, min(rate_limit, 10000))

        cursor.execute(
            """
            INSERT INTO apiKeys
                (user_id, api_key, key_hash, key_prefix, created, last_used,
                 key_name, expires_at, is_active, rate_limit_per_minute)
            VALUES (%s, NULL, %s, %s, %s, NULL, %s, %s, 1, %s)
            """,
            [user["id"], key_hash, key_prefix, now, name, expires_at, rate_limit],
        )
        cursor.execute("SELECT LAST_INSERT_ID()")
        key_id = cursor.fetchone()["LAST_INSERT_ID()"]
        conn.commit()
        return {
            "id": key_id,
            "key": plaintext,
            "key_prefix": key_prefix,
            "created": now,
            "last_used": None,
            "expires_at": expires_at,
            "name": name,
            "status": "active",
            "rate_limit_per_minute": rate_limit,
        }
    finally:
        conn.close()


def list_api_keys(email: str) -> dict[str, list[dict[str, Any]]]:
    conn, cursor = get_db_connection()
    try:
        cursor.execute("SELECT id FROM users WHERE email = %s", [email])
        user = cursor.fetchone()
        if user is None:
            return {"keys": []}

        cursor.execute(
            """
            SELECT id, api_key, key_prefix, created, last_used, key_name,
                   expires_at, is_active, rate_limit_per_minute
            FROM apiKeys
            WHERE user_id = %s
            ORDER BY created DESC
            """,
            [user["id"]],
        )
        keys = []
        for row in cursor.fetchall() or []:
            legacy_key = row.get("api_key")
            prefix = row.get("key_prefix") or (legacy_key[:DISPLAY_PREFIX_LENGTH] if legacy_key else "")
            keys.append(
                {
                    "id": row["id"],
                    "key": f"{prefix}..." if prefix else "sk-ai-...",
                    "key_prefix": prefix,
                    "created": row["created"],
                    "last_used": row.get("last_used"),
                    "expires_at": row.get("expires_at"),
                    "name": row.get("key_name") or "Untitled Key",
                    "status": _status_for_key(row),
                    "rate_limit_per_minute": row.get("rate_limit_per_minute")
                    or DEFAULT_RATE_LIMIT_PER_MINUTE,
                }
            )
        return {"keys": keys}
    finally:
        conn.close()


def revoke_api_key(api_key_id: int) -> None:
    conn, cursor = get_db_connection()
    try:
        cursor.execute(
            """
            UPDATE apiKeys
            SET is_active = 0, revoked_at = CURRENT_TIMESTAMP
            WHERE id = %s
            """,
            [api_key_id],
        )
        conn.commit()
    finally:
        conn.close()


def find_api_key_record(api_key: str) -> dict[str, Any] | None:
    """Return a verified active API key row.

    New keys are bcrypt hashed and narrowed by prefix before verification.
    Legacy plaintext rows are accepted for backwards compatibility.
    """
    if not api_key:
        return None

    conn, cursor = get_db_connection()
    try:
        prefix = api_key[:DISPLAY_PREFIX_LENGTH]
        cursor.execute(
            """
            SELECT c.*, p.email, p.credits
            FROM apiKeys c
            JOIN users p ON c.user_id = p.id
            WHERE (c.key_prefix = %s OR c.api_key = %s)
              AND COALESCE(c.is_active, 1) = 1
              AND (c.expires_at IS NULL OR c.expires_at > CURRENT_TIMESTAMP)
            """,
            [prefix, api_key],
        )
        for row in cursor.fetchall() or []:
            if row.get("api_key") == api_key or verify_api_key(api_key, row.get("key_hash")):
                return dict(row)
        return None
    finally:
        conn.close()

