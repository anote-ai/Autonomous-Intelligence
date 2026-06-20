"""Operator console data access — issue #140 (slice 1: runs + interventions).

This is the persisted backbone for the operator console epic: a human
operator needs to list projects/runs, monitor a run's live status, and
issue pause / resume / cancel / retry / message-the-agent controls without
direct database access. Every control action is recorded as an
``agent_run_events`` row so the audit trail required by the issue's
acceptance criteria ("Intervention events are persisted and visible in the
audit trail") is satisfiable.

Design notes
------------
- Mirrors the raw-cursor style already used in ``database/db.py`` /
  ``database/qa_feedback.py`` rather than the SQLAlchemy ORM, since the rest
  of the write path for chats/messages uses the connection pool directly.
- Status machine is intentionally small: queued -> running -> (paused) ->
  running -> (completed | failed | canceled). Invalid transitions raise
  ``ValueError`` so the API layer can return a 400 instead of silently
  corrupting state.
- All cost is accumulated in ``cost_usd`` via ``increment_run_cost`` so the
  "cost" column required by the issue's acceptance criteria stays accurate
  across multiple agent steps.
"""

from __future__ import annotations

from typing import Any

from database.db_pool import get_db_connection

# ---------------------------------------------------------------------------
# Status machine
# ---------------------------------------------------------------------------

ACTIVE_STATUSES = {"queued", "running", "paused"}
TERMINAL_STATUSES = {"completed", "failed", "canceled"}
ALL_STATUSES = ACTIVE_STATUSES | TERMINAL_STATUSES

# event_type -> (allowed current statuses, resulting status)
_TRANSITIONS: dict[str, tuple[set[str], str]] = {
    "pause": ({"queued", "running"}, "paused"),
    "resume": ({"paused"}, "running"),
    "cancel": (ACTIVE_STATUSES, "canceled"),
    "retry": ({"failed", "canceled"}, "queued"),
}


def create_run(
    user_id: int,
    project_name: str,
    chat_id: int | None = None,
) -> int:
    """Create a new run in 'queued' status and return its id."""
    conn, cursor = get_db_connection()
    try:
        cursor.execute(
            """
            INSERT INTO agent_runs (user_id, chat_id, project_name, status)
            VALUES (%s, %s, %s, 'queued')
            """,
            [user_id, chat_id, project_name],
        )
        conn.commit()
        run_id = cursor.lastrowid
        _log_event(cursor, conn, run_id, "created", actor=None, message=f"Run '{project_name}' queued.")
        return run_id
    finally:
        conn.close()


def get_run(run_id: int, user_id: int) -> dict[str, Any] | None:
    """Fetch a single run scoped to its owning user."""
    conn, cursor = get_db_connection()
    try:
        cursor.execute(
            "SELECT * FROM agent_runs WHERE id = %s AND user_id = %s",
            [run_id, user_id],
        )
        return cursor.fetchone()
    finally:
        conn.close()


def list_runs(
    user_id: int,
    status: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """List runs for a user, optionally filtered by status, newest first."""
    limit = max(1, min(int(limit), 200))
    conn, cursor = get_db_connection()
    try:
        if status:
            cursor.execute(
                """
                SELECT * FROM agent_runs
                WHERE user_id = %s AND status = %s
                ORDER BY created DESC
                LIMIT %s
                """,
                [user_id, status, limit],
            )
        else:
            cursor.execute(
                """
                SELECT * FROM agent_runs
                WHERE user_id = %s
                ORDER BY created DESC
                LIMIT %s
                """,
                [user_id, limit],
            )
        return cursor.fetchall()
    finally:
        conn.close()


def update_run_progress(
    run_id: int,
    user_id: int,
    *,
    status: str | None = None,
    current_step: str | None = None,
    blocker: str | None = None,
    summary: str | None = None,
) -> bool:
    """Update live progress fields (status, current step, blocker, summary).

    Used by the agent execution loop to report progress; not a substitute
    for the intervention transitions in ``apply_intervention`` (those go
    through the status machine and write an audit event).
    """
    fields: list[str] = []
    values: list[Any] = []

    if status is not None:
        if status not in ALL_STATUSES:
            raise ValueError(f"Unknown status: {status!r}")
        fields.append("status = %s")
        values.append(status)
        if status == "running":
            fields.append("started_at = COALESCE(started_at, CURRENT_TIMESTAMP)")
        if status in TERMINAL_STATUSES:
            fields.append("finished_at = CURRENT_TIMESTAMP")
    if current_step is not None:
        fields.append("current_step = %s")
        values.append(current_step)
    if blocker is not None:
        fields.append("blocker = %s")
        values.append(blocker)
    if summary is not None:
        fields.append("summary = %s")
        values.append(summary)

    if not fields:
        return False

    fields.append("updated = CURRENT_TIMESTAMP")
    values.extend([run_id, user_id])

    conn, cursor = get_db_connection()
    try:
        cursor.execute(
            f"UPDATE agent_runs SET {', '.join(fields)} WHERE id = %s AND user_id = %s",
            values,
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def increment_run_cost(run_id: int, user_id: int, delta_usd: float) -> bool:
    """Add ``delta_usd`` to the run's accumulated cost."""
    conn, cursor = get_db_connection()
    try:
        cursor.execute(
            """
            UPDATE agent_runs
            SET cost_usd = cost_usd + %s, updated = CURRENT_TIMESTAMP
            WHERE id = %s AND user_id = %s
            """,
            [delta_usd, run_id, user_id],
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def apply_intervention(
    run_id: int,
    user_id: int,
    event_type: str,
    actor: str | None = None,
    message: str | None = None,
) -> dict[str, Any]:
    """Apply an operator intervention (pause/resume/cancel/retry/message).

    Validates the transition against the current status, updates the run,
    and persists an ``agent_run_events`` row — this is what makes
    interventions visible in the audit trail per the issue's acceptance
    criteria. Raises ``ValueError`` for an unknown run or an invalid
    transition; callers should translate that into a 404/400.
    """
    if event_type == "message":
        # Messaging the agent doesn't change status — just logs an event
        # the live-run consumer (e.g. the agent loop) can pick up.
        conn, cursor = get_db_connection()
        try:
            cursor.execute(
                "SELECT id FROM agent_runs WHERE id = %s AND user_id = %s",
                [run_id, user_id],
            )
            if cursor.fetchone() is None:
                raise ValueError(f"Run {run_id} not found.")
            _log_event(cursor, conn, run_id, "message", actor=actor, message=message)
            return {"run_id": run_id, "event_type": "message", "status": None}
        finally:
            conn.close()

    if event_type not in _TRANSITIONS:
        raise ValueError(
            f"Unknown intervention type: {event_type!r}. "
            f"Expected one of: {sorted(_TRANSITIONS) + ['message']}"
        )

    allowed_from, new_status = _TRANSITIONS[event_type]

    conn, cursor = get_db_connection()
    try:
        cursor.execute(
            "SELECT status FROM agent_runs WHERE id = %s AND user_id = %s",
            [run_id, user_id],
        )
        row = cursor.fetchone()
        if row is None:
            raise ValueError(f"Run {run_id} not found.")

        current_status = row["status"]
        if current_status not in allowed_from:
            raise ValueError(
                f"Cannot {event_type} a run in status {current_status!r}. "
                f"Allowed from: {sorted(allowed_from)}"
            )

        if new_status in TERMINAL_STATUSES:
            cursor.execute(
                """
                UPDATE agent_runs
                SET status = %s, updated = CURRENT_TIMESTAMP, finished_at = CURRENT_TIMESTAMP
                WHERE id = %s AND user_id = %s
                """,
                [new_status, run_id, user_id],
            )
        elif new_status == "running":
            cursor.execute(
                """
                UPDATE agent_runs
                SET status = %s, updated = CURRENT_TIMESTAMP,
                    started_at = COALESCE(started_at, CURRENT_TIMESTAMP)
                WHERE id = %s AND user_id = %s
                """,
                [new_status, run_id, user_id],
            )
        else:
            cursor.execute(
                "UPDATE agent_runs SET status = %s, updated = CURRENT_TIMESTAMP WHERE id = %s AND user_id = %s",
                [new_status, run_id, user_id],
            )
        conn.commit()

        _log_event(cursor, conn, run_id, event_type, actor=actor, message=message)
        return {"run_id": run_id, "event_type": event_type, "status": new_status}
    finally:
        conn.close()


def list_run_events(run_id: int, user_id: int, limit: int = 100) -> list[dict[str, Any]]:
    """Return the audit trail of intervention events for a run, newest first."""
    limit = max(1, min(int(limit), 500))
    conn, cursor = get_db_connection()
    try:
        cursor.execute(
            "SELECT id FROM agent_runs WHERE id = %s AND user_id = %s",
            [run_id, user_id],
        )
        if cursor.fetchone() is None:
            return []
        cursor.execute(
            """
            SELECT * FROM agent_run_events
            WHERE run_id = %s
            ORDER BY created DESC
            LIMIT %s
            """,
            [run_id, limit],
        )
        return cursor.fetchall()
    finally:
        conn.close()


def _log_event(
    cursor: Any,
    conn: Any,
    run_id: int,
    event_type: str,
    actor: str | None,
    message: str | None,
) -> None:
    """Insert one audit-trail row and commit. Caller owns the connection."""
    cursor.execute(
        """
        INSERT INTO agent_run_events (run_id, event_type, actor, message)
        VALUES (%s, %s, %s, %s)
        """,
        [run_id, event_type, actor, message],
    )
    conn.commit()
