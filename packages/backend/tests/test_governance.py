"""Tests for data governance: policies, legal holds, exports, classifications."""
from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from app import create_app

# ── Fixtures ───────────────────────────────────────────────────────────────────

@pytest.fixture
def app() -> Any:
    return create_app({"TESTING": True, "JWT_SECRET_KEY": "test-secret"})


@pytest.fixture
def client(app: Any) -> Any:
    return app.test_client()


@pytest.fixture
def token(app: Any) -> str:
    with app.app_context():
        from flask_jwt_extended import create_access_token
        return create_access_token(identity="42")


@pytest.fixture
def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _member(role: str = "admin") -> dict[str, Any]:
    return {
        "id": 1, "org_id": 1, "user_id": 42, "role": role,
        "provisioned_by": "manual", "scim_external_id": None,
        "email": "admin@acme.com", "name": "Admin",
        "sso_provider": None, "is_active": True,
        "created_at": "2024-01-01", "updated_at": "2024-01-01",
    }


def _policy(data_type: str = "documents") -> dict[str, Any]:
    return {
        "id": 1, "org_id": 1, "data_type": data_type,
        "retention_days": 365, "auto_delete": False,
        "classification": "internal",
        "created_by": 42, "updated_by": 42,
        "created_at": "2024-01-01", "updated_at": "2024-01-01",
    }


def _hold() -> dict[str, Any]:
    return {
        "id": 10, "org_id": 1, "resource_type": "documents",
        "resource_id": "doc-123", "reason": "Litigation hold",
        "placed_by": 42, "released_by": None, "released_at": None,
        "expires_at": None, "created_at": "2024-01-01",
    }


def _export_req() -> dict[str, Any]:
    return {
        "id": 5, "org_id": 1, "requested_by": 42,
        "data_types": '["documents","chats"]', "scope": None,
        "status": "pending", "download_url": None,
        "fulfilled_by": None, "fulfilled_at": None,
        "expires_at": None, "created_at": "2024-01-01", "updated_at": "2024-01-01",
    }


def _cls_row() -> dict[str, Any]:
    return {
        "id": 7, "org_id": 1, "resource_type": "documents",
        "resource_id": "doc-123", "classification": "confidential",
        "tagged_by": 42, "created_at": "2024-01-01",
    }


def _gov_event() -> dict[str, Any]:
    return {
        "id": 1, "org_id": 1, "actor_id": 42,
        "action": "policy_set", "resource": "documents",
        "detail": '{"retention_days": 90}', "created_at": "2024-01-01",
    }


def _cnx() -> MagicMock:
    return MagicMock()


# ── services/governance.py ─────────────────────────────────────────────────────

class TestGovernanceService:
    def test_validate_policy_ok(self) -> None:
        from services.governance import validate_policy
        assert validate_policy("documents", 90, "confidential") is None

    def test_validate_policy_bad_type(self) -> None:
        from services.governance import validate_policy
        err = validate_policy("blobs", 90, "internal")
        assert err is not None
        assert "data_type" in err

    def test_validate_policy_bad_days(self) -> None:
        from services.governance import validate_policy
        assert validate_policy("chats", 0, "internal") is not None
        assert validate_policy("chats", 99999999, "internal") is not None

    def test_validate_policy_bad_classification(self) -> None:
        from services.governance import validate_policy
        assert validate_policy("chats", 30, "ultra-secret") is not None

    def test_validate_hold_ok(self) -> None:
        from services.governance import validate_hold
        assert validate_hold("documents", "doc-1", "Litigation") is None

    def test_validate_hold_missing_reason(self) -> None:
        from services.governance import validate_hold
        assert validate_hold("documents", "doc-1", "  ") is not None

    def test_validate_hold_missing_resource_type(self) -> None:
        from services.governance import validate_hold
        assert validate_hold("", "doc-1", "reason") is not None

    def test_validate_classification_ok(self) -> None:
        from services.governance import validate_classification
        assert validate_classification("chats", "chat-1", "sensitive") is None

    def test_validate_classification_bad(self) -> None:
        from services.governance import validate_classification
        assert validate_classification("chats", "chat-1", "top-secret") is not None

    def test_classification_rank(self) -> None:
        from services.governance import classification_rank
        assert classification_rank("sensitive") > classification_rank("confidential")
        assert classification_rank("confidential") > classification_rank("internal")
        assert classification_rank("internal") > classification_rank("public")

    def test_evaluate_deletion_allowed_no_hold(self) -> None:
        from services.governance import evaluate_deletion_allowed
        cnx = MagicMock()
        with patch("database.db.has_active_legal_hold", return_value=False):
            result = evaluate_deletion_allowed(cnx, 1, "documents", "doc-1")
        assert result["allowed"] is True
        assert result["blocked_by_hold"] is False

    def test_evaluate_deletion_blocked_by_hold(self) -> None:
        from services.governance import evaluate_deletion_allowed
        cnx = MagicMock()
        with patch("database.db.has_active_legal_hold", return_value=True):
            result = evaluate_deletion_allowed(cnx, 1, "documents", "doc-1")
        assert result["allowed"] is False
        assert result["blocked_by_hold"] is True


# ── Retention policies ─────────────────────────────────────────────────────────

class TestPolicies:
    def test_list_policies(self, client: Any, auth: dict) -> None:
        cnx = _cnx()
        with patch("database.db.get_connection", return_value=cnx), \
             patch("database.db.get_member", return_value=_member()), \
             patch("database.db.list_data_policies", return_value=[_policy()]):
            resp = client.get("/api/admin/organizations/1/governance/policies", headers=auth)
        assert resp.status_code == 200
        data = resp.get_json()
        assert "policies" in data
        assert len(data["policies"]) == 1

    def test_list_policies_db_error(self, client: Any, auth: dict) -> None:
        # First get_connection call succeeds for RBAC; second raises in the handler
        with patch("database.db.get_connection", side_effect=[_cnx(), RuntimeError("db down")]), \
             patch("database.db.get_member", return_value=_member()):
            resp = client.get("/api/admin/organizations/1/governance/policies", headers=auth)
        assert resp.status_code == 503

    def test_set_policy(self, client: Any, auth: dict) -> None:
        cnx = _cnx()
        with patch("database.db.get_connection", return_value=cnx), \
             patch("database.db.get_member", return_value=_member()), \
             patch("database.db.upsert_data_policy") as mock_upsert, \
             patch("database.db.log_governance_event"):
            resp = client.put(
                "/api/admin/organizations/1/governance/policies/documents",
                json={"retention_days": 90, "auto_delete": True, "classification": "confidential"},
                headers=auth,
            )
        assert resp.status_code == 200
        mock_upsert.assert_called_once()
        data = resp.get_json()
        assert data["retention_days"] == 90
        assert data["classification"] == "confidential"

    def test_set_policy_invalid_data_type(self, client: Any, auth: dict) -> None:
        # Validation fires before DB call; still need get_connection for RBAC
        with patch("database.db.get_connection", return_value=_cnx()), \
             patch("database.db.get_member", return_value=_member()):
            resp = client.put(
                "/api/admin/organizations/1/governance/policies/blobs",
                json={"retention_days": 90},
                headers=auth,
            )
        assert resp.status_code == 400

    def test_set_policy_invalid_days(self, client: Any, auth: dict) -> None:
        with patch("database.db.get_connection", return_value=_cnx()), \
             patch("database.db.get_member", return_value=_member()):
            resp = client.put(
                "/api/admin/organizations/1/governance/policies/documents",
                json={"retention_days": -1},
                headers=auth,
            )
        assert resp.status_code == 400

    def test_reset_policy(self, client: Any, auth: dict) -> None:
        cnx = _cnx()
        with patch("database.db.get_connection", return_value=cnx), \
             patch("database.db.get_member", return_value=_member()), \
             patch("database.db.delete_data_policy") as mock_del, \
             patch("database.db.log_governance_event"):
            resp = client.delete(
                "/api/admin/organizations/1/governance/policies/chats", headers=auth
            )
        assert resp.status_code == 200
        mock_del.assert_called_once()
        assert resp.get_json()["reset"] is True

    def test_reset_policy_unknown_type(self, client: Any, auth: dict) -> None:
        with patch("database.db.get_connection", return_value=_cnx()), \
             patch("database.db.get_member", return_value=_member()):
            resp = client.delete(
                "/api/admin/organizations/1/governance/policies/blobs", headers=auth
            )
        assert resp.status_code == 400


# ── Legal holds ────────────────────────────────────────────────────────────────

class TestLegalHolds:
    def test_list_holds(self, client: Any, auth: dict) -> None:
        cnx = _cnx()
        with patch("database.db.get_connection", return_value=cnx), \
             patch("database.db.get_member", return_value=_member()), \
             patch("database.db.list_legal_holds", return_value=[_hold()]):
            resp = client.get("/api/admin/organizations/1/governance/holds", headers=auth)
        assert resp.status_code == 200
        assert len(resp.get_json()["holds"]) == 1

    def test_place_hold(self, client: Any, auth: dict) -> None:
        cnx = _cnx()
        with patch("database.db.get_connection", return_value=cnx), \
             patch("database.db.get_member", return_value=_member()), \
             patch("database.db.create_legal_hold", return_value=10) as mock_create, \
             patch("database.db.log_governance_event"):
            resp = client.post(
                "/api/admin/organizations/1/governance/holds",
                json={"resource_type": "documents", "resource_id": "doc-123", "reason": "Litigation"},
                headers=auth,
            )
        assert resp.status_code == 201
        mock_create.assert_called_once()
        assert resp.get_json()["hold_id"] == 10

    def test_place_hold_missing_reason(self, client: Any, auth: dict) -> None:
        with patch("database.db.get_connection", return_value=_cnx()), \
             patch("database.db.get_member", return_value=_member()):
            resp = client.post(
                "/api/admin/organizations/1/governance/holds",
                json={"resource_type": "documents", "resource_id": "doc-1", "reason": ""},
                headers=auth,
            )
        assert resp.status_code == 400

    def test_release_hold(self, client: Any, auth: dict) -> None:
        cnx = _cnx()
        hold = {**_hold(), "org_id": 1, "released_at": None}
        with patch("database.db.get_connection", return_value=cnx), \
             patch("database.db.get_member", return_value=_member()), \
             patch("database.db.get_legal_hold", return_value=hold), \
             patch("database.db.release_legal_hold") as mock_release, \
             patch("database.db.log_governance_event"):
            resp = client.delete(
                "/api/admin/organizations/1/governance/holds/10", headers=auth
            )
        assert resp.status_code == 200
        mock_release.assert_called_once()
        assert resp.get_json()["released"] is True

    def test_release_hold_already_released(self, client: Any, auth: dict) -> None:
        cnx = _cnx()
        hold = {**_hold(), "org_id": 1, "released_at": "2024-06-01"}
        with patch("database.db.get_connection", return_value=cnx), \
             patch("database.db.get_member", return_value=_member()), \
             patch("database.db.get_legal_hold", return_value=hold):
            resp = client.delete(
                "/api/admin/organizations/1/governance/holds/10", headers=auth
            )
        assert resp.status_code == 409

    def test_release_hold_not_found(self, client: Any, auth: dict) -> None:
        cnx = _cnx()
        with patch("database.db.get_connection", return_value=cnx), \
             patch("database.db.get_member", return_value=_member()), \
             patch("database.db.get_legal_hold", return_value=None):
            resp = client.delete(
                "/api/admin/organizations/1/governance/holds/99", headers=auth
            )
        assert resp.status_code == 404

    def test_release_hold_wrong_org(self, client: Any, auth: dict) -> None:
        cnx = _cnx()
        hold = {**_hold(), "org_id": 99}
        with patch("database.db.get_connection", return_value=cnx), \
             patch("database.db.get_member", return_value=_member()), \
             patch("database.db.get_legal_hold", return_value=hold):
            resp = client.delete(
                "/api/admin/organizations/1/governance/holds/10", headers=auth
            )
        assert resp.status_code == 404


# ── Export requests ────────────────────────────────────────────────────────────

class TestExports:
    def test_list_exports(self, client: Any, auth: dict) -> None:
        cnx = _cnx()
        with patch("database.db.get_connection", return_value=cnx), \
             patch("database.db.get_member", return_value=_member()), \
             patch("database.db.list_export_requests", return_value=[_export_req()]):
            resp = client.get("/api/admin/organizations/1/governance/exports", headers=auth)
        assert resp.status_code == 200
        assert len(resp.get_json()["exports"]) == 1

    def test_request_export(self, client: Any, auth: dict) -> None:
        cnx = _cnx()
        with patch("database.db.get_connection", return_value=cnx), \
             patch("database.db.get_member", return_value=_member()), \
             patch("database.db.create_export_request", return_value=5) as mock_create, \
             patch("database.db.log_governance_event"):
            resp = client.post(
                "/api/admin/organizations/1/governance/exports",
                json={"data_types": ["documents", "chats"]},
                headers=auth,
            )
        assert resp.status_code == 201
        mock_create.assert_called_once()
        assert resp.get_json()["req_id"] == 5

    def test_request_export_empty_types(self, client: Any, auth: dict) -> None:
        with patch("database.db.get_connection", return_value=_cnx()), \
             patch("database.db.get_member", return_value=_member()):
            resp = client.post(
                "/api/admin/organizations/1/governance/exports",
                json={"data_types": []},
                headers=auth,
            )
        assert resp.status_code == 400

    def test_request_export_invalid_type(self, client: Any, auth: dict) -> None:
        with patch("database.db.get_connection", return_value=_cnx()), \
             patch("database.db.get_member", return_value=_member()):
            resp = client.post(
                "/api/admin/organizations/1/governance/exports",
                json={"data_types": ["documents", "blobs"]},
                headers=auth,
            )
        assert resp.status_code == 400

    def test_get_export(self, client: Any, auth: dict) -> None:
        cnx = _cnx()
        req = {**_export_req(), "org_id": 1}
        with patch("database.db.get_connection", return_value=cnx), \
             patch("database.db.get_member", return_value=_member()), \
             patch("database.db.get_export_request", return_value=req):
            resp = client.get("/api/admin/organizations/1/governance/exports/5", headers=auth)
        assert resp.status_code == 200
        assert resp.get_json()["status"] == "pending"

    def test_get_export_not_found(self, client: Any, auth: dict) -> None:
        cnx = _cnx()
        with patch("database.db.get_connection", return_value=cnx), \
             patch("database.db.get_member", return_value=_member()), \
             patch("database.db.get_export_request", return_value=None):
            resp = client.get("/api/admin/organizations/1/governance/exports/99", headers=auth)
        assert resp.status_code == 404

    def test_get_export_wrong_org(self, client: Any, auth: dict) -> None:
        cnx = _cnx()
        req = {**_export_req(), "org_id": 99}
        with patch("database.db.get_connection", return_value=cnx), \
             patch("database.db.get_member", return_value=_member()), \
             patch("database.db.get_export_request", return_value=req):
            resp = client.get("/api/admin/organizations/1/governance/exports/5", headers=auth)
        assert resp.status_code == 404

    def test_fulfill_export(self, client: Any, auth: dict) -> None:
        cnx = _cnx()
        req = {**_export_req(), "org_id": 1}
        with patch("database.db.get_connection", return_value=cnx), \
             patch("database.db.get_member", return_value=_member()), \
             patch("database.db.get_export_request", return_value=req), \
             patch("database.db.update_export_status") as mock_update, \
             patch("database.db.log_governance_event"):
            resp = client.post(
                "/api/admin/organizations/1/governance/exports/5/fulfill",
                json={"status": "fulfilled", "download_url": "https://s3.example.com/export.zip"},
                headers=auth,
            )
        assert resp.status_code == 200
        mock_update.assert_called_once()
        assert resp.get_json()["status"] == "fulfilled"

    def test_fulfill_export_invalid_status(self, client: Any, auth: dict) -> None:
        with patch("database.db.get_connection", return_value=_cnx()), \
             patch("database.db.get_member", return_value=_member()):
            resp = client.post(
                "/api/admin/organizations/1/governance/exports/5/fulfill",
                json={"status": "deleted"},
                headers=auth,
            )
        assert resp.status_code == 400

    def test_fulfill_export_not_found(self, client: Any, auth: dict) -> None:
        cnx = _cnx()
        with patch("database.db.get_connection", return_value=cnx), \
             patch("database.db.get_member", return_value=_member()), \
             patch("database.db.get_export_request", return_value=None):
            resp = client.post(
                "/api/admin/organizations/1/governance/exports/99/fulfill",
                json={"status": "fulfilled"},
                headers=auth,
            )
        assert resp.status_code == 404


# ── Classifications ────────────────────────────────────────────────────────────

class TestClassifications:
    def test_list_classifications(self, client: Any, auth: dict) -> None:
        cnx = _cnx()
        with patch("database.db.get_connection", return_value=cnx), \
             patch("database.db.get_member", return_value=_member()), \
             patch("database.db.list_resource_classifications", return_value=[_cls_row()]):
            resp = client.get("/api/admin/organizations/1/governance/classifications", headers=auth)
        assert resp.status_code == 200
        assert len(resp.get_json()["classifications"]) == 1

    def test_tag_resource(self, client: Any, auth: dict) -> None:
        cnx = _cnx()
        with patch("database.db.get_connection", return_value=cnx), \
             patch("database.db.get_member", return_value=_member()), \
             patch("database.db.upsert_resource_classification", return_value=7) as mock_tag, \
             patch("database.db.log_governance_event"):
            resp = client.post(
                "/api/admin/organizations/1/governance/classifications",
                json={"resource_type": "documents", "resource_id": "doc-123", "classification": "sensitive"},
                headers=auth,
            )
        assert resp.status_code == 201
        mock_tag.assert_called_once()
        assert resp.get_json()["classification"] == "sensitive"

    def test_tag_resource_invalid_classification(self, client: Any, auth: dict) -> None:
        with patch("database.db.get_connection", return_value=_cnx()), \
             patch("database.db.get_member", return_value=_member()):
            resp = client.post(
                "/api/admin/organizations/1/governance/classifications",
                json={"resource_type": "documents", "resource_id": "doc-1", "classification": "top-secret"},
                headers=auth,
            )
        assert resp.status_code == 400

    def test_remove_classification(self, client: Any, auth: dict) -> None:
        cnx = _cnx()
        with patch("database.db.get_connection", return_value=cnx), \
             patch("database.db.get_member", return_value=_member()), \
             patch("database.db.delete_resource_classification") as mock_del, \
             patch("database.db.log_governance_event"):
            resp = client.delete(
                "/api/admin/organizations/1/governance/classifications/7", headers=auth
            )
        assert resp.status_code == 200
        mock_del.assert_called_once()
        assert resp.get_json()["removed"] is True


# ── Deletion check ─────────────────────────────────────────────────────────────

class TestDeletionCheck:
    def test_deletion_allowed(self, client: Any, auth: dict) -> None:
        cnx = _cnx()
        with patch("database.db.get_connection", return_value=cnx), \
             patch("database.db.get_member", return_value=_member()), \
             patch("database.db.has_active_legal_hold", return_value=False):
            resp = client.get(
                "/api/admin/organizations/1/governance/deletion-check"
                "?resource_type=documents&resource_id=doc-1",
                headers=auth,
            )
        assert resp.status_code == 200
        assert resp.get_json()["allowed"] is True

    def test_deletion_blocked(self, client: Any, auth: dict) -> None:
        cnx = _cnx()
        with patch("database.db.get_connection", return_value=cnx), \
             patch("database.db.get_member", return_value=_member()), \
             patch("database.db.has_active_legal_hold", return_value=True):
            resp = client.get(
                "/api/admin/organizations/1/governance/deletion-check"
                "?resource_type=documents&resource_id=doc-1",
                headers=auth,
            )
        assert resp.status_code == 200
        assert resp.get_json()["allowed"] is False

    def test_deletion_check_missing_params(self, client: Any, auth: dict) -> None:
        with patch("database.db.get_connection", return_value=_cnx()), \
             patch("database.db.get_member", return_value=_member()):
            resp = client.get(
                "/api/admin/organizations/1/governance/deletion-check", headers=auth
            )
        assert resp.status_code == 400


# ── Governance audit ───────────────────────────────────────────────────────────

class TestGovernanceAudit:
    def test_list_audit(self, client: Any, auth: dict) -> None:
        cnx = _cnx()
        with patch("database.db.get_connection", return_value=cnx), \
             patch("database.db.get_member", return_value=_member()), \
             patch("database.db.list_governance_audit", return_value=[_gov_event()]):
            resp = client.get("/api/admin/organizations/1/governance/audit", headers=auth)
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data["events"]) == 1
        assert data["events"][0]["action"] == "policy_set"

    def test_list_audit_db_error(self, client: Any, auth: dict) -> None:
        # First get_connection (RBAC) succeeds; second (handler) raises
        with patch("database.db.get_connection", side_effect=[_cnx(), RuntimeError("db down")]), \
             patch("database.db.get_member", return_value=_member()):
            resp = client.get("/api/admin/organizations/1/governance/audit", headers=auth)
        assert resp.status_code == 503

    def test_list_audit_viewer_forbidden(self, client: Any, auth: dict) -> None:
        with patch("database.db.get_connection", return_value=_cnx()), \
             patch("database.db.get_member", return_value=_member("viewer")):
            resp = client.get("/api/admin/organizations/1/governance/audit", headers=auth)
        assert resp.status_code == 403


# ── Auth enforcement ───────────────────────────────────────────────────────────

class TestGovernanceAuth:
    def test_unauthenticated_request_rejected(self, client: Any) -> None:
        resp = client.get("/api/admin/organizations/1/governance/policies")
        assert resp.status_code in (401, 422)

    def test_viewer_cannot_set_policy(self, client: Any, auth: dict) -> None:
        with patch("database.db.get_connection", return_value=_cnx()), \
             patch("database.db.get_member", return_value=_member("viewer")):
            resp = client.put(
                "/api/admin/organizations/1/governance/policies/documents",
                json={"retention_days": 90},
                headers=auth,
            )
        assert resp.status_code == 403

    def test_viewer_cannot_place_hold(self, client: Any, auth: dict) -> None:
        with patch("database.db.get_connection", return_value=_cnx()), \
             patch("database.db.get_member", return_value=_member("viewer")):
            resp = client.post(
                "/api/admin/organizations/1/governance/holds",
                json={"resource_type": "documents", "resource_id": "doc-1", "reason": "test"},
                headers=auth,
            )
        assert resp.status_code == 403
