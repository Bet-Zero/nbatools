from __future__ import annotations

import pandas as pd
import pytest

from nbatools.commands.data_utils import (
    load_league_lineup_viz_for_seasons,
    select_trusted_league_lineup_viz_rows,
)
from nbatools.commands.lineup_leaderboard import build_result as build_lineup_leaderboard
from nbatools.commands.lineup_summary import build_result as build_lineup_summary
from nbatools.commands.pipeline.pull_league_lineup_viz import (
    build_league_lineup_viz_backfill,
    normalize_league_lineup_viz,
)
from nbatools.commands.pipeline.validate_raw import validate_league_lineup_viz_df
from nbatools.commands.structured_results import LeaderboardResult, NoResult, SummaryResult

pytestmark = pytest.mark.engine


def _source_row(
    *,
    group_id: str = "-1628369-1627759-201950-203110-201143-",
    group_name: str = "Jayson Tatum - Jaylen Brown - Jrue Holiday - Al Horford - Kristaps Porzingis",
    team_id: int = 1610612738,
    team_abbr: str = "BOS",
    minutes: float = 250.0,
    net_rating: float = 12.5,
) -> dict:
    return {
        "GROUP_ID": group_id,
        "GROUP_NAME": group_name,
        "TEAM_ID": team_id,
        "TEAM_ABBREVIATION": team_abbr,
        "MIN": minutes,
        "OFF_RATING": 124.2,
        "DEF_RATING": 111.7,
        "NET_RATING": net_rating,
        "PACE": 98.4,
        "TS_PCT": 0.628,
    }


def _normalized_lineup_df() -> pd.DataFrame:
    return normalize_league_lineup_viz(
        pd.DataFrame([_source_row()]),
        season="2099-00",
        season_type="Regular Season",
        unit_size=5,
        minute_minimum=25,
        source_pull_date="2099-01-01",
    )


def _normalized_two_man_df() -> pd.DataFrame:
    return normalize_league_lineup_viz(
        pd.DataFrame(
            [
                _source_row(
                    group_id="-1628369-1627759-",
                    group_name="Jayson Tatum - Jaylen Brown",
                    net_rating=11.0,
                ),
                _source_row(
                    group_id="-203999-203932-",
                    group_name="Nikola Jokic - Aaron Gordon",
                    team_id=1610612743,
                    team_abbr="DEN",
                    net_rating=15.0,
                ),
            ]
        ),
        season="2099-00",
        season_type="Regular Season",
        unit_size=2,
        minute_minimum=0,
        source_pull_date="2099-01-01",
    )


def test_normalize_league_lineup_viz_parses_membership_and_marks_trusted():
    df = _normalized_lineup_df()

    assert df["coverage_trusted"].tolist() == [1]
    assert df["coverage_validation_reason"].fillna("").tolist() == [""]
    assert df["player_ids"].tolist() == ["1628369|1627759|201950|203110|201143"]
    assert df["player_names"].tolist() == [
        "Jayson Tatum|Jaylen Brown|Jrue Holiday|Al Horford|Kristaps Porzingis"
    ]
    assert set(["minutes", "off_rating", "def_rating", "net_rating", "pace", "ts_pct"]).issubset(
        df.columns
    )


def test_normalize_league_lineup_viz_marks_membership_mismatch_untrusted():
    df = normalize_league_lineup_viz(
        pd.DataFrame([_source_row(group_id="-1628369-1627759-")]),
        season="2099-00",
        season_type="Regular Season",
        unit_size=5,
        minute_minimum=25,
        source_pull_date="2099-01-01",
    )

    assert df["coverage_trusted"].tolist() == [0]
    assert df["coverage_validation_reason"].tolist() == ["player_id_count_mismatch"]


def test_validate_league_lineup_viz_rejects_duplicate_keys():
    df = pd.concat([_normalized_lineup_df(), _normalized_lineup_df()], ignore_index=True)

    with pytest.raises(ValueError, match="Duplicate"):
        validate_league_lineup_viz_df(df)


def test_validate_league_lineup_viz_rejects_trust_mismatch():
    df = _normalized_lineup_df()
    df["coverage_trusted"] = 0

    with pytest.raises(ValueError, match="coverage_trusted mismatch"):
        validate_league_lineup_viz_df(df)


def test_load_league_lineup_viz_for_seasons_requires_all_files(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    with pytest.raises(FileNotFoundError, match="league_lineup_viz"):
        load_league_lineup_viz_for_seasons(["2099-00"], "Regular Season")


def test_load_league_lineup_viz_for_seasons_accepts_valid_dataset(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    out_dir = tmp_path / "data/raw/league_lineup_viz"
    out_dir.mkdir(parents=True)
    _normalized_lineup_df().to_csv(out_dir / "2099-00_regular_season.csv", index=False)

    loaded = load_league_lineup_viz_for_seasons(["2099-00"], "Regular Season")

    assert len(loaded) == 1
    assert loaded["unit_size"].tolist() == [5]
    assert loaded["minute_minimum"].tolist() == [25]


def test_load_league_lineup_viz_for_seasons_rejects_untrusted_reason_mismatch(
    tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    out_dir = tmp_path / "data/raw/league_lineup_viz"
    out_dir.mkdir(parents=True)
    df = _normalized_lineup_df()
    df["coverage_trusted"] = 0
    df.to_csv(out_dir / "2099-00_regular_season.csv", index=False)

    with pytest.raises(ValueError, match="coverage_trusted mismatch"):
        load_league_lineup_viz_for_seasons(["2099-00"], "Regular Season")


def test_select_trusted_league_lineup_viz_rows_filters_lineup_and_reports_failures():
    trusted = _normalized_lineup_df()
    untrusted = normalize_league_lineup_viz(
        pd.DataFrame(
            [
                _source_row(
                    group_id="-1628369-1627759-",
                    team_id=1610612747,
                    team_abbr="LAL",
                    net_rating=-4.0,
                )
            ]
        ),
        season="2099-00",
        season_type="Regular Season",
        unit_size=5,
        minute_minimum=25,
        source_pull_date="2099-01-01",
    )
    df = pd.concat([trusted, untrusted], ignore_index=True)

    selected, failures = select_trusted_league_lineup_viz_rows(
        df,
        unit_size=5,
        minute_minimum=25,
        lineup_members=["Jayson Tatum", "Jaylen Brown"],
    )

    assert selected["team_abbr"].tolist() == ["BOS"]
    assert failures == ["player_id_count_mismatch"]


def test_build_league_lineup_viz_backfill_uses_unit_and_minute_sources(monkeypatch):
    from nbatools.commands.pipeline import pull_league_lineup_viz as puller

    calls: list[tuple[int, int]] = []

    def fake_fetch(*, season: str, season_type: str, unit_size: int, minute_minimum: int):
        calls.append((unit_size, minute_minimum))
        return pd.DataFrame(
            [
                _source_row(
                    group_id=f"-{unit_size}{minute_minimum}01-{unit_size}{minute_minimum}02-",
                    group_name="Player One - Player Two",
                    team_id=1610612738,
                )
            ]
        )

    monkeypatch.setattr(puller, "fetch_league_lineup_viz", fake_fetch)

    df = build_league_lineup_viz_backfill(
        "2099-00",
        "Regular Season",
        unit_sizes=(2,),
        minute_minimums=(0, 25),
    )

    assert calls == [(2, 0), (2, 25)]
    assert len(df) == 2
    assert set(df["minute_minimum"]) == {0, 25}


def test_lineup_summary_returns_source_backed_rows(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    out_dir = tmp_path / "data/raw/league_lineup_viz"
    out_dir.mkdir(parents=True)
    _normalized_two_man_df().to_csv(out_dir / "2099-00_regular_season.csv", index=False)

    result = build_lineup_summary(
        season="2099-00",
        season_type="Regular Season",
        lineup_members=["Jayson Tatum", "Jaylen Brown"],
    )

    assert isinstance(result, SummaryResult)
    assert result.summary["team_abbr"].tolist() == ["BOS"]
    assert result.summary["unit_size"].tolist() == [2]
    assert result.summary["net_rating"].tolist() == [11.0]


def test_lineup_leaderboard_returns_ranked_source_backed_rows(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    out_dir = tmp_path / "data/raw/league_lineup_viz"
    out_dir.mkdir(parents=True)
    _normalized_two_man_df().to_csv(out_dir / "2099-00_regular_season.csv", index=False)

    result = build_lineup_leaderboard(
        season="2099-00",
        season_type="Regular Season",
        unit_size=2,
        limit=1,
    )

    assert isinstance(result, LeaderboardResult)
    assert result.leaders["rank"].tolist() == [1]
    assert result.leaders["team_abbr"].tolist() == ["DEN"]
    assert result.leaders["net_rating"].tolist() == [15.0]


def test_lineup_routes_keep_unsupported_response_when_dataset_missing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    result = build_lineup_summary(
        season="2099-00",
        season_type="Regular Season",
        lineup_members=["Jayson Tatum", "Jaylen Brown"],
    )

    assert isinstance(result, NoResult)
    assert result.reason == "unsupported"
    assert any("coverage" in note for note in result.notes)


def test_lineup_summary_rejects_untrusted_coverage(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    out_dir = tmp_path / "data/raw/league_lineup_viz"
    out_dir.mkdir(parents=True)
    df = normalize_league_lineup_viz(
        pd.DataFrame(
            [
                _source_row(
                    group_id="-1628369-1627759-",
                    group_name="Jayson Tatum - Jaylen Brown",
                )
            ]
        ),
        season="2099-00",
        season_type="Regular Season",
        unit_size=5,
        minute_minimum=0,
        source_pull_date="2099-01-01",
    )
    df.to_csv(out_dir / "2099-00_regular_season.csv", index=False)

    result = build_lineup_summary(
        season="2099-00",
        season_type="Regular Season",
        lineup_members=["Jayson Tatum", "Jaylen Brown"],
        unit_size=5,
    )

    assert isinstance(result, NoResult)
    assert result.reason == "unsupported"
    assert any("coverage" in note for note in result.notes)


def test_lineup_leaderboard_rejects_unsupported_unit_size():
    result = build_lineup_leaderboard(
        season="2099-00",
        season_type="Regular Season",
        unit_size=6,
    )

    assert isinstance(result, NoResult)
    assert result.reason == "unsupported"
    assert any("unit_size=6" in note for note in result.notes)
