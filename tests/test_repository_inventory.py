from __future__ import annotations

import json
from pathlib import Path
from textwrap import dedent

import pytest

from tools import generate_repository_inventory as inventory


def _write(root: Path, relative_path: str, text: str) -> Path:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(text).lstrip(), encoding="utf-8")
    return path


def _fixture_root(tmp_path: Path) -> Path:
    _write(
        tmp_path,
        "src/nbatools/query_service.py",
        """
        VALID_ROUTES = frozenset(
            [
                "route_b",
                "route_a",
            ]
        )
        """,
    )
    _write(
        tmp_path,
        "frontend/src/api/types.ts",
        """
        export type ResultReason =
          | "reason_b"
          | "reason_a"
          | null;

        export type RouteName =
          | "route_b"
          | "route_a";
        """,
    )
    _write(
        tmp_path,
        "src/nbatools/commands/structured_results.py",
        """
        from enum import StrEnum

        class ResultReason(StrEnum):
            REASON_B = "reason_b"
            REASON_A = "reason_a"
        """,
    )
    _write(
        tmp_path,
        "src/nbatools/commands/format_output.py",
        """
        StructuredResult = SummaryResult | NoResult
        """,
    )
    _write(
        tmp_path,
        "src/nbatools/commands/validation_control.py",
        """
        class DatasetSpec:
            name: str
            layer: str
            grain: str
            key_columns: tuple[str, ...]
            source: str
            required_columns: tuple[str, ...] = ()
            required: bool = True
            season_only: bool = False
            regular_season_only: bool = False
            trust_column: str | None = None
            trust_reason_column: str | None = None

        DATASET_SPECS = (
            DatasetSpec(
                "zeta",
                "raw",
                "game",
                ("game_id",),
                "source_z",
            ),
            DatasetSpec(
                "alpha",
                "processed",
                "player-game",
                ("game_id", "player_id"),
                "source_a",
                required=False,
                trust_column="coverage_trusted",
            ),
        )
        """,
    )
    _write(
        tmp_path,
        "qa/raw_query_answer_corpus.yaml",
        """
        version: 1
        cases:
          - id: case_b
            query: Example B
          - id: case_a
            query: Example A
        """,
    )
    _write(
        tmp_path,
        "qa/raw_query_answer_acceptance_families.yaml",
        """
        version: 1
        families:
          - id: family_b
            label: Family B
          - id: family_a
            label: Family A
        """,
    )
    _write(
        tmp_path,
        "qa/harness_slices/example.yaml",
        """
        name: example
        case_ids:
          - case_b
          - case_a
        """,
    )
    return tmp_path


def test_committed_repository_inventory_matches_current_authoritative_sources() -> None:
    generated = inventory.build_inventory(inventory.ROOT)
    path = inventory.ROOT / inventory.OUTPUT_PATH

    assert json.loads(path.read_text(encoding="utf-8")) == generated
    assert path.read_text(encoding="utf-8") == inventory.render_inventory(generated)
    assert generated["structured_routes"]["count"] == len(generated["structured_routes"]["names"])
    assert generated["structured_result_types"]["count"] == len(
        generated["structured_result_types"]["names"]
    )
    assert generated["result_reasons"]["count"] == len(generated["result_reasons"]["names"])
    assert generated["dataset_specs"]["count"] == len(generated["dataset_specs"]["items"])
    assert generated["frontend_layout"]["count"] == len(generated["frontend_layout"]["files"])


def test_inventory_generation_is_sorted_and_deterministic(tmp_path: Path) -> None:
    root = _fixture_root(tmp_path)

    first = inventory.build_inventory(root)
    second = inventory.build_inventory(root)

    assert inventory.render_inventory(first) == inventory.render_inventory(second)
    assert first["structured_routes"]["names"] == ["route_a", "route_b"]
    assert first["structured_result_types"]["names"] == ["NoResult", "SummaryResult"]
    assert first["result_reasons"]["names"] == ["reason_a", "reason_b"]
    assert first["frontend_layout"]["files"] == ["frontend/src/api/types.ts"]
    assert [item["name"] for item in first["dataset_specs"]["items"]] == [
        "alpha",
        "zeta",
    ]
    assert first["query_validation"] == {
        "acceptance_family_count": 2,
        "acceptance_family_ids": ["family_a", "family_b"],
        "raw_qa_case_count": 2,
        "slice_case_counts": {"example": 2},
    }


def test_check_mode_is_read_only_and_write_mode_repairs_stale_output(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = _fixture_root(tmp_path)
    output = tmp_path / "generated/repository_inventory.json"
    output.parent.mkdir(parents=True)
    output.write_text("{}\n", encoding="utf-8")

    assert not inventory.check_inventory(root, output)
    assert output.read_text(encoding="utf-8") == "{}\n"
    assert "repository inventory is stale" in capsys.readouterr().out

    inventory.write_inventory(root, output)
    assert inventory.check_inventory(root, output)
    assert output.read_text(encoding="utf-8") == inventory.render_inventory(
        inventory.build_inventory(root)
    )


def test_check_mode_reports_missing_output_without_creating_it(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = _fixture_root(tmp_path)
    output = tmp_path / "missing/repository_inventory.json"

    assert not inventory.check_inventory(root, output)
    assert not output.exists()
    assert "repository inventory is missing" in capsys.readouterr().out


def test_duplicate_source_ids_are_rejected(tmp_path: Path) -> None:
    root = _fixture_root(tmp_path)
    _write(
        root,
        "qa/raw_query_answer_corpus.yaml",
        """
        version: 1
        cases:
          - id: case_a
          - id: case_a
        """,
    )

    with pytest.raises(inventory.InventoryError, match="duplicate values: case_a"):
        inventory.build_inventory(root)


def test_alternate_mapping_item_shape_is_rejected_instead_of_undercounted(
    tmp_path: Path,
) -> None:
    root = _fixture_root(tmp_path)
    _write(
        root,
        "qa/raw_query_answer_corpus.yaml",
        """
        version: 1
        cases:
          -
            id: case_a
          - id: case_b
        """,
    )

    with pytest.raises(inventory.InventoryError, match="expected '  - id: <identifier>'"):
        inventory.build_inventory(root)


@pytest.mark.parametrize(
    ("relative_path", "old", "new", "match"),
    [
        (
            "qa/raw_query_answer_acceptance_families.yaml",
            "family_b",
            "family_a",
            "duplicate values: family_a",
        ),
        (
            "src/nbatools/query_service.py",
            '"route_b"',
            '"route_a"',
            "duplicate values: route_a",
        ),
        (
            "frontend/src/api/types.ts",
            '"route_b"',
            '"route_a"',
            "duplicate values: route_a",
        ),
        (
            "src/nbatools/commands/structured_results.py",
            '"reason_b"',
            '"reason_a"',
            "duplicate values: reason_a",
        ),
        (
            "frontend/src/api/types.ts",
            '"reason_b"',
            '"reason_a"',
            "duplicate values: reason_a",
        ),
        (
            "src/nbatools/commands/format_output.py",
            "NoResult",
            "SummaryResult",
            "duplicate values: SummaryResult",
        ),
        (
            "src/nbatools/commands/validation_control.py",
            '"zeta"',
            '"alpha"',
            "duplicate dataset names: alpha",
        ),
    ],
)
def test_duplicate_inventory_identifiers_are_rejected(
    tmp_path: Path,
    relative_path: str,
    old: str,
    new: str,
    match: str,
) -> None:
    root = _fixture_root(tmp_path)
    path = root / relative_path
    source = path.read_text(encoding="utf-8")
    assert old in source
    path.write_text(source.replace(old, new, 1), encoding="utf-8")

    with pytest.raises(inventory.InventoryError, match=match):
        inventory.build_inventory(root)


def test_slice_case_ids_must_exist_in_the_corpus(tmp_path: Path) -> None:
    root = _fixture_root(tmp_path)
    _write(
        root,
        "qa/harness_slices/example.yaml",
        """
        name: example
        case_ids:
          - case_a
          - absent_case
        """,
    )

    with pytest.raises(inventory.InventoryError, match="unknown corpus case ids: absent_case"):
        inventory.build_inventory(root)


def test_frontend_route_union_must_match_backend_routes(tmp_path: Path) -> None:
    root = _fixture_root(tmp_path)
    path = root / "frontend/src/api/types.ts"
    source = path.read_text(encoding="utf-8")
    path.write_text(source.replace('"route_b"', '"frontend_only"', 1), encoding="utf-8")

    with pytest.raises(
        inventory.InventoryError,
        match=r"RouteName differs from VALID_ROUTES \(missing: route_b; extra: frontend_only\)",
    ):
        inventory.build_inventory(root)


def test_frontend_reason_union_must_match_backend_reasons(tmp_path: Path) -> None:
    root = _fixture_root(tmp_path)
    path = root / "frontend/src/api/types.ts"
    source = path.read_text(encoding="utf-8")
    path.write_text(source.replace('"reason_b"', '"frontend_only"', 1), encoding="utf-8")

    with pytest.raises(
        inventory.InventoryError,
        match=(
            r"ResultReason differs from backend enum "
            r"\(missing: reason_b; extra: frontend_only\)"
        ),
    ):
        inventory.build_inventory(root)


def test_slice_name_must_match_its_filename(tmp_path: Path) -> None:
    root = _fixture_root(tmp_path)
    path = root / "qa/harness_slices/example.yaml"
    source = path.read_text(encoding="utf-8")
    path.write_text(source.replace("name: example", "name: renamed", 1), encoding="utf-8")

    with pytest.raises(inventory.InventoryError, match="must match filename stem"):
        inventory.build_inventory(root)


def test_changed_authoritative_source_shape_is_rejected(tmp_path: Path) -> None:
    root = _fixture_root(tmp_path)
    _write(
        root,
        "src/nbatools/query_service.py",
        """
        VALID_ROUTES = ("route_a", "route_b")
        """,
    )

    with pytest.raises(inventory.InventoryError, match="must be frozenset"):
        inventory.build_inventory(root)
