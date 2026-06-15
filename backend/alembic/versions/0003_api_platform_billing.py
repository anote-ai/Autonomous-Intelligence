"""API platform keys, usage metering, and credit billing tables.

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-15 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _add_column_if_missing(table: str, column: str, definition: str) -> None:
    op.execute(
        f"""
        SET @col_exists := (
            SELECT COUNT(*)
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = '{table}'
              AND COLUMN_NAME = '{column}'
        )
        """
    )
    op.execute(
        f"""
        SET @ddl := IF(
            @col_exists = 0,
            'ALTER TABLE {table} ADD COLUMN {column} {definition}',
            'SELECT 1'
        )
        """
    )
    op.execute("PREPARE stmt FROM @ddl")
    op.execute("EXECUTE stmt")
    op.execute("DEALLOCATE PREPARE stmt")


def upgrade() -> None:
    _add_column_if_missing("apiKeys", "key_hash", "VARCHAR(255) NULL")
    _add_column_if_missing("apiKeys", "key_prefix", "VARCHAR(32) NULL")
    _add_column_if_missing("apiKeys", "expires_at", "TIMESTAMP NULL")
    _add_column_if_missing("apiKeys", "is_active", "TINYINT NOT NULL DEFAULT 1")
    _add_column_if_missing("apiKeys", "rate_limit_per_minute", "INTEGER NOT NULL DEFAULT 60")
    _add_column_if_missing("apiKeys", "revoked_at", "TIMESTAMP NULL")
    op.execute("ALTER TABLE apiKeys MODIFY COLUMN last_used TIMESTAMP NULL")
    op.execute("CREATE INDEX idx_api_keys_prefix ON apiKeys(key_prefix)")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS user_credits (
            user_id INTEGER PRIMARY KEY,
            balance INTEGER NOT NULL DEFAULT 0,
            lifetime_purchased INTEGER NOT NULL DEFAULT 0,
            lifetime_used INTEGER NOT NULL DEFAULT 0,
            low_balance_alert_sent_at TIMESTAMP NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        """
    )
    op.execute(
        """
        INSERT IGNORE INTO user_credits (user_id, balance)
        SELECT id, credits FROM users
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS api_usage_log (
            id INTEGER PRIMARY KEY AUTO_INCREMENT,
            user_id INTEGER,
            api_key_id INTEGER,
            endpoint VARCHAR(255) NOT NULL,
            model VARCHAR(128),
            input_tokens INTEGER NOT NULL DEFAULT 0,
            output_tokens INTEGER NOT NULL DEFAULT 0,
            credits_charged DECIMAL(10, 2) NOT NULL DEFAULT 0,
            request_duration_ms INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
            FOREIGN KEY (api_key_id) REFERENCES apiKeys(id) ON DELETE SET NULL
        )
        """
    )
    op.execute("CREATE INDEX idx_api_usage_log_user_created ON api_usage_log(user_id, created_at)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS api_usage_log")
    op.execute("DROP TABLE IF EXISTS user_credits")
    op.execute("DROP INDEX idx_api_keys_prefix ON apiKeys")
    op.execute("ALTER TABLE apiKeys DROP COLUMN revoked_at")
    op.execute("ALTER TABLE apiKeys DROP COLUMN rate_limit_per_minute")
    op.execute("ALTER TABLE apiKeys DROP COLUMN is_active")
    op.execute("ALTER TABLE apiKeys DROP COLUMN expires_at")
    op.execute("ALTER TABLE apiKeys DROP COLUMN key_prefix")
    op.execute("ALTER TABLE apiKeys DROP COLUMN key_hash")
