import pytest

from nbatools.query_service import execute_natural_query

pytestmark = [pytest.mark.query, pytest.mark.needs_data]


def _unsupported_filters(metadata: dict) -> list[str] | None:
    return metadata.get("unsupported_filters")


@pytest.mark.parametrize(
    "case",
    [
        {
            "query": "best 5-game team scoring stretch this season",
            "route": "player_stretch_leaderboard",
            "reason": "filter_not_supported",
            "unsupported_filters": ["team_rolling_stretch"],
        },
        {
            "query": "rookie assist leaders this season",
            "route": "season_leaders",
            "reason": "filter_not_supported",
            "unsupported_filters": ["rookie_leaderboard"],
        },
        {
            "query": "bench rebound leaders this season",
            "route": "season_leaders",
            "reason": "filter_not_supported",
            "unsupported_filters": ["role_leaderboard"],
        },
        {
            "query": "Celtics bench points this season",
            "route": "game_finder",
            "reason": "filter_not_supported",
            "unsupported_filters": ["team_bench_scoring"],
        },
        {
            "query": "Celtics record against east coast teams",
            "route": "team_record",
            "reason": "filter_not_supported",
            "unsupported_filters": ["opponent_conference"],
        },
        {
            "query": "playoff record against Northwest Division teams",
            "route": "team_record_leaderboard",
            "reason": "filter_not_supported",
            "unsupported_filters": ["opponent_division"],
        },
        {
            "query": "Lakers record against Western Conference Pacific Division teams",
            "route": "team_record",
            "reason": "filter_not_supported",
            "unsupported_filters": ["opponent_division"],
        },
        {
            "query": "Celtics playoff record vs Atlantic Division",
            "route": "team_record",
            "reason": "filter_not_supported",
            "unsupported_filters": ["opponent_division"],
        },
        {
            "query": "Celtics conference finals record vs Atlantic Division",
            "route": "playoff_history",
            "reason": "filter_not_supported",
            "unsupported_filters": ["single_team_playoff_round_record"],
        },
        {
            "query": "Celtics record vs Atlantic Division in 2023-24",
            "route": "team_record",
            "reason": "filter_not_supported",
            "unsupported_filters": ["division_coverage"],
        },
        {
            "query": "Celtics record against the East in 2023-24",
            "route": "team_record",
            "reason": "filter_not_supported",
            "unsupported_filters": ["conference_coverage"],
        },
        {
            "query": "Warriors net rating since January",
            "route": "game_summary",
            "reason": "filter_not_supported",
            "unsupported_filters": ["single_team_advanced_stat_summary"],
        },
        {
            "query": "Celtics conference finals record",
            "route": "playoff_history",
            "reason": "filter_not_supported",
            "unsupported_filters": ["single_team_playoff_round_record"],
        },
        {
            "query": "What is the Lakers record when LeBron James and Anthony Davis both play?",
            "route": "team_record",
            "reason": "filter_not_supported",
            "unsupported_filters": ["multi_player_availability"],
        },
        {
            "query": "Lakers record with Reaves without Luka",
            "route": "team_record",
            "reason": "filter_not_supported",
            "unsupported_filters": ["multi_player_availability"],
        },
        {
            "query": "Lakers record without Luk",
            "route": "team_record",
            "reason": "filter_not_supported",
            "unsupported_filters": ["unresolved_player_availability"],
        },
        {
            "query": "Nuggets net rating with Nikola Jokic on the floor versus off the floor",
            "route": "player_on_off",
            "reason": "unsupported",
        },
        {
            "query": "best 5-man lineups",
            "route": "lineup_leaderboard",
            "reason": "unsupported",
        },
        {
            "query": "Tatum clutch stats",
            "route": "player_game_summary",
            "reason": "filter_not_supported",
        },
        {
            "query": "Who is the most clutch player this season?",
            "route": "season_leaders",
            "reason": "filter_not_supported",
        },
        {
            "query": "who has cooled off lately",
            "route": None,
            "status": "error",
            "reason": "unrouted",
        },
        {
            "query": "Who is the best duo this season?",
            "route": None,
            "status": "error",
            "reason": "unrouted",
        },
        {
            "query": "in clutch time",
            "route": "season_leaders",
            "reason": "filter_not_supported",
        },
        {
            "query": "who won mvp this season",
            "route": None,
            "reason": "filter_not_supported",
            "unsupported_filters": ["award_query"],
        },
        {
            "query": "who won rookie of the year",
            "route": None,
            "reason": "filter_not_supported",
            "unsupported_filters": ["award_query"],
        },
    ],
    ids=lambda case: case["query"],
)
def test_unsupported_boundaries_do_not_return_broad_fallback_sections(case):
    qr = execute_natural_query(case["query"])

    assert qr.route == case["route"]
    assert qr.result.result_status == case.get("status", "no_result")
    assert qr.result.result_reason == case["reason"]
    assert qr.to_dict()["sections"] == {}

    if "unsupported_filters" in case:
        assert _unsupported_filters(qr.metadata) == case["unsupported_filters"]
    else:
        assert _unsupported_filters(qr.metadata) in (None, [])
