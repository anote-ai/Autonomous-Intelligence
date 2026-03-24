from __future__ import annotations

import os
import socket
from typing import Any

import mysql.connector.pooling

from constants.global_constants import dbHost, dbName, dbPassword, dbUser

_connection_pool: mysql.connector.pooling.MySQLConnectionPool | None = None


def _db_connection_config() -> dict[str, Any]:
    is_local = (
        ".local" in socket.gethostname()
        or ".lan" in socket.gethostname()
        or "Shadow" in socket.gethostname()
        or os.environ.get("APP_ENV") == "local"
    )

    if is_local:
        return {
            "user": "root",
            "unix_socket": "/tmp/mysql.sock",
            "database": dbName,
        }

    return {
        "host": dbHost,
        "user": dbUser,
        "password": dbPassword,
        "database": dbName,
    }


def _get_pool() -> mysql.connector.pooling.MySQLConnectionPool:
    global _connection_pool
    if _connection_pool is None:
        _connection_pool = mysql.connector.pooling.MySQLConnectionPool(
            pool_name="anote_pool",
            pool_size=10,
            **_db_connection_config(),
        )
    return _connection_pool


def get_db_connection():
    connection = _get_pool().get_connection()
    return connection, connection.cursor(dictionary=True)
