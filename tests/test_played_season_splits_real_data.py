"""Required played-sample checks on raw rows from one pinned NBA generation.

These tests establish snapshot-row arithmetic, not season completeness, freshness,
absence, injury or on-court presence. A raw-only witness search freezes an opponent
whose samples discriminate both teammate filters; it never consults query output.
"""

from pathlib import Path

import pytest

from nbatools.commands import player_split_summary, team_split_summary
from nbatools.data_source import data_read_csv
from nbatools.query_service import execute_natural_query

pytestmark = [pytest.mark.needs_data, pytest.mark.query]
SEASONS = ["2023-24", "2025-26"]
NAMES = ("Jayson Tatum", "Derrick White")


def _keys(frame):
    return set(zip(frame.game_id.astype(str), frame.team_id.astype(str)))


def _qualified_sample(kind):
    sources = {}
    for season in SEASONS:
        players = data_read_csv(Path(f"data/raw/player_game_stats/{season}_regular_season.csv"))
        teams = data_read_csv(Path(f"data/raw/team_game_stats/{season}_regular_season.csv"))
        for frame, key in (
            (players, ["game_id", "team_id", "player_id"]),
            (teams, ["game_id", "team_id"]),
        ):
            assert not frame.empty, f"Required source missing: {season}"
            assert not frame[key].isna().any().any(), f"Null source keys: {season}"
            assert not frame.duplicated(key).any(), f"Duplicate source keys: {season}"
        base = (
            teams.loc[teams.team_abbr.eq("BOS")]
            if kind == "team"
            else players.loc[players.player_name.eq("Jaylen Brown") & players.team_abbr.eq("BOS")]
        )
        assert not base.empty, f"Required subject coverage missing: {season}"
        played = [
            _keys(players.loc[players.player_name.eq(name) & players.team_abbr.eq("BOS")])
            for name in NAMES
        ]
        sources[season] = (base, played)

    opponents = set.intersection(*(set(base.opponent_team_abbr) for base, _ in sources.values()))
    for opponent in sorted(opponents):
        stages = {}
        for season, (base, played) in sources.items():
            frame = base.loc[base.opponent_team_abbr.eq(opponent)]
            stages[season] = [frame]
            for keys in played:
                frame = frame.loc[
                    [
                        key in keys
                        for key in zip(frame.game_id.astype(str), frame.team_id.astype(str))
                    ]
                ]
                stages[season].append(frame)
        totals = [sum(len(frames[index]) for frames in stages.values()) for index in range(3)]
        if totals[0] > totals[1] > totals[2] > 0:
            return opponent, stages
    pytest.fail("Pinned rows provide no positive opponent sample discriminating BOTH teammates")


@pytest.mark.parametrize("kind", ["team", "player"])
@pytest.mark.parametrize("teammate_count", [1, 2])
def test_played_season_split_matches_raw_keys_and_values(monkeypatch, kind, teammate_count):
    opponent, stages = _qualified_sample(kind)
    expected = {season: frames[teammate_count] for season, frames in stages.items()}
    module = team_split_summary if kind == "team" else player_split_summary
    original = module._summarize_bucket
    seen = {}

    def capture(frame, bucket):
        seen[bucket] = _keys(frame)
        return original(frame, bucket)

    monkeypatch.setattr(module, "_summarize_bucket", capture)
    subject = "Celtics record" if kind == "team" else "Jaylen Brown averages"
    teammate = " and ".join(NAMES[:teammate_count])
    query = f"{subject} with {teammate} playing against {opponent} in 2023-24 and 2025-26"
    result = execute_natural_query(query)
    assert result.result_status == "ok", (query, result.metadata)
    assert result.metadata["with_player"] == teammate
    assert result.metadata["opponent"] == opponent
    assert result.metadata["season_list"] == SEASONS
    rows = result.to_dict()["sections"]["split_comparison"]
    assert [row["bucket"] for row in rows] == [s for s in SEASONS if len(expected[s])]
    for season in SEASONS:
        if expected[season].empty:
            assert any(f"no games in {season}" in note for note in result.result.caveats)
            assert not seen.get(season)
    for row in rows:
        frame = expected[row["bucket"]]
        assert seen[row["bucket"]] == _keys(frame), query
        assert row["games"] == len(frame)
        assert row["wins"] == frame.wl.eq("W").sum()
        assert row["losses"] == frame.wl.eq("L").sum()
        assert row["pts_avg"] == pytest.approx(frame.pts.mean(), abs=0.001)
