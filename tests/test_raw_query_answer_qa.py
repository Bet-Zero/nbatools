from tools import raw_query_answer_qa as qa


def _case() -> dict:
    return {
        "id": "biggest_scoring_games",
        "query": "What were the biggest scoring games this season?",
        "category": "top_performances",
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


def test_frontend_hero_policy_is_informational_not_suspicious() -> None:
    flags = qa.build_review_flags(
        {
            **_case(),
            "answer_text_policy": "frontend_hero_expected",
            "category": "team_record",
        },
        result_status="ok",
        route="team_record",
        answer_text=None,
        shape_hint="team_record",
        metadata={"query_class": "summary"},
        sections={"summary": [{}]},
    )

    assert flags["answer_text_status"] == "frontend_hero_expected"
    assert flags["suspicious_flags"] == []
    assert flags["informational_flags"][0]["id"] == "frontend_hero_expected"


def test_required_backend_answer_text_policy_flags_missing_phrase() -> None:
    flags = qa.build_review_flags(
        {**_case(), "answer_text_policy": "requires_backend_answer_text"},
        result_status="ok",
        route="game_finder",
        answer_text=None,
        shape_hint="count_with_finder",
        metadata={"query_class": "finder"},
        sections={"count": [{}], "finder": [{}]},
    )

    assert flags["answer_text_status"] == "missing_backend_answer_text"
    assert flags["informational_flags"] == []
    assert flags["suspicious_flags"][0]["id"] == "missing_backend_answer_text"


def test_required_backend_answer_text_policy_accepts_answer_or_count_phrase() -> None:
    for metadata in (
        {"answer_phrase": "The Suns are 8-10 without Devin Booker."},
        {"count_phrase": "Nikola Jokic recorded 34 triple-doubles."},
    ):
        answer_text, _source = qa.answer_text_from_metadata(metadata)
        flags = qa.build_review_flags(
            {**_case(), "answer_text_policy": "requires_backend_answer_text"},
            result_status="ok",
            route="game_summary",
            answer_text=answer_text,
            shape_hint="game_log_team_detail",
            metadata={**metadata, "query_class": "summary"},
            sections={"summary": [{}], "game_log": [{}]},
        )

        assert flags["answer_text_status"] == "backend_answer_text_present"
        assert flags["suspicious_flags"] == []
        assert flags["informational_flags"] == []


def test_no_answer_text_expected_policy_does_not_flag_missing_phrase() -> None:
    flags = qa.build_review_flags(
        {
            **_case(),
            "answer_text_policy": "no_answer_text_expected",
            "expected_status": "no_result",
        },
        result_status="no_result",
        route="season_leaders",
        answer_text=None,
        shape_hint="no_result",
        metadata={"query_class": "leaderboard"},
        sections={},
    )

    assert flags["answer_text_status"] == "no_answer_text_expected"
    assert flags["suspicious_flags"] == []
    assert flags["informational_flags"] == []


def test_summary_counts_distinguish_informational_and_suspicious_flags() -> None:
    rows = [
        {
            **_case(),
            "id": "frontend_case",
            "answer_text_policy": "frontend_hero_expected",
            "answer_text_status": "frontend_hero_expected",
            "result_status": "ok",
            "route": "team_record",
            "manual_review": {"status": "unreviewed", "tags": [], "notes": ""},
            "suspicious_flags": [],
            "informational_flags": [{"id": "frontend_hero_expected"}],
            "verified_outliers": [],
            "suggested_review_tags": [],
            "expectation_results": {"status": "pass", "checks": [{"status": "pass"}]},
        },
        {
            **_case(),
            "id": "required_case",
            "answer_text_policy": "requires_backend_answer_text",
            "answer_text_status": "missing_backend_answer_text",
            "result_status": "ok",
            "route": "game_finder",
            "manual_review": {"status": "unreviewed", "tags": [], "notes": ""},
            "suspicious_flags": [{"id": "missing_backend_answer_text"}],
            "informational_flags": [],
            "verified_outliers": [],
            "suggested_review_tags": ["backend_answer_text_required"],
            "expectation_results": {"status": "pass", "checks": [{"status": "pass"}]},
        },
    ]

    summary = qa.summarize_rows(
        rows,
        run_id="test",
        started_at="2026-05-13T00:00:00+00:00",
        completed_at="2026-05-13T00:00:01+00:00",
        corpus_path=qa.ROOT / "qa/raw_query_answer_corpus.yaml",
        output_paths={"report_jsonl": qa.ROOT / "outputs/test/report.jsonl"},
    )

    assert summary["suspicious_flag_case_count"] == 1
    assert summary["suspicious_flag_counts"] == {"missing_backend_answer_text": 1}
    assert summary["informational_flag_case_count"] == 1
    assert summary["informational_flag_counts"] == {"frontend_hero_expected": 1}
    assert summary["answer_text_policy_counts"] == {
        "frontend_hero_expected": 1,
        "requires_backend_answer_text": 1,
    }
