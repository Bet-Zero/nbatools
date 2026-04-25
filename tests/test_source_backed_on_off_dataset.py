from __future__ import annotations

import pandas as pd
import pytest

from nbatools.commands.data_utils import load_team_player_on_off_summary_for_seasons
from nbatools.commands.pipeline.pull_team_player_on_off_summary import (
    build_team_player_on_off_summary_backfill,
    normalize_team_player_on_off_summary,
)
from nbatools.commands.pipeline.validate_raw import validate_team_player_on_off_summary_df
from nbatools.commands.player_on_off import build_result as build_on_off_result
from nbatools.commands.structured_results import NoResult, SummaryResult


def _source_row(court_status: str, *, player_id: int = 203999) -> dict:
    return {
        "TEAM_ID": 1610612743,
        "TEAM_ABBREVIATION": "DEN",
        "TEAM_NAME": "Denver Nuggets",
        "VS_PLAYER_ID": player_id,
        "VS_PLAYER_NAME": "Nikola Jokic",
        "COURT_STATUS": court_status,
        "GP": 70,
        "MIN": 2400.0 if court_status == "On" else 960.0,
        "PLUS_MINUS": 420.0 if court_status == "On" else -80.0,
        "OFF_RATING": 123.4 if court_status == "On" else 111.2,
        "DEF_RATING": 111.1 if court_status == "On" else 116.0,
        "NET_RATING": 12.3 if court_status == "On" else -4.8,
    }


def _normalized_on_off_df() -> pd.DataFrame:
    return normalize_team_player_on_off_summary(
        pd.DataFrame([_source_row("On")]),
        pd.DataFrame([_source_row("Off")]),
        season="2099-00",
        season_type="Regular Season",
        source_pull_date="2099-01-01",
    )


def test_normalize_team_player_on_off_summary_marks_complete_pairs_trusted():
    df = _normalized_on_off_df()

    assert set(df["presence_state"]) == {"on", "off"}
    assert df["coverage_trusted"].eq(1).all()
    assert df["coverage_validation_reason"].fillna("").eq("").all()
    assert set(["off_rating", "def_rating", "net_rating"]).issubset(df.columns)


def test_normalize_team_player_on_off_summary_marks_missing_pair_untrusted():
    df = normalize_team_player_on_off_summary(
        pd.DataFrame([_source_row("On")]),
        pd.DataFrame([_source_row("Off", player_id=204001)]),
        season="2099-00",
        season_type="Regular Season",
        source_pull_date="2099-01-01",
    )

    assert df["coverage_trusted"].eq(0).all()
    assert df["coverage_validation_reason"].eq("missing_presence_state").all()


def test_validate_team_player_on_off_summary_rejects_duplicate_presence_rows():
    df = pd.concat([_normalized_on_off_df(), _normalized_on_off_df()], ignore_index=True)

    with pytest.raises(ValueError, match="Duplicate"):
        validate_team_player_on_off_summary_df(df)


def test_validate_team_player_on_off_summary_rejects_trust_mismatch():
    df = _normalized_on_off_df()
    df.loc[df["presence_state"].eq("on"), "coverage_trusted"] = 0

    with pytest.raises(ValueError, match="coverage_trusted mismatch"):
        validate_team_player_on_off_summary_df(df)


def test_load_team_player_on_off_summary_for_seasons_requires_all_files(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    with pytest.raises(FileNotFoundError, match="team_player_on_off_summary"):
        load_team_player_on_off_summary_for_seasons(["2099-00"], "Regular Season")


def test_load_team_player_on_off_summary_for_seasons_accepts_valid_dataset(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    out_dir = tmp_path / "data/raw/team_player_on_off_summary"
    out_dir.mkdir(parents=True)
    _normalized_on_off_df().to_csv(out_dir / "2099-00_regular_season.csv", index=False)

    loaded = load_team_player_on_off_summary_for_seasons(["2099-00"], "Regular Season")

    assert len(loaded) == 2
    assert set(loaded["presence_state"]) == {"on", "off"}


def test_build_team_player_on_off_summary_backfill_uses_team_sources(monkeypatch):
    from nbatools.commands.pipeline import pull_team_player_on_off_summary as puller

    monkeypatch.setattr(puller, "team_ids", lambda: [1610612743])
    monkeypatch.setattr(
        puller,
        "fetch_team_player_on_off_summary_for_team",
        lambda team_id, season, season_type: (
            pd.DataFrame([_source_row("On")]),
            pd.DataFrame([_source_row("Off")]),
        ),
    )

    df = build_team_player_on_off_summary_backfill("2099-00", "Regular Season")

    assert len(df) == 2
    assert df["team_id"].eq(1610612743).all()
    assert df["coverage_trusted"].eq(1).all()


def test_player_on_off_returns_source_backed_summary(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    out_dir = tmp_path / "data/raw/team_player_on_off_summary"
    out_dir.mkdir(parents=True)
    _normalized_on_off_df().to_csv(out_dir / "2099-00_regular_season.csv", index=False)

    result = build_on_off_result(
        season="2099-00",
        season_type="Regular Season",
        lineup_members=["Nikola Jokic"],
        presence_state="both",
    )

    assert isinstance(result, SummaryResult)
    assert set(result.summary["presence_state"]) == {"on", "off"}
    assert result.summary["off_rating"].tolist() == [111.2, 123.4]


def test_player_on_off_filters_presence_state(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    out_dir = tmp_path / "data/raw/team_player_on_off_summary"
    out_dir.mkdir(parents=True)
    _normalized_on_off_df().to_csv(out_dir / "2099-00_regular_season.csv", index=False)

    result = build_on_off_result(
        season="2099-00",
        season_type="Regular Season",
        lineup_members=["Nikola Jokić"],
        presence_state="on",
    )

    assert isinstance(result, SummaryResult)
    assert result.summary["presence_state"].tolist() == ["on"]


def test_player_on_off_keeps_placeholder_when_dataset_missing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    result = build_on_off_result(
        season="2099-00",
        season_type="Regular Season",
        lineup_members=["Nikola Jokić"],
        presence_state="both",
    )

    assert isinstance(result, NoResult)
    assert result.reason == "unsupported"
    assert any("placeholder" in note for note in result.notes)


def test_player_on_off_rejects_untrusted_coverage(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    out_dir = tmp_path / "data/raw/team_player_on_off_summary"
    out_dir.mkdir(parents=True)
    df = _normalized_on_off_df()
    df["coverage_trusted"] = 0
    df["coverage_validation_reason"] = "missing_presence_state"
    df.to_csv(out_dir / "2099-00_regular_season.csv", index=False)

    result = build_on_off_result(
        season="2099-00",
        season_type="Regular Season",
        lineup_members=["Nikola Jokić"],
        presence_state="both",
    )

    assert isinstance(result, NoResult)
    assert result.reason == "unsupported"
    assert any("coverage" in note for note in result.notes)


def test_player_on_off_rejects_multi_player_requests():
    result = build_on_off_result(
        season="2099-00",
        season_type="Regular Season",
        lineup_members=["Nikola Jokić", "Aaron Gordon"],
        presence_state="both",
    )

    assert isinstance(result, NoResult)
    assert result.reason == "unsupported"
    assert any("multi-player" in note for note in result.notes)
