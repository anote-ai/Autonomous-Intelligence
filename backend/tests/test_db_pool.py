from __future__ import annotations

from unittest.mock import MagicMock

from database import db_pool


def test_get_db_connection_reuses_single_pool(monkeypatch) -> None:
    connection = MagicMock()
    cursor = MagicMock()
    connection.cursor.return_value = cursor

    pool_instance = MagicMock()
    pool_instance.get_connection.return_value = connection

    pool_factory = MagicMock(return_value=pool_instance)
    monkeypatch.setattr(db_pool.mysql.connector.pooling, "MySQLConnectionPool", pool_factory)
    monkeypatch.setattr(db_pool, "_connection_pool", None)

    first_connection, first_cursor = db_pool.get_db_connection()
    second_connection, second_cursor = db_pool.get_db_connection()

    assert first_connection is connection
    assert second_connection is connection
    assert first_cursor is cursor
    assert second_cursor is cursor
    assert pool_factory.call_count == 1
    assert pool_instance.get_connection.call_count == 2
