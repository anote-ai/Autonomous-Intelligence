"""Tests for folder endpoints."""
from __future__ import annotations

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
# POST /api/folders
# ---------------------------------------------------------------------------

def test_create_folder_no_auth(client):
    resp = client.post("/api/folders", json={"name": "Test"})
    assert resp.status_code == 401


def test_create_folder_missing_name(client, auth_headers):
    resp = client.post("/api/folders", json={}, headers=auth_headers)
    assert resp.status_code == 400


def test_create_folder_empty_name(client, auth_headers):
    resp = client.post("/api/folders", json={"name": "  "}, headers=auth_headers)
    assert resp.status_code == 400


def test_create_folder(client, auth_headers):
    with patch("api_endpoints.folders.handler.get_connection", return_value=_mock_cnx(lastrowid=7)):
        resp = client.post("/api/folders", json={"name": "Q3 Reports"}, headers=auth_headers)
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["name"] == "Q3 Reports"
    assert body["id"] == 7


# ---------------------------------------------------------------------------
# GET /api/folders
# ---------------------------------------------------------------------------

def test_list_folders_no_auth(client):
    resp = client.get("/api/folders")
    assert resp.status_code == 401


def test_list_folders_empty(client, auth_headers):
    with patch("api_endpoints.folders.handler.get_connection", return_value=_mock_cnx(fetchall=[])):
        resp = client.get("/api/folders", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.get_json()["folders"] == []


def test_list_folders(client, auth_headers):
    folders = [{"id": 1, "name": "Alpha"}, {"id": 2, "name": "Beta"}]
    with patch("api_endpoints.folders.handler.get_connection", return_value=_mock_cnx(fetchall=folders)):
        resp = client.get("/api/folders", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.get_json()["folders"]) == 2


# ---------------------------------------------------------------------------
# PATCH /api/folders/<id>
# ---------------------------------------------------------------------------

def test_rename_folder_no_auth(client):
    resp = client.patch("/api/folders/1", json={"name": "New"})
    assert resp.status_code == 401


def test_rename_folder_missing_name(client, auth_headers):
    resp = client.patch("/api/folders/1", json={}, headers=auth_headers)
    assert resp.status_code == 400


def test_rename_folder_not_found(client, auth_headers):
    with patch("api_endpoints.folders.handler.get_connection", return_value=_mock_cnx(rowcount=0)):
        resp = client.patch("/api/folders/999", json={"name": "New Name"}, headers=auth_headers)
    assert resp.status_code == 404


def test_rename_folder(client, auth_headers):
    with patch("api_endpoints.folders.handler.get_connection", return_value=_mock_cnx(rowcount=1)):
        resp = client.patch("/api/folders/1", json={"name": "Renamed"}, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.get_json()["name"] == "Renamed"


# ---------------------------------------------------------------------------
# DELETE /api/folders/<id>
# ---------------------------------------------------------------------------

def test_delete_folder_no_auth(client):
    resp = client.delete("/api/folders/1")
    assert resp.status_code == 401


def test_delete_folder_not_found(client, auth_headers):
    with patch("api_endpoints.folders.handler.get_connection", return_value=_mock_cnx(rowcount=0)):
        resp = client.delete("/api/folders/999", headers=auth_headers)
    assert resp.status_code == 404


def test_delete_folder(client, auth_headers):
    with patch("api_endpoints.folders.handler.get_connection", return_value=_mock_cnx(rowcount=1)):
        resp = client.delete("/api/folders/1", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.get_json()["deleted"] is True


# ---------------------------------------------------------------------------
# Exception paths (500 responses)
# ---------------------------------------------------------------------------

def test_create_folder_db_error(client, auth_headers):
    with patch("api_endpoints.folders.handler.get_connection", side_effect=Exception("db down")):
        resp = client.post("/api/folders", json={"name": "Test"}, headers=auth_headers)
    assert resp.status_code == 500


def test_list_folders_db_error(client, auth_headers):
    with patch("api_endpoints.folders.handler.get_connection", side_effect=Exception("db down")):
        resp = client.get("/api/folders", headers=auth_headers)
    assert resp.status_code == 500


def test_rename_folder_db_error(client, auth_headers):
    with patch("api_endpoints.folders.handler.get_connection", side_effect=Exception("db down")):
        resp = client.patch("/api/folders/1", json={"name": "X"}, headers=auth_headers)
    assert resp.status_code == 500


def test_delete_folder_db_error(client, auth_headers):
    with patch("api_endpoints.folders.handler.get_connection", side_effect=Exception("db down")):
        resp = client.delete("/api/folders/1", headers=auth_headers)
    assert resp.status_code == 500
