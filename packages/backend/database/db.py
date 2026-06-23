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


# ── Data governance ────────────────────────────────────────────────────────────

def list_data_policies(cnx: Any, org_id: int) -> list[dict[str, Any]]:
    cursor = cnx.cursor(dictionary=True)
    cursor.execute("SELECT * FROM data_policies WHERE org_id = %s ORDER BY data_type", (org_id,))
    rows: list[dict[str, Any]] = cursor.fetchall()
    cursor.close()
    return rows


def get_data_policy(cnx: Any, org_id: int, data_type: str) -> dict[str, Any] | None:
    cursor = cnx.cursor(dictionary=True)
    cursor.execute(
        "SELECT * FROM data_policies WHERE org_id = %s AND data_type = %s LIMIT 1",
        (org_id, data_type),
    )
    row: dict[str, Any] | None = cursor.fetchone()
    cursor.close()
    return row


def upsert_data_policy(
    cnx: Any,
    org_id: int,
    data_type: str,
    retention_days: int,
    auto_delete: bool,
    classification: str,
    actor_id: int | None = None,
) -> None:
    cursor = cnx.cursor()
    cursor.execute(
        """
        INSERT INTO data_policies
            (org_id, data_type, retention_days, auto_delete, classification, created_by, updated_by)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            retention_days = VALUES(retention_days),
            auto_delete    = VALUES(auto_delete),
            classification = VALUES(classification),
            updated_by     = VALUES(updated_by),
            updated_at     = NOW()
        """,
        (org_id, data_type, retention_days, 1 if auto_delete else 0, classification, actor_id, actor_id),
    )
    cursor.close()


def delete_data_policy(cnx: Any, org_id: int, data_type: str) -> None:
    cursor = cnx.cursor()
    cursor.execute(
        "DELETE FROM data_policies WHERE org_id = %s AND data_type = %s",
        (org_id, data_type),
    )
    cursor.close()


# ── Legal holds ────────────────────────────────────────────────────────────────

def list_legal_holds(cnx: Any, org_id: int, include_released: bool = False) -> list[dict[str, Any]]:
    cursor = cnx.cursor(dictionary=True)
    if include_released:
        cursor.execute(
            "SELECT * FROM legal_holds WHERE org_id = %s ORDER BY created_at DESC",
            (org_id,),
        )
    else:
        cursor.execute(
            "SELECT * FROM legal_holds WHERE org_id = %s AND released_at IS NULL ORDER BY created_at DESC",
            (org_id,),
        )
    rows: list[dict[str, Any]] = cursor.fetchall()
    cursor.close()
    return rows


def get_legal_hold(cnx: Any, hold_id: int) -> dict[str, Any] | None:
    cursor = cnx.cursor(dictionary=True)
    cursor.execute("SELECT * FROM legal_holds WHERE id = %s LIMIT 1", (hold_id,))
    row: dict[str, Any] | None = cursor.fetchone()
    cursor.close()
    return row


def create_legal_hold(
    cnx: Any,
    org_id: int,
    resource_type: str,
    resource_id: str,
    reason: str,
    placed_by: int | None,
    expires_at: str | None = None,
) -> int:
    cursor = cnx.cursor()
    cursor.execute(
        """
        INSERT INTO legal_holds (org_id, resource_type, resource_id, reason, placed_by, expires_at)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (org_id, resource_type, resource_id, reason, placed_by, expires_at),
    )
    hold_id: int = cursor.lastrowid
    cursor.close()
    return hold_id


def release_legal_hold(cnx: Any, hold_id: int, released_by: int) -> None:
    cursor = cnx.cursor()
    cursor.execute(
        "UPDATE legal_holds SET released_by = %s, released_at = NOW() WHERE id = %s",
        (released_by, hold_id),
    )
    cursor.close()


def has_active_legal_hold(cnx: Any, org_id: int, resource_type: str, resource_id: str) -> bool:
    cursor = cnx.cursor()
    cursor.execute(
        """
        SELECT COUNT(*) FROM legal_holds
        WHERE org_id = %s AND resource_type = %s AND resource_id = %s AND released_at IS NULL
        """,
        (org_id, resource_type, resource_id),
    )
    row = cursor.fetchone()
    cursor.close()
    return bool(row and row[0] > 0)


# ── Export requests ────────────────────────────────────────────────────────────

def list_export_requests(cnx: Any, org_id: int) -> list[dict[str, Any]]:
    cursor = cnx.cursor(dictionary=True)
    cursor.execute(
        "SELECT * FROM export_requests WHERE org_id = %s ORDER BY created_at DESC",
        (org_id,),
    )
    rows: list[dict[str, Any]] = cursor.fetchall()
    cursor.close()
    return rows


def get_export_request(cnx: Any, req_id: int) -> dict[str, Any] | None:
    cursor = cnx.cursor(dictionary=True)
    cursor.execute("SELECT * FROM export_requests WHERE id = %s LIMIT 1", (req_id,))
    row: dict[str, Any] | None = cursor.fetchone()
    cursor.close()
    return row


def create_export_request(
    cnx: Any,
    org_id: int,
    requested_by: int,
    data_types: list[str],
    scope: dict[str, Any] | None = None,
) -> int:
    import json as _json
    cursor = cnx.cursor()
    cursor.execute(
        """
        INSERT INTO export_requests (org_id, requested_by, data_types, scope)
        VALUES (%s, %s, %s, %s)
        """,
        (org_id, requested_by, _json.dumps(data_types), _json.dumps(scope) if scope else None),
    )
    req_id: int = cursor.lastrowid
    cursor.close()
    return req_id


def update_export_status(
    cnx: Any,
    req_id: int,
    status: str,
    download_url: str | None = None,
    fulfilled_by: int | None = None,
) -> None:
    cursor = cnx.cursor()
    cursor.execute(
        """
        UPDATE export_requests
        SET status = %s, download_url = %s, fulfilled_by = %s,
            fulfilled_at = IF(%s = 'fulfilled', NOW(), fulfilled_at),
            updated_at = NOW()
        WHERE id = %s
        """,
        (status, download_url, fulfilled_by, status, req_id),
    )
    cursor.close()


# ── Resource classifications ───────────────────────────────────────────────────

def list_resource_classifications(cnx: Any, org_id: int) -> list[dict[str, Any]]:
    cursor = cnx.cursor(dictionary=True)
    cursor.execute(
        "SELECT * FROM resource_classifications WHERE org_id = %s ORDER BY resource_type, resource_id",
        (org_id,),
    )
    rows: list[dict[str, Any]] = cursor.fetchall()
    cursor.close()
    return rows


def get_resource_classification(
    cnx: Any, org_id: int, resource_type: str, resource_id: str
) -> dict[str, Any] | None:
    cursor = cnx.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT * FROM resource_classifications
        WHERE org_id = %s AND resource_type = %s AND resource_id = %s LIMIT 1
        """,
        (org_id, resource_type, resource_id),
    )
    row: dict[str, Any] | None = cursor.fetchone()
    cursor.close()
    return row


def upsert_resource_classification(
    cnx: Any,
    org_id: int,
    resource_type: str,
    resource_id: str,
    classification: str,
    tagged_by: int | None = None,
) -> int:
    cursor = cnx.cursor()
    cursor.execute(
        """
        INSERT INTO resource_classifications (org_id, resource_type, resource_id, classification, tagged_by)
        VALUES (%s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE classification = VALUES(classification), tagged_by = VALUES(tagged_by)
        """,
        (org_id, resource_type, resource_id, classification, tagged_by),
    )
    row_id: int = cursor.lastrowid or 0
    cursor.close()
    return row_id


def delete_resource_classification(cnx: Any, cls_id: int, org_id: int) -> None:
    cursor = cnx.cursor()
    cursor.execute(
        "DELETE FROM resource_classifications WHERE id = %s AND org_id = %s",
        (cls_id, org_id),
    )
    cursor.close()


# ── Governance audit log ───────────────────────────────────────────────────────

def log_governance_event(
    cnx: Any,
    org_id: int,
    action: str,
    actor_id: int | None = None,
    resource: str | None = None,
    detail: dict[str, Any] | None = None,
) -> None:
    import json as _json
    cursor = cnx.cursor()
    cursor.execute(
        "INSERT INTO governance_audit_log (org_id, actor_id, action, resource, detail) VALUES (%s, %s, %s, %s, %s)",
        (org_id, actor_id, action, resource, _json.dumps(detail) if detail else None),
    )
    cursor.close()


def list_governance_audit(cnx: Any, org_id: int, limit: int = 100) -> list[dict[str, Any]]:
    cursor = cnx.cursor(dictionary=True)
    cursor.execute(
        "SELECT * FROM governance_audit_log WHERE org_id = %s ORDER BY created_at DESC LIMIT %s",
        (org_id, limit),
    )
    rows: list[dict[str, Any]] = cursor.fetchall()
    cursor.close()
    return rows
