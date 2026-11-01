"""Merge guards only; these synthetic bytes establish no NBA source qualification."""

import pytest

from tests.cloud_historical_participation_stage_real_data import _merge_roots


def _tree(path, files):
    for name, content in files.items():
        target = path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
    return path


def test_shared_inputs_must_be_identical_and_disjoint_paths_survive(tmp_path):
    first = _tree(
        tmp_path / "first", {"metadata/player_names.csv": b"same base", "raw/first.csv": b"first"}
    )
    second = _tree(
        tmp_path / "second",
        {"metadata/player_names.csv": b"same base", "raw/second.csv": b"second"},
    )
    result = _merge_roots([first, second], tmp_path / "combined")
    assert (result / "metadata/player_names.csv").read_bytes() == b"same base"
    assert (result / "raw/first.csv").read_bytes() == b"first"
    assert (result / "raw/second.csv").read_bytes() == b"second"


def test_conflicting_source_authority_never_overwrites_first_stage(tmp_path):
    relative = "raw/player_game_availability_sources/source.json"
    first = _tree(tmp_path / "first", {relative: b"original"})
    second = _tree(tmp_path / "second", {relative: b"different"})
    with pytest.raises(AssertionError, match="Conflicting stage path"):
        _merge_roots([first, second], tmp_path / "combined")
    assert (first / relative).read_bytes() == b"original"
    assert (second / relative).read_bytes() == b"different"
    assert (tmp_path / "combined/data" / relative).read_bytes() == b"original"


def test_stage_inventory_cannot_be_merged_as_a_new_base(tmp_path):
    first = _tree(tmp_path / "first", {"metadata/generation_manifest.json": b"test-only inventory"})
    with pytest.raises(AssertionError):
        _merge_roots([first], tmp_path / "combined")
