"""Opportunity ingestion, qualification scoring, and review-state tracking.

This is the ingestion + qualification slice of the autonomous proposal/RFP
workflow described in GitHub issue #143. It lets a user (or an upstream
portal/inbox connector) submit candidate opportunities, scores them against
a company profile, tracks simple review states and reviewer comments, and
flags missing information before a submission attempt.

Draft generation, citation linking to evidence/knowledge assets, and portal
submission tracking are out of scope for this slice (see PR description).
"""
from __future__ import annotations

import uuid
from typing import Any

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from services.opportunity_scoring import missing_fields, score_opportunity

opportunities_bp = Blueprint("opportunities", __name__, url_prefix="/api/opportunities")

REVIEW_STATES = ("new", "qualifying", "in_review", "approved", "rejected", "submitted")

# In-memory stores, mirroring the pattern used by api_endpoints/workspaces.
_opportunities: dict[str, dict[str, Any]] = {}
_profiles: dict[str, dict[str, Any]] = {}  # keyed by user identity


@opportunities_bp.post("")
@jwt_required()
def create_opportunity() -> tuple:  # type: ignore[type-arg]
    """Ingest a new opportunity (from manual entry, a portal, or an inbox connector)."""
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    if not title:
        return jsonify({"error": "title is required"}), 400

    user_id = get_jwt_identity()
    opp_id = str(uuid.uuid4())
    opportunity = {
        "id": opp_id,
        "userId": user_id,
        "title": title,
        "agency": (data.get("agency") or "").strip(),
        "description": (data.get("description") or "").strip(),
        "deadline": data.get("deadline"),
        "budget": data.get("budget"),
        "tags": data.get("tags") or [],
        "source": data.get("source", "manual"),
        "reviewState": "new",
        "reviewerComments": [],
        "blockers": [],
        "score": None,
    }
    _opportunities[opp_id] = opportunity
    return jsonify(opportunity), 201


@opportunities_bp.get("")
@jwt_required()
def list_opportunities() -> tuple:  # type: ignore[type-arg]
    """List opportunities for the current user, optionally filtered by review state."""
    user_id = get_jwt_identity()
    state_filter = request.args.get("reviewState")
    results = [
        o for o in _opportunities.values()
        if o["userId"] == user_id and (state_filter is None or o["reviewState"] == state_filter)
    ]
    return jsonify({"opportunities": results}), 200


@opportunities_bp.get("/<opp_id>")
@jwt_required()
def get_opportunity(opp_id: str) -> tuple:  # type: ignore[type-arg]
    opp = _opportunities.get(opp_id)
    if not opp or opp["userId"] != get_jwt_identity():
        return jsonify({"error": "Opportunity not found"}), 404
    return jsonify(opp), 200


@opportunities_bp.delete("/<opp_id>")
@jwt_required()
def delete_opportunity(opp_id: str) -> tuple:  # type: ignore[type-arg]
    opp = _opportunities.get(opp_id)
    if not opp or opp["userId"] != get_jwt_identity():
        return jsonify({"error": "Opportunity not found"}), 404
    del _opportunities[opp_id]
    return jsonify({"deleted": True}), 200


@opportunities_bp.put("/profile")
@jwt_required()
def set_profile() -> tuple:  # type: ignore[type-arg]
    """Set the company profile used to qualify opportunities (capabilities, budget range)."""
    data = request.get_json(silent=True) or {}
    user_id = get_jwt_identity()
    profile = {
        "capabilities": data.get("capabilities") or [],
        "minBudget": data.get("minBudget"),
        "maxBudget": data.get("maxBudget"),
    }
    _profiles[user_id] = profile
    return jsonify(profile), 200


@opportunities_bp.get("/profile")
@jwt_required()
def get_profile() -> tuple:  # type: ignore[type-arg]
    user_id = get_jwt_identity()
    return jsonify(_profiles.get(user_id, {"capabilities": [], "minBudget": None, "maxBudget": None})), 200


@opportunities_bp.post("/<opp_id>/score")
@jwt_required()
def score(opp_id: str) -> tuple:  # type: ignore[type-arg]
    """Score an opportunity against the company profile, deadline, and budget fit."""
    user_id = get_jwt_identity()
    opp = _opportunities.get(opp_id)
    if not opp or opp["userId"] != user_id:
        return jsonify({"error": "Opportunity not found"}), 404

    profile = _profiles.get(user_id, {})
    result = score_opportunity(opp, profile)
    opp["score"] = result["score"]
    opp["blockers"] = result["missingFields"]
    opp["reviewState"] = "qualifying" if opp["reviewState"] == "new" else opp["reviewState"]
    return jsonify({"opportunity": opp, "scoring": result}), 200


@opportunities_bp.post("/<opp_id>/review")
@jwt_required()
def update_review(opp_id: str) -> tuple:  # type: ignore[type-arg]
    """Transition review state and/or attach a reviewer comment."""
    opp = _opportunities.get(opp_id)
    if not opp or opp["userId"] != get_jwt_identity():
        return jsonify({"error": "Opportunity not found"}), 404

    data = request.get_json(silent=True) or {}
    new_state = data.get("reviewState")
    comment = data.get("comment")

    if new_state is not None:
        if new_state not in REVIEW_STATES:
            return jsonify({"error": f"reviewState must be one of {REVIEW_STATES}"}), 400
        if new_state == "submitted":
            blockers = missing_fields(opp)
            if blockers:
                return jsonify({
                    "error": "Cannot mark as submitted — required information is missing",
                    "missingFields": blockers,
                }), 422
        opp["reviewState"] = new_state

    if comment:
        opp["reviewerComments"].append({
            "author": get_jwt_identity(),
            "comment": str(comment),
        })

    return jsonify(opp), 200


@opportunities_bp.get("/<opp_id>/blockers")
@jwt_required()
def get_blockers(opp_id: str) -> tuple:  # type: ignore[type-arg]
    """Flag missing information that would block a submission attempt."""
    opp = _opportunities.get(opp_id)
    if not opp or opp["userId"] != get_jwt_identity():
        return jsonify({"error": "Opportunity not found"}), 404
    return jsonify({"blockers": missing_fields(opp)}), 200
