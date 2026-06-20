"""Scoring logic for proposal/RFP opportunities.

Scores an opportunity against a company profile, deadline proximity, and
budget fit, and flags missing information that would block a submission.
This is the first slice of the larger autonomous proposal/RFP workflow
(see GitHub issue #143): opportunity ingestion + qualification scoring.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any

# Required fields an opportunity must have before it can be submitted.
REQUIRED_SUBMISSION_FIELDS = ("title", "agency", "deadline", "budget", "description")


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def _score_keyword_fit(opportunity: dict[str, Any], profile: dict[str, Any]) -> float:
    """Score 0-1 overlap between opportunity text and profile keywords/capabilities."""
    capabilities = [c.lower() for c in profile.get("capabilities", [])]
    if not capabilities:
        return 0.5  # neutral when no profile keywords configured

    text = " ".join(
        str(opportunity.get(field, "")) for field in ("title", "description", "tags")
    ).lower()
    if not text.strip():
        return 0.0

    matches = sum(1 for cap in capabilities if cap in text)
    return min(1.0, matches / len(capabilities))


def _score_deadline(opportunity: dict[str, Any], today: date | None = None) -> float:
    """Score 0-1 based on how much runway remains before the deadline."""
    today = today or date.today()
    deadline = _parse_date(opportunity.get("deadline"))
    if deadline is None:
        return 0.0
    days_left = (deadline - today).days
    if days_left < 0:
        return 0.0
    if days_left >= 30:
        return 1.0
    if days_left == 0:
        return 0.05
    return round(days_left / 30, 4)


def _score_budget_fit(opportunity: dict[str, Any], profile: dict[str, Any]) -> float:
    """Score 0-1 based on whether opportunity budget falls in the company's target range."""
    budget = opportunity.get("budget")
    min_budget = profile.get("minBudget")
    max_budget = profile.get("maxBudget")
    if budget is None or (min_budget is None and max_budget is None):
        return 0.5  # neutral when data is insufficient
    try:
        budget = float(budget)
    except (TypeError, ValueError):
        return 0.0
    if min_budget is not None and budget < float(min_budget):
        return 0.2
    if max_budget is not None and budget > float(max_budget):
        return 0.3
    return 1.0


def missing_fields(opportunity: dict[str, Any]) -> list[str]:
    """Return required submission fields that are missing or empty."""
    missing = []
    for field in REQUIRED_SUBMISSION_FIELDS:
        value = opportunity.get(field)
        if value is None or (isinstance(value, str) and not value.strip()):
            missing.append(field)
    return missing


def score_opportunity(
    opportunity: dict[str, Any],
    profile: dict[str, Any] | None = None,
    today: date | None = None,
) -> dict[str, Any]:
    """Score an opportunity against company profile, deadline, and budget fit.

    Returns a dict with the overall score (0-100), a breakdown of the
    sub-scores, a qualification verdict, and any missing fields that would
    block a submission attempt.
    """
    profile = profile or {}

    fit_score = _score_keyword_fit(opportunity, profile)
    deadline_score = _score_deadline(opportunity, today)
    budget_score = _score_budget_fit(opportunity, profile)

    weights = {"fit": 0.5, "deadline": 0.25, "budget": 0.25}
    overall = (
        fit_score * weights["fit"]
        + deadline_score * weights["deadline"]
        + budget_score * weights["budget"]
    )
    overall_pct = round(overall * 100, 2)

    missing = missing_fields(opportunity)
    qualifies = overall_pct >= 50 and deadline_score > 0 and not missing

    return {
        "score": overall_pct,
        "breakdown": {
            "fit": round(fit_score * 100, 2),
            "deadline": round(deadline_score * 100, 2),
            "budget": round(budget_score * 100, 2),
        },
        "qualifies": qualifies,
        "missingFields": missing,
    }
