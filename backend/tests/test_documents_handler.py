"""Tests for the hardened upload pipeline in `api_endpoints/documents/handler`.

Covers the new behaviours added on top of the original ingest path:
  * Missing / empty `chat_id` → HTTP 400
  * Missing `files[]` field → HTTP 400
  * Batch over `MAX_FILES_PER_BATCH` → HTTP 413
  * Per-category size limits enforced BEFORE the file body is consumed
  * Per-file try/except: one failure does not abort the batch
  * Backward-compatible response shape (still exposes the `Success` key)
"""
from __future__ import annotations

import io
from types import SimpleNamespace
from typing import Any

import pytest

from api_endpoints.documents import handler as documents_handler

# ---------------------------------------------------------------------------
# Test doubles
# ---------------------------------------------------------------------------


def _make_file(
    *,
    filename: str = "sample.pdf",
    content_type: str | None = None,
    body: bytes = b"hello",
    declared_content_length: int = 0,
) -> Any:
    """Build a Werkzeug-FileStorage-shaped duck-typed object for tests."""
    stream = io.BytesIO(body)
    return SimpleNamespace(
        filename=filename,
        content_type=content_type,
        content_length=declared_content_length,
        stream=stream,
        read=stream.read,
    )


def _make_request(
    *,
    chat_id_values: list[str] | None = None,
    files: list[Any] | None = None,
) -> Any:
    form_map = {"chat_id": chat_id_values if chat_id_values is not None else ["11"]}
    files_map = {"files[]": files if files is not None else []}
    return SimpleNamespace(
        form=SimpleNamespace(getlist=lambda key: form_map.get(key, [])),
        files=SimpleNamespace(getlist=lambda key: files_map.get(key, [])),
    )


class _StubChunker:
    """Captures `.remote(text, max_chunk_size, doc_id)` invocations."""

    def __init__(self) -> None:
        self.calls: list[tuple[Any, int, int]] = []

    def remote(self, text: Any, max_chunk_size: int, doc_id: int) -> None:
        self.calls.append((text, max_chunk_size, doc_id))


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------


def test_missing_chat_id_returns_400(app_module: Any) -> None:
    with app_module.app.app_context():
        request = _make_request(chat_id_values=[])
        response, status = documents_handler.IngestDocumentsHandler(
            request, "u@x.com", parser_module=SimpleNamespace(), chunk_document_fn=_StubChunker()
        )
        assert status == 400
        assert response.get_json()["error"] == "missing_chat_id"


def test_empty_chat_id_returns_400(app_module: Any) -> None:
    with app_module.app.app_context():
        request = _make_request(chat_id_values=[""])
        response, status = documents_handler.IngestDocumentsHandler(
            request, "u@x.com", parser_module=SimpleNamespace(), chunk_document_fn=_StubChunker()
        )
        assert status == 400
        assert response.get_json()["error"] == "missing_chat_id"


def test_no_files_returns_400(app_module: Any) -> None:
    with app_module.app.app_context():
        request = _make_request(files=[])
        response, status = documents_handler.IngestDocumentsHandler(
            request, "u@x.com", parser_module=SimpleNamespace(), chunk_document_fn=_StubChunker()
        )
        assert status == 400
        assert response.get_json()["error"] == "no_files"


def test_too_many_files_returns_413(app_module: Any) -> None:
    with app_module.app.app_context():
        too_many = [_make_file(filename=f"f{i}.txt") for i in range(documents_handler.MAX_FILES_PER_BATCH + 1)]
        request = _make_request(files=too_many)
        response, status = documents_handler.IngestDocumentsHandler(
            request, "u@x.com", parser_module=SimpleNamespace(), chunk_document_fn=_StubChunker()
        )
        assert status == 413
        body = response.get_json()
        assert body["error"] == "too_many_files"
        assert body["limit"] == documents_handler.MAX_FILES_PER_BATCH
        assert body["received"] == documents_handler.MAX_FILES_PER_BATCH + 1


# ---------------------------------------------------------------------------
# Size guard
# ---------------------------------------------------------------------------


def test_oversized_image_is_skipped_not_read(
    app_module: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Image larger than MAX_IMAGE_BYTES must be skipped without invoking describe_image."""
    describe_calls: list[Any] = []

    def _fake_describe_image(image_bytes: bytes, mime_type: str = "image/jpeg", **_: Any) -> str:
        describe_calls.append(len(image_bytes))
        return "should not be called"

    monkeypatch.setattr(documents_handler, "describe_image", _fake_describe_image)

    over_limit = documents_handler._CATEGORY_BYTE_LIMITS["image"] + 1
    big_image = _make_file(
        filename="huge.jpg",
        content_type="image/jpeg",
        body=b"x" * 16,  # body itself is tiny; we rely on declared content_length
        declared_content_length=over_limit,
    )

    with app_module.app.app_context():
        request = _make_request(files=[big_image])
        response, status = documents_handler.IngestDocumentsHandler(
            request, "u@x.com", parser_module=SimpleNamespace(), chunk_document_fn=_StubChunker()
        )

    assert status == 200
    body = response.get_json()
    assert body["uploaded"] == []
    assert body["failed"] == []
    assert len(body["skipped"]) == 1
    assert body["skipped"][0]["reason"] == "file_too_large"
    assert body["skipped"][0]["category"] == "image"
    assert body["Success"] == "Partial success"
    # critical: describe_image must NOT be invoked on a rejected file
    assert describe_calls == []


# ---------------------------------------------------------------------------
# Per-file isolation
# ---------------------------------------------------------------------------


def test_per_file_failure_does_not_poison_batch(
    app_module: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """If one file blows up in the parser, the other must still succeed."""
    add_doc_calls: list[tuple[str, str]] = []

    def _fake_add_document(text: str, filename: str, **kwargs: Any) -> tuple[int, bool]:
        add_doc_calls.append((text, filename))
        return 42, False

    monkeypatch.setattr(documents_handler, "add_document", _fake_add_document)

    # First file blows up in Tika, second succeeds
    def _flaky_parser(file: Any) -> dict[str, str]:
        if file.filename == "bad.pdf":
            raise RuntimeError("tika exploded")
        return {"content": "good content"}

    parser_module = SimpleNamespace(from_buffer=_flaky_parser)

    bad = _make_file(filename="bad.pdf", content_type="application/pdf")
    good = _make_file(filename="good.pdf", content_type="application/pdf")

    with app_module.app.app_context():
        request = _make_request(files=[bad, good])
        response, status = documents_handler.IngestDocumentsHandler(
            request, "u@x.com", parser_module=parser_module, chunk_document_fn=_StubChunker()
        )

    assert status == 200
    body = response.get_json()
    assert len(body["uploaded"]) == 1
    assert body["uploaded"][0]["filename"] == "good.pdf"
    assert len(body["failed"]) == 1
    assert body["failed"][0]["filename"] == "bad.pdf"
    # Response carries class name only — exception message stays in server logs
    # to avoid leaking internal details (CodeQL: information exposure).
    assert body["failed"][0]["error"] == "RuntimeError"
    assert body["Success"] == "Partial success"
    # add_document only called for the good file
    assert add_doc_calls == [("good content", "good.pdf")]


# ---------------------------------------------------------------------------
# _file_size_bytes helper
# ---------------------------------------------------------------------------


def test_file_size_uses_content_length_first() -> None:
    f = _make_file(declared_content_length=12345, body=b"short")
    assert documents_handler._file_size_bytes(f) == 12345


def test_file_size_falls_back_to_stream_tell() -> None:
    f = _make_file(declared_content_length=0, body=b"x" * 999)
    assert documents_handler._file_size_bytes(f) == 999
    # stream position must be restored to original
    assert f.stream.tell() == 0


# ---------------------------------------------------------------------------
# _mask_email helper (PII hygiene for logs)
# ---------------------------------------------------------------------------


def test_mask_email_keeps_domain_visible() -> None:
    assert documents_handler._mask_email("alice@example.com") == "a***@example.com"


def test_mask_email_handles_empty_and_malformed() -> None:
    assert documents_handler._mask_email("") == "***"
    assert documents_handler._mask_email("noatsign") == "***"
    assert documents_handler._mask_email("@example.com") == "***@example.com"
