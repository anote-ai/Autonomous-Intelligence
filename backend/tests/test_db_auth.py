from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from database import db_auth


@pytest.fixture()
def db_auth_connection(monkeypatch: pytest.MonkeyPatch) -> tuple[MagicMock, MagicMock]:
    connection = MagicMock()
    cursor = MagicMock()
    monkeypatch.setattr(db_auth, "get_db_connection", lambda: (connection, cursor))
    return connection, cursor


def test_extract_user_email_from_jwt(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(db_auth, "decode_token", lambda token: {"sub": "jwt@example.com"})
    request = SimpleNamespace(headers={"Authorization": "Bearer jwt-token"})
    assert db_auth.extractUserEmailFromRequest(request) == "jwt@example.com"


def test_extract_user_email_falls_back_to_session(monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise_invalid(token: str) -> dict[str, str]:
        raise db_auth.InvalidTokenError()

    monkeypatch.setattr(db_auth, "decode_token", _raise_invalid)
    monkeypatch.setattr(db_auth, "user_email_for_session_token", lambda token: "session@example.com")
    request = SimpleNamespace(headers={"Authorization": "Bearer session-token"})
    assert db_auth.extractUserEmailFromRequest(request) == "session@example.com"


def test_extract_user_email_falls_back_to_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise_invalid(token: str) -> dict[str, str]:
        raise db_auth.InvalidTokenError()

    def _raise_session_failure(token: str) -> str:
        raise RuntimeError("bad session")

    monkeypatch.setattr(db_auth, "decode_token", _raise_invalid)
    monkeypatch.setattr(db_auth, "user_email_for_session_token", _raise_session_failure)
    monkeypatch.setattr(db_auth, "is_api_key_valid", lambda token: True)
    monkeypatch.setattr(db_auth, "user_email_for_api_key", lambda token: "api@example.com")
    request = SimpleNamespace(headers={"Authorization": "Bearer api-key"})
    assert db_auth.extractUserEmailFromRequest(request) == "api@example.com"


def test_extract_user_email_raises_on_invalid_header() -> None:
    request = SimpleNamespace(headers={"Authorization": "invalid"})
    with pytest.raises(db_auth.InvalidTokenError):
        db_auth.extractUserEmailFromRequest(request)


def test_lookup_helpers_and_credit_checks(db_auth_connection: tuple[MagicMock, MagicMock]) -> None:
    connection, cursor = db_auth_connection
    cursor.fetchone.side_effect = [
        {"email": "session@example.com"},
        {"email": "api@example.com"},
        {"COUNT(*)": 1},
        {"COUNT(*)": 0},
        {"credits": 5},
        {"credits": 0},
        {"credits": 3},
    ]
    assert db_auth.user_email_for_session_token("session-token") == "session@example.com"
    assert db_auth.user_email_for_api_key("api-key") == "api@example.com"
    assert db_auth.is_api_key_valid("api-key") is True
    assert db_auth.is_session_token_valid("session-token") is False
    assert db_auth.user_has_credits("user@example.com", min_credits=1) is True
    assert db_auth.user_has_credits("user@example.com", min_credits=1) is False
    assert db_auth.api_key_user_has_credits("api-key", min_credits=1) is True
    assert connection.close.call_count >= 7
