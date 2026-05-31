import json

import pytest

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


def test_slice_loading_by_name_uses_saved_slice_file() -> None:
    case_ids = qa.load_slice_case_ids("product_boundaries")

    assert case_ids[:2] == [
        "players_personal_fouls_wave5",
        "warriors_net_rating_single_team_wave5",
    ]


def test_acceptance_metadata_normalization_validates_extended_fields() -> None:
    case = {
        "id": "case_a",
        "acceptance": {
            "family": "team_record_availability",
            "variant": "nearby_unsupported",
            "concept": "multi_player_availability_boundary",
            "public_surface": True,
            "review_required": True,
            "review_role": "boundary",
            "no_broad_fallback": True,
            "sibling_of": ["case_b"],
            "intent_model": "team_record",
            "qualifier_model": ["with_player", "without_player"],
        },
        "expected_status": "no_result",
        "expected_route": "team_record",
        "expected_reason": "filter_not_supported",
        "expected_sections": [],
    }

    acceptance = qa.normalize_acceptance(case)

    assert acceptance["concept"] == "multi_player_availability_boundary"
    assert acceptance["review_role"] == "boundary"
    assert acceptance["sibling_of"] == ["case_b"]
    assert acceptance["qualifier_model"] == ["with_player", "without_player"]


def test_acceptance_metadata_rejects_unknown_field() -> None:
    with pytest.raises(ValueError, match="unknown fields"):
        qa.normalize_acceptance(
            {
                "id": "case_a",
                "acceptance": {
                    "family": "team_records",
                    "variant": "canonical",
                    "typoed_field": True,
                },
            }
        )


@pytest.mark.parametrize(
    "case",
    [
        {
            "id": "supported_descriptive_only",
            "acceptance": {
                "family": "team_records",
                "variant": "canonical",
                "no_broad_fallback": True,
            },
            "expected_status": "ok",
            "expected_route": "team_record",
        },
        {
            "id": "unsupported_descriptive_only",
            "acceptance": {
                "family": "team_records",
                "variant": "nearby_unsupported",
                "no_broad_fallback": True,
            },
            "expected_status": "no_result",
            "expected_route": "team_record",
        },
    ],
)
def test_no_broad_fallback_metadata_requires_explicit_proof(case) -> None:
    with pytest.raises(ValueError, match="no_broad_fallback"):
        qa.normalize_acceptance(case)


def test_acceptance_family_registry_loads_current_public_families() -> None:
    registry = qa.load_acceptance_family_registry(qa.DEFAULT_ACCEPTANCE_FAMILIES_PATH)

    assert registry["surface"] == "public_query_acceptance"
    assert len(registry["families"]) == 16
    assert "player_comparisons" not in registry["families_by_id"]
    availability = registry["families_by_id"]["team_record_availability"]
    assert availability["required_variants"] == [
        "canonical",
        "short",
        "sentence",
        "synonym",
        "inverse_sibling",
        "nearby_unsupported",
        "typo_partial",
    ]
    typo_guards = registry["families_by_id"]["typo_partial_entity_behavior"]
    assert [entry["variant"] for entry in typo_guards["not_applicable_variants"]] == [
        "canonical",
        "sentence",
        "synonym",
        "inverse_sibling",
        "nearby_unsupported",
    ]


def test_public_query_acceptance_slice_loads_with_validated_metadata() -> None:
    registry = qa.load_acceptance_family_registry(qa.DEFAULT_ACCEPTANCE_FAMILIES_PATH)
    _version, cases = qa.load_corpus(qa.ROOT / "qa/raw_query_answer_corpus.yaml")
    qa.validate_corpus_acceptance(cases, registry)
    case_ids = set(qa.load_slice_case_ids("public_query_acceptance"))
    selected = qa.filter_cases(
        cases,
        case_ids=case_ids,
        limit=None,
        explicit_selection=True,
    )

    assert len(selected) == 109
    assert {case["acceptance"]["family"] for case in selected} == set(registry["families_by_id"])


def test_product_review_markdown_includes_family_matrix_and_handoff(tmp_path) -> None:
    registry = qa.load_acceptance_family_registry(qa.DEFAULT_ACCEPTANCE_FAMILIES_PATH)
    rows = [
        {
            "id": "availability_supported",
            "query": "Lakers record with Luka",
            "acceptance": {
                "family": "team_record_availability",
                "variant": "canonical",
                "concept": "whole_game_player_presence",
                "review_required": True,
                "review_role": "representative",
                "no_broad_fallback": True,
            },
            "expected": {
                "expected_route": "team_record",
                "expected_status": "ok",
                "expected_shape": "team_record",
            },
            "route": "team_record",
            "result_status": "ok",
            "shape_hint": "team_record",
            "answer_text": None,
            "answer_summary": "Los Angeles Lakers -- 43-21 over 64 games",
            "applied_filters": [{"kind": "player", "label": "With player", "value": "Luka"}],
            "section_summaries": {"summary": {"row_count": 1, "top_rows": [{"wins": 43}]}},
            "expectation_results": {"status": "pass"},
            "manual_review": {"status": "unreviewed", "tags": [], "notes": ""},
            "suspicious_flags": [],
        }
    ]
    summary = {
        "run_id": "test",
        "corpus_path": "qa/raw_query_answer_corpus.yaml",
        "case_count": 1,
        "failed_case_ids": [],
    }
    review = qa.build_product_review(rows, family_registry=registry, summary=summary)
    path = tmp_path / "product_review.md"

    qa.write_product_review_markdown(path, review)
    markdown = path.read_text()

    assert "## Feature-Family Summary" in markdown
    assert "## Missing / Unchecked Variant Checklist" in markdown
    assert "### availability_supported" in markdown
    assert "## Unsupported / No-Broad-Fallback Rows" in markdown
    assert "## Product Decisions Needed" in markdown
    assert "## Suspicious Rows" in markdown
    assert "## What To Send ChatGPT" in markdown
    assert "Do not treat machine pass counts as sufficient." in markdown
    availability = next(
        family for family in review["family_summary"] if family["id"] == "team_record_availability"
    )
    assert availability["machine_status"] == "pass"
    assert availability["human_review"] == "pending"
    assert "short" in availability["missing_variants"]
    assert not availability["public_accepted"]


def test_slice_loading_by_direct_path(tmp_path) -> None:
    slice_path = tmp_path / "custom_slice.yaml"
    slice_path.write_text(
        "\n".join(
            [
                "name: custom",
                "case_ids:",
                "  - case_b",
                "  - case_c",
                "",
            ]
        )
    )

    assert qa.load_slice_case_ids(str(slice_path)) == ["case_b", "case_c"]


def test_unknown_case_ids_fail_loudly() -> None:
    cases = [{"id": "case_a"}, {"id": "case_b"}]

    with pytest.raises(ValueError, match="Unknown case id"):
        qa.filter_cases(
            cases,
            case_ids={"case_a", "missing_case"},
            limit=None,
            explicit_selection=True,
        )


def test_case_and_slice_selection_composes_deduplicates_and_preserves_corpus_order(
    tmp_path,
) -> None:
    slice_path = tmp_path / "selection_slice.yaml"
    slice_path.write_text("case_ids:\n  - case_b\n  - case_c\n")
    cases = [{"id": "case_a"}, {"id": "case_b"}, {"id": "case_c"}, {"id": "case_d"}]

    selected_ids, explicit = qa.collect_selected_case_ids(
        case_values=["case_c,case_a"],
        slice_values=[str(slice_path)],
        failed_from_values=[],
    )
    selected = qa.filter_cases(
        cases,
        case_ids=selected_ids,
        limit=None,
        explicit_selection=explicit,
    )

    assert explicit
    assert [case["id"] for case in selected] == ["case_a", "case_b", "case_c"]


def test_failed_from_summary_json_parsing(tmp_path) -> None:
    summary_path = tmp_path / "summary.json"
    summary_path.write_text(json.dumps({"failed_case_ids": ["case_b", "case_a"]}))

    assert qa.load_failed_case_ids(summary_path) == ["case_b", "case_a"]


def test_failed_from_report_jsonl_parsing(tmp_path) -> None:
    report_path = tmp_path / "report.jsonl"
    rows = [
        {"id": "case_a", "expectation_results": {"status": "pass", "fail_count": 0}},
        {"id": "case_b", "expectation_results": {"status": "fail", "fail_count": 1}},
        {"id": "case_c", "expectation_results": {"status": "pass", "fail_count": 2}},
    ]
    report_path.write_text("\n".join(json.dumps(row) for row in rows) + "\n")

    assert qa.load_failed_case_ids(report_path) == ["case_b", "case_c"]


def _comparison_row(
    case_id: str,
    *,
    expectation_status: str,
    result_status: str = "ok",
    route: str = "team_record",
    suspicious_flags: list[dict] | None = None,
    verified_outliers: list[dict] | None = None,
) -> dict:
    return {
        "id": case_id,
        "query": case_id,
        "result_status": result_status,
        "route": route,
        "suspicious_flags": suspicious_flags or [],
        "verified_outliers": verified_outliers or [],
        "expectation_results": {"status": expectation_status, "fail_count": 0},
    }


def test_compare_summary_generation_from_report_jsonl(tmp_path) -> None:
    previous_path = tmp_path / "report.jsonl"
    previous_rows = [
        _comparison_row("case_a", expectation_status="pass", route="old_route"),
        _comparison_row(
            "case_b",
            expectation_status="pass",
            suspicious_flags=[{"id": "old_flag"}],
        ),
        _comparison_row(
            "case_c",
            expectation_status="fail",
            verified_outliers=[{"id": "top_performance_high_points"}],
        ),
    ]
    previous_path.write_text("\n".join(json.dumps(row) for row in previous_rows) + "\n")
    current_rows = [
        _comparison_row("case_a", expectation_status="pass", route="new_route"),
        _comparison_row("case_b", expectation_status="fail"),
        _comparison_row("case_c", expectation_status="pass"),
    ]

    comparison = qa.build_run_comparison(current_rows, previous_path)

    assert comparison["newly_failing_case_ids"] == ["case_b"]
    assert comparison["newly_passing_case_ids"] == ["case_c"]
    assert comparison["failed_case_delta"] == 0
    assert comparison["result_status_count_delta"] == {}
    assert comparison["suspicious_flag_count_delta"] == -1
    assert comparison["verified_outlier_count_delta"] == -1
    assert comparison["route_status_drift"] == [
        {
            "id": "case_a",
            "previous_route": "old_route",
            "current_route": "new_route",
            "previous_result_status": "ok",
            "current_result_status": "ok",
        }
    ]


def test_duration_and_slowest_summary_from_synthetic_rows() -> None:
    rows = [
        {**_comparison_row("case_a", expectation_status="pass"), "duration_seconds": 0.25},
        {**_comparison_row("case_b", expectation_status="pass"), "duration_seconds": 1.5},
        {**_comparison_row("case_c", expectation_status="pass"), "duration_seconds": 0.75},
    ]

    slowest = qa.build_slowest_cases(rows, limit=2)
    summary = qa.summarize_rows(
        rows,
        run_id="test",
        started_at="2026-05-17T00:00:00+00:00",
        completed_at="2026-05-17T00:00:01+00:00",
        corpus_path=qa.ROOT / "qa/raw_query_answer_corpus.yaml",
        output_paths={"summary_json": qa.ROOT / "outputs/test/summary.json"},
    )

    assert [row["id"] for row in slowest] == ["case_b", "case_c"]
    assert [row["id"] for row in summary["slowest_cases"]] == ["case_b", "case_c", "case_a"]
