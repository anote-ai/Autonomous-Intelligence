from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from database import agent_runs


@pytest.fixture()
def db_connection(monkeypatch: pytest.MonkeyPatch) -> tuple[MagicMock, MagicMock]:
    connection = MagicMock()
    cursor = MagicMock()
    monkeypatch.setattr(agent_runs, "get_db_connection", lambda: (connection, cursor))
    return connection, cursor


# ---------------------------------------------------------------------------
# create_run / get_run / list_runs
# ---------------------------------------------------------------------------


def test_create_run_inserts_and_logs_event(db_connection: tuple[MagicMock, MagicMock]) -> None:
    connection, cursor = db_connection
    cursor.lastrowid = 42
    run_id = agent_runs.create_run(user_id=1, project_name="Nightly ingest")

    assert run_id == 42
    # one INSERT for the run, one INSERT for the audit event
    assert cursor.execute.call_count == 2
    assert "INSERT INTO agent_runs" in cursor.execute.call_args_list[0].args[0]
    assert "INSERT INTO agent_run_events" in cursor.execute.call_args_list[1].args[0]
    assert connection.commit.call_count == 2
    assert connection.close.called


def test_get_run_scopes_by_user(db_connection: tuple[MagicMock, MagicMock]) -> None:
    _, cursor = db_connection
    cursor.fetchone.return_value = {"id": 5, "user_id": 1, "status": "running"}
    run = agent_runs.get_run(5, user_id=1)
    assert run == {"id": 5, "user_id": 1, "status": "running"}
    assert cursor.execute.call_args.args[1] == [5, 1]


def test_list_runs_filters_by_status(db_connection: tuple[MagicMock, MagicMock]) -> None:
    _, cursor = db_connection
    cursor.fetchall.return_value = [{"id": 1, "status": "paused"}]
    runs = agent_runs.list_runs(user_id=1, status="paused", limit=10)
    assert runs == [{"id": 1, "status": "paused"}]
    sql, params = cursor.execute.call_args.args
    assert "WHERE user_id = %s AND status = %s" in sql
    assert params == [1, "paused", 10]


def test_list_runs_clamps_limit(db_connection: tuple[MagicMock, MagicMock]) -> None:
    _, cursor = db_connection
    cursor.fetchall.return_value = []
    agent_runs.list_runs(user_id=1, limit=10_000)
    _, params = cursor.execute.call_args.args
    assert params[-1] == 200  # clamped to max


# ---------------------------------------------------------------------------
# update_run_progress / increment_run_cost
# ---------------------------------------------------------------------------


def test_update_run_progress_sets_started_at_on_running(db_connection: tuple[MagicMock, MagicMock]) -> None:
    connection, cursor = db_connection
    cursor.rowcount = 1
    updated = agent_runs.update_run_progress(1, user_id=1, status="running", current_step="Step 2")
    assert updated is True
    sql = cursor.execute.call_args.args[0]
    assert "started_at = COALESCE(started_at, CURRENT_TIMESTAMP)" in sql
    connection.commit.assert_called_once()


def test_update_run_progress_sets_finished_at_on_terminal_status(
    db_connection: tuple[MagicMock, MagicMock]
) -> None:
    _, cursor = db_connection
    cursor.rowcount = 1
    agent_runs.update_run_progress(1, user_id=1, status="completed")
    sql = cursor.execute.call_args.args[0]
    assert "finished_at = CURRENT_TIMESTAMP" in sql


def test_update_run_progress_rejects_unknown_status(db_connection: tuple[MagicMock, MagicMock]) -> None:
    with pytest.raises(ValueError):
        agent_runs.update_run_progress(1, user_id=1, status="bogus")


def test_update_run_progress_no_fields_returns_false(db_connection: tuple[MagicMock, MagicMock]) -> None:
    assert agent_runs.update_run_progress(1, user_id=1) is False


def test_increment_run_cost(db_connection: tuple[MagicMock, MagicMock]) -> None:
    connection, cursor = db_connection
    cursor.rowcount = 1
    assert agent_runs.increment_run_cost(1, user_id=1, delta_usd=0.25) is True
    connection.commit.assert_called_once()


# ---------------------------------------------------------------------------
# apply_intervention — the status machine + audit trail
# ---------------------------------------------------------------------------


def test_apply_intervention_pause_running_run(db_connection: tuple[MagicMock, MagicMock]) -> None:
    connection, cursor = db_connection
    cursor.fetchone.return_value = {"status": "running"}

    result = agent_runs.apply_intervention(1, user_id=1, event_type="pause", actor="op@example.com")

    assert result == {"run_id": 1, "event_type": "pause", "status": "paused"}
    # SELECT status, UPDATE status, INSERT event
    assert cursor.execute.call_count == 3
    assert connection.commit.call_count == 2


def test_apply_intervention_resume_paused_run(db_connection: tuple[MagicMock, MagicMock]) -> None:
    _, cursor = db_connection
    cursor.fetchone.return_value = {"status": "paused"}
    result = agent_runs.apply_intervention(1, user_id=1, event_type="resume")
    assert result["status"] == "running"


def test_apply_intervention_rejects_invalid_transition(db_connection: tuple[MagicMock, MagicMock]) -> None:
    _, cursor = db_connection
    cursor.fetchone.return_value = {"status": "completed"}
    with pytest.raises(ValueError, match="Cannot pause"):
        agent_runs.apply_intervention(1, user_id=1, event_type="pause")


def test_apply_intervention_missing_run_raises(db_connection: tuple[MagicMock, MagicMock]) -> None:
    _, cursor = db_connection
    cursor.fetchone.return_value = None
    with pytest.raises(ValueError, match="not found"):
        agent_runs.apply_intervention(999, user_id=1, event_type="pause")


def test_apply_intervention_unknown_type_raises(db_connection: tuple[MagicMock, MagicMock]) -> None:
    _, cursor = db_connection
    cursor.fetchone.return_value = {"status": "running"}
    with pytest.raises(ValueError, match="Unknown intervention type"):
        agent_runs.apply_intervention(1, user_id=1, event_type="explode")


def test_apply_intervention_message_does_not_change_status(db_connection: tuple[MagicMock, MagicMock]) -> None:
    connection, cursor = db_connection
    cursor.fetchone.return_value = {"id": 1}

    result = agent_runs.apply_intervention(
        1, user_id=1, event_type="message", actor="op@example.com", message="Please pivot strategy"
    )

    assert result == {"run_id": 1, "event_type": "message", "status": None}
    insert_sql = cursor.execute.call_args_list[-1].args[0]
    assert "INSERT INTO agent_run_events" in insert_sql
    connection.commit.assert_called()


def test_apply_intervention_message_missing_run_raises(db_connection: tuple[MagicMock, MagicMock]) -> None:
    _, cursor = db_connection
    cursor.fetchone.return_value = None
    with pytest.raises(ValueError, match="not found"):
        agent_runs.apply_intervention(999, user_id=1, event_type="message", message="hi")


def test_apply_intervention_cancel_from_queued(db_connection: tuple[MagicMock, MagicMock]) -> None:
    _, cursor = db_connection
    cursor.fetchone.return_value = {"status": "queued"}
    result = agent_runs.apply_intervention(1, user_id=1, event_type="cancel")
    assert result["status"] == "canceled"


def test_apply_intervention_retry_from_failed(db_connection: tuple[MagicMock, MagicMock]) -> None:
    _, cursor = db_connection
    cursor.fetchone.return_value = {"status": "failed"}
    result = agent_runs.apply_intervention(1, user_id=1, event_type="retry")
    assert result["status"] == "queued"


# ---------------------------------------------------------------------------
# list_run_events
# ---------------------------------------------------------------------------


def test_list_run_events_returns_empty_for_missing_run(db_connection: tuple[MagicMock, MagicMock]) -> None:
    _, cursor = db_connection
    cursor.fetchone.return_value = None
    assert agent_runs.list_run_events(1, user_id=1) == []


def test_list_run_events_returns_rows_for_owned_run(db_connection: tuple[MagicMock, MagicMock]) -> None:
    _, cursor = db_connection
    cursor.fetchone.return_value = {"id": 1}
    cursor.fetchall.return_value = [{"id": 1, "event_type": "pause"}]
    events = agent_runs.list_run_events(1, user_id=1)
    assert events == [{"id": 1, "event_type": "pause"}]
