"""Derive season team conference/division membership from official standings.

``data/raw/teams/team_conference_membership.csv`` started as a hand-entered
table for two seasons. The NBA's league standings report every team's
conference and division for each season, so this rebuilds a season's rows
from the stored standings snapshot (with the season's own team abbreviations
from its team game stats). Rows for seasons whose standings carry no conference or
division are left as they are.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

MEMBERSHIP_PATH = Path("data/raw/teams/team_conference_membership.csv")
MEMBERSHIP_COLUMNS = [
    "season",
    "team_abbr",
    "team_id",
    "conference",
    "division",
    "source",
    "coverage_trusted",
]
SOURCE = "nba_stats_league_standings"
DIVISIONS = {
    "East": {"Atlantic", "Central", "Southeast"},
    "West": {"Midwest", "Northwest", "Pacific", "Southwest"},
}


def derive_membership(season: str, data_dir: Path = Path("data")) -> pd.DataFrame | None:
    """Return one row per team for ``season``, or None without the columns."""
    standings_path = data_dir / "raw" / "standings_snapshots" / f"{season}_regular_season.csv"
    games_path = data_dir / "raw" / "team_game_stats" / f"{season}_regular_season.csv"
    if not standings_path.exists() or not games_path.exists():
        return None
    standings = pd.read_csv(standings_path)
    if not {"conference", "division"} <= set(standings.columns):
        return None
    standings = standings.dropna(subset=["conference", "division"])
    if standings.empty:
        return None
    if "snapshot_date" in standings.columns:
        latest = standings["snapshot_date"].max()
        standings = standings[standings["snapshot_date"] == latest]

    games = pd.read_csv(games_path, usecols=["game_date", "team_id", "team_abbr"])
    # A team's abbreviation as of its last game that season.
    abbreviations = games.sort_values("game_date").groupby("team_id")["team_abbr"].last()

    rows = []
    for record in standings.itertuples(index=False):
        team_id = int(record.team_id)
        conference = _conference(str(record.conference))
        division = str(record.division).strip()
        if team_id not in abbreviations.index:
            raise ValueError(f"{season}: standings team {team_id} has no games")
        if division not in DIVISIONS[conference]:
            raise ValueError(f"{season}: {division!r} is not a {conference} division")
        rows.append(
            {
                "season": season,
                "team_abbr": str(abbreviations[team_id]).upper(),
                "team_id": team_id,
                "conference": conference,
                "division": division,
                "source": SOURCE,
                "coverage_trusted": "true",
            }
        )
    frame = pd.DataFrame(rows, columns=MEMBERSHIP_COLUMNS)
    if frame["team_abbr"].duplicated().any():
        raise ValueError(f"{season}: two standings rows share a team abbreviation")
    if len(frame) != len(abbreviations):
        raise ValueError(
            f"{season}: standings list {len(frame)} teams but games list {len(abbreviations)}"
        )
    return frame


def run(season: str, season_type: str, data_dir: Path = Path("data")) -> None:
    """Replace ``season``'s membership rows with ones derived from standings."""
    if season_type == "Playoffs":
        print("Skipping conference membership for playoffs (same as regular season)")
        return
    derived = derive_membership(season, data_dir)
    if derived is None:
        print(f"No conference/division in {season} standings; membership unchanged")
        return
    path = data_dir / MEMBERSHIP_PATH.relative_to("data")
    existing = (
        pd.read_csv(path, dtype=str) if path.exists() else pd.DataFrame(columns=MEMBERSHIP_COLUMNS)
    )
    kept = existing[existing["season"] != season]
    merged = pd.concat([kept, derived.astype(str)], ignore_index=True)
    merged = merged.sort_values(["season", "team_abbr"]).reset_index(drop=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    merged[MEMBERSHIP_COLUMNS].to_csv(path, index=False)
    print(f"Saved {path} ({len(derived)} rows for {season})")


def _conference(value: str) -> str:
    normalized = value.strip().lower()
    if normalized.startswith("east"):
        return "East"
    if normalized.startswith("west"):
        return "West"
    raise ValueError(f"Unrecognized conference: {value!r}")
