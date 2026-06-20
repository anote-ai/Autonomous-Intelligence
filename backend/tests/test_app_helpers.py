from __future__ import annotations

import json
from pathlib import Path

import pytest
from app_helpers import (
    SUPPORTED_EXPORT_FORMATS,
    UnsupportedExportFormatError,
    build_callback_redirect_url,
    build_oauth_state,
    chat_history_csv_response,
    chat_history_export_response,
    chat_history_json_response,
    chat_history_markdown_response,
    chat_history_text_response,
    pair_chat_messages,
    reset_local_chat_artifacts,
)


def test_build_oauth_state() -> None:
    assert build_oauth_state("http://localhost/callback", None, None) == {
        "redirect_uri": "http://localhost/callback"
    }
    assert build_oauth_state("http://localhost/callback", "prod-1", "trial-1") == {
        "redirect_uri": "http://localhost/callback",
        "product_hash": "prod-1",
        "free_trial_code": "trial-1",
    }


def test_build_callback_redirect_url() -> None:
    assert (
        build_callback_redirect_url(
            "https://chat.anote.ai",
            "access",
            "refresh",
            "prod-1",
            "trial-1",
        )
        == "https://chat.anote.ai?accessToken=access&refreshToken=refresh&product_hash=prod-1&free_trial_code=trial-1"
    )


def test_pair_chat_messages() -> None:
    messages = [
        {"sent_from_user": 1, "message_text": "Q1", "relevant_chunks": None},
        {
            "sent_from_user": 0,
            "message_text": "A1",
            "relevant_chunks": "Document: Alpha: First paragraph Document: Beta: Second paragraph",
        },
        {"sent_from_user": 1, "message_text": "Q2", "relevant_chunks": None},
        {"sent_from_user": 0, "message_text": "A2", "relevant_chunks": None},
    ]
    assert pair_chat_messages(messages) == [
        ("Q1", "A1", "First paragraph", "Second paragraph"),
        ("Q2", "A2", None, None),
    ]


def test_pair_chat_messages_single_paragraph_and_none() -> None:
    assert pair_chat_messages(
        [
            {"sent_from_user": 1, "message_text": "Q1", "relevant_chunks": None},
            {
                "sent_from_user": 0,
                "message_text": "A1",
                "relevant_chunks": "Document: Alpha: First paragraph",
            },
        ]
    ) == [("Q1", "A1", "First paragraph", None)]

    with pytest.raises(TypeError):
        pair_chat_messages(None)


def test_chat_history_csv_response() -> None:
    response = chat_history_csv_response([("Q1", "A1", "Chunk1", None)])
    assert response.mimetype == "text/csv"
    body = response.get_data(as_text=True)
    assert "query,response,chunk1,chunk2" in body
    assert "Q1,A1,Chunk1," in body


def test_chat_history_markdown_response() -> None:
    response = chat_history_markdown_response(
        [("Q1", "A1", "Chunk1", "Chunk2"), ("Q2", "A2", None, None)]
    )
    assert response.mimetype == "text/markdown"
    body = response.get_data(as_text=True)
    assert "# Chat History" in body
    assert "## Q: Q1" in body
    assert "A1" in body
    assert "> Chunk1" in body
    assert "> Chunk2" in body
    assert "## Q: Q2" in body
    assert "Sources" not in body.split("## Q: Q2")[1]


def test_chat_history_json_response() -> None:
    response = chat_history_json_response([("Q1", "A1", "Chunk1", None)])
    assert response.mimetype == "application/json"
    payload = json.loads(response.get_data(as_text=True))
    assert "exportedAt" in payload
    assert payload["messages"] == [
        {"query": "Q1", "response": "A1", "sources": ["Chunk1"]}
    ]


def test_chat_history_text_response() -> None:
    response = chat_history_text_response([("Q1", "A1", "Chunk1", "Chunk2")])
    assert response.mimetype == "text/plain"
    body = response.get_data(as_text=True)
    assert "Q: Q1" in body
    assert "A: A1" in body
    assert "Source: Chunk1" in body
    assert "Source: Chunk2" in body


@pytest.mark.parametrize(
    ("fmt", "expected_mimetype"),
    [
        ("csv", "text/csv"),
        ("markdown", "text/markdown"),
        ("json", "application/json"),
        ("text", "text/plain"),
        ("CSV", "text/csv"),
        (None, "text/csv"),
    ],
)
def test_chat_history_export_response_dispatch(fmt: str | None, expected_mimetype: str) -> None:
    response = chat_history_export_response([("Q1", "A1", None, None)], fmt)
    assert response.mimetype == expected_mimetype


def test_chat_history_export_response_unsupported_format() -> None:
    with pytest.raises(UnsupportedExportFormatError) as exc_info:
        chat_history_export_response([("Q1", "A1", None, None)], "pdf")
    assert "pdf" in str(exc_info.value)
    for fmt in SUPPORTED_EXPORT_FORMATS:
        assert fmt in str(exc_info.value)


def test_chat_history_export_response_consumes_generator_once() -> None:
    def _gen():
        yield ("Q1", "A1", None, None)
        yield ("Q2", "A2", None, None)

    response = chat_history_export_response(_gen(), "json")
    payload = json.loads(response.get_data(as_text=True))
    assert len(payload["messages"]) == 2


def test_reset_local_chat_artifacts(tmp_path: Path) -> None:
    source_dir = tmp_path / "sources"
    output_dir = tmp_path / "output"
    source_dir.mkdir()
    output_dir.mkdir()
    (output_dir / "chat_history.csv").write_text("old", encoding="utf-8")

    result = reset_local_chat_artifacts(str(source_dir), str(output_dir))
    assert result == "Reset was successful!"
    assert not source_dir.exists()
    assert (output_dir / "chat_history.csv").read_text(encoding="utf-8").strip() == "query,response"
