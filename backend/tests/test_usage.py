"""Tests for backend/database/usage.py usage-metering helpers."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

# ── helpers ──────────────────────────────────────────────────────────────────

def _make_cursor(rows=None, fetchone_return=None):
    cursor = MagicMock()
    cursor.fetchall.return_value = rows or []
    cursor.fetchone.return_value = fetchone_return
    return cursor


def _make_conn(cursor):
    conn = MagicMock()
    conn.__enter__ = lambda s: s
    conn.__exit__ = MagicMock(return_value=False)
    return conn


def _patch_db(cursor, conn=None):
    """Return a context manager that patches get_db_connection."""
    if conn is None:
        conn = _make_conn(cursor)
    return patch("database.usage.get_db_connection", return_value=(conn, cursor))


# ── log_api_usage ─────────────────────────────────────────────────────────────

class TestLogApiUsage:
    def test_inserts_row_with_correct_total(self):
        cursor = _make_cursor()
        conn = _make_conn(cursor)
        with _patch_db(cursor, conn):
            from database.usage import log_api_usage
            log_api_usage(
                user_id=1,
                api_key_id=2,
                endpoint="/v1/chat/completions",
                model="gpt-4o",
                prompt_tokens=100,
                completion_tokens=50,
                credits_used=1,
            )
        cursor.execute.assert_called_once()
        sql, params = cursor.execute.call_args[0]
        assert "INSERT INTO api_usage" in sql
        assert 150 in params  # total_tokens = 100 + 50
        conn.commit.assert_called_once()

    def test_swallows_db_errors(self):
        """log_api_usage must never propagate exceptions."""
        with patch("database.usage.get_db_connection", side_effect=RuntimeError("db down")):
            from database.usage import log_api_usage
            # Should not raise
            log_api_usage(
                user_id=None,
                api_key_id=None,
                endpoint="/v1/chat/completions",
                model="gpt-4o",
                prompt_tokens=0,
                completion_tokens=0,
            )

    def test_handles_none_user_and_key(self):
        cursor = _make_cursor()
        conn = _make_conn(cursor)
        with _patch_db(cursor, conn):
            from database.usage import log_api_usage
            log_api_usage(
                user_id=None,
                api_key_id=None,
                endpoint="/v1/question-answer",
                model=None,
                prompt_tokens=0,
                completion_tokens=0,
            )
        _, params = cursor.execute.call_args[0]
        assert params[0] is None  # user_id
        assert params[1] is None  # api_key_id


# ── get_usage_rows ─────────────────────────────────────────────────────────────

class TestGetUsageRows:
    def test_returns_rows_as_dicts(self):
        fake_row = {
            "id": 1, "endpoint": "/v1/chat/completions", "model": "gpt-4o",
            "prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150,
            "credits_used": 1, "created": "2024-01-15 10:00:00",
        }
        cursor = _make_cursor(rows=[fake_row])
        with _patch_db(cursor):
            from database.usage import get_usage_rows
            result = get_usage_rows(user_id=1)
        assert len(result) == 1
        assert result[0]["model"] == "gpt-4o"
        assert result[0]["total_tokens"] == 150

    def test_passes_date_filters_to_query(self):
        cursor = _make_cursor(rows=[])
        with _patch_db(cursor):
            from database.usage import get_usage_rows
            get_usage_rows(user_id=5, start_date="2024-01-01", end_date="2024-01-31")
        sql, params = cursor.execute.call_args[0]
        assert "created >=" in sql
        assert "DATE_ADD" in sql
        assert "2024-01-01" in params
        assert "2024-01-31" in params

    def test_caps_limit_at_1000(self):
        cursor = _make_cursor(rows=[])
        with _patch_db(cursor):
            from database.usage import get_usage_rows
            get_usage_rows(user_id=1, limit=99999)
        _, params = cursor.execute.call_args[0]
        assert 1000 in params

    def test_returns_empty_list_when_no_rows(self):
        cursor = _make_cursor(rows=[])
        with _patch_db(cursor):
            from database.usage import get_usage_rows
            result = get_usage_rows(user_id=99)
        assert result == []


# ── get_usage_summary ──────────────────────────────────────────────────────────

class TestGetUsageSummary:
    def test_returns_aggregated_totals(self):
        fake_summary = {
            "total_requests": 10,
            "prompt_tokens": 800,
            "completion_tokens": 400,
            "total_tokens": 1200,
            "credits_used": 10,
        }
        cursor = _make_cursor(fetchone_return=fake_summary)
        with _patch_db(cursor):
            from database.usage import get_usage_summary
            result = get_usage_summary(user_id=1)
        assert result["total_requests"] == 10
        assert result["total_tokens"] == 1200

    def test_returns_zeros_when_no_data(self):
        cursor = _make_cursor(fetchone_return=None)
        with _patch_db(cursor):
            from database.usage import get_usage_summary
            result = get_usage_summary(user_id=99)
        assert result["total_requests"] == 0
        assert result["credits_used"] == 0


# ── user_and_key_ids_for_api_key ───────────────────────────────────────────────

class TestUserAndKeyIdsForApiKey:
    def test_returns_ids_when_key_found(self):
        cursor = _make_cursor(fetchone_return={"user_id": 7, "key_id": 3})
        with _patch_db(cursor):
            from database.usage import user_and_key_ids_for_api_key
            uid, kid = user_and_key_ids_for_api_key("test-key-abc")
        assert uid == 7
        assert kid == 3

    def test_returns_nones_when_key_not_found(self):
        cursor = _make_cursor(fetchone_return=None)
        with _patch_db(cursor):
            from database.usage import user_and_key_ids_for_api_key
            uid, kid = user_and_key_ids_for_api_key("nonexistent-key")
        assert uid is None
        assert kid is None
