"""Tests for enterprise identity: SSO, SCIM, admin endpoints, RBAC."""
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


def _org(overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    base: dict[str, Any] = {
        "id": 1, "name": "Acme Corp", "slug": "acme-corp", "domain": "acme.com",
        "sso_provider": "okta", "sso_client_id": "client-id",
        "sso_client_secret": "secret", "sso_discovery_url": "https://acme.okta.com/.well-known/openid-configuration",
        "mfa_required": False, "scim_token_hash": None,
        "created_at": "2024-01-01", "updated_at": "2024-01-01",
    }
    if overrides:
        base.update(overrides)
    return base


def _member(overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    base: dict[str, Any] = {
        "id": 1, "org_id": 1, "user_id": 42, "role": "admin",
        "provisioned_by": "manual", "scim_external_id": None,
        "email": "admin@acme.com", "name": "Admin User",
        "sso_provider": None, "is_active": True,
        "created_at": "2024-01-01", "updated_at": "2024-01-01",
    }
    if overrides:
        base.update(overrides)
    return base


# ── services/identity.py ───────────────────────────────────────────────────────

class TestGetAuthorizationUrl:
    def test_builds_url_with_correct_params(self) -> None:
        from services.identity import get_authorization_url
        org = _org()
        oidc_config = {"authorization_endpoint": "https://acme.okta.com/oauth2/v1/authorize"}
        with patch("services.identity._fetch_oidc_config", return_value=oidc_config):
            url = get_authorization_url(org, "state123", "https://app.example.com/auth/sso/callback")
        assert "client-id" in url
        assert "state123" in url
        assert "openid" in url

    def test_raises_if_no_discovery_url(self) -> None:
        from services.identity import get_authorization_url
        org = _org({"sso_discovery_url": None})
        with pytest.raises(ValueError, match="SSO not configured"):
            get_authorization_url(org, "s", "https://cb.example.com")


class TestExchangeCode:
    def test_decodes_claims_from_id_token(self) -> None:
        import base64
        import json as _json

        from services.identity import exchange_code_for_tokens
        header = base64.urlsafe_b64encode(b'{"alg":"RS256"}').rstrip(b"=").decode()
        payload_data = {"sub": "usr-1", "email": "alice@acme.com", "name": "Alice"}
        payload = base64.urlsafe_b64encode(_json.dumps(payload_data).encode()).rstrip(b"=").decode()
        fake_id_token = f"{header}.{payload}.fakesig"
        fake_response = MagicMock()
        fake_response.json.return_value = {"id_token": fake_id_token, "access_token": "at"}
        oidc_config = {"token_endpoint": "https://acme.okta.com/oauth2/v1/token"}
        with patch("services.identity._fetch_oidc_config", return_value=oidc_config):
            with patch("services.identity.http.post", return_value=fake_response):
                claims = exchange_code_for_tokens(_org(), "code-abc", "https://cb.example.com")
        assert claims["email"] == "alice@acme.com"
        assert claims["sub"] == "usr-1"

    def test_raises_on_malformed_id_token(self) -> None:
        from services.identity import exchange_code_for_tokens
        fake_response = MagicMock()
        fake_response.json.return_value = {"id_token": "onlyonepart"}
        oidc_config = {"token_endpoint": "https://acme.okta.com/oauth2/v1/token"}
        with patch("services.identity._fetch_oidc_config", return_value=oidc_config):
            with patch("services.identity.http.post", return_value=fake_response):
                with pytest.raises(ValueError, match="Malformed"):
                    exchange_code_for_tokens(_org(), "code", "https://cb.example.com")


class TestGroupNameToRole:
    def test_admin_keywords(self) -> None:
        from services.identity import group_name_to_role
        assert group_name_to_role("Admin") == "admin"
        assert group_name_to_role("ADMINISTRATOR") == "admin"

    def test_viewer_keywords(self) -> None:
        from services.identity import group_name_to_role
        assert group_name_to_role("viewer") == "viewer"
        assert group_name_to_role("Read-Only") == "viewer"
        assert group_name_to_role("readonly") == "viewer"

    def test_unknown_defaults_to_member(self) -> None:
        from services.identity import group_name_to_role
        assert group_name_to_role("Engineering") == "member"
        assert group_name_to_role("Sales Team") == "member"


class TestGenerateScimToken:
    def test_returns_raw_and_hash(self) -> None:
        import bcrypt

        from services.identity import generate_scim_token
        raw, hashed = generate_scim_token()
        assert len(raw) > 20
        assert bcrypt.checkpw(raw.encode(), hashed.encode())

    def test_each_call_unique(self) -> None:
        from services.identity import generate_scim_token
        raw1, _ = generate_scim_token()
        raw2, _ = generate_scim_token()
        assert raw1 != raw2


# ── middleware/rbac.py ─────────────────────────────────────────────────────────

class TestRequireOrgRole:
    def test_403_when_not_member(self, client: Any, auth: dict[str, str]) -> None:
        with patch("database.db.get_connection"), \
             patch("database.db.get_member", return_value=None):
            resp = client.get("/api/admin/organizations/1/members", headers={**auth, "X-Org-Id": "1"})
        assert resp.status_code == 403

    def test_403_when_wrong_role(self, client: Any, auth: dict[str, str]) -> None:
        viewer = _member({"user_id": 42, "role": "viewer"})
        with patch("database.db.get_connection"), \
             patch("database.db.get_member", return_value=viewer):
            resp = client.patch(
                "/api/admin/organizations/1/members/99",
                json={"role": "admin"},
                headers={**auth, "X-Org-Id": "1"},
            )
        assert resp.status_code == 403

    def test_401_without_token(self, client: Any) -> None:
        resp = client.get("/api/admin/organizations/1/members", headers={"X-Org-Id": "1"})
        assert resp.status_code == 401


# ── SSO endpoints ──────────────────────────────────────────────────────────────

class TestSsoInit:
    def test_400_missing_org_id(self, client: Any) -> None:
        resp = client.get("/auth/sso/init")
        assert resp.status_code == 400

    def test_404_org_not_found(self, client: Any) -> None:
        with patch("database.db.get_connection"), \
             patch("database.db.get_org_by_id", return_value=None):
            resp = client.get("/auth/sso/init?org_id=999")
        assert resp.status_code == 404

    def test_422_sso_not_configured(self, client: Any) -> None:
        org = _org({"sso_discovery_url": None})
        with patch("database.db.get_connection"), \
             patch("database.db.get_org_by_id", return_value=org):
            resp = client.get("/auth/sso/init?org_id=1")
        assert resp.status_code == 422

    def test_redirects_to_idp(self, client: Any) -> None:
        org = _org()
        auth_url = "https://acme.okta.com/oauth2/v1/authorize?response_type=code"
        with patch("database.db.get_connection"), \
             patch("database.db.get_org_by_id", return_value=org), \
             patch("services.identity.get_authorization_url", return_value=auth_url):
            resp = client.get("/auth/sso/init?org_id=1")
        assert resp.status_code == 302
        assert "okta.com" in resp.headers["Location"]

    def test_providers_list(self, client: Any) -> None:
        resp = client.get("/auth/sso/providers")
        assert resp.status_code == 200
        data = resp.get_json()
        provider_ids = [p["id"] for p in data["providers"]]
        assert "okta" in provider_ids
        assert "azure" in provider_ids
        assert "google" in provider_ids


class TestSsoCallback:
    def test_400_missing_code(self, client: Any) -> None:
        resp = client.get("/auth/sso/callback?state=abc")
        assert resp.status_code == 400

    def test_400_invalid_state(self, client: Any) -> None:
        resp = client.get("/auth/sso/callback?code=xyz&state=nonexistent-state")
        assert resp.status_code == 400

    def test_returns_token_on_success(self, client: Any) -> None:
        import api_endpoints.sso.handler as sso_mod
        sso_mod._SSO_STATE_STORE["test-state"] = 1
        claims = {"sub": "u1", "email": "alice@acme.com", "name": "Alice"}
        with patch("database.db.get_connection"), \
             patch("database.db.get_org_by_id", return_value=_org()), \
             patch("services.identity.exchange_code_for_tokens", return_value=claims), \
             patch("services.identity.provision_sso_user", return_value=42):
            resp = client.get("/auth/sso/callback?code=validcode&state=test-state")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "token" in data
        assert data["userId"] == 42

    def test_idp_error_param(self, client: Any) -> None:
        resp = client.get("/auth/sso/callback?error=access_denied&state=s")
        assert resp.status_code == 400
        assert "access_denied" in resp.get_json()["error"]


# ── SCIM endpoints ─────────────────────────────────────────────────────────────

def _scim_headers(token: str = "raw-scim-token") -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def _scim_org() -> dict[str, Any]:
    """Org with a non-null scim_token_hash so the decorator's DB lookup succeeds."""
    return _org({"scim_token_hash": "fake-hash"})


def _scim_ctx() -> Any:
    """Context manager stack that satisfies require_scim_token."""
    return patch.multiple(
        "database.db",
        get_connection=MagicMock(),
        get_org_by_id=MagicMock(return_value=_scim_org()),
    )


class TestScimUsers:
    def test_list_users_200(self, client: Any) -> None:
        members = [_member({"scim_external_id": "ext-1"})]
        with patch("bcrypt.checkpw", return_value=True), \
             patch("database.db.get_connection"), \
             patch("database.db.get_org_by_id", return_value=_scim_org()), \
             patch("database.db.list_members", return_value=members):
            resp = client.get("/scim/v2/1/Users", headers=_scim_headers())
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["totalResults"] == 1
        assert data["Resources"][0]["userName"] == "admin@acme.com"

    def test_create_user_201(self, client: Any) -> None:
        new_member = _member({"user_id": 99, "email": "bob@acme.com", "scim_external_id": "ext-bob"})
        with patch("bcrypt.checkpw", return_value=True), \
             patch("database.db.get_connection"), \
             patch("database.db.get_org_by_id", return_value=_scim_org()), \
             patch("database.db.get_member_by_scim_id", return_value=None), \
             patch("database.db.upsert_sso_user", return_value=99), \
             patch("database.db.upsert_member"), \
             patch("database.db.log_identity_event"), \
             patch("database.db.list_members", return_value=[new_member]):
            resp = client.post("/scim/v2/1/Users", headers=_scim_headers(), json={
                "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
                "userName": "bob@acme.com",
                "emails": [{"value": "bob@acme.com", "primary": True}],
                "externalId": "ext-bob",
                "active": True,
            })
        assert resp.status_code == 201
        assert resp.get_json()["userName"] == "bob@acme.com"

    def test_create_user_409_duplicate(self, client: Any) -> None:
        existing = _member({"scim_external_id": "ext-bob"})
        with patch("bcrypt.checkpw", return_value=True), \
             patch("database.db.get_connection"), \
             patch("database.db.get_org_by_id", return_value=_scim_org()), \
             patch("database.db.get_member_by_scim_id", return_value=existing):
            resp = client.post("/scim/v2/1/Users", headers=_scim_headers(), json={
                "userName": "bob@acme.com",
                "emails": [{"value": "bob@acme.com", "primary": True}],
                "externalId": "ext-bob",
            })
        assert resp.status_code == 409

    def test_delete_user_204(self, client: Any) -> None:
        mem_row = {"user_id": 42}
        with patch("bcrypt.checkpw", return_value=True), \
             patch("database.db.get_connection") as mock_cnx, \
             patch("database.db.get_org_by_id", return_value=_scim_org()), \
             patch("database.db.get_member_by_scim_id", return_value=mem_row), \
             patch("database.db.remove_member"), \
             patch("database.db.log_identity_event"):
            mock_cnx.return_value.cursor.return_value.execute = MagicMock()
            resp = client.delete("/scim/v2/1/Users/ext-1", headers=_scim_headers())
        assert resp.status_code == 204

    def test_patch_user_active_false(self, client: Any) -> None:
        mem_row = {"user_id": 42}
        updated = _member({"is_active": False, "scim_external_id": "ext-1"})
        with patch("bcrypt.checkpw", return_value=True), \
             patch("database.db.get_connection") as mock_cnx, \
             patch("database.db.get_org_by_id", return_value=_scim_org()), \
             patch("database.db.get_member_by_scim_id", return_value=mem_row), \
             patch("database.db.log_identity_event"), \
             patch("database.db.list_members", return_value=[updated]):
            mock_cnx.return_value.cursor.return_value.execute = MagicMock()
            resp = client.patch("/scim/v2/1/Users/ext-1", headers=_scim_headers(), json={
                "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
                "Operations": [{"op": "Replace", "path": "active", "value": False}],
            })
        assert resp.status_code == 200
        assert resp.get_json()["active"] is False

    def test_get_user_404(self, client: Any) -> None:
        with patch("bcrypt.checkpw", return_value=True), \
             patch("database.db.get_connection"), \
             patch("database.db.get_org_by_id", return_value=_scim_org()), \
             patch("database.db.get_member_by_scim_id", return_value=None):
            resp = client.get("/scim/v2/1/Users/no-such-id", headers=_scim_headers())
        assert resp.status_code == 404


class TestScimGroups:
    def test_list_groups_returns_three_roles(self, client: Any) -> None:
        with patch("bcrypt.checkpw", return_value=True), \
             patch("database.db.get_connection"), \
             patch("database.db.get_org_by_id", return_value=_scim_org()):
            resp = client.get("/scim/v2/1/Groups", headers=_scim_headers())
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["totalResults"] == 3
        ids = [g["id"] for g in data["Resources"]]
        assert "admin" in ids and "member" in ids and "viewer" in ids

    def test_create_group_maps_admin_role(self, client: Any) -> None:
        with patch("bcrypt.checkpw", return_value=True), \
             patch("database.db.get_connection"), \
             patch("database.db.get_org_by_id", return_value=_scim_org()), \
             patch("database.db.upsert_sso_user", return_value=10), \
             patch("database.db.upsert_member"), \
             patch("database.db.log_identity_event"):
            resp = client.post("/scim/v2/1/Groups", headers=_scim_headers(), json={
                "displayName": "Admin",
                "members": [{"value": "alice@acme.com", "display": "Alice"}],
            })
        assert resp.status_code == 201
        assert resp.get_json()["id"] == "admin"

    def test_patch_group_add_member(self, client: Any) -> None:
        with patch("bcrypt.checkpw", return_value=True), \
             patch("database.db.get_connection"), \
             patch("database.db.get_org_by_id", return_value=_scim_org()), \
             patch("database.db.upsert_sso_user", return_value=55), \
             patch("database.db.upsert_member"), \
             patch("database.db.log_identity_event"):
            resp = client.patch("/scim/v2/1/Groups/member", headers=_scim_headers(), json={
                "Operations": [{"op": "add", "value": [{"value": "bob@acme.com"}]}],
            })
        assert resp.status_code == 200

    def test_delete_group_204(self, client: Any) -> None:
        with patch("bcrypt.checkpw", return_value=True), \
             patch("database.db.get_connection"), \
             patch("database.db.get_org_by_id", return_value=_scim_org()):
            resp = client.delete("/scim/v2/1/Groups/member", headers=_scim_headers())
        assert resp.status_code == 204


# ── Admin endpoints ────────────────────────────────────────────────────────────

class TestAdminOrganizations:
    def _admin_member(self) -> dict[str, Any]:
        return _member({"user_id": 42, "role": "admin"})

    def test_list_orgs_200(self, client: Any, auth: dict[str, str]) -> None:
        with patch("database.db.get_connection"), \
             patch("database.db.list_orgs", return_value=[_org()]):
            resp = client.get("/api/admin/organizations", headers=auth)
        assert resp.status_code == 200
        assert len(resp.get_json()["organizations"]) == 1

    def test_create_org_201(self, client: Any, auth: dict[str, str]) -> None:
        with patch("database.db.get_connection"), \
             patch("database.db.get_org_by_slug", return_value=None), \
             patch("database.db.create_org", return_value=7), \
             patch("database.db.upsert_member"), \
             patch("database.db.log_identity_event"):
            resp = client.post("/api/admin/organizations", headers=auth, json={"name": "Beta Corp", "domain": "beta.com"})
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["id"] == 7
        assert "beta-corp" in data["slug"]

    def test_create_org_400_no_name(self, client: Any, auth: dict[str, str]) -> None:
        resp = client.post("/api/admin/organizations", headers=auth, json={})
        assert resp.status_code == 400

    def test_get_org_200(self, client: Any, auth: dict[str, str]) -> None:
        with patch("database.db.get_connection"), \
             patch("database.db.get_member", return_value=self._admin_member()), \
             patch("database.db.get_connection"), \
             patch("database.db.get_org_by_id", return_value=_org()):
            resp = client.get("/api/admin/organizations/1", headers=auth)
        assert resp.status_code == 200
        assert resp.get_json()["name"] == "Acme Corp"

    def test_get_org_404(self, client: Any, auth: dict[str, str]) -> None:
        with patch("database.db.get_connection"), \
             patch("database.db.get_member", return_value=self._admin_member()), \
             patch("database.db.get_connection"), \
             patch("database.db.get_org_by_id", return_value=None):
            resp = client.get("/api/admin/organizations/999", headers=auth)
        assert resp.status_code == 404

    def test_update_org_200(self, client: Any, auth: dict[str, str]) -> None:
        updated = _org({"mfa_required": True})
        with patch("database.db.get_connection"), \
             patch("database.db.get_member", return_value=self._admin_member()), \
             patch("database.db.get_connection"), \
             patch("database.db.update_org"), \
             patch("database.db.log_identity_event"), \
             patch("database.db.get_org_by_id", return_value=updated):
            resp = client.patch("/api/admin/organizations/1", headers=auth, json={"mfa_required": True})
        assert resp.status_code == 200

    def test_delete_org_200(self, client: Any, auth: dict[str, str]) -> None:
        with patch("database.db.get_connection"), \
             patch("database.db.get_member", return_value=self._admin_member()), \
             patch("database.db.get_connection"), \
             patch("database.db.log_identity_event"), \
             patch("database.db.delete_org"):
            resp = client.delete("/api/admin/organizations/1", headers=auth)
        assert resp.status_code == 200


class TestAdminSso:
    def _admin(self) -> dict[str, Any]:
        return _member({"user_id": 42, "role": "admin"})

    def test_configure_sso_200(self, client: Any, auth: dict[str, str]) -> None:
        with patch("database.db.get_connection"), \
             patch("database.db.get_member", return_value=self._admin()), \
             patch("database.db.get_connection"), \
             patch("database.db.update_org"), \
             patch("database.db.log_identity_event"):
            resp = client.put("/api/admin/organizations/1/sso", headers=auth, json={
                "provider": "okta",
                "client_id": "cid",
                "client_secret": "csecret",
                "discovery_url": "https://acme.okta.com/.well-known/openid-configuration",
            })
        assert resp.status_code == 200
        assert resp.get_json()["configured"] is True

    def test_configure_sso_400_invalid_provider(self, client: Any, auth: dict[str, str]) -> None:
        with patch("database.db.get_connection"), \
             patch("database.db.get_member", return_value=self._admin()):
            resp = client.put("/api/admin/organizations/1/sso", headers=auth, json={
                "provider": "unknown-idp",
                "client_id": "cid",
                "client_secret": "csecret",
                "discovery_url": "https://example.com",
            })
        assert resp.status_code == 400

    def test_disable_sso_200(self, client: Any, auth: dict[str, str]) -> None:
        with patch("database.db.get_connection"), \
             patch("database.db.get_member", return_value=self._admin()), \
             patch("database.db.get_connection"), \
             patch("database.db.update_org"), \
             patch("database.db.log_identity_event"):
            resp = client.delete("/api/admin/organizations/1/sso", headers=auth)
        assert resp.status_code == 200


class TestAdminScimToken:
    def test_rotate_returns_raw_token(self, client: Any, auth: dict[str, str]) -> None:
        with patch("database.db.get_connection"), \
             patch("database.db.get_member", return_value=_member({"user_id": 42, "role": "admin"})), \
             patch("database.db.get_connection"), \
             patch("database.db.update_org"), \
             patch("database.db.log_identity_event"):
            resp = client.post("/api/admin/organizations/1/scim-token", headers=auth)
        assert resp.status_code == 201
        data = resp.get_json()
        assert "token" in data
        assert len(data["token"]) > 20
        assert "warning" in data
        assert "/scim/v2/1" in data["scim_base_url"]


class TestAdminMembers:
    def _admin(self) -> dict[str, Any]:
        return _member({"user_id": 42, "role": "admin"})

    def test_list_members_200(self, client: Any, auth: dict[str, str]) -> None:
        with patch("database.db.get_connection"), \
             patch("database.db.get_member", return_value=self._admin()), \
             patch("database.db.get_connection"), \
             patch("database.db.list_members", return_value=[_member()]):
            resp = client.get("/api/admin/organizations/1/members", headers=auth)
        assert resp.status_code == 200
        assert len(resp.get_json()["members"]) == 1

    def test_add_member_201(self, client: Any, auth: dict[str, str]) -> None:
        user = {"id": 99, "email": "bob@acme.com", "name": "Bob", "password_hash": "x"}
        with patch("database.db.get_connection"), \
             patch("database.db.get_member", return_value=self._admin()), \
             patch("database.db.get_connection"), \
             patch("database.db.get_user_by_email", return_value=user), \
             patch("database.db.upsert_member"), \
             patch("database.db.log_identity_event"):
            resp = client.post("/api/admin/organizations/1/members", headers=auth,
                               json={"email": "bob@acme.com", "role": "member"})
        assert resp.status_code == 201
        assert resp.get_json()["email"] == "bob@acme.com"

    def test_add_member_404_user_not_found(self, client: Any, auth: dict[str, str]) -> None:
        with patch("database.db.get_connection"), \
             patch("database.db.get_member", return_value=self._admin()), \
             patch("database.db.get_connection"), \
             patch("database.db.get_user_by_email", return_value=None):
            resp = client.post("/api/admin/organizations/1/members", headers=auth,
                               json={"email": "nobody@acme.com", "role": "member"})
        assert resp.status_code == 404

    def test_update_member_role_200(self, client: Any, auth: dict[str, str]) -> None:
        with patch("database.db.get_connection"), \
             patch("database.db.get_member", return_value=self._admin()), \
             patch("database.db.get_connection"), \
             patch("database.db.get_member", return_value=_member()), \
             patch("database.db.upsert_member"), \
             patch("database.db.log_identity_event"):
            resp = client.patch("/api/admin/organizations/1/members/99", headers=auth, json={"role": "viewer"})
        assert resp.status_code == 200
        assert resp.get_json()["role"] == "viewer"

    def test_update_member_role_400_invalid(self, client: Any, auth: dict[str, str]) -> None:
        with patch("database.db.get_connection"), \
             patch("database.db.get_member", return_value=self._admin()):
            resp = client.patch("/api/admin/organizations/1/members/99", headers=auth, json={"role": "superuser"})
        assert resp.status_code == 400

    def test_remove_member_200(self, client: Any, auth: dict[str, str]) -> None:
        with patch("database.db.get_connection"), \
             patch("database.db.get_member", return_value=self._admin()), \
             patch("database.db.get_connection"), \
             patch("database.db.remove_member"), \
             patch("database.db.log_identity_event"):
            resp = client.delete("/api/admin/organizations/1/members/99", headers=auth)
        assert resp.status_code == 200


class TestAdminAuditLog:
    def test_audit_log_200(self, client: Any, auth: dict[str, str]) -> None:
        events = [
            {"id": 1, "org_id": 1, "user_id": 42, "event_type": "sso_login",
             "actor": "alice@acme.com", "detail": {"provider": "okta"}, "created_at": "2024-01-01T00:00:00"},
        ]
        with patch("database.db.get_connection"), \
             patch("database.db.get_member", return_value=_member({"user_id": 42, "role": "admin"})), \
             patch("database.db.get_connection"), \
             patch("database.db.list_audit_events", return_value=events):
            resp = client.get("/api/admin/organizations/1/audit-log", headers=auth)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["total"] == 1
        assert data["events"][0]["event_type"] == "sso_login"

    def test_audit_log_limit_capped(self, client: Any, auth: dict[str, str]) -> None:
        with patch("database.db.get_connection"), \
             patch("database.db.get_member", return_value=_member({"user_id": 42, "role": "admin"})), \
             patch("database.db.get_connection"), \
             patch("database.db.list_audit_events", return_value=[]) as mock_list:
            client.get("/api/admin/organizations/1/audit-log?limit=9999", headers=auth)
        mock_list.assert_called_once()
        called_limit = mock_list.call_args[0][2]
        assert called_limit <= 500


# ── DB helpers (offline, no MySQL) ────────────────────────────────────────────

class TestDbHelpers:
    def _make_cnx(self, fetchone: Any = None, fetchall: Any = None) -> MagicMock:
        cursor = MagicMock()
        cursor.fetchone.return_value = fetchone
        cursor.fetchall.return_value = fetchall or []
        cursor.lastrowid = 99
        cnx = MagicMock()
        cnx.cursor.return_value = cursor
        return cnx

    def test_get_org_by_id_returns_row(self) -> None:
        from database.db import get_org_by_id
        row = {"id": 1, "name": "Acme"}
        cnx = self._make_cnx(fetchone=row)
        result = get_org_by_id(cnx, 1)
        assert result == row

    def test_get_org_by_slug_returns_none(self) -> None:
        from database.db import get_org_by_slug
        cnx = self._make_cnx(fetchone=None)
        result = get_org_by_slug(cnx, "no-such-slug")
        assert result is None

    def test_create_org_returns_id(self) -> None:
        from database.db import create_org
        cnx = self._make_cnx()
        org_id = create_org(cnx, "Test Org", "test-org")
        assert org_id == 99

    def test_upsert_member_calls_execute(self) -> None:
        from database.db import upsert_member
        cnx = self._make_cnx()
        upsert_member(cnx, org_id=1, user_id=5, role="viewer")
        assert cnx.cursor().execute.called

    def test_remove_member_calls_execute(self) -> None:
        from database.db import remove_member
        cnx = self._make_cnx()
        remove_member(cnx, org_id=1, user_id=5)
        assert cnx.cursor().execute.called

    def test_log_identity_event_inserts(self) -> None:
        from database.db import log_identity_event
        cnx = self._make_cnx()
        log_identity_event(cnx, "sso_login", org_id=1, user_id=5, actor="alice@test.com", detail={"k": "v"})
        assert cnx.cursor().execute.called

    def test_list_audit_events_returns_rows(self) -> None:
        from database.db import list_audit_events
        rows = [{"id": 1, "event_type": "sso_login"}]
        cnx = self._make_cnx(fetchall=rows)
        result = list_audit_events(cnx, org_id=1)
        assert result == rows

    def test_update_org_skips_unknown_fields(self) -> None:
        from database.db import update_org
        cnx = self._make_cnx()
        update_org(cnx, org_id=1, fields={"hacked_field": "evil", "name": "Good Name"})
        call_args = cnx.cursor().execute.call_args
        assert "name" in call_args[0][0]
        assert "hacked_field" not in call_args[0][0]

    def test_update_org_noop_on_empty_fields(self) -> None:
        from database.db import update_org
        cnx = self._make_cnx()
        update_org(cnx, org_id=1, fields={"bad_field": "x"})
        cnx.cursor().execute.assert_not_called()

    def test_list_members_returns_rows(self) -> None:
        from database.db import list_members
        rows = [{"user_id": 1, "email": "x@x.com", "role": "admin"}]
        cnx = self._make_cnx(fetchall=rows)
        result = list_members(cnx, org_id=1)
        assert result == rows

    def test_get_user_by_email_returns_row(self) -> None:
        from database.db import get_user_by_email
        row = {"id": 1, "email": "alice@test.com"}
        cnx = self._make_cnx(fetchone=row)
        result = get_user_by_email(cnx, "alice@test.com")
        assert result == row

    def test_get_user_by_email_returns_none(self) -> None:
        from database.db import get_user_by_email
        cnx = self._make_cnx(fetchone=None)
        result = get_user_by_email(cnx, "nobody@test.com")
        assert result is None

    def test_create_user_returns_id(self) -> None:
        from database.db import create_user
        cnx = self._make_cnx()
        user_id = create_user(cnx, "bob@test.com", "hashed", "Bob")
        assert user_id == 99

    def test_get_user_by_id_returns_row(self) -> None:
        from database.db import get_user_by_id
        row = {"id": 5, "email": "carol@test.com"}
        cnx = self._make_cnx(fetchone=row)
        result = get_user_by_id(cnx, 5)
        assert result == row

    def test_get_user_by_id_returns_none(self) -> None:
        from database.db import get_user_by_id
        cnx = self._make_cnx(fetchone=None)
        assert get_user_by_id(cnx, 999) is None

    def test_upsert_sso_user_returns_user_id(self) -> None:
        from database.db import upsert_sso_user
        cursor = MagicMock()
        cursor.fetchone.return_value = (42,)
        cursor.lastrowid = 42
        cnx = MagicMock()
        cnx.cursor.return_value = cursor
        result = upsert_sso_user(cnx, "dave@test.com", "Dave", "okta", "sub-123")
        assert result == 42

    def test_upsert_sso_user_returns_zero_on_missing_row(self) -> None:
        from database.db import upsert_sso_user
        cursor = MagicMock()
        cursor.fetchone.return_value = None
        cnx = MagicMock()
        cnx.cursor.return_value = cursor
        result = upsert_sso_user(cnx, "eve@test.com", "Eve", "okta", "sub-456")
        assert result == 0

    def test_get_member_by_scim_id_returns_row(self) -> None:
        from database.db import get_member_by_scim_id
        row = {"id": 1, "org_id": 1, "user_id": 5, "scim_external_id": "ext-abc"}
        cnx = self._make_cnx(fetchone=row)
        result = get_member_by_scim_id(cnx, org_id=1, scim_external_id="ext-abc")
        assert result == row

    def test_get_member_returns_none_when_missing(self) -> None:
        from database.db import get_member
        cnx = self._make_cnx(fetchone=None)
        assert get_member(cnx, org_id=1, user_id=999) is None

    def test_delete_org_calls_execute(self) -> None:
        from database.db import delete_org
        cnx = self._make_cnx()
        delete_org(cnx, org_id=5)
        assert cnx.cursor().execute.called


# ── Additional coverage: rbac error paths ─────────────────────────────────────

class TestRbacErrorPaths:
    def test_scim_token_missing_bearer(self, client: Any) -> None:
        """require_scim_token returns 401 when Authorization header is absent."""
        resp = client.get("/scim/v2/1/Users", headers={"Content-Type": "application/json"})
        assert resp.status_code == 401

    def test_scim_token_not_configured(self, client: Any) -> None:
        """require_scim_token returns 403 when org has no scim_token_hash."""
        org_no_scim = _org({"scim_token_hash": None})
        with patch("database.db.get_connection"), \
             patch("database.db.get_org_by_id", return_value=org_no_scim):
            resp = client.get("/scim/v2/1/Users",
                              headers={"Authorization": "Bearer some-token"})
        assert resp.status_code == 403

    def test_scim_token_invalid(self, client: Any) -> None:
        """require_scim_token returns 401 when token doesn't match hash."""
        org_with_hash = _org({"scim_token_hash": "$2b$12$fakehash"})
        with patch("database.db.get_connection"), \
             patch("database.db.get_org_by_id", return_value=org_with_hash), \
             patch("bcrypt.checkpw", return_value=False):
            resp = client.get("/scim/v2/1/Users",
                              headers={"Authorization": "Bearer wrong-token"})
        assert resp.status_code == 401

    def test_scim_token_db_error_returns_503(self, client: Any) -> None:
        """require_scim_token returns 503 when DB raises."""
        with patch("database.db.get_connection", side_effect=Exception("db down")):
            resp = client.get("/scim/v2/1/Users",
                              headers={"Authorization": "Bearer any-token"})
        assert resp.status_code == 503

    def test_require_org_role_db_error_still_403(self, client: Any, auth: dict[str, str]) -> None:
        """require_org_role falls back to 403 when DB is unavailable."""
        with patch("database.db.get_connection", side_effect=Exception("db down")):
            resp = client.get("/api/admin/organizations/1/members",
                              headers={**auth, "X-Org-Id": "1"})
        assert resp.status_code == 403


# ── Additional coverage: identity service ─────────────────────────────────────

class TestIdentityServiceExtra:
    def test_fetch_oidc_config_returns_json(self) -> None:
        from services.identity import _fetch_oidc_config
        fake = MagicMock()
        fake.json.return_value = {"authorization_endpoint": "https://idp.example.com/auth"}
        with patch("services.identity.http.get", return_value=fake):
            result = _fetch_oidc_config("https://idp.example.com/.well-known/openid-configuration")
        assert result["authorization_endpoint"] == "https://idp.example.com/auth"

    def test_provision_sso_user_returns_user_id(self) -> None:
        from services.identity import provision_sso_user
        claims = {"sub": "sub-123", "email": "alice@acme.com", "name": "Alice"}
        with patch("database.db.upsert_sso_user", return_value=7), \
             patch("database.db.upsert_member"), \
             patch("database.db.log_identity_event"):
            cnx = MagicMock()
            result = provision_sso_user(cnx, org_id=1, claims=claims, sso_provider="okta")
        assert result == 7

    def test_provision_sso_user_raises_on_missing_email(self) -> None:
        from services.identity import provision_sso_user
        claims: dict[str, Any] = {"sub": "sub-123"}
        with pytest.raises(ValueError, match="missing email"):
            provision_sso_user(MagicMock(), org_id=1, claims=claims, sso_provider="okta")


# ── Additional coverage: SCIM error paths ─────────────────────────────────────

class TestScimExtraErrors:
    def test_create_user_400_missing_email(self, client: Any) -> None:
        with patch("bcrypt.checkpw", return_value=True), \
             patch("database.db.get_connection"), \
             patch("database.db.get_org_by_id", return_value=_scim_org()):
            resp = client.post("/scim/v2/1/Users",
                               headers=_scim_headers(),
                               json={"schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"]})
        assert resp.status_code == 400

    def test_list_users_503_on_db_error(self, client: Any) -> None:
        with patch("bcrypt.checkpw", return_value=True), \
             patch("database.db.get_connection"), \
             patch("database.db.get_org_by_id", return_value=_scim_org()), \
             patch("database.db.list_members", side_effect=Exception("db error")):
            resp = client.get("/scim/v2/1/Users", headers=_scim_headers())
        assert resp.status_code == 503

    def test_replace_user_404_not_found(self, client: Any) -> None:
        with patch("bcrypt.checkpw", return_value=True), \
             patch("database.db.get_connection"), \
             patch("database.db.get_org_by_id", return_value=_scim_org()), \
             patch("database.db.get_member_by_scim_id", return_value=None):
            resp = client.put("/scim/v2/1/Users/no-such-id",
                              headers=_scim_headers(),
                              json={"active": True})
        assert resp.status_code == 404
