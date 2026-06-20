"""Operator console foundation: agent_runs + agent_run_events (issue #140)

Adds the persisted data model behind the operator console epic — a place to
track autonomous "runs" (project/queue/live/historical) along with status,
current step, blockers, cost, and an audit trail of human intervention
events (pause/resume/cancel/retry/message). The frontend operator console
(and the REST endpoints in api_endpoints/agent_runs/) build on these tables.

This migration only adds tables; nothing writes to them until the new
/api/agent-runs endpoints are exercised, so it is inert for existing flows.

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-20 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS agent_runs (
            id INTEGER PRIMARY KEY AUTO_INCREMENT,
            created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            user_id INTEGER NOT NULL,
            chat_id INTEGER DEFAULT NULL,
            project_name VARCHAR(255) NOT NULL,
            status VARCHAR(32) NOT NULL DEFAULT 'queued',
            current_step TEXT,
            blocker TEXT,
            cost_usd DECIMAL(10, 4) NOT NULL DEFAULT 0,
            started_at TIMESTAMP DEFAULT NULL,
            finished_at TIMESTAMP DEFAULT NULL,
            summary TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (chat_id) REFERENCES chats(id)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS agent_run_events (
            id INTEGER PRIMARY KEY AUTO_INCREMENT,
            created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            run_id INTEGER NOT NULL,
            event_type VARCHAR(32) NOT NULL,
            actor VARCHAR(255),
            message TEXT,
            FOREIGN KEY (run_id) REFERENCES agent_runs(id)
        )
        """
    )
    op.execute("CREATE INDEX idx_agent_runs_user_id ON agent_runs(user_id)")
    op.execute("CREATE INDEX idx_agent_runs_status ON agent_runs(status)")
    op.execute("CREATE INDEX idx_agent_run_events_run_id ON agent_run_events(run_id)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS agent_run_events")
    op.execute("DROP TABLE IF EXISTS agent_runs")
