"""Identity service: OIDC/SSO flow and SCIM helpers."""
from __future__ import annotations

import secrets
import urllib.parse
from typing import Any

import requests as http

# ── OIDC discovery ─────────────────────────────────────────────────────────────

def _fetch_oidc_config(discovery_url: str) -> dict[str, Any]:
    resp = http.get(discovery_url, timeout=10)
    resp.raise_for_status()
    result: dict[str, Any] = resp.json()
    return result


def get_authorization_url(org: dict[str, Any], state: str, redirect_uri: str) -> str:
    """Build the OIDC authorization URL for the given org's SSO provider."""
    discovery_url = org.get("sso_discovery_url") or ""
    if not discovery_url:
        raise ValueError("SSO not configured for this organization")
    config = _fetch_oidc_config(discovery_url)
    auth_endpoint: str = config["authorization_endpoint"]
    params = {
        "response_type": "code",
        "client_id": org["sso_client_id"],
        "redirect_uri": redirect_uri,
        "scope": "openid email profile",
        "state": state,
    }
    return f"{auth_endpoint}?{urllib.parse.urlencode(params)}"


def exchange_code_for_tokens(
    org: dict[str, Any], code: str, redirect_uri: str
) -> dict[str, Any]:
    """Exchange OIDC authorization code for tokens; return id_token claims."""
    discovery_url = org.get("sso_discovery_url") or ""
    config = _fetch_oidc_config(discovery_url)
    token_endpoint: str = config["token_endpoint"]
    resp = http.post(
        token_endpoint,
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": org["sso_client_id"],
            "client_secret": org["sso_client_secret"],
        },
        timeout=15,
    )
    resp.raise_for_status()
    token_data: dict[str, Any] = resp.json()

    # Decode the id_token claims without signature verification (server-side flow).
    import base64
    import json as _json
    id_token: str = token_data.get("id_token", "")
    parts = id_token.split(".")
    if len(parts) != 3:
        raise ValueError("Malformed id_token")
    padded = parts[1] + "=" * (-len(parts[1]) % 4)
    claims: dict[str, Any] = _json.loads(base64.urlsafe_b64decode(padded))
    return claims


def provision_sso_user(
    cnx: Any,
    org_id: int,
    claims: dict[str, Any],
    sso_provider: str,
) -> int:
    """Create-or-update the user from OIDC claims; add to org; return user_id."""
    from database.db import log_identity_event, upsert_member, upsert_sso_user

    email: str = (claims.get("email") or "").lower().strip()
    name: str = claims.get("name") or claims.get("given_name") or email
    sso_id: str = str(claims.get("sub") or "")

    if not email:
        raise ValueError("SSO token missing email claim")

    user_id = upsert_sso_user(cnx, email, name, sso_provider, sso_id)
    upsert_member(cnx, org_id, user_id, role="member", provisioned_by="sso")
    log_identity_event(
        cnx,
        event_type="sso_login",
        org_id=org_id,
        user_id=user_id,
        actor=email,
        detail={"provider": sso_provider, "sub": sso_id},
    )
    return user_id


# ── SCIM helpers ───────────────────────────────────────────────────────────────

SCIM_USER_SCHEMA = "urn:ietf:params:scim:schemas:core:2.0:User"
SCIM_GROUP_SCHEMA = "urn:ietf:params:scim:schemas:core:2.0:Group"
SCIM_LIST_SCHEMA = "urn:ietf:params:scim:api:messages:2.0:ListResponse"
SCIM_ERROR_SCHEMA = "urn:ietf:params:scim:api:messages:2.0:Error"


def scim_user_from_row(member: dict[str, Any], base_url: str, org_id: int) -> dict[str, Any]:
    return {
        "schemas": [SCIM_USER_SCHEMA],
        "id": str(member["scim_external_id"] or member["user_id"]),
        "externalId": member.get("scim_external_id"),
        "userName": member["email"],
        "name": {"formatted": member.get("name") or member["email"]},
        "emails": [{"value": member["email"], "primary": True}],
        "active": bool(member.get("is_active", True)),
        "meta": {
            "resourceType": "User",
            "location": f"{base_url}/scim/v2/{org_id}/Users/{member['scim_external_id'] or member['user_id']}",
        },
    }


def scim_error(detail: str, status: int = 400) -> dict[str, Any]:
    return {
        "schemas": [SCIM_ERROR_SCHEMA],
        "detail": detail,
        "status": str(status),
    }


def generate_scim_token() -> tuple[str, str]:
    """Return (raw_token, bcrypt_hash). Store hash; send raw to admin."""
    import bcrypt
    raw = secrets.token_urlsafe(32)
    hashed = bcrypt.hashpw(raw.encode(), bcrypt.gensalt()).decode()
    return raw, hashed


# ── SCIM group → role mapping ──────────────────────────────────────────────────

_ROLE_KEYWORDS: dict[str, str] = {
    "admin": "admin",
    "administrator": "admin",
    "viewer": "viewer",
    "readonly": "viewer",
    "read-only": "viewer",
    "read_only": "viewer",
}


def group_name_to_role(display_name: str) -> str:
    key = display_name.lower().strip()
    return _ROLE_KEYWORDS.get(key, "member")
