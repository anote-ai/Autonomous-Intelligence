from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import numpy as np
import pytest
from services import finance_gpt


def _fake_embedding_response(vectors: list[list[float]]) -> Any:
    return SimpleNamespace(data=[SimpleNamespace(embedding=vector) for vector in vectors])


def test_get_model_and_embedding_helpers(monkeypatch: pytest.MonkeyPatch) -> None:
    finance_gpt._embedding_model = None
    finance_gpt._text_splitters = {}

    client = SimpleNamespace(
        embeddings=SimpleNamespace(
            create=lambda **kwargs: _fake_embedding_response(
                [[float(index)] * finance_gpt.EMBEDDING_DIMENSIONS for index, _ in enumerate(kwargs["input"], start=1)]
            )
        )
    )
    monkeypatch.setattr(finance_gpt, "_client", client)

    model = finance_gpt._get_model()
    assert len(model(["first", "second"])) == 2
    assert finance_gpt._get_model() is model

    embedding = finance_gpt.get_embedding("question")
    assert len(embedding) == finance_gpt.EMBEDDING_DIMENSIONS

    embeddings = finance_gpt.get_embeddings_batch(["a", "b", "c"], batch_size=2)
    assert len(embeddings) == 3


def test_text_splitter_and_preload_helpers(monkeypatch: pytest.MonkeyPatch) -> None:
    finance_gpt._text_splitters = {}
    splitter = finance_gpt._get_text_splitter(5)
    assert splitter.split_text("abcdefghij") == ["abcde", "fghij"]
    assert finance_gpt._get_text_splitter(5) is splitter

    calls = {"splitter": 0, "model": 0}
    monkeypatch.setattr(finance_gpt, "_get_text_splitter", lambda chunk_size=None: calls.__setitem__("splitter", calls["splitter"] + 1))
    monkeypatch.setattr(finance_gpt, "_get_model", lambda: calls.__setitem__("model", calls["model"] + 1))

    finance_gpt.preload_text_splitter()
    finance_gpt.preload_embedding_model()
    finance_gpt.preload_models()

    assert calls == {"splitter": 2, "model": 2}


def test_prepare_chunks_and_knn() -> None:
    finance_gpt._text_splitters = {}
    chunk_texts, chunk_metadata = finance_gpt.prepare_chunks_for_embedding(["abcdef", "ghijkl"], 3)
    assert chunk_texts == ["abc", "def", "ghi", "jkl"]
    assert chunk_metadata[0]["global_start"] == 0
    assert chunk_metadata[-1]["page_number"] == 2

    query = np.array([1.0, 0.0])
    documents = np.array([[1.0, 0.0], [0.0, 1.0]])
    result = finance_gpt.knn(query, documents)
    assert result[0]["index"] == 0


def test_chunk_document_optimized(monkeypatch: pytest.MonkeyPatch) -> None:
    inserted = []
    monkeypatch.setattr(finance_gpt, "get_embeddings_batch", lambda texts, batch_size=32: [[0.1] * finance_gpt.EMBEDDING_DIMENSIONS for _ in texts])
    monkeypatch.setattr(finance_gpt, "add_chunks", lambda chunk_data: inserted.extend(chunk_data))

    finance_gpt.chunk_document_optimized("abcdef", 3, 99)

    assert inserted
    assert inserted[0][2] == 99


def test_chunk_document_by_page_and_fast_ingestion(monkeypatch: pytest.MonkeyPatch) -> None:
    inserted = []
    monkeypatch.setattr(finance_gpt, "get_embeddings_batch", lambda texts, batch_size=32: [[0.2] * finance_gpt.EMBEDDING_DIMENSIONS for _ in texts])
    monkeypatch.setattr(finance_gpt, "add_chunks_with_page_numbers", lambda chunk_data: inserted.extend(chunk_data))

    finance_gpt.chunk_document_by_page_optimized(["abcdef", "ghijkl"], 3, 123)
    processed = finance_gpt.fast_pdf_ingestion(["mnopqr"], 3, 456)

    assert processed > 0
    assert any(row[2] == 123 for row in inserted)
    assert any(row[2] == 456 for row in inserted)


def test_get_relevant_chunks(monkeypatch: pytest.MonkeyPatch) -> None:
    vector = np.array([1.0] * finance_gpt.EMBEDDING_DIMENSIONS, dtype=np.float64).tobytes()
    monkeypatch.setattr(
        finance_gpt,
        "get_chat_chunks",
        lambda user_email, chat_id: [
            {
                "start_index": 0,
                "end_index": 4,
                "embedding_vector": vector,
                "document_name": "doc-a",
                "document_text": "abcdefgh",
            },
            {
                "start_index": 4,
                "end_index": 8,
                "embedding_vector": vector,
                "document_name": "doc-b",
                "document_text": "ijklmnop",
            },
        ],
    )
    monkeypatch.setattr(finance_gpt, "get_embedding", lambda question: [1.0] * finance_gpt.EMBEDDING_DIMENSIONS)

    sources = finance_gpt.get_relevant_chunks(1, "question", 9, "user@example.com")
    assert len(sources) == 1
    assert sources[0][1] in {"doc-a", "doc-b"}


def test_get_relevant_chunks_handles_embedding_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(finance_gpt, "get_chat_chunks", lambda user_email, chat_id: [])
    assert finance_gpt.get_relevant_chunks(2, "question", 1, "user@example.com") == []

    bad_vector = np.array([1.0, 2.0], dtype=np.float64).tobytes()
    monkeypatch.setattr(
        finance_gpt,
        "get_chat_chunks",
        lambda user_email, chat_id: [
            {
                "start_index": 0,
                "end_index": 2,
                "embedding_vector": bad_vector,
                "document_name": "doc",
                "document_text": "ab",
            }
        ],
    )
    assert finance_gpt.get_relevant_chunks(2, "question", 1, "user@example.com") == []


def test_pdf_and_url_helpers(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakePage:
        def __init__(self, text: str) -> None:
            self._text = text

        def extract_text(self) -> str:
            return self._text

    monkeypatch.setattr(
        finance_gpt.PyPDF2,
        "PdfReader",
        lambda file: SimpleNamespace(pages=[FakePage("first"), FakePage("second")]),
    )
    monkeypatch.setattr(finance_gpt, "fetch_external_url", lambda url: SimpleNamespace(content=b"<html></html>"))
    monkeypatch.setattr(finance_gpt.p, "from_buffer", lambda content: {"content": "line 1\nline 2\t"})

    assert finance_gpt.get_text_from_single_file("file") == "firstsecond"
    assert finance_gpt.get_text_pages_from_single_file("file") == ["first", "second"]
    assert finance_gpt.get_text_from_url("https://example.com") == "line 1line 2"


def test_validate_external_url_allows_public_hosts(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(finance_gpt, "ALLOWED_FETCH_HOSTS", ("example.com",))
    monkeypatch.setattr(
        finance_gpt.socket,
        "getaddrinfo",
        lambda host, port: [(None, None, None, None, ("93.184.216.34", 0))],
    )
    finance_gpt.validate_external_url("https://example.com")
    assert (
        finance_gpt.build_validated_public_url(
            "https://example.com/path?q=1#fragment"
        )
        == "https://example.com/path?q=1"
    )


def test_validate_external_url_blocks_private_hosts(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(finance_gpt, "ALLOWED_FETCH_HOSTS", ("localhost",))
    monkeypatch.setattr(
        finance_gpt.socket,
        "getaddrinfo",
        lambda host, port: [(None, None, None, None, ("127.0.0.1", 0))],
    )
    with pytest.raises(finance_gpt.UnsafeUrlError):
        finance_gpt.validate_external_url("http://localhost")


def test_validate_external_url_blocks_non_allowlisted_host(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(finance_gpt, "ALLOWED_FETCH_HOSTS", ("example.com",))
    with pytest.raises(finance_gpt.UnsafeUrlError):
        finance_gpt.validate_external_url("https://evil.com")
