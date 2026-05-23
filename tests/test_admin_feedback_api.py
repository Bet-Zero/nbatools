from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from nbatools.api import app
from nbatools.query_feedback_review import FeedbackReviewError

pytestmark = pytest.mark.api


def test_admin_feedback_groups_disabled_by_default(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("NBATOOLS_ADMIN_FEEDBACK_ENABLED", raising=False)
    monkeypatch.delenv("NBATOOLS_ADMIN_TOKEN", raising=False)
    client = TestClient(app)

    response = client.get("/api/admin/feedback/groups")

    assert response.status_code == 404
    assert response.json()["error"] == "admin_feedback_disabled"


def test_admin_feedback_requires_token_when_configured(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("NBATOOLS_ADMIN_FEEDBACK_ENABLED", "true")
    monkeypatch.setenv("NBATOOLS_ADMIN_TOKEN", "secret")
    client = TestClient(app)

    response = client.get("/api/admin/feedback/groups")
    authorized = client.get(
        "/api/admin/feedback/groups",
        headers={"X-NBATools-Admin-Token": "secret"},
    )

    assert response.status_code == 401
    assert response.json()["error"] == "admin_token_required"
    assert authorized.status_code == 500
    assert authorized.json()["error"] == "feedback_review_error"


def test_admin_feedback_requires_token_config_in_deployed_env(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("NBATOOLS_ADMIN_FEEDBACK_ENABLED", "true")
    monkeypatch.delenv("NBATOOLS_ADMIN_TOKEN", raising=False)
    monkeypatch.setenv("VERCEL_ENV", "preview")
    client = TestClient(app)

    response = client.get("/api/admin/feedback/groups")

    assert response.status_code == 403
    assert response.json()["error"] == "admin_token_not_configured"


def test_admin_feedback_list_groups_with_overlay_joined(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("NBATOOLS_ADMIN_FEEDBACK_ENABLED", "true")
    monkeypatch.setenv("NBATOOLS_ADMIN_TOKEN", "secret")

    captured = {}

    def fake_list_feedback_groups(filters=None):
        captured["filters"] = filters
        return {
            "ok": True,
            "group_count": 1,
            "groups": [
                {
                    "group_id": "qfg_test",
                    "count": 2,
                    "representative_query": "Jokic last 10 games",
                    "triage_overlay": {
                        "group_id": "qfg_test",
                        "review_status": "reviewed",
                        "triage_decision": "bug",
                    },
                }
            ],
        }

    monkeypatch.setattr("nbatools.api.list_feedback_groups", fake_list_feedback_groups)
    client = TestClient(app)

    response = client.get(
        "/api/admin/feedback/groups?review_status=reviewed&triage_decision=bug"
        "&feedback_type=wrong_answer&feedback_source=user_submitted&route=season_leaders"
        "&status=ok&reason=none",
        headers={"X-NBATools-Admin-Token": "secret"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["groups"][0]["triage_overlay"]["triage_decision"] == "bug"
    filters = captured["filters"]
    assert filters.review_statuses == {"reviewed"}
    assert filters.triage_decisions == {"bug"}
    assert filters.feedback_types == {"wrong_answer"}
    assert filters.sources == {"user_submitted"}
    assert filters.routes == {"season_leaders"}
    assert filters.statuses == {"ok"}
    assert filters.reasons == {"none"}


def test_admin_feedback_group_detail(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("NBATOOLS_ADMIN_FEEDBACK_ENABLED", "true")
    monkeypatch.setenv("NBATOOLS_ADMIN_TOKEN", "secret")
    monkeypatch.setattr(
        "nbatools.api.get_feedback_group_detail",
        lambda group_id, filters=None: {
            "ok": True,
            "group": {"group_id": group_id, "count": 1},
            "records": [{"id": "qfb_test"}],
            "triage_overlay": {"group_id": group_id, "review_status": "new"},
            "handoff_summary": "Group: qfg_test",
        },
    )
    client = TestClient(app)

    response = client.get(
        "/api/admin/feedback/groups/qfg_test",
        headers={"X-NBATools-Admin-Token": "secret"},
    )

    assert response.status_code == 200
    assert response.json()["records"][0]["id"] == "qfb_test"


def test_admin_feedback_read_and_save_triage(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("NBATOOLS_ADMIN_FEEDBACK_ENABLED", "true")
    monkeypatch.setenv("NBATOOLS_ADMIN_TOKEN", "secret")
    monkeypatch.setattr(
        "nbatools.api.read_triage_overlay",
        lambda group_id: {
            "group_id": group_id,
            "review_status": "new",
            "triage_decision": None,
        },
    )
    monkeypatch.setattr(
        "nbatools.api.get_feedback_group_detail",
        lambda group_id, filters=None: {"ok": True, "group": {"group_id": group_id}},
    )

    def fake_write_triage_overlay(group_id, body, existing_group=None):
        assert existing_group == {"group_id": group_id}
        return {
            "group_id": group_id,
            "review_status": body["review_status"],
            "triage_decision": body["triage_decision"],
        }

    monkeypatch.setattr("nbatools.api.write_triage_overlay", fake_write_triage_overlay)
    client = TestClient(app)

    read_response = client.get(
        "/api/admin/feedback/groups/qfg_test/triage",
        headers={"X-NBATools-Admin-Token": "secret"},
    )
    write_response = client.put(
        "/api/admin/feedback/groups/qfg_test/triage",
        headers={"X-NBATools-Admin-Token": "secret"},
        json={"review_status": "reviewed", "triage_decision": "bug"},
    )

    assert read_response.status_code == 200
    assert read_response.json()["triage_overlay"]["review_status"] == "new"
    assert write_response.status_code == 200
    assert write_response.json()["triage_overlay"]["triage_decision"] == "bug"


def test_admin_feedback_storage_errors_are_json(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("NBATOOLS_ADMIN_FEEDBACK_ENABLED", "true")
    monkeypatch.setenv("NBATOOLS_ADMIN_TOKEN", "secret")

    def fail(filters=None):
        raise FeedbackReviewError("store down")

    monkeypatch.setattr("nbatools.api.list_feedback_groups", fail)
    client = TestClient(app)

    response = client.get(
        "/api/admin/feedback/groups",
        headers={"X-NBATools-Admin-Token": "secret"},
    )

    assert response.status_code == 500
    assert response.json()["error"] == "feedback_review_error"
