import time
from pathlib import Path

import pandas as pd
from nba_api.stats.endpoints import LeagueStandings
from nba_api.stats.static import teams

REQUEST_TIMEOUT = 30
MAX_RETRIES = 3
RETRY_SLEEP_SECONDS = 2.0


def fetch_standings(season: str, season_type: str) -> pd.DataFrame:
    last_err = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            endpoint = LeagueStandings(
                season=season,
                season_type=season_type,
                timeout=REQUEST_TIMEOUT,
            )
            df = endpoint.get_data_frames()[0]
            if df.empty:
                raise ValueError(
                    f"No standings returned for season={season}, season_type={season_type}"
                )
            return df
        except Exception as exc:
            last_err = exc
            if attempt < MAX_RETRIES:
                sleep_for = RETRY_SLEEP_SECONDS * attempt
                print(
                    f"Standings request failed (attempt {attempt}/{MAX_RETRIES}). "
                    f"Retrying in {sleep_for:.1f}s..."
                )
                time.sleep(sleep_for)
            else:
                break

    raise RuntimeError(f"Failed to fetch standings: {last_err}")


def choose_column(df: pd.DataFrame, candidates: list[str], out_name: str) -> pd.Series:
    for col in candidates:
        if col in df.columns:
            return df[col]
    raise ValueError(f"Could not find any column for {out_name}. Tried: {candidates}")


def normalize(raw: pd.DataFrame, season: str, season_type: str, snapshot_date: str) -> pd.DataFrame:
    df = raw.copy()

    team_lookup = pd.DataFrame(teams.get_teams())[["id", "abbreviation"]].rename(
        columns={"id": "team_id", "abbreviation": "team_abbr_lookup"}
    )

    out = pd.DataFrame()

    out["team_id"] = choose_column(df, ["TeamID", "TEAM_ID"], "team_id")

    if "TeamAbbreviation" in df.columns:
        out["team_abbr"] = df["TeamAbbreviation"]
    elif "TEAM_ABBREVIATION" in df.columns:
        out["team_abbr"] = df["TEAM_ABBREVIATION"]
    else:
        out = out.merge(team_lookup, on="team_id", how="left")
        out["team_abbr"] = out["team_abbr_lookup"]
        out = out.drop(columns=["team_abbr_lookup"])

    out["wins"] = choose_column(df, ["WINS", "Wins", "W"], "wins")
    out["losses"] = choose_column(df, ["LOSSES", "Losses", "L"], "losses")
    out["win_pct"] = choose_column(df, ["WinPCT", "WIN_PCT", "PCT"], "win_pct")
    out["conference_rank"] = choose_column(
        df,
        ["ConferenceRank", "CONFERENCE_RANK", "PlayoffRank", "PLAYOFF_RANK"],
        "conference_rank",
    )
    out["division_rank"] = choose_column(
        df,
        ["DivisionRank", "DIVISION_RANK"],
        "division_rank",
    )

    games_back_candidates = [
        "GamesBack",
        "GAMES_BACK",
        "ConferenceGamesBack",
        "CONFERENCE_GAMES_BACK",
    ]
    out["games_back"] = choose_column(df, games_back_candidates, "games_back")

    streak_candidates = [
        "strCurrentStreak",
        "Streak",
        "CurrentStreak",
        "STR_CURRENT_STREAK",
    ]
    out["streak"] = choose_column(df, streak_candidates, "streak")

    out["season"] = season
    out["season_type"] = season_type
    out["snapshot_date"] = snapshot_date

    keep_cols = [
        "snapshot_date",
        "season",
        "season_type",
        "team_id",
        "team_abbr",
        "wins",
        "losses",
        "win_pct",
        "conference_rank",
        "division_rank",
        "games_back",
        "streak",
    ]

    out = out[keep_cols].copy()

    out["wins"] = pd.to_numeric(out["wins"], errors="coerce")
    out["losses"] = pd.to_numeric(out["losses"], errors="coerce")
    out["win_pct"] = pd.to_numeric(out["win_pct"], errors="coerce")
    out["conference_rank"] = pd.to_numeric(out["conference_rank"], errors="coerce")
    out["division_rank"] = pd.to_numeric(out["division_rank"], errors="coerce")
    out["games_back"] = pd.to_numeric(out["games_back"], errors="coerce")
    out["streak"] = out["streak"].astype(str)

    return out


def run(season: str, season_type: str) -> None:
    if season_type == "Playoffs":
        print("Skipping standings for playoffs (not applicable)")
        return

    out_dir = Path("data/raw/standings_snapshots")
    out_dir.mkdir(parents=True, exist_ok=True)

    safe = season_type.lower().replace(" ", "_")
    out_path = out_dir / f"{season}_{safe}.csv"

    games_path = Path(f"data/raw/games/{season}_{safe}.csv")
    if not games_path.exists():
        raise FileNotFoundError("Games file required to derive snapshot_date")

    games_df = pd.read_csv(games_path)
    snapshot_date = pd.to_datetime(games_df["game_date"]).max().strftime("%Y-%m-%d")

    raw = fetch_standings(season=season, season_type=season_type)
    df = normalize(raw, season=season, season_type=season_type, snapshot_date=snapshot_date)

    df = (
        df.drop_duplicates(subset=["team_id", "snapshot_date"])
        .sort_values(["conference_rank", "team_id"])
        .reset_index(drop=True)
    )

    df.to_csv(out_path, index=False)
    print(f"Saved {out_path}")
    print(f"Rows: {len(df)}")
