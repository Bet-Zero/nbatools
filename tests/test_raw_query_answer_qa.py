from tools import raw_query_answer_qa as qa


def _case() -> dict:
    return {
        "id": "biggest_scoring_games",
        "query": "What were the biggest scoring games this season?",
        "priority": "p1",
        "expected_status": "ok",
    }


def _sections(*, game_id: str | int = "22500938", points: int = 83) -> dict:
    return {
        "leaderboard": [
            {
                "rank": 1,
                "player_id": 1628389,
                "player_name": "Bam Adebayo",
                "team_name": "Miami Heat",
                "team_abbr": "MIA",
                "opponent_team_abbr": "WAS",
                "game_id": game_id,
                "game_date": "2026-03-10T00:00:00",
                "pts": points,
            }
        ]
    }


def _verified_outlier() -> dict:
    return {
        "id": "bam_adebayo_83_points_2026_03_10",
        "category": "top_performance_high_points",
        "player_name": "Bam Adebayo",
        "player_id": 1628389,
        "game_id": "0022500938",
        "game_date": "2026-03-10",
        "stat": "pts",
        "value": 83,
        "verification_status": "verified_official",
    }


def test_verified_high_point_outlier_is_not_open_suspicious() -> None:
    flags = qa.build_review_flags(
        _case(),
        result_status="ok",
        route="top_player_games",
        answer_text=None,
        shape_hint="top_performances",
        metadata={},
        sections=_sections(),
        verified_outliers=[_verified_outlier()],
    )

    assert flags["suspicious_flags"] == []
    assert flags["verified_outliers"][0]["id"] == "top_performance_high_points"
    row = flags["verified_outliers"][0]["details"]["rows"][0]
    assert row["verified_outlier_id"] == "bam_adebayo_83_points_2026_03_10"


def test_unverified_high_point_outlier_stays_open_suspicious() -> None:
    flags = qa.build_review_flags(
        _case(),
        result_status="ok",
        route="top_player_games",
        answer_text=None,
        shape_hint="top_performances",
        metadata={},
        sections=_sections(points=82),
        verified_outliers=[_verified_outlier()],
    )

    assert flags["verified_outliers"] == []
    assert flags["suspicious_flags"][0]["id"] == "top_performance_high_points"
    assert flags["suspicious_flags"][0]["details"]["rows"][0]["value"] == 82


def test_verified_outlier_game_id_matching_handles_leading_zero_forms() -> None:
    row = qa.top_performance_high_point_rows(
        route="top_player_games",
        shape_hint="top_performances",
        sections=_sections(game_id=22500938),
    )[0]

    assert qa.outlier_entry_matches_row(_verified_outlier(), row)
    assert qa.game_id_variants("0022500938") & qa.game_id_variants(22500938)
