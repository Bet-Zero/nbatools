"""TEMPORARY discovery probe (removed before merge): list shared player names."""

from __future__ import annotations

import pytest

from nbatools.data_source import data_glob, data_read_csv

pytestmark = [pytest.mark.needs_data]


def test_list_shared_names():
    import pandas as pd

    frames = []
    for path in data_glob("raw/player_game_stats/*.csv"):
        df = data_read_csv(path, usecols=["player_id", "player_name", "season", "season_type", "team_abbr"])
        frames.append(df)
    all_rows = pd.concat(frames, ignore_index=True)
    g = all_rows.groupby(["player_name", "player_id"]).agg(
        first=("season", "min"), last=("season", "max"), games=("season", "size"),
        teams=("team_abbr", lambda s: ",".join(sorted(set(map(str, s))))),
    ).reset_index()
    dup = g[g.duplicated("player_name", keep=False)].sort_values(["player_name", "first"])
    lines = [f"{r.player_name}|{r.player_id}|{r.first}|{r.last}|{r.games}|{r.teams}" for r in dup.itertuples()]
    # same id under several names
    ids = g[g.duplicated("player_id", keep=False)].sort_values(["player_id"])
    lines.append("---- ids with several names ----")
    lines += [f"{r.player_id}|{r.player_name}|{r.first}|{r.last}|{r.games}" for r in ids.itertuples()]
    seasons = sorted(all_rows["season"].unique())
    lines.append(f"seasons {seasons[0]}..{seasons[-1]} n={len(seasons)} rows={len(all_rows)}")
    pytest.fail("\nDISCOVERY\n" + "\n".join(lines))
