import json

import pytest

from nbatools.query_service import VALID_ROUTES
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


def test_shape_hint_route_policy_covers_valid_routes() -> None:
    route_specific = set(qa.SHAPE_BY_ROUTE) | set(qa.LEADERBOARD_ROUTES)
    section_derived = {
        "matchup_by_decade",
        "player_compare",
        "player_game_finder",
        "player_split_summary",
        "team_compare",
        "team_occurrence_leaders",
        "team_split_summary",
    }

    assert route_specific | section_derived == set(VALID_ROUTES)


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
        slice_values=["public_query_acceptance"],
    )

    assert summary["slice_names"] == ["public_query_acceptance"]
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
        "warriors_net_rating_single_team_wave5",
        "turnover_leaders_wave4",
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
    assert registry["review_closure"]["state"] == "human_review_complete"
    assert registry["review_closure"]["case_count"] == 127
    assert registry["review_closure"]["ui_spot_check"]["status"] == "not_applicable"
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
    comparisons = registry["families_by_id"]["comparisons"]
    assert comparisons["product_decisions"][0]["status"] == "resolved"


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

    assert len(selected) == 127
    assert {case["acceptance"]["family"] for case in selected} == set(registry["families_by_id"])


def test_run_id_label_accepts_folder_name_only() -> None:
    assert qa.validate_run_id_label("latest_public_query_acceptance") == (
        "latest_public_query_acceptance"
    )

    for run_id in ("", ".", "..", "../outside", "nested/run", "/tmp/run", "bad name"):
        with pytest.raises(ValueError, match="--run-id"):
            qa.validate_run_id_label(run_id)


def test_existing_named_run_directory_requires_overwrite(tmp_path) -> None:
    expected_root = tmp_path / "outputs" / "raw_query_answer_qa"
    run_dir = expected_root / "latest_public_query_acceptance"
    run_dir.mkdir(parents=True)
    (run_dir / "stale.txt").write_text("old")

    with pytest.raises(ValueError, match="already exists"):
        qa.validate_run_directory_target(
            run_dir,
            overwrite_run_id=False,
            expected_root=expected_root,
        )

    qa.validate_run_directory_target(
        run_dir,
        overwrite_run_id=True,
        expected_root=expected_root,
    )
    qa.prepare_run_directory(
        run_dir,
        overwrite_run_id=True,
        expected_root=expected_root,
    )

    assert run_dir.exists()
    assert list(run_dir.iterdir()) == []


def test_overwrite_run_directory_must_be_direct_child_of_raw_qa_root(tmp_path) -> None:
    expected_root = tmp_path / "outputs" / "raw_query_answer_qa"
    outside_run_dir = tmp_path / "other_outputs" / "latest_public_query_acceptance"
    nested_run_dir = expected_root / "nested" / "latest_public_query_acceptance"

    for run_dir in (outside_run_dir, nested_run_dir):
        with pytest.raises(ValueError, match="directly under"):
            qa.validate_run_directory_target(
                run_dir,
                overwrite_run_id=True,
                expected_root=expected_root,
            )


def test_raw_qa_report_uses_query_output_snapshot_markdown(tmp_path) -> None:
    payload = {
        "ok": True,
        "query": "Lakers record with Luka",
        "route": "team_record",
        "result_status": "ok",
        "result_reason": None,
        "intent": "team_record",
        "result": {
            "query_class": "summary",
            "metadata": {
                "query_class": "summary",
                "applied_filters": [
                    {"kind": "player", "label": "With player", "value": "Luka Doncic"}
                ],
            },
            "sections": {
                "summary": [
                    {
                        "team_name": "Los Angeles Lakers",
                        "games": 64,
                        "wins": 43,
                        "losses": 21,
                        "win_pct": 0.672,
                    }
                ]
            },
        },
    }
    snapshot = qa.build_query_ui_snapshot(payload, top_rows=1)
    row = {
        **_case(),
        "id": "lakers_record_with_luka",
        "query": "Lakers record with Luka",
        "category": "team_record",
        "priority": "p1",
        "route": "team_record",
        "intent": "team_record",
        "query_class": "summary",
        "result_status": "ok",
        "result_reason": None,
        "shape_hint": "team_record",
        "shape_source": "backend_approximation",
        "answer_text_policy": "frontend_hero_expected",
        "answer_text_status": "frontend_hero_expected",
        "answer_text": None,
        "answer_summary": "Los Angeles Lakers -- 43-21 over 64 games",
        "applied_filters": [{"kind": "player", "label": "With player", "value": "Luka Doncic"}],
        "section_summaries": {"summary": {"row_count": 1, "top_rows": []}},
        "query_output_snapshot": snapshot,
        "expectation_results": {"status": "pass", "pass_count": 1, "fail_count": 0},
        "expected": {"review_notes": None},
        "manual_review": {"status": "unreviewed", "tags": [], "notes": ""},
        "suspicious_flags": [],
        "informational_flags": [],
        "verified_outliers": [],
        "suggested_review_tags": [],
        "notes": [],
        "caveats": [],
        "errors": [],
    }
    summary = {
        "run_id": "review",
        "started_at": "2026-06-07T00:00:00+00:00",
        "completed_at": "2026-06-07T00:00:01+00:00",
        "corpus_path": "qa/raw_query_answer_corpus.yaml",
        "slice_names": [],
        "case_count": 1,
        "result_status_counts": {"ok": 1},
        "category_counts": {"team_record": 1},
        "route_counts": {"team_record": 1},
        "manual_review_status_counts": {"unreviewed": 1},
        "manual_review_tag_counts": {},
        "answer_text_policy_counts": {"frontend_hero_expected": 1},
        "answer_text_status_counts": {"frontend_hero_expected": 1},
        "suspicious_flag_case_count": 0,
        "suspicious_flag_counts": {},
        "informational_flag_case_count": 0,
        "informational_flag_counts": {},
        "verified_outlier_case_count": 0,
        "verified_outlier_counts": {},
        "suggested_review_tag_counts": {},
        "expectation_case_counts": {"pass": 1},
        "expectation_check_counts": {"pass": 1},
        "failed_case_ids": [],
        "slowest_cases": [],
    }
    path = tmp_path / "report.md"

    qa.write_markdown(path, [row], summary)
    markdown = path.read_text()

    assert "**Answer shown**" in markdown
    assert "The Los Angeles Lakers are 43-21" in markdown
    assert "#### Table — Team record" in markdown
    assert "Table type: record_summary" in markdown
    assert "Column schema: team_record_summary_default" in markdown
    assert "Filter: With player: Luka Doncic" in markdown
    assert "| Team | W-L | Games | Win % |" in markdown


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


def test_product_review_uses_registry_review_closure_for_matching_clean_scope() -> None:
    registry = {
        "surface": "public_query_acceptance",
        "review_closure": {
            "state": "human_review_complete",
            "scope": "public_query_acceptance",
            "reviewed_run_id": "reviewed_run",
            "completed_on": "2026-06-03",
            "case_count": 1,
            "ui_spot_check": {"status": "passed"},
        },
        "families": [
            {
                "id": "player_stats_this_season",
                "label": "Player stats this season",
                "public_surface": True,
                "required_variants": ["canonical"],
                "not_applicable_variants": [],
                "intentionally_unsupported_variants": [],
                "coverage_questions": [],
                "sibling_families": [],
                "product_decisions": [],
            }
        ],
    }
    rows = [
        {
            "id": "player_stats",
            "query": "Jokic stats",
            "acceptance": {
                "family": "player_stats_this_season",
                "variant": "canonical",
                "review_required": True,
            },
            "expected": {"expected_route": "player_game_summary", "expected_status": "ok"},
            "route": "player_game_summary",
            "result_status": "ok",
            "shape_hint": "entity_summary",
            "answer_summary": "Nikola Jokic summary",
            "applied_filters": [],
            "section_summaries": {"summary": {"row_count": 1, "top_rows": [{"games": 10}]}},
            "expectation_results": {"status": "pass"},
            "manual_review": {"status": "unreviewed", "tags": [], "notes": ""},
            "suspicious_flags": [],
        }
    ]
    summary = {
        "run_id": "latest_public_query_acceptance",
        "corpus_path": "qa/raw_query_answer_corpus.yaml",
        "case_count": 1,
        "failed_case_ids": [],
    }

    review = qa.build_product_review(rows, family_registry=registry, summary=summary)
    family = review["family_summary"][0]

    assert review["machine_regression"] == "pass"
    assert review["coverage_declaration"] == "complete"
    assert review["review_declaration"] == "human_review_complete"
    assert family["human_review"] == "reviewed_pass"
    assert family["human_review_source"] == "registry_closure"
    assert family["public_accepted"]


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
