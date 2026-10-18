"""Fixture-only integrity controls for the deterministic availability combiner."""

import copy
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "combiner", ROOT / "tools/combine_availability_package.py"
)
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)
pytestmark = [pytest.mark.fixture_data, pytest.mark.engine]


def source(tmp_path, name, game):
    root = tmp_path / name
    directory = root / "raw/player_game_availability"
    directory.mkdir(parents=True)
    (directory / "2025-26_regular_season.csv").write_text(
        f'game_id,team_id,player_id,source_comment\n{game:010d},1,2,"DNP, explicit"\n'
    )
    (directory / "2025-26_regular_season.imports.json").write_text(
        json.dumps({str(game): {"sha256": name, "source": "report"}})
    )
    retained = root / "raw/player_game_availability_sources/receipt.json"
    retained.parent.mkdir()
    retained.write_text('{"source":"same"}\n')
    inventory = dict(
        base_generation="base",
        reviewed_sha="a" * 40,
        request_sha="b" * 40,
        run_id=1,
        artifact_id=2,
        artifact_zip_sha256="c" * 64,
    )
    pin(root, inventory)
    return root, inventory


def pin(root, inventory):
    inventory["files"] = [
        dict(
            path=p.relative_to(root).as_posix(),
            size_bytes=p.stat().st_size,
            sha256=hashlib.sha256(p.read_bytes()).hexdigest(),
        )
        for p in sorted(root.rglob("*"))
        if p.is_file()
    ]


def test_disjoint_union_is_lossless_deterministic_and_keeps_lineage(tmp_path):
    first, second = source(tmp_path, "one", 10), source(tmp_path, "two", 20)
    out = tmp_path / "out"
    receipt = builder.combine([first, second], out, candidate_sha="d" * 40)
    assert list(receipt["row_counts"].values()) == [2]
    csv = (out / "raw/player_game_availability/2025-26_regular_season.csv").read_text()
    assert '0000000010,1,2,"DNP, explicit"' in csv
    assert '0000000020,1,2,"DNP, explicit"' in csv
    lineage = json.loads(
        (out / "raw/player_game_availability/2025-26_regular_season.imports.json").read_text()
    )
    assert lineage == {
        "10": {"sha256": "one", "source": "report"},
        "20": {"sha256": "two", "source": "report"},
    }
    other = tmp_path / "other"
    builder.combine([first, second], other, candidate_sha="d" * 40)
    assert {p.relative_to(out): p.read_bytes() for p in out.rglob("*") if p.is_file()} == {
        p.relative_to(other): p.read_bytes() for p in other.rglob("*") if p.is_file()
    }
    with pytest.raises(ValueError, match="new directory"):
        builder.combine([first], out, candidate_sha="d" * 40)


@pytest.mark.parametrize(
    "defect",
    [
        "checksum",
        "extra",
        "missing",
        "symlink",
        "duplicate_inventory",
        "unsafe_path",
        "base",
        "overlap",
        "conflicting_source",
        "missing_lineage",
        "extra_lineage",
        "duplicate_row",
    ],
)
def test_corrupt_or_conflicting_inputs_fail_closed(tmp_path, defect):
    first, second = source(tmp_path, "one", 10), source(tmp_path, "two", 20)
    root, inventory = second
    inventory = copy.deepcopy(inventory)
    second = root, inventory
    csv = root / "raw/player_game_availability/2025-26_regular_season.csv"
    lineage = csv.with_suffix(".imports.json")
    if defect == "checksum":
        csv.write_text(csv.read_text() + " ")
    elif defect == "extra":
        (root / "extra").write_text("unreviewed")
    elif defect == "missing":
        csv.unlink()
    elif defect == "symlink":
        csv.rename(root / "target")
        csv.symlink_to(root / "target")
        pin(root, inventory)
    elif defect == "duplicate_inventory":
        inventory["files"].append(inventory["files"][0])
    elif defect == "unsafe_path":
        inventory["files"][0]["path"] = "../escape"
    elif defect == "base":
        inventory["base_generation"] = "changed"
    elif defect == "overlap":
        second = source(tmp_path, "overlap", 10)
    elif defect == "conflicting_source":
        (root / "raw/player_game_availability_sources/receipt.json").write_text("different")
        pin(root, inventory)
    elif defect == "missing_lineage":
        lineage.unlink()
        pin(root, inventory)
    elif defect == "extra_lineage":
        lineage.write_text(json.dumps({"20": {}, "30": {}}))
        pin(root, inventory)
    elif defect == "duplicate_row":
        csv.write_text(csv.read_text() + csv.read_text().splitlines()[-1] + "\n")
        pin(root, inventory)
    out = tmp_path / "out"
    with pytest.raises(ValueError):
        builder.combine([first, second], out, candidate_sha="d" * 40)
    assert not out.exists()
