"""Tests for document endpoints."""
from __future__ import annotations

import io
from unittest.mock import MagicMock, patch


def _mock_cnx(fetchall=None, fetchone=None, lastrowid=1, rowcount=1):
    cursor = MagicMock()
    cursor.fetchall.return_value = fetchall if fetchall is not None else []
    cursor.fetchone.return_value = fetchone
    cursor.lastrowid = lastrowid
    cursor.rowcount = rowcount
    cnx = MagicMock()
    cnx.cursor.return_value = cursor
    return cnx


# ---------------------------------------------------------------------------
# GET /api/documents
# ---------------------------------------------------------------------------

def test_list_documents_no_auth(client):
    resp = client.get("/api/documents")
    assert resp.status_code == 401


def test_list_documents(client, auth_headers):
    with patch("api_endpoints.documents.handler.get_connection", return_value=_mock_cnx()):
        resp = client.get("/api/documents", headers=auth_headers)
    assert resp.status_code == 200
    assert "documents" in resp.get_json()


def test_list_documents_with_folder(client, auth_headers):
    with patch("api_endpoints.documents.handler.get_connection", return_value=_mock_cnx()):
        resp = client.get("/api/documents?folder_id=1", headers=auth_headers)
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# POST /api/documents/upload
# ---------------------------------------------------------------------------

def test_upload_no_file(client, auth_headers):
    resp = client.post("/api/documents/upload", headers=auth_headers)
    assert resp.status_code == 400


def test_upload_bad_type(client, auth_headers):
    data = {"file": (io.BytesIO(b"data"), "test.exe")}
    resp = client.post(
        "/api/documents/upload", data=data,
        content_type="multipart/form-data", headers=auth_headers,
    )
    assert resp.status_code == 400


def test_upload_text_file_success(client, auth_headers, tmp_path):
    with patch("api_endpoints.documents.handler.UPLOAD_FOLDER", tmp_path), \
         patch("api_endpoints.documents.handler.ingest_document", return_value=5), \
         patch("api_endpoints.documents.handler.get_connection", return_value=_mock_cnx()):
        data = {"file": (io.BytesIO(b"Hello world document."), "test.txt")}
        resp = client.post(
            "/api/documents/upload", data=data,
            content_type="multipart/form-data", headers=auth_headers,
        )
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["filename"] == "test.txt"
    assert body["chunks"] == 5


def test_upload_with_folder_id(client, auth_headers, tmp_path):
    with patch("api_endpoints.documents.handler.UPLOAD_FOLDER", tmp_path), \
         patch("api_endpoints.documents.handler.ingest_document", return_value=3), \
         patch("api_endpoints.documents.handler.get_connection", return_value=_mock_cnx()):
        data = {"file": (io.BytesIO(b"Folder content."), "notes.txt"), "folder_id": "2"}
        resp = client.post(
            "/api/documents/upload", data=data,
            content_type="multipart/form-data", headers=auth_headers,
        )
    assert resp.status_code == 201
    assert resp.get_json()["folder_id"] == 2


def test_upload_ingest_failure(client, auth_headers, tmp_path):
    with patch("api_endpoints.documents.handler.UPLOAD_FOLDER", tmp_path), \
         patch("api_endpoints.documents.handler.ingest_document", side_effect=RuntimeError("boom")):
        data = {"file": (io.BytesIO(b"data"), "test.txt")}
        resp = client.post(
            "/api/documents/upload", data=data,
            content_type="multipart/form-data", headers=auth_headers,
        )
    assert resp.status_code == 500


# ---------------------------------------------------------------------------
# GET /api/documents/<doc_id>
# ---------------------------------------------------------------------------

def test_get_document_not_found(client, auth_headers):
    with patch("api_endpoints.documents.handler.get_connection", return_value=_mock_cnx(fetchone=None)):
        resp = client.get("/api/documents/nonexistent", headers=auth_headers)
    assert resp.status_code == 404


def test_get_document_found(client, auth_headers):
    doc = {"id": "abc", "filename": "test.txt", "chunk_count": 5, "folder_id": None, "created_at": None}
    with patch("api_endpoints.documents.handler.get_connection", return_value=_mock_cnx(fetchone=doc)):
        resp = client.get("/api/documents/abc", headers=auth_headers)
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# DELETE /api/documents/<doc_id>
# ---------------------------------------------------------------------------

def test_delete_document_not_found(client, auth_headers):
    with patch("api_endpoints.documents.handler.get_connection", return_value=_mock_cnx(fetchone=None)):
        resp = client.delete("/api/documents/nonexistent", headers=auth_headers)
    assert resp.status_code == 404


def test_delete_document_found(client, auth_headers):
    doc = {"id": "abc", "filename": "test.txt", "chunk_count": 5, "folder_id": None, "created_at": None}
    with patch("api_endpoints.documents.handler.get_connection", return_value=_mock_cnx(fetchone=doc)):
        resp = client.delete("/api/documents/abc", headers=auth_headers)
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# PATCH /api/documents/<doc_id>/move
# ---------------------------------------------------------------------------

def test_move_document(client, auth_headers):
    with patch("api_endpoints.documents.handler.get_connection", return_value=_mock_cnx(rowcount=1)):
        resp = client.patch("/api/documents/abc/move", json={"folder_id": 1}, headers=auth_headers)
    assert resp.status_code == 200


def test_move_document_to_root(client, auth_headers):
    with patch("api_endpoints.documents.handler.get_connection", return_value=_mock_cnx(rowcount=1)):
        resp = client.patch("/api/documents/abc/move", json={"folder_id": None}, headers=auth_headers)
    assert resp.status_code == 200


def test_move_document_not_found(client, auth_headers):
    with patch("api_endpoints.documents.handler.get_connection", return_value=_mock_cnx(rowcount=0)):
        resp = client.patch("/api/documents/abc/move", json={"folder_id": 1}, headers=auth_headers)
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /api/documents/<doc_id>/ask
# ---------------------------------------------------------------------------

def test_ask_document_missing_question(client, auth_headers):
    resp = client.post("/api/documents/abc/ask", json={}, headers=auth_headers)
    assert resp.status_code == 400


def test_ask_document(client, auth_headers):
    with patch("api_endpoints.documents.handler.query_documents", return_value="The answer."):
        resp = client.post("/api/documents/abc/ask", json={"question": "what?"}, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.get_json()["answer"] == "The answer."


def test_ask_document_with_folder(client, auth_headers):
    docs = [{"id": "abc"}, {"id": "def"}]
    with patch("api_endpoints.documents.handler.get_connection", return_value=_mock_cnx(fetchall=docs)), \
         patch("api_endpoints.documents.handler.query_documents", return_value="Folder answer."):
        resp = client.post(
            "/api/documents/abc/ask",
            json={"question": "what?", "folder_id": 1},
            headers=auth_headers,
        )
    assert resp.status_code == 200
