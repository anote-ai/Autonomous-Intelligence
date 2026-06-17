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


def create_api_key(
    cnx: Any,
    user_id: int,
    key_hash: str,
    key_prefix: str,
    name: str = "",
    rate_limit_per_minute: int = 60,
    expires_at: str | None = None,
) -> int:
    cursor = cnx.cursor()
    cursor.execute(
        """INSERT INTO api_keys
           (user_id, name, key_hash, key_prefix, rate_limit_per_minute, expires_at, created_at)
           VALUES (%s, %s, %s, %s, %s, %s, NOW())""",
        (user_id, name, key_hash, key_prefix, rate_limit_per_minute, expires_at),
    )
    key_id: int = cursor.lastrowid
    cursor.close()
    return key_id


def list_api_keys_for_user(cnx: Any, user_id: int) -> list[dict]:
    cursor = cnx.cursor(dictionary=True)
    cursor.execute(
        """SELECT id, name, key_prefix, is_active, rate_limit_per_minute,
                  last_used_at, expires_at, created_at
           FROM api_keys WHERE user_id = %s ORDER BY created_at DESC""",
        (user_id,),
    )
    rows = cursor.fetchall()
    cursor.close()
    return rows


def get_active_api_keys(cnx: Any) -> list[dict]:
    cursor = cnx.cursor(dictionary=True)
    cursor.execute(
        """SELECT id, user_id, key_hash, key_prefix, rate_limit_per_minute, expires_at
           FROM api_keys WHERE is_active = TRUE"""
    )
    rows = cursor.fetchall()
    cursor.close()
    return rows


def revoke_api_key(cnx: Any, user_id: int, key_id: int) -> bool:
    cursor = cnx.cursor()
    cursor.execute(
        "UPDATE api_keys SET is_active = FALSE WHERE id = %s AND user_id = %s",
        (key_id, user_id),
    )
    updated = cursor.rowcount > 0
    cursor.close()
    return updated


def touch_api_key(cnx: Any, key_id: int) -> None:
    cursor = cnx.cursor()
    cursor.execute("UPDATE api_keys SET last_used_at = NOW() WHERE id = %s", (key_id,))
    cursor.close()


def log_api_usage(
    cnx: Any,
    api_key_id: int,
    user_id: int,
    endpoint: str,
    status_code: int,
    credits_used: int = 0,
) -> None:
    cursor = cnx.cursor()
    cursor.execute(
        """INSERT INTO api_usage_log
           (api_key_id, user_id, endpoint, status_code, credits_used, created_at)
           VALUES (%s, %s, %s, %s, %s, NOW())""",
        (api_key_id, user_id, endpoint, status_code, credits_used),
    )
    cursor.close()


def get_usage_summary(cnx: Any, user_id: int) -> dict:
    cursor = cnx.cursor(dictionary=True)
    cursor.execute(
        """SELECT COUNT(*) AS request_count, COALESCE(SUM(credits_used), 0) AS total_credits_used
           FROM api_usage_log WHERE user_id = %s""",
        (user_id,),
    )
    row = cursor.fetchone()
    cursor.close()
    return row or {"request_count": 0, "total_credits_used": 0}


def deduct_credits(cnx: Any, user_id: int, amount: int) -> bool:
    cursor = cnx.cursor()
    cursor.execute(
        "UPDATE users SET credits = credits - %s WHERE id = %s AND credits >= %s",
        (amount, user_id, amount),
    )
    deducted = cursor.rowcount > 0
    cursor.close()
    return deducted


def add_credits(cnx: Any, user_id: int, amount: int) -> None:
    cursor = cnx.cursor()
    cursor.execute(
        "UPDATE users SET credits = credits + %s WHERE id = %s",
        (amount, user_id),
    )
    cursor.close()
