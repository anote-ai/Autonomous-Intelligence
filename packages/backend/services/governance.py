"""Data governance: retention policies, legal holds, export, classification validation."""
from __future__ import annotations

from typing import Any

VALID_DATA_TYPES = frozenset({
    "runs", "artifacts", "logs", "prompts", "connector_data", "documents", "chats",
})

VALID_CLASSIFICATIONS = frozenset({"public", "internal", "confidential", "sensitive"})

VALID_EXPORT_STATUSES = frozenset({"pending", "processing", "ready", "fulfilled", "failed"})

CLASSIFICATION_RANK: dict[str, int] = {
    "public": 0,
    "internal": 1,
    "confidential": 2,
    "sensitive": 3,
}

DEFAULT_RETENTION_DAYS = 365
MAX_RETENTION_DAYS = 36500  # 100 years


def validate_policy(
    data_type: str,
    retention_days: int | None,
    classification: str | None,
) -> str | None:
    """Return an error string or None if valid."""
    if data_type not in VALID_DATA_TYPES:
        return f"data_type must be one of: {sorted(VALID_DATA_TYPES)}"
    if retention_days is None or not isinstance(retention_days, int):
        return "retention_days must be an integer"
    if retention_days < 1 or retention_days > MAX_RETENTION_DAYS:
        return f"retention_days must be between 1 and {MAX_RETENTION_DAYS}"
    if classification and classification not in VALID_CLASSIFICATIONS:
        return f"classification must be one of: {sorted(VALID_CLASSIFICATIONS)}"
    return None


def validate_hold(resource_type: str, resource_id: str, reason: str) -> str | None:
    if not resource_type or len(resource_type) > 100:
        return "resource_type is required (max 100 chars)"
    if not resource_id or len(resource_id) > 255:
        return "resource_id is required (max 255 chars)"
    if not reason or not reason.strip():
        return "reason is required"
    return None


def validate_classification(resource_type: str, resource_id: str, classification: str) -> str | None:
    if not resource_type or len(resource_type) > 100:
        return "resource_type is required (max 100 chars)"
    if not resource_id or len(resource_id) > 255:
        return "resource_id is required (max 255 chars)"
    if classification not in VALID_CLASSIFICATIONS:
        return f"classification must be one of: {sorted(VALID_CLASSIFICATIONS)}"
    return None


def evaluate_deletion_allowed(
    cnx: Any, org_id: int, resource_type: str, resource_id: str
) -> dict[str, Any]:
    """Check whether a resource may be deleted under governance rules."""
    from database.db import has_active_legal_hold
    blocked_by_hold = has_active_legal_hold(cnx, org_id, resource_type, resource_id)
    return {
        "allowed": not blocked_by_hold,
        "blocked_by_hold": blocked_by_hold,
        "resource_type": resource_type,
        "resource_id": resource_id,
    }


def classification_rank(classification: str) -> int:
    return CLASSIFICATION_RANK.get(classification, 0)
