"""C1: month splits, the best month and home vs road on real rows (2023-24)."""

from __future__ import annotations

import pandas as pd
import pytest

pytestmark = [pytest.mark.needs_data, pytest.mark.query]


def _months(df: pd.DataFrame) -> pd.DataFrame:
    dates = pd.to_datetime(df["game_date"])
    df = df.assign(
        month=dates.dt.month_name() + " " + dates.dt.year.astype(str),
        key=dates.dt.strftime("%Y-%m"),
    )
    grouped = df.groupby(["key", "month"])
    out = pd.DataFrame(
        {
            "games": grouped.size(),
            "wins": grouped["wl"].apply(lambda s: int((s == "W").sum())),
            "losses": grouped["wl"].apply(lambda s: int((s == "L").sum())),
            "pts_avg": grouped["pts"].mean(),
        }
    ).reset_index()
    out["win_pct"] = (out["wins"] / out["games"]).round(3)
    return out.sort_values("key").reset_index(drop=True)


def _sections(query: str) -> tuple[dict, list[dict], dict]:
    from nbatools.query_service import execute_natural_query

    result = execute_natural_query(query)
    sections = result.result.to_dict()["sections"]
    return sections["summary"][0], sections["split_comparison"], result.metadata


def test_lebron_points_by_month_2023_24():
    from nbatools.commands.data_utils import load_player_games_for_seasons

    rows = load_player_games_for_seasons(["2023-24"], "Regular Season", player="LeBron James")
    rows = rows[rows["player_name"] == "LeBron James"]
    expected = _months(rows)
    _, split, _ = _sections("LeBron points per game by month in 2023-24")
    assert [r["bucket"] for r in split] == list(expected["month"])
    assert [r["games"] for r in split] == list(expected["games"])
    assert [r["pts_avg"] for r in split] == pytest.approx(list(expected["pts_avg"]), abs=1e-3)

    top = expected.sort_values("pts_avg", ascending=False, kind="stable").iloc[0]
    _, ranked, metadata = _sections("best month for LeBron in 2023-24")
    assert ranked[0]["bucket"] == top["month"]
    assert top["month"] in metadata["answer_phrase"]


def test_lakers_record_by_month_and_best_month_2023_24():
    from nbatools.commands.data_utils import load_team_games_for_seasons

    team = load_team_games_for_seasons(["2023-24"], "Regular Season")
    team = team[team["team_abbr"] == "LAL"]
    expected = _months(team)
    _, split, _ = _sections("Lakers record by month in 2023-24")
    assert [(r["bucket"], r["wins"], r["losses"]) for r in split] == list(
        zip(expected["month"], expected["wins"], expected["losses"], strict=True)
    )

    best = expected.sort_values(["win_pct", "wins"], ascending=False, kind="stable").iloc[0]
    _, ranked, metadata = _sections("Lakers best month in 2023-24")
    assert (ranked[0]["wins"], ranked[0]["losses"]) == (best["wins"], best["losses"])
    assert f"{best['wins']}-{best['losses']}" in metadata["answer_phrase"]


def test_lakers_home_vs_road_2023_24():
    from nbatools.commands.data_utils import load_team_games_for_seasons

    team = load_team_games_for_seasons(["2023-24"], "Regular Season")
    team = team[team["team_abbr"] == "LAL"]
    home = team[team["is_home"].astype(int) == 1]
    road = team[team["is_home"].astype(int) == 0]
    summary, split, _ = _sections("Lakers home vs road in 2023-24")
    assert summary["split"] == "home_away"
    assert [(r["bucket"], r["wins"], r["losses"]) for r in split] == [
        ("home", int((home["wl"] == "W").sum()), int((home["wl"] == "L").sum())),
        ("away", int((road["wl"] == "W").sum()), int((road["wl"] == "L").sum())),
    ]
