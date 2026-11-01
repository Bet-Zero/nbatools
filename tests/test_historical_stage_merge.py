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


@pytest.fixture
def count_snapshot(tmp_path, monkeypatch):
    from tests.test_participation_coverage import snapshot

    yield from snapshot.__wrapped__(tmp_path, monkeypatch)


@pytest.mark.parametrize("zero", [False, True], ids=["five-explicit-DNP", "qualified-zero"])
def test_missed_count_and_structured_list_have_distinct_output_contracts(count_snapshot, zero):
    import pandas as pd

    from nbatools.query_service import execute_natural_query
    from tests.cloud_historical_participation_stage_real_data import _assert_missed_count_and_rows
    from tests.test_participation_coverage import SUFFIX

    root, games, bind = count_snapshot
    player_path = root / "raw/player_game_stats" / SUFFIX
    players = pd.read_csv(player_path)
    more_games = games.iloc[60:] if zero else games.iloc[65:]
    added = pd.DataFrame([players.iloc[0]] * len(more_games)).reset_index(drop=True)
    added["game_id"] = more_games.game_id.to_numpy()
    added["game_date"] = more_games.game_date.to_numpy()
    pd.concat([players, added], ignore_index=True).to_csv(player_path, index=False)
    if zero:
        (root / "raw/player_game_availability" / SUFFIX).unlink()
    bind()
    query = "how many games did LeBron James miss in 2025-26"
    ids = set() if zero else set(games.game_id.iloc[60:65].astype(int))
    counted = execute_natural_query(query)
    assert counted.result.to_dict()["sections"]["count"] == [{"count": len(ids)}]
    if zero:
        assert "finder" not in counted.result.to_dict()["sections"]
    _assert_missed_count_and_rows(
        query, ids, season="2025-26", team="LAL", player="LeBron James", home_only=False
    )
