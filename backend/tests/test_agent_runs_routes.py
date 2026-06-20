from __future__ import annotations

from typing import Any

import pytest


def _authenticate(monkeypatch: pytest.MonkeyPatch, app_module: Any, email: str = "test@example.com") -> None:
    monkeypatch.setattr(app_module, "extractUserEmailFromRequest", lambda request: email)


def _invalidate_token(monkeypatch: pytest.MonkeyPatch, app_module: Any) -> None:
    def _raise_invalid(request: Any) -> str:
        raise app_module.InvalidTokenError()

    monkeypatch.setattr(app_module, "extractUserEmailFromRequest", _raise_invalid)


def test_create_agent_run_requires_auth(client: Any, app_module: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    _invalidate_token(monkeypatch, app_module)
    response = client.post("/api/agent-runs", json={"project_name": "Nightly run"})
    assert response.status_code == 401


def test_create_agent_run_requires_project_name(
    client: Any, app_module: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    _authenticate(monkeypatch, app_module)
    response = client.post("/api/agent-runs", json={})
    assert response.status_code == 400


def test_create_agent_run_unknown_user_returns_404(
    client: Any, app_module: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    _authenticate(monkeypatch, app_module)
    import api_endpoints.agent_runs.handler as handler

    monkeypatch.setattr(handler, "user_id_for_email", lambda email: None)
    response = client.post("/api/agent-runs", json={"project_name": "Nightly run"})
    assert response.status_code == 404


def test_create_and_get_agent_run_roundtrip(
    client: Any, app_module: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    _authenticate(monkeypatch, app_module)
    import api_endpoints.agent_runs.handler as handler

    monkeypatch.setattr(handler, "user_id_for_email", lambda email: 7)
    monkeypatch.setattr(handler, "create_run", lambda user_id, project_name, chat_id=None: 99)
    fake_run = {
        "id": 99,
        "user_id": 7,
        "project_name": "Nightly run",
        "status": "queued",
        "cost_usd": 0,
        "created": None,
        "updated": None,
        "started_at": None,
        "finished_at": None,
    }
    monkeypatch.setattr(handler, "get_run", lambda run_id, user_id: fake_run)

    response = client.post("/api/agent-runs", json={"project_name": "Nightly run"})
    assert response.status_code == 201
    body = response.get_json()
    assert body["id"] == 99
    assert body["status"] == "queued"

    response = client.get("/api/agent-runs/99")
    assert response.status_code == 200
    assert response.get_json()["project_name"] == "Nightly run"


def test_get_agent_run_not_found(client: Any, app_module: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    _authenticate(monkeypatch, app_module)
    import api_endpoints.agent_runs.handler as handler

    monkeypatch.setattr(handler, "user_id_for_email", lambda email: 7)
    monkeypatch.setattr(handler, "get_run", lambda run_id, user_id: None)

    response = client.get("/api/agent-runs/123")
    assert response.status_code == 404


def test_list_agent_runs(client: Any, app_module: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    _authenticate(monkeypatch, app_module)
    import api_endpoints.agent_runs.handler as handler

    monkeypatch.setattr(handler, "user_id_for_email", lambda email: 7)
    monkeypatch.setattr(
        handler,
        "list_runs",
        lambda user_id, status=None, limit=50: [
            {"id": 1, "status": "running", "cost_usd": 1.5, "created": None, "updated": None,
             "started_at": None, "finished_at": None}
        ],
    )

    response = client.get("/api/agent-runs?status=running")
    assert response.status_code == 200
    body = response.get_json()
    assert len(body["runs"]) == 1
    assert body["runs"][0]["cost_usd"] == 1.5


def test_intervention_invalid_action_returns_400(
    client: Any, app_module: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    _authenticate(monkeypatch, app_module)
    import api_endpoints.agent_runs.handler as handler

    monkeypatch.setattr(handler, "user_id_for_email", lambda email: 7)

    response = client.post("/api/agent-runs/1/intervene", json={"action": "explode"})
    assert response.status_code == 400


def test_intervention_message_requires_message_body(
    client: Any, app_module: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    _authenticate(monkeypatch, app_module)
    import api_endpoints.agent_runs.handler as handler

    monkeypatch.setattr(handler, "user_id_for_email", lambda email: 7)

    response = client.post("/api/agent-runs/1/intervene", json={"action": "message"})
    assert response.status_code == 400


def test_intervention_pause_success(client: Any, app_module: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    _authenticate(monkeypatch, app_module)
    import api_endpoints.agent_runs.handler as handler

    monkeypatch.setattr(handler, "user_id_for_email", lambda email: 7)
    monkeypatch.setattr(
        handler,
        "apply_intervention",
        lambda run_id, user_id, event_type, actor=None, message=None: {
            "run_id": run_id, "event_type": event_type, "status": "paused"
        },
    )

    response = client.post("/api/agent-runs/1/intervene", json={"action": "pause"})
    assert response.status_code == 200
    assert response.get_json()["status"] == "paused"


def test_intervention_invalid_transition_returns_400(
    client: Any, app_module: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    _authenticate(monkeypatch, app_module)
    import api_endpoints.agent_runs.handler as handler

    monkeypatch.setattr(handler, "user_id_for_email", lambda email: 7)

    def _raise(*args: Any, **kwargs: Any) -> None:
        raise ValueError("Cannot pause a run in status 'completed'.")

    monkeypatch.setattr(handler, "apply_intervention", _raise)

    response = client.post("/api/agent-runs/1/intervene", json={"action": "pause"})
    assert response.status_code == 400


def test_intervention_missing_run_returns_404(
    client: Any, app_module: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    _authenticate(monkeypatch, app_module)
    import api_endpoints.agent_runs.handler as handler

    monkeypatch.setattr(handler, "user_id_for_email", lambda email: 7)

    def _raise(*args: Any, **kwargs: Any) -> None:
        raise ValueError("Run 999 not found.")

    monkeypatch.setattr(handler, "apply_intervention", _raise)

    response = client.post("/api/agent-runs/999/intervene", json={"action": "pause"})
    assert response.status_code == 404


def test_get_run_events(client: Any, app_module: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    _authenticate(monkeypatch, app_module)
    import api_endpoints.agent_runs.handler as handler

    monkeypatch.setattr(handler, "user_id_for_email", lambda email: 7)
    monkeypatch.setattr(handler, "get_run", lambda run_id, user_id: {"id": run_id})
    monkeypatch.setattr(
        handler,
        "list_run_events",
        lambda run_id, user_id, limit=100: [{"id": 1, "event_type": "pause", "created": None}],
    )

    response = client.get("/api/agent-runs/1/events")
    assert response.status_code == 200
    assert len(response.get_json()["events"]) == 1


def test_get_run_events_missing_run_returns_404(
    client: Any, app_module: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    _authenticate(monkeypatch, app_module)
    import api_endpoints.agent_runs.handler as handler

    monkeypatch.setattr(handler, "user_id_for_email", lambda email: 7)
    monkeypatch.setattr(handler, "get_run", lambda run_id, user_id: None)

    response = client.get("/api/agent-runs/1/events")
    assert response.status_code == 404
