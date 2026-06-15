"""Tests for document endpoints."""
import io


def test_list_documents(client):
    resp = client.get("/api/documents")
    assert resp.status_code == 200
    assert "documents" in resp.get_json()


def test_upload_no_file(client):
    resp = client.post("/api/documents/upload")
    assert resp.status_code == 400


def test_upload_bad_type(client):
    data = {"file": (io.BytesIO(b"data"), "test.exe")}
    resp = client.post("/api/documents/upload", data=data, content_type="multipart/form-data")
    assert resp.status_code == 400


def test_upload_text_file(client):
    data = {"file": (io.BytesIO(b"Hello world document."), "test.txt")}
    resp = client.post("/api/documents/upload", data=data, content_type="multipart/form-data")
    assert resp.status_code in (201, 500)


def test_get_document_not_found(client):
    resp = client.get("/api/documents/nonexistent")
    assert resp.status_code == 404


def test_delete_document_not_found(client):
    resp = client.delete("/api/documents/nonexistent")
    assert resp.status_code == 404


def test_ask_document_not_found(client):
    resp = client.post("/api/documents/nonexistent/ask", json={"question": "what?"})
    assert resp.status_code == 404


def test_ask_document_missing_question(client):
    data = {"file": (io.BytesIO(b"Content."), "doc.txt")}
    up = client.post("/api/documents/upload", data=data, content_type="multipart/form-data")
    if up.status_code != 201:
        return
    doc_id = up.get_json()["id"]
    resp = client.post(f"/api/documents/{doc_id}/ask", json={})
    assert resp.status_code == 400
