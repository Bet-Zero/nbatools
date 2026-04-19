"""Tests for heuristic confidence scoring."""

import pytest

from nbatools.commands._confidence import compute_parse_confidence
from nbatools.commands.natural_query import parse_query

# ---------------------------------------------------------------------------
# Unit tests for compute_parse_confidence
# ---------------------------------------------------------------------------


class TestComputeParseConfidence:
    """Verify score behaviour for synthetic parse-state dicts."""

    def _base(self, **overrides) -> dict:
        """Minimal parse state with sensible defaults."""
        state = {
            "route": "player_game_summary",
            "player": "JOKIC",
            "team": None,
            "player_a": None,
            "player_b": None,
            "team_a": None,
            "team_b": None,
            "entity_ambiguity": None,
            "summary_intent": True,
            "finder_intent": False,
            "count_intent": False,
            "record_intent": False,
            "split_intent": False,
            "career_intent": False,
            "season_high_intent": False,
            "streak_request": None,
            "team_streak_request": None,
            "head_to_head": False,
            "leaderboard_intent": False,
            "team_leaderboard_intent": False,
            "occurrence_event": None,
            "by_decade_intent": False,
            "playoff_history_intent": False,
            "playoff_appearance_intent": False,
            "stat": "pts",
            "season": "2025-26",
            "start_season": None,
            "last_n": None,
            "start_date": None,
            "min_value": None,
            "max_value": None,
            "notes": [],
        }
        state.update(overrides)
        return state

    def test_high_confidence_explicit_query(self):
        """Explicit intent + entity + stat + timeframe → >0.85."""
        state = self._base()
        score = compute_parse_confidence(state)
        assert score > 0.85

    def test_no_route_is_very_low(self):
        """Unroutable query → <0.40."""
        state = self._base(route=None)
        score = compute_parse_confidence(state)
        assert score < 0.40

    def test_entity_ambiguity_reduces_confidence(self):
        """Ambiguous entity should bring score down significantly."""
        state = self._base(
            entity_ambiguity={"type": "player", "candidates": ["A", "B"]},
        )
        high = compute_parse_confidence(self._base())
        low = compute_parse_confidence(state)
        assert low < high
        assert low < 0.80

    def test_default_rule_penalises(self):
        """Notes starting with 'default:' → lower score."""
        state = self._base(
            summary_intent=False,
            notes=["default: <player> + <timeframe> → summary"],
        )
        high = compute_parse_confidence(self._base())
        low = compute_parse_confidence(state)
        assert low < high

    def test_no_stat_penalises(self):
        state = self._base(stat=None)
        full = compute_parse_confidence(self._base())
        no_stat = compute_parse_confidence(state)
        assert no_stat < full

    def test_no_timeframe_penalises(self):
        state = self._base(season=None)
        full = compute_parse_confidence(self._base())
        no_time = compute_parse_confidence(state)
        assert no_time < full

    def test_threshold_boosts(self):
        state = self._base(min_value=20)
        base = compute_parse_confidence(self._base())
        with_thresh = compute_parse_confidence(state)
        assert with_thresh >= base

    def test_score_clamped_0_to_1(self):
        """Score is always within [0, 1]."""
        worst = self._base(
            route=None,
            player=None,
            stat=None,
            season=None,
            summary_intent=False,
            entity_ambiguity={"type": "player", "candidates": []},
            notes=["default: x", "default: y", "default: z"],
        )
        assert 0.0 <= compute_parse_confidence(worst) <= 1.0

    def test_leaderboard_without_entity_not_penalised(self):
        """League-wide leaderboard has no entity but shouldn't be penalised for it."""
        state = self._base(
            route="season_leaders",
            player=None,
            leaderboard_intent=True,
        )
        score = compute_parse_confidence(state)
        assert score > 0.80

    def test_multiple_defaults_stack(self):
        """Each default note should add its own penalty."""
        one = self._base(
            summary_intent=False,
            notes=["default: rule1"],
        )
        two = self._base(
            summary_intent=False,
            notes=["default: rule1", "default: rule2"],
        )
        assert compute_parse_confidence(two) < compute_parse_confidence(one)


# ---------------------------------------------------------------------------
# Integration tests: confidence field in parse_query output
# ---------------------------------------------------------------------------


class TestParseQueryConfidence:
    """Verify that parse_query populates the confidence field."""

    @pytest.mark.parser
    def test_confidence_present(self):
        result = parse_query("Jokic last 10 games")
        assert "confidence" in result
        assert isinstance(result["confidence"], float)
        assert 0.0 <= result["confidence"] <= 1.0

    @pytest.mark.parser
    def test_high_confidence_explicit(self):
        """Fully explicit query → high confidence."""
        result = parse_query("Jokic games over 30 points this season")
        assert result["confidence"] >= 0.85

    @pytest.mark.parser
    def test_high_confidence_summary(self):
        result = parse_query("LeBron averages 2025-26")
        assert result["confidence"] > 0.85

    @pytest.mark.parser
    def test_high_confidence_comparison(self):
        result = parse_query("Jokic vs Embiid this season")
        assert result["confidence"] >= 0.80

    @pytest.mark.parser
    def test_high_confidence_leaderboard(self):
        result = parse_query("scoring leaders this season")
        assert result["confidence"] > 0.80

    @pytest.mark.parser
    def test_high_confidence_count(self):
        result = parse_query("how many games Jokic scored 30+ points")
        assert result["confidence"] > 0.85

    @pytest.mark.parser
    def test_medium_confidence_default_routed(self):
        """Query routed via default rule → medium confidence."""
        result = parse_query("Jokic 2024-25")
        # This routes via player_timeframe_summary_default
        assert 0.50 <= result["confidence"] <= 0.90

    @pytest.mark.parser
    def test_high_confidence_streak(self):
        result = parse_query("Jokic longest streak of 30 point games")
        assert result["confidence"] > 0.80

    @pytest.mark.parser
    def test_high_confidence_split(self):
        result = parse_query("Jokic home away split this season")
        assert result["confidence"] > 0.80

    @pytest.mark.parser
    def test_high_confidence_finder(self):
        result = parse_query("Curry games with 5+ threes this season")
        assert result["confidence"] > 0.85
