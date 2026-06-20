"""Tests for opportunity ingestion, scoring, and review-state endpoints."""
from datetime import date, timedelta


def _create_opportunity(client, auth_headers, **overrides):
    payload = {
        "title": "City of Springfield Road Maintenance RFP",
        "agency": "City of Springfield",
        "description": "Road maintenance and pothole repair services.",
        "deadline": (date.today() + timedelta(days=20)).isoformat(),
        "budget": 50000,
        "tags": ["construction", "maintenance"],
    }
    payload.update(overrides)
    return client.post("/api/opportunities", json=payload, headers=auth_headers)


def test_create_opportunity_requires_auth(client):
    resp = client.post("/api/opportunities", json={"title": "x"})
    assert resp.status_code == 401


def test_create_opportunity_requires_title(client, auth_headers):
    resp = client.post("/api/opportunities", json={}, headers=auth_headers)
    assert resp.status_code == 400


def test_create_and_list_opportunity(client, auth_headers):
    resp = _create_opportunity(client, auth_headers)
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["reviewState"] == "new"
    assert body["title"] == "City of Springfield Road Maintenance RFP"

    listed = client.get("/api/opportunities", headers=auth_headers)
    assert listed.status_code == 200
    assert any(o["id"] == body["id"] for o in listed.get_json()["opportunities"])


def test_get_and_delete_opportunity(client, auth_headers):
    created = _create_opportunity(client, auth_headers).get_json()
    opp_id = created["id"]

    got = client.get(f"/api/opportunities/{opp_id}", headers=auth_headers)
    assert got.status_code == 200

    deleted = client.delete(f"/api/opportunities/{opp_id}", headers=auth_headers)
    assert deleted.status_code == 200

    missing = client.get(f"/api/opportunities/{opp_id}", headers=auth_headers)
    assert missing.status_code == 404


def test_get_opportunity_not_found(client, auth_headers):
    resp = client.get("/api/opportunities/does-not-exist", headers=auth_headers)
    assert resp.status_code == 404


def test_profile_set_and_get(client, auth_headers):
    set_resp = client.put(
        "/api/opportunities/profile",
        json={"capabilities": ["construction", "roads"], "minBudget": 10000, "maxBudget": 200000},
        headers=auth_headers,
    )
    assert set_resp.status_code == 200

    get_resp = client.get("/api/opportunities/profile", headers=auth_headers)
    assert get_resp.status_code == 200
    assert "construction" in get_resp.get_json()["capabilities"]


def test_score_opportunity_qualifies_with_good_fit(client, auth_headers):
    client.put(
        "/api/opportunities/profile",
        json={"capabilities": ["construction", "maintenance"], "minBudget": 1000, "maxBudget": 100000},
        headers=auth_headers,
    )
    created = _create_opportunity(client, auth_headers).get_json()
    resp = client.post(f"/api/opportunities/{created['id']}/score", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["scoring"]["qualifies"] is True
    assert body["scoring"]["score"] > 50
    assert body["opportunity"]["reviewState"] == "qualifying"


def test_score_opportunity_flags_missing_fields(client, auth_headers):
    created = _create_opportunity(client, auth_headers, budget=None, description="").get_json()
    resp = client.post(f"/api/opportunities/{created['id']}/score", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.get_json()
    assert "budget" in body["scoring"]["missingFields"]
    assert "description" in body["scoring"]["missingFields"]
    assert body["scoring"]["qualifies"] is False


def test_score_opportunity_past_deadline_scores_zero_deadline(client, auth_headers):
    created = _create_opportunity(
        client, auth_headers, deadline=(date.today() - timedelta(days=5)).isoformat()
    ).get_json()
    resp = client.post(f"/api/opportunities/{created['id']}/score", headers=auth_headers)
    body = resp.get_json()
    assert body["scoring"]["breakdown"]["deadline"] == 0
    assert body["scoring"]["qualifies"] is False


def test_score_opportunity_not_found(client, auth_headers):
    resp = client.post("/api/opportunities/nope/score", headers=auth_headers)
    assert resp.status_code == 404


def test_update_review_state(client, auth_headers):
    created = _create_opportunity(client, auth_headers).get_json()
    resp = client.post(
        f"/api/opportunities/{created['id']}/review",
        json={"reviewState": "in_review", "comment": "Looks promising, need budget confirmation."},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["reviewState"] == "in_review"
    assert len(body["reviewerComments"]) == 1


def test_update_review_invalid_state(client, auth_headers):
    created = _create_opportunity(client, auth_headers).get_json()
    resp = client.post(
        f"/api/opportunities/{created['id']}/review",
        json={"reviewState": "bogus"},
        headers=auth_headers,
    )
    assert resp.status_code == 400


def test_cannot_submit_with_missing_fields(client, auth_headers):
    created = _create_opportunity(client, auth_headers, budget=None).get_json()
    resp = client.post(
        f"/api/opportunities/{created['id']}/review",
        json={"reviewState": "submitted"},
        headers=auth_headers,
    )
    assert resp.status_code == 422
    assert "budget" in resp.get_json()["missingFields"]


def test_can_submit_when_complete(client, auth_headers):
    created = _create_opportunity(client, auth_headers).get_json()
    resp = client.post(
        f"/api/opportunities/{created['id']}/review",
        json={"reviewState": "submitted"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.get_json()["reviewState"] == "submitted"


def test_get_blockers(client, auth_headers):
    created = _create_opportunity(client, auth_headers, agency="").get_json()
    resp = client.get(f"/api/opportunities/{created['id']}/blockers", headers=auth_headers)
    assert resp.status_code == 200
    assert "agency" in resp.get_json()["blockers"]


def test_list_filters_by_review_state(client, auth_headers):
    _create_opportunity(client, auth_headers, title="Opp A")
    second = _create_opportunity(client, auth_headers, title="Opp B").get_json()
    client.post(
        f"/api/opportunities/{second['id']}/review",
        json={"reviewState": "approved"},
        headers=auth_headers,
    )
    resp = client.get("/api/opportunities?reviewState=approved", headers=auth_headers)
    titles = [o["title"] for o in resp.get_json()["opportunities"]]
    assert titles == ["Opp B"]
