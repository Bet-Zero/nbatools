"""Measure box-score-derived "missed games" against official participation records.

Usage: python measure.py <generation raw/ folder>

Read-only. Prints the counts recorded in the Resume checkpoint's UNRESOLVED
with/without section (2026-11-14, live generation
availability-participation-2025-durant-v1-20261114):
- option 1: a missing box line between a player's first and last game for a
  team counts as a miss;
- option 2: the whole season counts for single-team roster players, scored on
  fully listed official team-games (13+ listed players).
"""

import collections
import sys

import pandas as pd

SEASONS = ["2023-24", "2025-26", "2024-25", "2007-08", "1997-98", "2004-05", "2014-15"]


def main(raw):
    span_counts, whole_counts = collections.Counter(), collections.Counter()
    for season in SEASONS:
        official = pd.read_csv(
            f"{raw}/player_game_availability/{season}_regular_season.csv", dtype={"game_id": str}
        )
        box = pd.read_csv(
            f"{raw}/player_game_stats/{season}_regular_season.csv", dtype={"game_id": str}
        )
        roster = pd.read_csv(f"{raw}/rosters/{season}.csv")
        for frame in (official, box):
            frame["gid"] = frame.game_id.astype(str).str.lstrip("0")
            frame["day"] = pd.to_datetime(frame.game_date).dt.date
        played = set(zip(box.gid, box.player_id))
        span = box.groupby(["player_id", "team_id"]).day.agg(["min", "max"])
        for row in official.itertuples():
            key = (row.player_id, row.team_id)
            if (row.gid, row.player_id) in played:
                call = "played"
            elif key in span.index and span.loc[key, "min"] <= row.day <= span.loc[key, "max"]:
                call = "missed_in_span"
            else:
                call = "outside_span"
            span_counts[(row.participation_state, call)] += 1

        roster_teams = roster.groupby("player_id").team_id.nunique()
        box_teams = box.groupby("player_id").team_id.nunique()
        single = {
            (p, t)
            for p, t in zip(roster.player_id, roster.team_id)
            if roster_teams[p] == 1 and box_teams.get(p, 0) <= 1
        }
        state = {
            (g, p): s
            for g, p, s in zip(official.gid, official.player_id, official.participation_state)
        }
        for (gid, team), listed in (
            official.groupby(["gid", "team_id"]).player_id.apply(set).items()
        ):
            if len(listed) < 13:
                continue
            whole_counts["fully_listed_team_games"] += 1
            for player in {p for p, t in single if t == team}:
                if (gid, player) in played:
                    continue
                whole_counts["official_" + state.get((gid, player), "not_on_team")] += 1
    print("Option 1 (official state, call):")
    for key, value in sorted(span_counts.items()):
        print(" ", key, value)
    print("Option 2 (rule says missed):")
    for key, value in sorted(whole_counts.items()):
        print(" ", key, value)


if __name__ == "__main__":
    main(sys.argv[1])
