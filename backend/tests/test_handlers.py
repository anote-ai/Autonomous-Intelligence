from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
from api_endpoints.chat import handler as chat_handler
from api_endpoints.documents import handler as documents_handler


def _json_request(payload: dict[str, Any]) -> Any:
    return SimpleNamespace(get_json=lambda force=True: payload)


def test_chat_handlers(app_module: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    with app_module.app.app_context():
        monkeypatch.setattr(chat_handler, "add_chat", lambda user_email, chat_type, model_type: 7)
        create_response = chat_handler.CreateNewChatHandler(
            _json_request({"chat_type": 0, "model_type": 1}),
            "user@example.com",
        )
        assert create_response.get_json() == {"chat_id": 7}

        monkeypatch.setattr(chat_handler, "retrieve_chats", lambda user_email: [{"id": 1}])
        chats_response = chat_handler.RetrieveChatsHandler("user@example.com")
        assert chats_response.get_json() == {"chat_info": [{"id": 1}]}

        monkeypatch.setattr(chat_handler, "retrieve_messages", lambda *args: [{"id": 1, "message_text": "hello"}])
        monkeypatch.setattr(chat_handler, "get_chat_info", lambda chat_id: (0, 0, "Chat 1"))
        messages_response = chat_handler.RetrieveMessagesHandler(
            _json_request({"chat_type": 0, "chat_id": 1}),
            "user@example.com",
        )
        assert messages_response.get_json() == {"messages": [{"id": 1, "message_text": "hello"}], "chat_name": "Chat 1"}

        captured: dict[str, Any] = {}

        def _update_chat_name(user_email: str, chat_id: int, chat_name: str) -> None:
            captured["user_email"] = user_email
            captured["chat_id"] = chat_id
            captured["chat_name"] = chat_name

        monkeypatch.setattr(chat_handler, "update_chat_name", _update_chat_name)
        update_response, update_status = chat_handler.UpdateChatNameHandler(
            _json_request({"chat_id": 1, "chat_name": "Renamed"}),
            "user@example.com",
        )
        assert update_status == 200
        assert update_response.get_json() == {"Success": "Chat name updated"}
        assert captured == {"user_email": "user@example.com", "chat_id": 1, "chat_name": "Renamed"}

        monkeypatch.setattr(chat_handler, "delete_chat", lambda chat_id, user_email: "deleted")
        delete_response = chat_handler.DeleteChatHandler(_json_request({"chat_id": 1}), "user@example.com")
        assert delete_response.get_json() == {"message": "deleted"}

        monkeypatch.setattr(chat_handler, "find_most_recent_chat", lambda user_email: {"id": 2})
        recent_response = chat_handler.FindMostRecentChatHandler("user@example.com")
        assert recent_response.get_json() == {"chat_info": {"id": 2}}


def test_document_handlers(app_module: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    with app_module.app.app_context():
        add_document_calls: list[tuple[str, str, str]] = []
        remote_calls: list[tuple[str, int, int]] = []

        def _add_document(text: str, filename: str, chat_id: str, **kwargs: Any) -> tuple[int, bool]:
            add_document_calls.append((text, filename, chat_id))
            return 5, False

        class _Chunker:
            @staticmethod
            def remote(text: str, max_chunk_size: int, doc_id: int) -> None:
                remote_calls.append((text, max_chunk_size, doc_id))

        request = SimpleNamespace(
            form=SimpleNamespace(getlist=lambda key: ["11"]),
            files=SimpleNamespace(getlist=lambda key: [SimpleNamespace(filename="sample.pdf", content_type=None)]),
        )
        parser_module = SimpleNamespace(from_buffer=lambda file: {"content": "document text"})

        monkeypatch.setattr(documents_handler, "add_document", _add_document)
        ingest_response, ingest_status = documents_handler.IngestDocumentsHandler(
            request,
            "user@example.com",
            parser_module,
            _Chunker(),
        )
        assert ingest_status == 200
        assert ingest_response.get_json() == {"Success": "Document Uploaded"}
        assert add_document_calls == [("document text", "sample.pdf", "11")]
        assert remote_calls == [("document text", 1000, 5)]

        monkeypatch.setattr(documents_handler, "retrieve_docs", lambda chat_id, user_email: [{"id": 1}])
        docs_response = documents_handler.RetrieveCurrentDocsHandler(
            _json_request({"chat_id": 11}),
            "user@example.com",
        )
        assert docs_response.get_json() == {"doc_info": [{"id": 1}]}

        deleted_docs: list[tuple[int, str]] = []
        monkeypatch.setattr(documents_handler, "delete_doc", lambda doc_id, user_email: deleted_docs.append((doc_id, user_email)))
        assert documents_handler.DeleteDocHandler(_json_request({"doc_id": 9}), "user@example.com") == "success"
        assert deleted_docs == [(9, "user@example.com")]

        reset_calls: list[tuple[int, str]] = []
        mode_changes: list[tuple[int, int, str]] = []
        monkeypatch.setattr(documents_handler, "reset_chat", lambda chat_id, user_email: reset_calls.append((chat_id, user_email)))
        monkeypatch.setattr(documents_handler, "change_chat_mode", lambda chat_mode, chat_id, user_email: mode_changes.append((chat_mode, chat_id, user_email)))
        assert (
            documents_handler.ChangeChatModeHandler(
                _json_request({"chat_id": 11, "model_type": 1}),
                "user@example.com",
            )
            == "Success"
        )
        assert reset_calls == [(11, "user@example.com")]
        assert mode_changes == [(1, 11, "user@example.com")]

        deleted_uploads: list[tuple[int, str]] = []
        monkeypatch.setattr(documents_handler, "reset_uploaded_docs", lambda chat_id, user_email: deleted_uploads.append((chat_id, user_email)))
        reset_response, reset_status = documents_handler.ResetChatHandler(
            _json_request({"chat_id": 11, "delete_docs": True}),
            "user@example.com",
        )
        assert reset_status == 200
        assert reset_response.get_json() == {"Success": "Success"}
        assert deleted_uploads == [(11, "user@example.com")]
