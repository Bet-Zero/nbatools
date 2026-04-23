from pathlib import Path

import pandas as pd

from nbatools.commands.data_utils import SCHEDULE_CONTEXT_REQUIRED_COLUMNS, normalize_season_type


def _require_columns(df: pd.DataFrame, required: list[str], name: str) -> None:
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"{name} missing required columns: {missing}")


def _normalize_national_tv_value(value: object) -> str:
    if pd.isna(value):
        return ""
    text = str(value).strip()
    if text.lower() in {"", "nan", "none", "null"}:
        return ""
    return text


def _rest_advantage(row: pd.Series) -> str:
    rest = row["rest_days"]
    opponent_rest = row["opponent_rest_days"]
    if pd.isna(rest) or pd.isna(opponent_rest):
        return "unknown"
    if rest > opponent_rest:
        return "advantage"
    if rest < opponent_rest:
        return "disadvantage"
    return "even"


def build_schedule_context_features(season: str, season_type: str) -> pd.DataFrame:
    safe = normalize_season_type(season_type)
    team_path = Path(f"data/raw/team_game_stats/{season}_{safe}.csv")
    schedule_path = Path(f"data/raw/schedule/{season}_{safe}.csv")

    if not team_path.exists():
        raise FileNotFoundError(f"Missing input: {team_path}")
    if not schedule_path.exists():
        raise FileNotFoundError(f"Missing input: {schedule_path}")

    team = pd.read_csv(team_path)
    schedule = pd.read_csv(schedule_path)

    _require_columns(
        team,
        [
            "game_id",
            "season",
            "season_type",
            "game_date",
            "team_id",
            "team_abbr",
            "team_name",
            "opponent_team_id",
            "opponent_team_abbr",
            "opponent_team_name",
            "is_home",
            "is_away",
            "pts",
            "plus_minus",
        ],
        "team_game_stats",
    )
    _require_columns(schedule, ["game_id"], "schedule")

    if team.duplicated(subset=["game_id", "team_id"]).any():
        raise ValueError("Duplicate (game_id, team_id) in team_game_stats")

    work = team.copy()
    work["game_date"] = pd.to_datetime(work["game_date"], errors="coerce").dt.normalize()
    if work["game_date"].isna().any():
        raise ValueError("team_game_stats game_date contains unparseable values")

    work = work.sort_values(["team_id", "game_date", "game_id"]).reset_index(drop=True)
    work["prev_game_date"] = work.groupby("team_id")["game_date"].shift(1)
    date_diff = (work["game_date"] - work["prev_game_date"]).dt.days
    work["rest_days"] = (date_diff - 1).clip(lower=0)
    work["rest_days"] = work["rest_days"].where(work["prev_game_date"].notna(), pd.NA)
    work["back_to_back"] = ((date_diff == 1) & work["prev_game_date"].notna()).astype(int)

    opponent_rest = work[["game_id", "team_id", "rest_days"]].rename(
        columns={
            "team_id": "opponent_team_id",
            "rest_days": "opponent_rest_days",
        }
    )
    work = work.merge(
        opponent_rest,
        on=["game_id", "opponent_team_id"],
        how="left",
        validate="one_to_one",
    )
    work["rest_advantage"] = work.apply(_rest_advantage, axis=1)

    work["score_margin"] = pd.to_numeric(work["plus_minus"], errors="coerce").abs()
    if work["score_margin"].isna().any():
        raise ValueError("team_game_stats plus_minus contains unparseable values")
    work["one_possession"] = work["score_margin"].le(3).astype(int)

    schedule_work = schedule[["game_id"]].drop_duplicates(subset=["game_id"]).copy()
    if "national_tv" in schedule.columns:
        schedule_work["national_tv_source"] = schedule["national_tv"].map(
            _normalize_national_tv_value
        )
    else:
        schedule_work["national_tv_source"] = ""

    national_tv_trusted = int(schedule_work["national_tv_source"].ne("").any())
    schedule_work["national_tv_source_trusted"] = national_tv_trusted
    schedule_work["nationally_televised"] = schedule_work["national_tv_source"].ne("").astype(int)

    work = work.merge(
        schedule_work[
            [
                "game_id",
                "national_tv_source",
                "national_tv_source_trusted",
                "nationally_televised",
            ]
        ],
        on="game_id",
        how="left",
        validate="many_to_one",
    )
    work["national_tv_source"] = work["national_tv_source"].fillna("")
    work["national_tv_source_trusted"] = (
        pd.to_numeric(work["national_tv_source_trusted"], errors="coerce").fillna(0).astype(int)
    )
    work["nationally_televised"] = (
        pd.to_numeric(work["nationally_televised"], errors="coerce").fillna(0).astype(int)
    )

    work["schedule_context_source"] = "team_game_stats+schedule"
    work["schedule_context_source_trusted"] = 1

    out = work[SCHEDULE_CONTEXT_REQUIRED_COLUMNS].copy()
    out["game_date"] = pd.to_datetime(out["game_date"], errors="coerce").dt.strftime("%Y-%m-%d")
    out = out.sort_values(["game_date", "game_id", "team_id"]).reset_index(drop=True)
    return out


def run(season: str, season_type: str) -> None:
    safe = normalize_season_type(season_type)
    out_dir = Path("data/processed/schedule_context_features")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{season}_{safe}.csv"

    out = build_schedule_context_features(season, season_type)
    out.to_csv(out_path, index=False)
    print(f"Saved {out_path}")
