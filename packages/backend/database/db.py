"""MySQL database connection and query helpers."""
from __future__ import annotations

import os
from typing import Any

try:
    import mysql.connector
    MYSQL_AVAILABLE = True
except ImportError:
    MYSQL_AVAILABLE = False


def get_connection() -> Any:
    if not MYSQL_AVAILABLE:
        raise RuntimeError("mysql-connector-python not installed")
    return mysql.connector.connect(
        host=os.environ.get("DB_HOST", "localhost"),
        database=os.environ.get("DB_NAME", "anote"),
        user=os.environ.get("DB_USER", "root"),
        password=os.environ.get("DB_PASSWORD", ""),
        autocommit=True,
    )


def get_user_by_email(cnx: Any, email: str) -> dict | None:
    cursor = cnx.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE email = %s LIMIT 1", (email,))
    row = cursor.fetchone()
    cursor.close()
    return row


def create_user(cnx: Any, email: str, password_hash: str, name: str = "") -> int:
    cursor = cnx.cursor()
    cursor.execute(
        "INSERT INTO users (email, password_hash, name, created_at) VALUES (%s, %s, %s, NOW())",
        (email, password_hash, name),
    )
    user_id: int = cursor.lastrowid
    cursor.close()
    return user_id


def get_user_by_id(cnx: Any, user_id: int) -> dict[str, Any] | None:
    cursor = cnx.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE id = %s LIMIT 1", (user_id,))
    row: dict[str, Any] | None = cursor.fetchone()
    cursor.close()
    return row


def upsert_sso_user(cnx: Any, email: str, name: str, sso_provider: str, sso_id: str) -> int:
    """Create or update a user arriving via SSO; return their user_id."""
    cursor = cnx.cursor()
    cursor.execute(
        """
        INSERT INTO users (email, password_hash, name, sso_provider, sso_id, created_at)
        VALUES (%s, '', %s, %s, %s, NOW())
        ON DUPLICATE KEY UPDATE name = VALUES(name), sso_provider = VALUES(sso_provider),
                                sso_id = VALUES(sso_id), updated_at = NOW()
        """,
        (email, name, sso_provider, sso_id),
    )
    cursor.execute("SELECT id FROM users WHERE email = %s LIMIT 1", (email,))
    row = cursor.fetchone()
    cursor.close()
    return int(row[0]) if row else 0


# ── Organizations ──────────────────────────────────────────────────────────────

def create_org(cnx: Any, name: str, slug: str, domain: str | None = None) -> int:
    cursor = cnx.cursor()
    cursor.execute(
        "INSERT INTO organizations (name, slug, domain) VALUES (%s, %s, %s)",
        (name, slug, domain),
    )
    org_id: int = cursor.lastrowid
    cursor.close()
    return org_id


def get_org_by_id(cnx: Any, org_id: int) -> dict[str, Any] | None:
    cursor = cnx.cursor(dictionary=True)
    cursor.execute("SELECT * FROM organizations WHERE id = %s LIMIT 1", (org_id,))
    row: dict[str, Any] | None = cursor.fetchone()
    cursor.close()
    return row


def get_org_by_slug(cnx: Any, slug: str) -> dict[str, Any] | None:
    cursor = cnx.cursor(dictionary=True)
    cursor.execute("SELECT * FROM organizations WHERE slug = %s LIMIT 1", (slug,))
    row: dict[str, Any] | None = cursor.fetchone()
    cursor.close()
    return row


def list_orgs(cnx: Any) -> list[dict[str, Any]]:
    cursor = cnx.cursor(dictionary=True)
    cursor.execute("SELECT * FROM organizations ORDER BY created_at DESC")
    rows: list[dict[str, Any]] = cursor.fetchall()
    cursor.close()
    return rows


def update_org(cnx: Any, org_id: int, fields: dict[str, Any]) -> None:
    allowed = {
        "name", "domain", "sso_provider", "sso_client_id", "sso_client_secret",
        "sso_discovery_url", "mfa_required", "scim_token_hash",
    }
    sets = ", ".join(f"{k} = %s" for k in fields if k in allowed)
    vals = [v for k, v in fields.items() if k in allowed]
    if not sets:
        return
    cursor = cnx.cursor()
    cursor.execute(f"UPDATE organizations SET {sets}, updated_at = NOW() WHERE id = %s", (*vals, org_id))
    cursor.close()


def delete_org(cnx: Any, org_id: int) -> None:
    cursor = cnx.cursor()
    cursor.execute("DELETE FROM organizations WHERE id = %s", (org_id,))
    cursor.close()


# ── Organization members ───────────────────────────────────────────────────────

def get_member(cnx: Any, org_id: int, user_id: int) -> dict[str, Any] | None:
    cursor = cnx.cursor(dictionary=True)
    cursor.execute(
        "SELECT * FROM organization_members WHERE org_id = %s AND user_id = %s LIMIT 1",
        (org_id, user_id),
    )
    row: dict[str, Any] | None = cursor.fetchone()
    cursor.close()
    return row


def list_members(cnx: Any, org_id: int) -> list[dict[str, Any]]:
    cursor = cnx.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT om.*, u.email, u.name, u.sso_provider, u.is_active
        FROM organization_members om
        JOIN users u ON u.id = om.user_id
        WHERE om.org_id = %s
        ORDER BY om.created_at
        """,
        (org_id,),
    )
    rows: list[dict[str, Any]] = cursor.fetchall()
    cursor.close()
    return rows


def upsert_member(
    cnx: Any,
    org_id: int,
    user_id: int,
    role: str = "member",
    provisioned_by: str = "manual",
    scim_external_id: str | None = None,
) -> None:
    cursor = cnx.cursor()
    cursor.execute(
        """
        INSERT INTO organization_members (org_id, user_id, role, provisioned_by, scim_external_id)
        VALUES (%s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE role = VALUES(role), provisioned_by = VALUES(provisioned_by),
                                scim_external_id = VALUES(scim_external_id), updated_at = NOW()
        """,
        (org_id, user_id, role, provisioned_by, scim_external_id),
    )
    cursor.close()


def remove_member(cnx: Any, org_id: int, user_id: int) -> None:
    cursor = cnx.cursor()
    cursor.execute(
        "DELETE FROM organization_members WHERE org_id = %s AND user_id = %s",
        (org_id, user_id),
    )
    cursor.close()


def get_member_by_scim_id(cnx: Any, org_id: int, scim_external_id: str) -> dict[str, Any] | None:
    cursor = cnx.cursor(dictionary=True)
    cursor.execute(
        "SELECT * FROM organization_members WHERE org_id = %s AND scim_external_id = %s LIMIT 1",
        (org_id, scim_external_id),
    )
    row: dict[str, Any] | None = cursor.fetchone()
    cursor.close()
    return row


# ── Identity audit log ─────────────────────────────────────────────────────────

def log_identity_event(
    cnx: Any,
    event_type: str,
    org_id: int | None = None,
    user_id: int | None = None,
    actor: str | None = None,
    detail: dict[str, Any] | None = None,
) -> None:
    import json as _json
    cursor = cnx.cursor()
    cursor.execute(
        "INSERT INTO identity_audit_log (org_id, user_id, event_type, actor, detail) VALUES (%s, %s, %s, %s, %s)",
        (org_id, user_id, event_type, actor, _json.dumps(detail) if detail else None),
    )
    cursor.close()


def list_audit_events(cnx: Any, org_id: int, limit: int = 100) -> list[dict[str, Any]]:
    cursor = cnx.cursor(dictionary=True)
    cursor.execute(
        "SELECT * FROM identity_audit_log WHERE org_id = %s ORDER BY created_at DESC LIMIT %s",
        (org_id, limit),
    )
    rows: list[dict[str, Any]] = cursor.fetchall()
    cursor.close()
    return rows
