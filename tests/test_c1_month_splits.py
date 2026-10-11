"""C1: splits by month, the best month, and home vs road.

"LeBron points per game by month" and "Lakers record by month" ignored the
month (a season summary); "best month for LeBron" was the same summary;
"Lakers home vs road" refused. A month split has one row per calendar month
of one year ("March 2026"); "best month" ranks those rows. Expectations come
from the fixture's raw game rows.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from nbatools.commands.natural_query import parse_query
from nbatools.query_service import execute_natural_query

pytestmark = [pytest.mark.query, pytest.mark.fixture_data]

RAW = Path("qa/fixtures/query_engine_sample/data/raw")


def _rows(kind: str, season: str = "2025-26", **match) -> pd.DataFrame:
    df = pd.read_csv(RAW / kind / f"{season}_regular_season.csv")
    for column, value in match.items():
        df = df[df[column] == value]
    df = df.copy()
    dates = pd.to_datetime(df["game_date"])
    df["month"] = dates.dt.month_name() + " " + dates.dt.year.astype(str)
    df["key"] = dates.dt.strftime("%Y-%m")
    return df


def _by_month(df: pd.DataFrame) -> pd.DataFrame:
    grouped = df.groupby(["key", "month"])
    out = pd.DataFrame(
        {
            "games": grouped.size(),
            "wins": grouped["wl"].apply(lambda s: int((s == "W").sum())),
            "losses": grouped["wl"].apply(lambda s: int((s == "L").sum())),
            "pts_avg": grouped["pts"].mean().round(3),
            "pts_sum": grouped["pts"].sum(),
            "fg3_pct": (grouped["fg3m"].sum() / grouped["fg3a"].sum()).round(3),
        }
    ).reset_index()
    out["win_pct"] = (out["wins"] / out["games"]).round(3)
    return out.sort_values("key").reset_index(drop=True)


def _split(query: str) -> tuple[dict, list[dict]]:
    sections = execute_natural_query(query).result.to_dict()["sections"]
    return sections["summary"][0], sections["split_comparison"]


def test_player_points_by_month():
    expected = _by_month(_rows("player_game_stats", player_name="LeBron James"))
    summary, rows = _split("LeBron points per game by month")
    assert summary["split"] == "month"
    assert summary["games_total"] == int(expected["games"].sum())
    assert [r["bucket"] for r in rows] == list(expected["month"])
    assert [r["games"] for r in rows] == list(expected["games"])
    assert [r["pts_avg"] for r in rows] == pytest.approx(list(expected["pts_avg"]))
    assert [r["pts_sum"] for r in rows] == pytest.approx(list(expected["pts_sum"]))


def test_team_record_by_month():
    expected = _by_month(_rows("team_game_stats", team_abbr="LAL"))
    _, rows = _split("Lakers record by month")
    assert [(r["bucket"], r["wins"], r["losses"]) for r in rows] == list(
        zip(expected["month"], expected["wins"], expected["losses"], strict=True)
    )


def test_a_span_keeps_each_year_s_months_apart():
    lal = pd.concat(
        [_rows("team_game_stats", season, team_abbr="LAL") for season in ("2024-25", "2025-26")]
    )
    expected = _by_month(lal)
    _, rows = _split("Lakers record by month since 2024")
    assert [r["bucket"] for r in rows] == list(expected["month"])
    assert sum(r["games"] for r in rows) == len(lal)


def test_best_month_for_a_player_is_points_per_game():
    expected = _by_month(_rows("player_game_stats", player_name="LeBron James"))
    top = expected.sort_values("pts_avg", ascending=False, kind="stable").iloc[0]
    result = execute_natural_query("best month for LeBron")
    rows = result.result.to_dict()["sections"]["split_comparison"]
    assert rows[0]["bucket"] == top["month"]
    assert [r["pts_avg"] for r in rows] == sorted(expected["pts_avg"], reverse=True)
    assert result.metadata["answer_phrase"] == (
        "LeBron James's month with the most points per game in the 2025-26 "
        f"regular season: {top['month']} ({top['pts_avg']:.1f} in {top['games']} games)."
    )


def test_team_best_and_worst_month_are_the_record():
    expected = _by_month(_rows("team_game_stats", team_abbr="LAL"))
    best = expected.sort_values(["win_pct", "wins"], ascending=False, kind="stable").iloc[0]
    _, rows = _split("Lakers best month")
    assert (rows[0]["bucket"], rows[0]["wins"], rows[0]["losses"]) == (
        best["month"],
        best["wins"],
        best["losses"],
    )

    worst_pct = expected["win_pct"].min()
    worst = expected[expected["win_pct"] == worst_pct]
    worst = worst[worst["losses"] == worst["losses"].max()]
    result = execute_natural_query("Lakers worst month")
    phrase = result.metadata["answer_phrase"]
    for month in worst["month"]:
        assert month in phrase
    record = f"{worst['wins'].iloc[0]}-{worst['losses'].iloc[0]}"
    assert phrase.startswith("The Los Angeles Lakers' worst month by record")
    assert f"({record}" in phrase


def test_best_three_point_shooting_month_is_the_month_s_rate():
    expected = _by_month(_rows("player_game_stats", player_name="LeBron James"))
    parsed = parse_query("LeBron best 3 point shooting month")
    assert parsed["route_kwargs"]["rank_stat"] == "fg3_pct"
    assert parsed["route_kwargs"].get("min_value") is None
    _, rows = _split("LeBron best 3 point shooting month")
    assert rows[0]["fg3_pct_avg"] == pytest.approx(expected["fg3_pct"].max())


def test_which_month_most_qualifying_games_counts_them():
    lebron = _rows("player_game_stats", player_name="LeBron James")
    counts = lebron[lebron["pts"] >= 30].groupby(["key", "month"]).size()
    _, rows = _split("which month did LeBron have the most 30 point games")
    assert rows[0]["games"] == counts.max()
    assert sum(r["games"] for r in rows) == counts.sum()


def test_which_month_most_wins_counts_every_game():
    expected = _by_month(_rows("team_game_stats", team_abbr="LAL"))
    parsed = parse_query("which month did the Lakers win the most games")
    assert not parsed["route_kwargs"].get("wins_only")
    _, rows = _split("which month did the Lakers win the most games")
    assert rows[0]["wins"] == expected["wins"].max()
    assert sum(r["games"] for r in rows) == expected["games"].sum()


def test_a_bound_on_another_stat_stays_a_filter():
    parsed = parse_query("Curry free throw shooting by month in games with 30 points")
    kwargs = parsed["route_kwargs"]
    assert (kwargs["split"], kwargs["stat"], kwargs["min_value"]) == ("month", "pts", 30.0)
    parsed = parse_query("Curry 3 point shooting by month")
    kwargs = parsed["route_kwargs"]
    assert (kwargs["stat"], kwargs.get("min_value")) == ("fg3_pct", None)


@pytest.mark.parametrize(
    "query",
    ["Lakers home vs road", "Lakers home and away record", "Lakers road vs home splits"],
)
def test_home_and_road_is_a_split(query):
    lal = _rows("team_game_stats", team_abbr="LAL")
    home = lal[lal["is_home"] == 1]
    road = lal[lal["is_home"] == 0]
    summary, rows = _split(query)
    assert summary["split"] == "home_away"
    assert [(r["bucket"], r["wins"], r["losses"]) for r in rows] == [
        ("home", int((home["wl"] == "W").sum()), int((home["wl"] == "L").sum())),
        ("away", int((road["wl"] == "W").sum()), int((road["wl"] == "L").sum())),
    ]


@pytest.mark.parametrize(
    "query",
    [
        "LeBron points last month",
        "LeBron points this month",
        "Lakers record in the last month",
        "LeBron player of the month",
        "which month did the Lakers start",
        "LeBron best game",
        # Months with none of the games are not in the split.
        "which month did LeBron have the fewest 30 point games",
    ],
)
def test_other_month_wording_is_not_a_month_split(query):
    try:
        parsed = parse_query(query)
    except ValueError:
        return
    assert (parsed.get("route_kwargs") or {}).get("split") != "month"


def _team_rate_by_month(made: str, attempts: str, **match) -> pd.DataFrame:
    rows = _rows("team_game_stats", team_abbr="LAL", **match)
    grouped = rows.groupby(["key", "month"])
    out = (grouped[made].sum() / grouped[attempts].sum()).round(3).reset_index(name="rate")
    return out.sort_values("key").reset_index(drop=True)


@pytest.mark.parametrize(
    ("query", "column", "made", "attempts"),
    [
        ("Lakers 3 point percentage by month", "fg3_pct_avg", "fg3m", "fg3a"),
        ("Lakers field goal percentage by month", "fg_pct_avg", "fgm", "fga"),
        ("Lakers free throw percentage by month", "ft_pct_avg", "ftm", "fta"),
    ],
)
def test_team_rates_by_month_are_the_month_s_totals(query, column, made, attempts):
    expected = _team_rate_by_month(made, attempts)
    _, rows = _split(query)
    assert [r["bucket"] for r in rows] == list(expected["month"])
    assert [r[column] for r in rows] == pytest.approx(list(expected["rate"]))


def test_team_best_shooting_month():
    expected = _team_rate_by_month("fg3m", "fg3a")
    top = expected.sort_values("rate", ascending=False, kind="stable").iloc[0]
    result = execute_natural_query("Lakers best 3 point shooting month")
    assert result.result.to_dict()["sections"]["split_comparison"][0]["bucket"] == top["month"]
    assert f"{top['month']} ({top['rate'] * 100:.1f}%" in result.metadata["answer_phrase"]


def test_team_home_record_by_month():
    home = _by_month(_rows("team_game_stats", team_abbr="LAL", is_home=1))
    _, rows = _split("Lakers home record by month")
    assert [(r["bucket"], r["wins"], r["losses"]) for r in rows] == list(
        zip(home["month"], home["wins"], home["losses"], strict=True)
    )


def test_a_bounded_sample_still_shows_the_named_rate():
    curry = _rows("player_game_stats", player_name="Stephen Curry")
    curry = curry[curry["pts"] >= 30]
    grouped = curry.groupby(["key", "month"])
    attempts = grouped["fta"].sum()
    rate = (grouped["ftm"].sum() / attempts.where(attempts > 0)).round(3).reset_index()
    _, rows = _split("Curry free throw shooting by month in games with 30 points")
    assert [r["bucket"] for r in rows] == list(rate["month"])
    got = [r["ft_pct_avg"] for r in rows]
    expected = [None if pd.isna(v) else v for v in rate[0]]
    assert got == pytest.approx(expected)


def test_score_the_most_points_ranks_the_month_s_total():
    lebron = _by_month(_rows("player_game_stats", player_name="LeBron James"))
    top = lebron.sort_values("pts_sum", ascending=False, kind="stable").iloc[0]
    result = execute_natural_query("which month did LeBron score the most points")
    assert result.result.to_dict()["sections"]["split_comparison"][0]["bucket"] == top["month"]
    assert result.metadata["answer_phrase"].endswith(
        f"{top['month']} ({top['pts_sum']:g} in {top['games']} games)."
    )
    averaged = parse_query("which month did LeBron average the most points")
    assert averaged["route_kwargs"]["rank_stat"] == "pts"


@pytest.mark.parametrize(
    "query",
    [
        # Comparisons, leaders and a team asked about in a player's games
        # have no month split: they refuse instead of dropping the month.
        "LeBron vs Curry by month",
        "LeBron vs Curry best month",
        "Lakers vs Celtics by month",
        "Lakers leading scorer by month",
        "Lakers best month in games LeBron scored 30",
        "Lakers best month in LeBron's 30 point games",
        "Lakers best month if LeBron scores 30",
        "Lakers best month after LeBron scored 30",
    ],
)
def test_month_splits_the_routes_cannot_build_refuse(query):
    result = execute_natural_query(query)
    assert result.result_status == "no_result"
    assert "month_split" in (parse_query(query)["route_kwargs"].get("unsupported_filters") or [])


@pytest.mark.parametrize(
    ("query", "player"),
    [
        ("Jokic points by month for the Nuggets", "Nikola Jokić"),
        ("Steph points by month for the Warriors", "Stephen Curry"),
        ("AD points by month for the Lakers", "Anthony Davis"),
        ("Lakers LeBron points by month", "LeBron James"),
        ("Warriors Curry best month", "Stephen Curry"),
        ("LeBron points by month in games the Lakers won", "LeBron James"),
    ],
)
def test_a_player_with_a_team_named_is_still_his_month_split(query, player):
    parsed = parse_query(query)
    assert parsed["route"] == "player_split_summary"
    assert parsed["route_kwargs"]["split"] == "month"
    assert parsed["route_kwargs"]["player"] == player


def test_who_inside_a_filter_is_not_a_leader_question():
    parsed = parse_query("Lakers record by month against teams who made the playoffs")
    assert parsed["route"] == "team_split_summary"
    assert not parsed["route_kwargs"].get("unsupported_filters")
