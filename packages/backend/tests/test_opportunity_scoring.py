"""Unit tests for services/opportunity_scoring.py."""
from datetime import date, timedelta

from services.opportunity_scoring import missing_fields, score_opportunity


def _opp(**overrides):
    base = {
        "title": "Road Maintenance RFP",
        "agency": "City of Springfield",
        "description": "Pothole repair and road maintenance services.",
        "deadline": (date.today() + timedelta(days=15)).isoformat(),
        "budget": 50000,
        "tags": ["construction"],
    }
    base.update(overrides)
    return base


def test_missing_fields_all_present():
    assert missing_fields(_opp()) == []


def test_missing_fields_detects_blank_and_none():
    opp = _opp(budget=None, description="   ")
    missing = missing_fields(opp)
    assert "budget" in missing
    assert "description" in missing
    assert "title" not in missing


def test_score_opportunity_good_match_qualifies():
    profile = {"capabilities": ["construction", "roads"], "minBudget": 1000, "maxBudget": 100000}
    result = score_opportunity(_opp(), profile)
    assert result["qualifies"] is True
    assert result["score"] > 50
    assert result["missingFields"] == []


def test_score_opportunity_no_profile_is_neutral_but_not_blocked_by_fit():
    result = score_opportunity(_opp(), {})
    # fit defaults neutral (0.5), deadline/budget also default reasonably
    assert 0 <= result["score"] <= 100


def test_score_opportunity_budget_out_of_range_lowers_score():
    profile = {"capabilities": ["construction"], "minBudget": 100000, "maxBudget": 500000}
    result = score_opportunity(_opp(budget=50000), profile)
    assert result["breakdown"]["budget"] < 100


def test_score_opportunity_expired_deadline_never_qualifies():
    profile = {"capabilities": ["construction"], "minBudget": 0, "maxBudget": 1000000}
    expired = _opp(deadline=(date.today() - timedelta(days=1)).isoformat())
    result = score_opportunity(expired, profile)
    assert result["breakdown"]["deadline"] == 0
    assert result["qualifies"] is False


def test_score_opportunity_missing_deadline_scores_zero_deadline():
    profile = {"capabilities": ["construction"]}
    result = score_opportunity(_opp(deadline=None), profile)
    assert result["breakdown"]["deadline"] == 0


def test_score_opportunity_flags_missing_fields_blocks_qualification():
    profile = {"capabilities": ["construction"], "minBudget": 0, "maxBudget": 1000000}
    result = score_opportunity(_opp(agency=""), profile)
    assert "agency" in result["missingFields"]
    assert result["qualifies"] is False
