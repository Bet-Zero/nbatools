"""Staging must reject mutable refs, overwrites and wrong source schemas."""

import json

import pytest

from tools.cloud_nba_archive import _official_table, prepare


def test_requires_immutable_mirror_revision(tmp_path):
    with pytest.raises(ValueError, match="immutable"):
        prepare(tmp_path / "new", revision="main")
    assert not (tmp_path / "new").exists()


def test_preserves_existing_destination(tmp_path):
    existing = tmp_path / "state"
    existing.mkdir()
    (existing / "checkpoint").write_text("preserve")
    with pytest.raises(FileExistsError):
        prepare(existing)
    assert (existing / "checkpoint").read_text() == "preserve"


@pytest.mark.parametrize("tables", [[], [{"name": "WrongGrain"}]])
def test_rejects_wrong_official_table(tmp_path, tables):
    source = tmp_path / "source.json"
    source.write_text(json.dumps({"resultSets": tables}))
    with pytest.raises(ValueError, match="exactly one"):
        _official_table(source, "LeagueGameLog")


def test_rejects_duplicate_columns(tmp_path):
    source = tmp_path / "source.json"
    source.write_text(
        json.dumps(
            {"resultSets": [{"name": "LeagueGameLog", "headers": ["A", "A"], "rowSet": [[1, 2]]}]}
        )
    )
    with pytest.raises(ValueError, match="Duplicate"):
        _official_table(source, "LeagueGameLog")
