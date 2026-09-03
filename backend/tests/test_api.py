"""Tests for the HTTP boundary: the error envelope, status codes, and the
list/get/patch contracts in `app.routers.referrals` and `app.main`.

This is the layer normalisation/duplicate-matcher/status-transition unit
tests can't cover: whether a bad query param, a bad request body, or an
out-of-range page_size actually comes back as the documented
`{"error": {code, message, field}}` shape instead of FastAPI's default
`{"detail": [...]}, and whether the right status code is attached.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import app.main as main_module
from app.db import get_connection


@pytest.fixture()
def client(tmp_path, monkeypatch):
    test_db_path = tmp_path / "test.sqlite3"
    monkeypatch.setattr(main_module, "get_connection", lambda: get_connection(test_db_path))
    with TestClient(main_module.app) as test_client:
        yield test_client


class TestListReferrals:
    def test_seeds_and_lists_referrals_on_first_boot(self, client):
        response = client.get("/referrals")

        assert response.status_code == 200
        body = response.json()
        assert "data" in body and "meta" in body
        # 37 seed records normalize cleanly (no NormalizationError skips);
        # a default page_size of 20 caps the first page below that.
        assert body["meta"]["total"] == 37
        assert len(body["data"]) == 20

    def test_invalid_status_returns_enveloped_422(self, client):
        response = client.get("/referrals", params={"status": "bogus"})

        assert response.status_code == 422
        error = response.json()["error"]
        assert error["code"] == "validation_error"
        assert error["field"] == "status"
        assert isinstance(error["message"], str) and error["message"]

    def test_invalid_sort_is_rejected_rather_than_silently_ascending(self, client):
        response = client.get("/referrals", params={"sort": "banana"})

        assert response.status_code == 422
        error = response.json()["error"]
        assert error["code"] == "validation_error"
        assert error["field"] == "sort"

    def test_page_size_over_the_limit_is_rejected(self, client):
        response = client.get("/referrals", params={"page_size": 9999})

        assert response.status_code == 422
        assert response.json()["error"]["field"] == "page_size"

    def test_valid_sort_values_are_accepted(self, client):
        for sort in ("-received_at", "received_at"):
            response = client.get("/referrals", params={"sort": sort})
            assert response.status_code == 200


class TestGetReferral:
    def test_get_existing_referral_includes_duplicate_group(self, client):
        listing = client.get("/referrals").json()
        referral_id = listing["data"][0]["id"]

        response = client.get(f"/referrals/{referral_id}")

        assert response.status_code == 200
        assert "duplicate_group" in response.json()["data"]

    def test_get_missing_referral_returns_enveloped_404(self, client):
        response = client.get("/referrals/does_not:exist")

        assert response.status_code == 404
        assert response.json()["error"]["code"] == "not_found"


class TestUpdateStatus:
    def _new_referral_id(self, client) -> str:
        listing = client.get("/referrals", params={"status": "new"}).json()
        return listing["data"][0]["id"]

    def test_valid_transition_updates_status(self, client):
        referral_id = self._new_referral_id(client)

        response = client.patch(f"/referrals/{referral_id}/status", json={"status": "in_review"})

        assert response.status_code == 200
        assert response.json()["data"]["status"] == "in_review"

    def test_disallowed_transition_returns_enveloped_409(self, client):
        referral_id = self._new_referral_id(client)

        response = client.patch(f"/referrals/{referral_id}/status", json={"status": "accepted"})

        assert response.status_code == 409
        error = response.json()["error"]
        assert error["code"] == "invalid_transition"
        assert error["field"] == "status"

    def test_invalid_status_value_returns_enveloped_422(self, client):
        referral_id = self._new_referral_id(client)

        response = client.patch(f"/referrals/{referral_id}/status", json={"status": "bogus"})

        assert response.status_code == 422
        assert response.json()["error"]["field"] == "status"

    def test_malformed_json_body_returns_enveloped_422(self, client):
        referral_id = self._new_referral_id(client)

        response = client.patch(
            f"/referrals/{referral_id}/status",
            content="not json",
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 422
        assert response.json()["error"]["code"] == "validation_error"

    def test_updating_a_missing_referral_returns_404_not_a_transition_error(self, client):
        response = client.patch("/referrals/does_not:exist/status", json={"status": "in_review"})

        assert response.status_code == 404
        assert response.json()["error"]["code"] == "not_found"
