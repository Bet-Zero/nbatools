"""Two-team questions and opponent quality inside groups and comparisons.

"Lakers and Warriors last 10 games vs the Celtics" is each team's games
against Boston; "compare the Lakers and Warriors vs winning teams" filters
both teams; "Celtics record vs Atlantic Division winning teams" needs both
the division and the bar. Expected values come from the fixture CSVs.
"""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

pytestmark = [pytest.mark.fixture_data, pytest.mark.query]

RAW = Path("qa/fixtures/query_engine_sample/data/raw")
SEASONS = ("2023-24", "2024-25", "2025-26")


def _csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _games(season: str, **match: str) -> list[dict[str, str]]:
    rows = _csv(RAW / "team_game_stats" / f"{season}_regular_season.csv")
    rows = [r for r in rows if all(r[k] == v for k, v in match.items())]
    return sorted(rows, key=lambda r: (r["game_date"], int(r["game_id"])), reverse=True)


def _winning(season: str) -> set[str]:
    rows = _csv(RAW / "standings_snapshots" / f"{season}_regular_season.csv")
    return {r["team_id"] for r in rows if float(r["win_pct"]) >= 0.5}


def _run(query: str):
    from nbatools.query_service import execute_natural_query

    result = execute_natural_query(query)
    assert result.result_status == "ok", (query, result.result_reason, result.metadata)
    return result


def _summary(query: str):
    return _run(query).result.to_dict()["sections"]["summary"]


def _wins(rows) -> int:
    return sum(r["wl"] == "W" for r in rows)


def test_pair_last_n_vs_a_third_team_is_each_teams_games_against_it():
    expected = {}
    for abbr in ("LAL", "GSW"):
        rows = [r for s in SEASONS for r in _games(s, team_abbr=abbr, opponent_team_abbr="BOS")]
        rows.sort(key=lambda r: (r["game_date"], int(r["game_id"])), reverse=True)
        expected[abbr] = rows[:10]
    lakers, warriors = _summary("Lakers and Warriors last 10 games vs the Celtics")
    assert lakers["games"] == warriors["games"] == 10
    assert lakers["wins"] == _wins(expected["LAL"])
    assert warriors["wins"] == _wins(expected["GSW"])


def test_compare_pair_vs_a_third_team_keeps_the_pair():
    lakers, warriors = _summary("compare Lakers and Warriors vs the Celtics")
    for side, abbr in ((lakers, "LAL"), (warriors, "GSW")):
        rows = _games("2025-26", team_abbr=abbr, opponent_team_abbr="BOS")
        assert side["games"] == len(rows)
        assert side["wins"] == _wins(rows)


def test_pair_record_is_each_teams_record():
    lakers, warriors = _summary("Lakers and Warriors record this season")
    assert lakers["games"] == len(_games("2025-26", team_abbr="LAL"))
    assert warriors["wins"] == _wins(_games("2025-26", team_abbr="GSW"))


def test_versus_pair_record_is_still_their_meetings():
    result = _run("Lakers vs Warriors record")
    assert result.route == "team_matchup_record"


def test_compare_pair_vs_winning_teams_is_season_by_season():
    lakers, warriors = _summary("compare Lakers and Warriors vs winning teams since 2023-24")
    for side, abbr in ((lakers, "LAL"), (warriors, "GSW")):
        rows = [
            r
            for s in SEASONS
            for r in _games(s, team_abbr=abbr)
            if r["opponent_team_id"] in _winning(s)
        ]
        assert side["games"] == len(rows)
        assert side["wins"] == _wins(rows)


def test_head_to_head_with_quality_refuses():
    from nbatools.query_service import execute_natural_query

    result = execute_natural_query("Lakers vs Warriors head to head vs winning teams")
    assert result.result_status == "no_result"


def test_division_and_quality_both_apply():
    atlantic = {
        r["team_id"]
        for r in _csv(RAW / "teams" / "team_conference_membership.csv")
        if r["season"] == "2024-25" and r["division"] == "Atlantic"
    }
    rows = [
        r
        for r in _games("2024-25", team_abbr="BOS")
        if r["opponent_team_id"] in atlantic and r["opponent_team_id"] in _winning("2024-25")
    ]
    (summary,) = _summary("Celtics record vs Atlantic Division winning teams 2024-25")
    assert summary["games"] == len(rows)
    assert summary["wins"] == _wins(rows)
