from __future__ import annotations

import io
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import jwt
import pytest
from werkzeug.exceptions import HTTPException


def _authenticate(monkeypatch: pytest.MonkeyPatch, app_module: Any, email: str = "test@example.com") -> None:
    monkeypatch.setattr(app_module, "extractUserEmailFromRequest", lambda request: email)


def _invalidate_token(monkeypatch: pytest.MonkeyPatch, app_module: Any) -> None:
    def _raise_invalid(request: Any) -> str:
        raise app_module.InvalidTokenError()

    monkeypatch.setattr(app_module, "extractUserEmailFromRequest", _raise_invalid)


def test_login_with_email_delegates(client: Any, app_module: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(app_module, "LoginHandler", lambda request: app_module.jsonify(email=request.args["email"]))
    response = client.get("/login?email=test@example.com")
    assert response.status_code == 200
    assert response.get_json() == {"email": "test@example.com"}


def test_login_without_email_returns_auth_url(client: Any) -> None:
    response = client.get("/login")
    assert response.status_code == 200
    assert response.get_json() == {"auth_url": "http://example.com/oauth"}


def test_login_without_email_preserves_product_hash_and_trial_code(client: Any, app_module: Any) -> None:
    response = client.get("/login?product_hash=prod-1&free_trial_code=trial-1")
    assert response.status_code == 200
    assert response.get_json() == {"auth_url": "http://example.com/oauth"}


def test_callback_success(client: Any, app_module: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(app_module, "create_user_if_does_not_exist", lambda *args: 1)
    monkeypatch.setattr(app_module, "create_access_token", lambda identity: "access-token")
    monkeypatch.setattr(app_module, "create_refresh_token", lambda identity: "refresh-token")
    state = jwt.encode({"redirect_uri": "http://localhost/callback"}, app_module.app.config["JWT_SECRET_KEY"], algorithm="HS256")
    response = client.get(f"/callback?state={state}&code=test-code")
    assert response.status_code == 302
    assert "accessToken=access-token" in response.location
    assert "refreshToken=refresh-token" in response.location


def test_callback_invalid_state_signature_returns_500(client: Any) -> None:
    invalid_state = jwt.encode({"redirect_uri": "http://localhost/callback"}, "wrong-secret", algorithm="HS256")
    response = client.get(f"/callback?state={invalid_state}&code=test-code")
    assert response.status_code == 500


def test_callback_includes_optional_redirect_params(client: Any, app_module: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(app_module, "create_user_if_does_not_exist", lambda *args: 1)
    monkeypatch.setattr(app_module, "create_access_token", lambda identity: "access-token")
    monkeypatch.setattr(app_module, "create_refresh_token", lambda identity: "refresh-token")
    state = jwt.encode(
        {
            "redirect_uri": "http://localhost/callback",
            "product_hash": "prod-1",
            "free_trial_code": "trial-1",
        },
        app_module.app.config["JWT_SECRET_KEY"],
        algorithm="HS256",
    )
    response = client.get(f"/callback?state={state}&code=test-code")
    assert response.status_code == 302
    assert "product_hash=prod-1" in response.location
    assert "free_trial_code=trial-1" in response.location


def test_refresh_success(client: Any, app_module: Any, monkeypatch: pytest.MonkeyPatch, refresh_headers: dict[str, str]) -> None:
    monkeypatch.setattr(app_module, "decode_token", lambda token: {"sub": "test@example.com"})
    monkeypatch.setattr(app_module, "create_access_token", lambda identity: "new-access-token")
    response = client.post("/refresh", headers=refresh_headers)
    assert response.status_code == 200
    assert response.get_json() == {"accessToken": "new-access-token"}


def test_refresh_invalid_token_returns_401(
    client: Any, app_module: Any, monkeypatch: pytest.MonkeyPatch, refresh_headers: dict[str, str]
) -> None:
    def _raise_invalid(token: str) -> dict[str, str]:
        raise app_module.InvalidTokenError()

    monkeypatch.setattr(app_module, "decode_token", _raise_invalid)
    response = client.post("/refresh", headers=refresh_headers)
    assert response.status_code == 401
    assert response.get_json() == {"error": "Invalid JWT"}


def test_refresh_invalid_header_returns_401(client: Any) -> None:
    with client.application.test_request_context("/refresh", method="POST", headers={"Authorization": "Bearer"}):
        response, status = client.application.view_functions["refresh"].__wrapped__()
    assert status == 401
    assert response.get_json() == {"error": "Invalid Authorization header"}


@pytest.mark.parametrize(
    ("endpoint", "handler_name", "payload"),
    [
        ("/signUp", "SignUpHandler", {"email": "new@example.com", "password": "pw", "name": "New User"}),
        ("/forgotPassword", "ForgotPasswordHandler", {"email": "new@example.com"}),
        ("/resetPassword", "ResetPasswordHandler", {"token": "reset-token", "password": "pw"}),
    ],
)
def test_auth_handler_routes_delegate(
    client: Any,
    app_module: Any,
    monkeypatch: pytest.MonkeyPatch,
    endpoint: str,
    handler_name: str,
    payload: dict[str, str],
) -> None:
    monkeypatch.setattr(app_module, handler_name, lambda *args: app_module.jsonify(ok=True))
    response = client.post(endpoint, json=payload)
    assert response.status_code == 200
    assert response.get_json() == {"ok": True}


def test_refresh_credits_success(client: Any, app_module: Any, monkeypatch: pytest.MonkeyPatch, auth_headers: dict[str, str]) -> None:
    _authenticate(monkeypatch, app_module)
    monkeypatch.setattr(app_module, "RefreshCreditsHandler", lambda request, user_email: {"credits": 9})
    response = client.post("/refreshCredits", headers=auth_headers)
    assert response.status_code == 200
    assert response.get_json() == {"credits": 9}


def test_refresh_credits_invalid_token(client: Any, app_module: Any, monkeypatch: pytest.MonkeyPatch, auth_headers: dict[str, str]) -> None:
    _invalidate_token(monkeypatch, app_module)
    response = client.post("/refreshCredits", headers=auth_headers)
    assert response.status_code == 401
    assert response.get_json() == {"error": "Invalid JWT"}


def test_deduct_credits_success(client: Any, app_module: Any, monkeypatch: pytest.MonkeyPatch, auth_headers: dict[str, str]) -> None:
    _authenticate(monkeypatch, app_module)
    monkeypatch.setattr("database.db.deduct_credits_from_user", lambda user_email, credits: True)
    mock_connection = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = {"credits": 7}
    mock_connection.cursor.return_value = mock_cursor
    monkeypatch.setattr("database.db.get_db_connection", lambda: (mock_connection, mock_cursor))
    response = client.post("/deductCredits", json={"creditsToDeduct": 3}, headers=auth_headers)
    assert response.status_code == 200
    assert response.get_json() == {"success": True, "newCredits": 7, "creditsDeducted": 3}


def test_deduct_credits_insufficient_balance(client: Any, app_module: Any, monkeypatch: pytest.MonkeyPatch, auth_headers: dict[str, str]) -> None:
    _authenticate(monkeypatch, app_module)
    monkeypatch.setattr("database.db.deduct_credits_from_user", lambda user_email, credits: False)
    response = client.post("/deductCredits", json={"creditsToDeduct": 3}, headers=auth_headers)
    assert response.status_code == 400
    assert response.get_json() == {"error": "Insufficient credits"}


def test_deduct_credits_invalid_token(client: Any, app_module: Any, monkeypatch: pytest.MonkeyPatch, auth_headers: dict[str, str]) -> None:
    _invalidate_token(monkeypatch, app_module)
    response = client.post("/deductCredits", json={"creditsToDeduct": 1}, headers=auth_headers)
    assert response.status_code == 401
    assert response.get_json() == {"error": "Invalid JWT"}


@pytest.mark.parametrize(
    ("endpoint", "handler_name", "payload", "expected"),
    [
        ("/createCheckoutSession", "CreateCheckoutSessionHandler", {}, {"session_id": "checkout-1"}),
        ("/createPortalSession", "CreatePortalSessionHandler", {}, {"url": "https://example.com/portal"}),
        ("/viewUser", "ViewUserHandler", None, {"email": "test@example.com"}),
        ("/generateAPIKey", "GenerateAPIKeyHandler", {}, {"api_key": "key-1"}),
        ("/getAPIKeys", "GetAPIKeysHandler", None, {"keys": []}),
    ],
)
def test_authenticated_handler_routes(
    client: Any,
    app_module: Any,
    monkeypatch: pytest.MonkeyPatch,
    auth_headers: dict[str, str],
    endpoint: str,
    handler_name: str,
    payload: dict[str, Any] | None,
    expected: dict[str, Any],
) -> None:
    _authenticate(monkeypatch, app_module)
    monkeypatch.setattr(app_module, "verifyAuthForPaymentsTrustedTesters", lambda user_email: True)
    monkeypatch.setattr(app_module, "verifyAuthForCheckoutSession", lambda user_email, mail: None)
    monkeypatch.setattr(app_module, "verifyAuthForPortalSession", lambda request, user_email, mail: None)
    monkeypatch.setattr(app_module, handler_name, lambda *args: app_module.jsonify(**expected))
    method = client.get if payload is None and endpoint in {"/viewUser", "/getAPIKeys"} else client.post
    response = method(endpoint, json=payload, headers=auth_headers)
    assert response.status_code == 200
    assert response.get_json() == expected


def test_delete_api_key_route_verifies_auth(client: Any, app_module: Any, monkeypatch: pytest.MonkeyPatch, auth_headers: dict[str, str]) -> None:
    monkeypatch.setattr(app_module, "verifyAuthForIDs", lambda *args: None)
    monkeypatch.setattr(app_module, "DeleteAPIKeyHandler", lambda request: "deleted")
    response = client.post("/deleteAPIKey", json={"api_key_id": 5}, headers=auth_headers)
    assert response.status_code == 200
    assert response.get_data(as_text=True) == "deleted"


def test_verify_auth_for_ids_invalid_token_and_access_denied(
    client: Any, app_module: Any, monkeypatch: pytest.MonkeyPatch, auth_headers: dict[str, str]
) -> None:
    _invalidate_token(monkeypatch, app_module)
    with app_module.app.test_request_context("/deleteAPIKey", method="POST", json={"api_key_id": 5}, headers=auth_headers):
        response, status = app_module.verifyAuthForIDs(app_module.ProtectedDatabaseTable.API_KEYS, 5)
        assert status == 401
        assert response.get_json() == {"error": "Invalid JWT"}

    _authenticate(monkeypatch, app_module)
    monkeypatch.setattr(app_module, "user_id_for_email", lambda email: 1)
    monkeypatch.setattr(app_module, "api_key_access_invalid", lambda user_id, api_key_id: True)
    with app_module.app.test_request_context("/deleteAPIKey", method="POST", json={"api_key_id": 5}, headers=auth_headers):
        with pytest.raises(HTTPException) as exc_info:
            app_module.verifyAuthForIDs(app_module.ProtectedDatabaseTable.API_KEYS, 5)
        assert exc_info.value.code == 401


def test_stripe_webhook_handles_success_and_bad_signature(client: Any, app_module: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(app_module, "StripeWebhookHandler", lambda request, event: "ok")
    response = client.post("/stripeWebhook", headers={"Stripe-Signature": "sig"}, data=b"{}")
    assert response.status_code == 200
    assert response.get_data(as_text=True) == "ok"

    def _raise_signature_error(data: bytes, signature: str | None, secret: str) -> dict[str, str]:
        raise app_module.stripe.error.SignatureVerificationError("bad sig")

    monkeypatch.setattr(app_module.stripe.Webhook, "construct_event", _raise_signature_error)
    bad_response = client.post("/stripeWebhook", headers={"Stripe-Signature": "sig"}, data=b"{}")
    assert bad_response.status_code == 400
    assert bad_response.get_data(as_text=True) == "Invalid signature"


def test_share_and_health_routes(client: Any, app_module: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(app_module, "create_chat_shareable_url", lambda chat_id: "/playbook/shared")
    share_response = client.get("/generate-playbook/9")
    assert share_response.status_code == 200
    assert share_response.get_json()["url"] == "/playbook/shared"

    monkeypatch.setattr(app_module, "access_sharable_chat", lambda playbook_url: app_module.jsonify(url=playbook_url))
    import_response = client.post("/playbook/shared-id")
    assert import_response.status_code == 200
    assert import_response.get_json() == {"url": "shared-id"}

    health_response = client.get("/health")
    assert health_response.status_code == 200
    assert health_response.get_data(as_text=True) == "Healthy"


def test_reset_everything_success(client: Any, app_module: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    output_dir = tmp_path / "output"
    source_dir = tmp_path / "sources"
    output_dir.mkdir()
    source_dir.mkdir()
    (output_dir / "chat_history.csv").write_text("old", encoding="utf-8")
    monkeypatch.setattr(app_module, "output_document_path", str(output_dir))
    monkeypatch.setattr(app_module, "source_documents_path", str(source_dir))
    response = client.post("/api/reset-everything")
    assert response.status_code == 200
    assert response.get_data(as_text=True) == "Reset was successful!"
    assert (output_dir / "chat_history.csv").exists()


def test_reset_everything_error_path(client: Any, app_module: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    monkeypatch.setattr(app_module, "output_document_path", str(output_dir))
    monkeypatch.setattr(app_module, "source_documents_path", str(tmp_path / "sources"))
    monkeypatch.setattr(
        app_module,
        "reset_local_chat_artifacts",
        lambda source_documents_path, output_document_path: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    response = client.post("/api/reset-everything")
    assert response.status_code == 500
    assert "Failed to delete DB folder: boom" == response.get_data(as_text=True)


def test_download_chat_history_success(client: Any, app_module: Any, monkeypatch: pytest.MonkeyPatch, auth_headers: dict[str, str]) -> None:
    _authenticate(monkeypatch, app_module)
    messages = [
        {"sent_from_user": 1, "message_text": "Hi", "relevant_chunks": None},
        {"sent_from_user": 0, "message_text": "Hello", "relevant_chunks": "Document: Sample: Paragraph"},
    ]
    monkeypatch.setattr(app_module, "retrieve_message_from_db", lambda *args: messages)
    response = client.post("/download-chat-history", json={"chat_type": 0, "chat_id": 9}, headers=auth_headers)
    assert response.status_code == 200
    assert response.mimetype == "text/csv"
    assert "query,response,chunk1,chunk2" in response.get_data(as_text=True)


def test_download_chat_history_invalid_token_and_error(
    client: Any, app_module: Any, monkeypatch: pytest.MonkeyPatch, auth_headers: dict[str, str]
) -> None:
    _invalidate_token(monkeypatch, app_module)
    invalid_response = client.post("/download-chat-history", json={"chat_type": 0, "chat_id": 9}, headers=auth_headers)
    assert invalid_response.status_code == 401
    assert invalid_response.get_json() == {"error": "Invalid JWT"}

    _authenticate(monkeypatch, app_module)
    monkeypatch.setattr(app_module, "retrieve_message_from_db", lambda *args: None)
    error_response = client.post("/download-chat-history", json={"chat_type": 0, "chat_id": 9}, headers=auth_headers)
    assert error_response.status_code == 500
    assert error_response.get_json()["error"] == "messages must not be None"


@pytest.mark.parametrize(
    ("endpoint", "handler_name", "payload", "expected_json", "expected_text"),
    [
        ("/create-new-chat", "CreateNewChatHandler", {"chat_type": 0, "model_type": 0}, {"chat_id": 1}, None),
        ("/retrieve-all-chats", "RetrieveChatsHandler", {}, {"chat_info": []}, None),
        ("/retrieve-messages-from-chat", "RetrieveMessagesHandler", {"chat_type": 0, "chat_id": 1}, {"messages": [], "chat_name": "Chat"}, None),
        ("/update-chat-name", "UpdateChatNameHandler", {"chat_name": "Renamed", "chat_id": 1}, {"Success": "Chat name updated"}, None),
        ("/delete-chat", "DeleteChatHandler", {"chat_id": 1}, None, "deleted"),
        ("/find-most-recent-chat", "FindMostRecentChatHandler", {}, {"chat_info": {"id": 1}}, None),
        ("/ingest-pdf", "IngestDocumentsHandler", None, {"Success": "Document Uploaded"}, None),
        ("/retrieve-current-docs", "RetrieveCurrentDocsHandler", {"chat_id": 1}, {"doc_info": []}, None),
        ("/delete-doc", "DeleteDocHandler", {"doc_id": 2}, None, "success"),
        ("/change-chat-mode", "ChangeChatModeHandler", {"chat_id": 1, "model_type": 0}, None, "Success"),
        ("/reset-chat", "ResetChatHandler", {"chat_id": 1, "delete_docs": True}, {"Success": "Success"}, None),
    ],
)
def test_chat_and_document_routes_delegate(
    client: Any,
    app_module: Any,
    monkeypatch: pytest.MonkeyPatch,
    auth_headers: dict[str, str],
    endpoint: str,
    handler_name: str,
    payload: dict[str, Any] | None,
    expected_json: dict[str, Any] | None,
    expected_text: str | None,
) -> None:
    _authenticate(monkeypatch, app_module)
    if payload is None:
        body = {
            "chat_id": "1",
            "files[]": (io.BytesIO(b"pdf data"), "sample.pdf"),
        }
        monkeypatch.setattr(app_module, handler_name, lambda *args: (app_module.jsonify(Success="Document Uploaded"), 200))
        response = client.post(endpoint, data=body, headers={"Authorization": "Bearer test-token"})
    else:
        if expected_json is not None:
            monkeypatch.setattr(app_module, handler_name, lambda *args: app_module.jsonify(**expected_json))
        else:
            monkeypatch.setattr(app_module, handler_name, lambda *args: expected_text)
        response = client.post(endpoint, json=payload, headers=auth_headers)
    assert response.status_code == 200
    if expected_json is not None:
        assert response.get_json() == expected_json
    else:
        assert response.get_data(as_text=True) == expected_text


@pytest.mark.parametrize(
    "endpoint,payload",
    [
        ("/create-new-chat", {"chat_type": 0, "model_type": 0}),
        ("/retrieve-all-chats", {}),
        ("/retrieve-messages-from-chat", {"chat_type": 0, "chat_id": 1}),
        ("/update-chat-name", {"chat_name": "Renamed", "chat_id": 1}),
        ("/delete-chat", {"chat_id": 1}),
        ("/find-most-recent-chat", {}),
        ("/retrieve-current-docs", {"chat_id": 1}),
        ("/delete-doc", {"doc_id": 2}),
        ("/change-chat-mode", {"chat_id": 1, "model_type": 0}),
        ("/reset-chat", {"chat_id": 1}),
    ],
)
def test_protected_routes_return_401_on_invalid_token(
    client: Any,
    app_module: Any,
    monkeypatch: pytest.MonkeyPatch,
    auth_headers: dict[str, str],
    endpoint: str,
    payload: dict[str, Any],
) -> None:
    _invalidate_token(monkeypatch, app_module)
    response = client.post(endpoint, json=payload, headers=auth_headers)
    assert response.status_code == 401
    assert response.get_json() == {"error": "Invalid JWT"}


def test_retrieve_shared_messages_is_public(client: Any, app_module: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(app_module, "retrieve_message_from_db", lambda *args: [{"message_text": "shared"}])
    response = client.post("/retrieve-shared-messages-from-chat", json={"chat_id": 7})
    assert response.status_code == 200
    assert response.get_json() == {"messages": [{"message_text": "shared"}]}


def test_infer_chat_name_updates_name(client: Any, app_module: Any, monkeypatch: pytest.MonkeyPatch, auth_headers: dict[str, str]) -> None:
    _authenticate(monkeypatch, app_module)
    monkeypatch.setattr(app_module, "update_chat_name", lambda user_email, chat_id, new_name: None)
    response = client.post(
        "/infer-chat-name",
        json={"messages": ["hello", "world"], "chat_id": 5},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.get_json() == {"chat_name": "openai answer"}


def test_infer_chat_name_invalid_token(client: Any, app_module: Any, monkeypatch: pytest.MonkeyPatch, auth_headers: dict[str, str]) -> None:
    _invalidate_token(monkeypatch, app_module)
    response = client.post("/infer-chat-name", json={"messages": ["hello"], "chat_id": 1}, headers=auth_headers)
    assert response.status_code == 401
    assert response.get_json() == {"error": "Invalid JWT"}


def test_process_message_pdf_guest_fallback_success(client: Any, app_module: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(app_module.AgentConfig, "is_agent_enabled", staticmethod(lambda: False))
    response = client.post(
        "/process-message-pdf",
        json={"message": "hello", "chat_id": 0, "model_type": 0, "is_guest": True},
    )
    assert response.status_code == 200
    assert "guest mode" in response.get_json()["answer"]


def test_process_message_pdf_authenticated_agent_stream(client: Any, app_module: Any, monkeypatch: pytest.MonkeyPatch, auth_headers: dict[str, str]) -> None:
    _authenticate(monkeypatch, app_module)

    class StreamingAgent:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        def process_query_stream(self, query: str, chat_id: int, user_email: str) -> list[dict[str, str]]:
            return [{"answer": "chunk-1"}]

    monkeypatch.setattr(app_module.AgentConfig, "is_agent_enabled", staticmethod(lambda: True))
    monkeypatch.setattr(app_module, "ReactiveDocumentAgent", StreamingAgent)
    response = client.post(
        "/process-message-pdf",
        json={"message": "hello", "chat_id": 1, "model_type": 0, "is_guest": False},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert "chunk-1" in response.get_data(as_text=True)


def test_process_message_pdf_invalid_token(client: Any, app_module: Any, monkeypatch: pytest.MonkeyPatch, auth_headers: dict[str, str]) -> None:
    monkeypatch.setattr(app_module.AgentConfig, "is_agent_enabled", staticmethod(lambda: False))
    _invalidate_token(monkeypatch, app_module)
    response = client.post(
        "/process-message-pdf",
        json={"message": "hello", "chat_id": 1, "model_type": 0, "is_guest": False},
        headers=auth_headers,
    )
    assert response.status_code == 401
    assert response.get_json() == {"error": "Invalid JWT"}


def test_add_model_key(client: Any, app_module: Any, monkeypatch: pytest.MonkeyPatch, auth_headers: dict[str, str]) -> None:
    _authenticate(monkeypatch, app_module)
    monkeypatch.setattr(app_module, "add_model_key_to_db", lambda *args: None)
    add_key_response = client.post("/add-model-key", json={"chat_id": 1, "model_key": "custom"}, headers=auth_headers)
    assert add_key_response.status_code == 200
    assert add_key_response.get_data(as_text=True) == "success"


def test_add_model_key_invalid_token(client: Any, app_module: Any, monkeypatch: pytest.MonkeyPatch, auth_headers: dict[str, str]) -> None:
    _invalidate_token(monkeypatch, app_module)
    response = client.post("/add-model-key", json={"chat_id": 1, "model_key": "custom"}, headers=auth_headers)
    assert response.status_code == 401
    assert response.get_json() == {"error": "Invalid JWT"}


def test_public_upload_success_and_invalid_task(client: Any, app_module: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(app_module, "is_api_key_valid", lambda api_key: True)
    monkeypatch.setattr("database.db_auth.api_key_user_has_credits", lambda api_key, min_credits=1: True)
    monkeypatch.setattr("database.db_auth.deduct_credits_from_api_key_user", lambda api_key, credits: True)
    monkeypatch.setattr(app_module, "ensure_SDK_user_exists", lambda user_email: 1)
    monkeypatch.setattr(app_module, "add_chat_to_db", lambda *args: 42)
    monkeypatch.setattr(app_module, "add_document_to_db", lambda *args, **kwargs: (5, False))
    monkeypatch.setattr(app_module, "get_text_from_url", lambda url: "text")

    success_response = client.post(
        "/public/upload",
        headers={"Authorization": "Bearer api-key"},
        data={
            "task_type": "documents",
            "model_type": "gpt",
            "files[]": (io.BytesIO(b"pdf"), "sample.pdf"),
        },
    )
    assert success_response.status_code == 200
    assert success_response.get_json() == {"id": 42}

    invalid_response = client.post(
        "/public/upload",
        headers={"Authorization": "Bearer api-key"},
        data={"task_type": "invalid", "model_type": "gpt"},
    )
    assert invalid_response.status_code == 400
    assert invalid_response.get_json() == {"id": "Please enter a valid task type"}


def test_public_endpoints_require_valid_api_key(client: Any, app_module: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(app_module, "is_api_key_valid", lambda api_key: False)
    response = client.post("/public/evaluate", json={"message_id": 1}, headers={"Authorization": "Bearer bad-key"})
    assert response.status_code == 401
    assert response.get_data(as_text=True) == "Unauthorized"

    monkeypatch.setattr(app_module, "is_api_key_valid", lambda api_key: True)
    monkeypatch.setattr("database.db_auth.api_key_user_has_credits", lambda api_key, min_credits=1: False)
    credit_response = client.post("/public/evaluate", json={"message_id": 1}, headers={"Authorization": "Bearer ok-key"})
    assert credit_response.status_code == 403
    assert credit_response.get_json() == {
        "error": "Insufficient credits. Please add credits to your account to use the API."
    }


def test_public_chat_and_evaluate(client: Any, app_module: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(app_module, "is_api_key_valid", lambda api_key: True)
    monkeypatch.setattr("database.db_auth.api_key_user_has_credits", lambda api_key, min_credits=1: True)
    monkeypatch.setattr("database.db_auth.deduct_credits_from_api_key_user", lambda api_key, credits: True)
    monkeypatch.setattr(app_module, "ensure_SDK_user_exists", lambda user_email: 1)
    monkeypatch.setattr(app_module.AgentConfig, "is_agent_enabled", staticmethod(lambda: False))
    monkeypatch.setattr(app_module, "get_chat_info", lambda chat_id: (0, 0, "Chat"))
    monkeypatch.setattr(app_module, "get_relevant_chunks", lambda *args: [("chunk", "doc", 1)])
    monkeypatch.setattr(app_module, "add_message_to_db", lambda *args, **kwargs: 10)
    monkeypatch.setattr(app_module, "add_sources_to_db", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        app_module,
        "get_message_info",
        lambda message_id, user_email: (
            {"message_text": "question"},
            {"message_text": "answer", "relevant_chunks": "context"},
        ),
    )

    chat_response = client.post(
        "/public/chat",
        headers={"Authorization": "Bearer api-key"},
        json={"chat_id": 9, "message": "hello"},
    )
    assert chat_response.status_code == 200
    assert chat_response.get_json() == {"message_id": 10, "answer": "openai answer", "sources": [["1", "doc", "chunk"]]}

    evaluate_response = client.post(
        "/public/evaluate",
        headers={"Authorization": "Bearer api-key"},
        json={"message_id": 10},
    )
    assert evaluate_response.status_code == 200
    assert evaluate_response.get_json() == {
        "question": ["question"],
        "answer": ["answer"],
        "contexts": [["context"]],
    }


def test_custom_json_encoder_and_user_from_token_none(app_module: Any) -> None:
    from dataclasses import dataclass

    class DictLike:
        __slots__ = ()

        def dict(self) -> dict[str, str]:
            return {"kind": "dictlike"}

    class NamespaceLike:
        def __init__(self) -> None:
            self.value = "namespace"

    @dataclass(slots=True)
    class DataClassLike:
        value: str

    encoder = app_module.CustomJSONEncoder()
    assert encoder.default(NamespaceLike()) == {"value": "namespace"}
    assert encoder.default(DictLike()) == {"kind": "dictlike"}
    assert encoder.default(DataClassLike("dataclass")) == {"value": "dataclass"}
    assert app_module.get_user_from_token(None) is None


def test_company_routes_and_user_lookup(client: Any, app_module: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    mock_cursor = MagicMock()
    mock_cursor.fetchall.side_effect = [
        [{"id": 1, "name": "Acme", "path": "/acme"}],
        [{"name": "Acme", "path": "/acme"}],
    ]
    mock_cursor.fetchone.side_effect = [
        {"id": 8},
        {"email": "test@example.com", "session_token_expiration": "2099-01-01 00:00:00"},
    ]
    app_module.mysql.connection.cursor.return_value = mock_cursor

    companies_response = client.get("/api/companies")
    assert companies_response.status_code == 200
    assert companies_response.get_json() == [{"id": 1, "name": "Acme", "path": "/acme"}]

    with app_module.app.app_context():
        jwt_token = app_module.create_access_token(identity="test@example.com")
    user_companies_response = client.get("/api/user/companies", headers={"Authorization": f"Bearer {jwt_token}"})
    assert user_companies_response.status_code == 200
    assert user_companies_response.get_json() == [{"name": "Acme", "path": "/acme"}]

    user = app_module.get_user_from_token("session-token")
    assert user == {"email": "test@example.com", "session_token_expiration": "2099-01-01 00:00:00"}


def test_user_companies_invalid_user(client: Any, app_module: Any) -> None:
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = None
    app_module.mysql.connection.cursor.return_value = mock_cursor
    with app_module.app.app_context():
        jwt_token = app_module.create_access_token(identity="missing@example.com")
    response = client.get("/api/user/companies", headers={"Authorization": f"Bearer {jwt_token}"})
    assert response.status_code == 401
    assert response.get_json() == {"error": "Invalid user"}


def test_generate_and_get_api_keys_invalid_token(
    client: Any, app_module: Any, monkeypatch: pytest.MonkeyPatch, auth_headers: dict[str, str]
) -> None:
    _invalidate_token(monkeypatch, app_module)
    generate_response = client.post("/generateAPIKey", json={}, headers=auth_headers)
    assert generate_response.status_code == 401
    assert generate_response.get_json() == {"error": "Invalid JWT"}

    get_response = client.get("/getAPIKeys", headers=auth_headers)
    assert get_response.status_code == 401
    assert get_response.get_json() == {"error": "Invalid JWT"}


def test_checkout_portal_and_view_user_reject_invalid_auth(
    client: Any, app_module: Any, monkeypatch: pytest.MonkeyPatch, auth_headers: dict[str, str]
) -> None:
    _invalidate_token(monkeypatch, app_module)
    for endpoint in ["/createCheckoutSession", "/createPortalSession"]:
        response = client.post(endpoint, json={}, headers=auth_headers)
        assert response.status_code == 401
        assert response.get_json() == {"error": "Invalid JWT"}

    view_response = client.get("/viewUser", headers=auth_headers)
    assert view_response.status_code == 401
    assert view_response.get_json() == {"error": "Invalid JWT"}

    _authenticate(monkeypatch, app_module)
    monkeypatch.setattr(app_module, "verifyAuthForPaymentsTrustedTesters", lambda user_email: False)
    unauthorized_checkout = client.post("/createCheckoutSession", json={}, headers=auth_headers)
    unauthorized_portal = client.post("/createPortalSession", json={}, headers=auth_headers)
    assert unauthorized_checkout.status_code == 401
    assert unauthorized_portal.status_code == 401
