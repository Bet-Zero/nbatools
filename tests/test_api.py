"""Tests for the nbatools HTTP API layer.

Validates that:
- /health returns status and version
- /routes returns available structured route names
- /query executes natural-language queries and returns structured JSON
- /structured-query executes route-based queries and returns structured JSON
- /freshness returns structured freshness status
- trust/status metadata is preserved in API responses
- no-result / error responses have correct shape
- invalid route names are rejected with helpful errors
- bad request bodies are rejected
"""

from unittest.mock import patch

from fastapi.testclient import TestClient

from nbatools.api import app
from nbatools.commands.freshness import FreshnessInfo, FreshnessStatus, SeasonFreshness
from nbatools.commands.structured_results import (
    LeaderboardResult,
    NoResult,
    SummaryResult,
)
from nbatools.query_service import QueryResult

client = TestClient(app)


# ---------------------------------------------------------------------------
# /health
# ---------------------------------------------------------------------------


class TestHealth:
    def test_health_returns_ok(self):
        resp = client.get("/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert "version" in body

    def test_health_version_matches_package(self):
        from nbatools import __version__

        resp = client.get("/health")
        assert resp.json()["version"] == __version__


# ---------------------------------------------------------------------------
# /routes
# ---------------------------------------------------------------------------


class TestRoutes:
    def test_routes_returns_sorted_list(self):
        resp = client.get("/routes")
        assert resp.status_code == 200
        body = resp.json()
        routes = body["routes"]
        assert isinstance(routes, list)
        assert routes == sorted(routes)
        assert "player_game_summary" in routes
        assert "season_leaders" in routes

    def test_routes_includes_all_valid_routes(self):
        from nbatools.query_service import VALID_ROUTES

        resp = client.get("/routes")
        returned = set(resp.json()["routes"])
        assert returned == VALID_ROUTES


# ---------------------------------------------------------------------------
# /query — natural language
# ---------------------------------------------------------------------------


class TestNaturalQuery:
    def _mock_result(self, **overrides):
        """Build a mock QueryResult for natural query tests."""
        result = SummaryResult(
            query_class="summary",
            result_status="ok",
            current_through="2026-04-10",
            notes=["test note"],
            caveats=["test caveat"],
        )
        defaults = dict(
            result=result,
            metadata={"query_text": "test", "route": "player_game_summary"},
            query="test query",
            route="player_game_summary",
        )
        defaults.update(overrides)
        return QueryResult(**defaults)

    @patch("nbatools.api.execute_natural_query")
    def test_natural_query_basic(self, mock_exec):
        mock_exec.return_value = self._mock_result()
        resp = client.post("/query", json={"query": "Jokic last 10 games"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        assert body["result_status"] == "ok"
        assert body["route"] == "player_game_summary"
        assert body["query"] == "test query"
        mock_exec.assert_called_once_with("Jokic last 10 games")

    @patch("nbatools.api.execute_natural_query")
    def test_natural_query_preserves_trust_metadata(self, mock_exec):
        mock_exec.return_value = self._mock_result()
        resp = client.post("/query", json={"query": "anything"})
        body = resp.json()
        assert body["current_through"] == "2026-04-10"
        assert body["notes"] == ["test note"]
        assert body["caveats"] == ["test caveat"]

    @patch("nbatools.api.execute_natural_query")
    def test_natural_query_no_result(self, mock_exec):
        no_result = NoResult(
            query_class="unknown",
            reason="unrouted",
            result_status="no_result",
            result_reason="unrouted",
        )
        mock_exec.return_value = QueryResult(
            result=no_result,
            metadata={"query_text": "gibberish"},
            query="gibberish",
            route=None,
        )
        resp = client.post("/query", json={"query": "gibberish"})
        body = resp.json()
        assert body["ok"] is False
        assert body["result_status"] == "no_result"
        assert body["result_reason"] == "unrouted"
        assert body["route"] is None

    def test_natural_query_missing_body(self):
        resp = client.post("/query", json={})
        assert resp.status_code == 422

    def test_natural_query_wrong_content_type(self):
        resp = client.post("/query", content="plain text")
        assert resp.status_code == 422

    @patch("nbatools.api.execute_natural_query")
    def test_natural_query_result_dict_in_response(self, mock_exec):
        mock_exec.return_value = self._mock_result()
        resp = client.post("/query", json={"query": "test"})
        body = resp.json()
        assert "result" in body
        assert isinstance(body["result"], dict)
        # SummaryResult.to_dict() includes query_class and sections
        assert body["result"].get("query_class") == "summary"


# ---------------------------------------------------------------------------
# /structured-query
# ---------------------------------------------------------------------------


class TestStructuredQuery:
    def _mock_result(self, **overrides):
        result = LeaderboardResult(
            query_class="leaderboard",
            result_status="ok",
            current_through="2026-04-10",
            notes=["leader note"],
            caveats=[],
        )
        defaults = dict(
            result=result,
            metadata={"route": "season_leaders"},
            query="structured:season_leaders",
            route="season_leaders",
        )
        defaults.update(overrides)
        return QueryResult(**defaults)

    @patch("nbatools.api.execute_structured_query")
    def test_structured_query_basic(self, mock_exec):
        mock_exec.return_value = self._mock_result()
        resp = client.post(
            "/structured-query",
            json={"route": "season_leaders", "kwargs": {"season": "2025-26"}},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        assert body["result_status"] == "ok"
        assert body["route"] == "season_leaders"
        mock_exec.assert_called_once_with("season_leaders", season="2025-26")

    @patch("nbatools.api.execute_structured_query")
    def test_structured_query_preserves_trust_metadata(self, mock_exec):
        mock_exec.return_value = self._mock_result()
        resp = client.post(
            "/structured-query",
            json={"route": "season_leaders", "kwargs": {}},
        )
        body = resp.json()
        assert body["current_through"] == "2026-04-10"
        assert body["notes"] == ["leader note"]
        assert body["caveats"] == []

    def test_structured_query_invalid_route(self):
        resp = client.post(
            "/structured-query",
            json={"route": "nonexistent_route", "kwargs": {}},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is False
        assert body["result_status"] == "no_result"
        assert body["result_reason"] == "unsupported"

    def test_structured_query_missing_route(self):
        resp = client.post("/structured-query", json={"kwargs": {}})
        assert resp.status_code == 422

    def test_structured_query_empty_kwargs_defaults(self):
        """kwargs defaults to empty dict when omitted."""
        # This will hit the real execute_structured_query with a bad route,
        # so we mock it.
        with patch("nbatools.api.execute_structured_query") as mock_exec:
            mock_exec.return_value = self._mock_result()
            resp = client.post(
                "/structured-query",
                json={"route": "season_leaders"},
            )
            assert resp.status_code == 200
            mock_exec.assert_called_once_with("season_leaders")

    @patch("nbatools.api.execute_structured_query")
    def test_structured_query_no_result(self, mock_exec):
        no_result = NoResult(
            query_class="leaderboard",
            reason="no_data",
            result_status="no_result",
            result_reason="no_data",
        )
        mock_exec.return_value = QueryResult(
            result=no_result,
            metadata={"route": "season_leaders"},
            query="structured:season_leaders",
            route="season_leaders",
        )
        resp = client.post(
            "/structured-query",
            json={"route": "season_leaders", "kwargs": {"season": "1900-01"}},
        )
        body = resp.json()
        assert body["ok"] is False
        assert body["result_status"] == "no_result"
        assert body["result_reason"] == "no_data"


# ---------------------------------------------------------------------------
# Response shape consistency
# ---------------------------------------------------------------------------


class TestResponseShape:
    """Verify the JSON envelope shape is stable and UI-friendly."""

    REQUIRED_KEYS = {"ok", "query", "route", "result_status", "result", "notes", "caveats"}

    @patch("nbatools.api.execute_natural_query")
    def test_natural_query_keys(self, mock_exec):
        result = SummaryResult(query_class="summary")
        mock_exec.return_value = QueryResult(
            result=result, metadata={}, query="test", route="player_game_summary"
        )
        resp = client.post("/query", json={"query": "test"})
        body = resp.json()
        assert self.REQUIRED_KEYS.issubset(body.keys())

    @patch("nbatools.api.execute_structured_query")
    def test_structured_query_keys(self, mock_exec):
        result = LeaderboardResult(query_class="leaderboard")
        mock_exec.return_value = QueryResult(
            result=result, metadata={}, query="test", route="season_leaders"
        )
        resp = client.post(
            "/structured-query",
            json={"route": "season_leaders", "kwargs": {}},
        )
        body = resp.json()
        assert self.REQUIRED_KEYS.issubset(body.keys())

    @patch("nbatools.api.execute_natural_query")
    def test_no_result_keys(self, mock_exec):
        no_result = NoResult(query_class="unknown", reason="unrouted")
        mock_exec.return_value = QueryResult(result=no_result, metadata={}, query="bad", route=None)
        resp = client.post("/query", json={"query": "bad"})
        body = resp.json()
        assert self.REQUIRED_KEYS.issubset(body.keys())
        assert body["ok"] is False


# ---------------------------------------------------------------------------
# UI endpoint
# ---------------------------------------------------------------------------


class TestUI:
    def test_ui_serves_html(self):
        resp = client.get("/")
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]
        assert "<title>nbatools</title>" in resp.text

    def test_ui_contains_react_root(self):
        resp = client.get("/")
        assert 'id="root"' in resp.text

    def test_ui_loads_js_bundle(self):
        resp = client.get("/")
        assert "/assets/index-" in resp.text
        assert 'type="module"' in resp.text


# ---------------------------------------------------------------------------
# /freshness
# ---------------------------------------------------------------------------


class TestFreshness:
    """Tests for the freshness status endpoint."""

    def _mock_freshness_info(self, **overrides) -> FreshnessInfo:
        defaults = dict(
            status=FreshnessStatus.FRESH,
            current_through="2026-04-13",
            checked_at="2026-04-14T10:00:00",
            seasons=[
                SeasonFreshness(
                    season="2025-26",
                    season_type="Regular Season",
                    status=FreshnessStatus.FRESH,
                    current_through="2026-04-13",
                    raw_complete=True,
                    processed_complete=True,
                    loaded_at="2026-04-14T09:00:00",
                )
            ],
            last_refresh_ok=True,
            last_refresh_at="2026-04-14T09:00:00",
        )
        defaults.update(overrides)
        return FreshnessInfo(**defaults)

    @patch("nbatools.api.build_freshness_info")
    def test_freshness_returns_structured_status(self, mock_build):
        mock_build.return_value = self._mock_freshness_info()
        resp = client.get("/freshness")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "fresh"
        assert body["current_through"] == "2026-04-13"
        assert body["checked_at"] == "2026-04-14T10:00:00"

    @patch("nbatools.api.build_freshness_info")
    def test_freshness_includes_season_details(self, mock_build):
        mock_build.return_value = self._mock_freshness_info()
        resp = client.get("/freshness")
        body = resp.json()
        assert len(body["seasons"]) == 1
        season = body["seasons"][0]
        assert season["season"] == "2025-26"
        assert season["status"] == "fresh"
        assert season["raw_complete"] is True
        assert season["processed_complete"] is True

    @patch("nbatools.api.build_freshness_info")
    def test_freshness_includes_last_refresh(self, mock_build):
        mock_build.return_value = self._mock_freshness_info()
        resp = client.get("/freshness")
        body = resp.json()
        assert body["last_refresh_ok"] is True
        assert body["last_refresh_at"] == "2026-04-14T09:00:00"
        assert body["last_refresh_error"] is None

    @patch("nbatools.api.build_freshness_info")
    def test_freshness_stale_status(self, mock_build):
        mock_build.return_value = self._mock_freshness_info(
            status=FreshnessStatus.STALE,
            current_through="2026-04-01",
        )
        resp = client.get("/freshness")
        body = resp.json()
        assert body["status"] == "stale"
        assert body["current_through"] == "2026-04-01"

    @patch("nbatools.api.build_freshness_info")
    def test_freshness_unknown_status(self, mock_build):
        mock_build.return_value = self._mock_freshness_info(
            status=FreshnessStatus.UNKNOWN,
            current_through=None,
            seasons=[],
        )
        resp = client.get("/freshness")
        body = resp.json()
        assert body["status"] == "unknown"
        assert body["current_through"] is None

    @patch("nbatools.api.build_freshness_info")
    def test_freshness_failed_status(self, mock_build):
        mock_build.return_value = self._mock_freshness_info(
            status=FreshnessStatus.FAILED,
            last_refresh_ok=False,
            last_refresh_error="API timeout",
        )
        resp = client.get("/freshness")
        body = resp.json()
        assert body["status"] == "failed"
        assert body["last_refresh_ok"] is False
        assert body["last_refresh_error"] == "API timeout"

    @patch("nbatools.api.build_freshness_info")
    def test_freshness_response_shape(self, mock_build):
        """All required keys are always present."""
        mock_build.return_value = self._mock_freshness_info()
        resp = client.get("/freshness")
        body = resp.json()
        required = {
            "status",
            "current_through",
            "checked_at",
            "seasons",
            "last_refresh_ok",
            "last_refresh_at",
            "last_refresh_error",
        }
        assert required.issubset(body.keys())
