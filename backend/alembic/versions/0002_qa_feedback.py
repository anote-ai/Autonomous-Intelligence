"""qa_feedback table for RSI document Q&A (issue #220)

Foundation for the RSI feedback loop: a place to persist implicit/explicit
feedback signals on Q&A answers so later slices (re-ranker training,
self-consistency checks) have a training signal. Adding the table is inert on
its own — nothing writes to it unless ENABLE_RSI_FEEDBACK is set.

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-14 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS qa_feedback (
            id INTEGER PRIMARY KEY AUTO_INCREMENT,
            created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            chat_id INTEGER NOT NULL,
            message_id INTEGER DEFAULT NULL,
            question TEXT NOT NULL,
            retrieved_chunks TEXT,
            answer TEXT NOT NULL,
            feedback_signal VARCHAR(32) NOT NULL,
            session_id VARCHAR(255) DEFAULT NULL,
            source VARCHAR(16) NOT NULL DEFAULT 'implicit',
            FOREIGN KEY (chat_id) REFERENCES chats(id)
        )
        """
    )
    op.execute(
        "CREATE INDEX idx_qa_feedback_chat_id ON qa_feedback(chat_id)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS qa_feedback")
