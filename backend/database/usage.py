"""
Usage metering helpers — log per-request API usage and query history.

All functions use the shared connection pool from database.db_pool.
"""

from __future__ import annotations

from typing import Any

from database.db_pool import get_db_connection


def log_api_usage(
    *,
    user_id: int | None,
    api_key_id: int | None,
    endpoint: str,
    model: str | None,
    prompt_tokens: int,
    completion_tokens: int,
    credits_used: int = 1,
) -> None:
    """Insert one row into ``api_usage``.  Never raises — failures are swallowed
    so that a logging error never breaks a user-facing request."""
    try:
        conn, cursor = get_db_connection()
        total = prompt_tokens + completion_tokens
        cursor.execute(
            """
            INSERT INTO api_usage
                (user_id, api_key_id, endpoint, model,
                 prompt_tokens, completion_tokens, total_tokens, credits_used)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            [user_id, api_key_id, endpoint, model,
             prompt_tokens, completion_tokens, total, credits_used],
        )
        conn.commit()
    except Exception as exc:  # noqa: BLE001
        print(f"[usage] log_api_usage failed: {exc}")
    finally:
        try:
            conn.close()
        except Exception:
            pass


def get_usage_rows(
    user_id: int,
    *,
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Return individual usage rows for a user, newest-first.

    ``start_date`` / ``end_date`` are optional ISO-8601 date strings (``YYYY-MM-DD``).
    """
    conn, cursor = get_db_connection()
    try:
        params: list[Any] = [user_id]
        clauses = ["user_id = %s"]

        if start_date:
            clauses.append("created >= %s")
            params.append(start_date)
        if end_date:
            clauses.append("created < DATE_ADD(%s, INTERVAL 1 DAY)")
            params.append(end_date)

        where = " AND ".join(clauses)
        params.append(min(limit, 1000))  # hard cap

        cursor.execute(
            f"""
            SELECT id, endpoint, model,
                   prompt_tokens, completion_tokens, total_tokens,
                   credits_used, created
            FROM api_usage
            WHERE {where}
            ORDER BY created DESC
            LIMIT %s
            """,
            params,
        )
        rows = cursor.fetchall()
        return [dict(r) for r in rows] if rows else []
    finally:
        conn.close()


def get_usage_summary(
    user_id: int,
    *,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict[str, Any]:
    """Return aggregated usage totals for a user over the given period."""
    conn, cursor = get_db_connection()
    try:
        params: list[Any] = [user_id]
        clauses = ["user_id = %s"]

        if start_date:
            clauses.append("created >= %s")
            params.append(start_date)
        if end_date:
            clauses.append("created < DATE_ADD(%s, INTERVAL 1 DAY)")
            params.append(end_date)

        where = " AND ".join(clauses)

        cursor.execute(
            f"""
            SELECT
                COUNT(*)                  AS total_requests,
                COALESCE(SUM(prompt_tokens),     0) AS prompt_tokens,
                COALESCE(SUM(completion_tokens), 0) AS completion_tokens,
                COALESCE(SUM(total_tokens),      0) AS total_tokens,
                COALESCE(SUM(credits_used),      0) AS credits_used
            FROM api_usage
            WHERE {where}
            """,
            params,
        )
        row = cursor.fetchone()
        if not row:
            return {
                "total_requests": 0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "credits_used": 0,
            }
        return {
            "total_requests": int(row["total_requests"]),
            "prompt_tokens": int(row["prompt_tokens"]),
            "completion_tokens": int(row["completion_tokens"]),
            "total_tokens": int(row["total_tokens"]),
            "credits_used": int(row["credits_used"]),
        }
    finally:
        conn.close()


def user_and_key_ids_for_api_key(api_key: str) -> tuple[int | None, int | None]:
    """Return ``(user_id, api_key_id)`` for the given raw API key string."""
    conn, cursor = get_db_connection()
    try:
        cursor.execute(
            "SELECT p.id AS user_id, c.id AS key_id "
            "FROM users p JOIN apiKeys c ON c.user_id = p.id "
            "WHERE c.api_key = %s",
            [api_key],
        )
        row = cursor.fetchone()
        if row:
            return int(row["user_id"]), int(row["key_id"])
        return None, None
    finally:
        conn.close()
