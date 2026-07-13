"""Canonical two-team game identity independent of home/away matchup markers."""

from __future__ import annotations

from typing import Any

import pandas as pd

PARTICIPANT_FIELDS = ("team_id", "team_abbr", "team_name")


def _participant(row: pd.Series, prefix: str) -> dict[str, Any]:
    if prefix in {"team_a", "team_b"}:
        return {
            f"{prefix}_{field.removeprefix('team_')}": row[field] for field in PARTICIPANT_FIELDS
        }
    return {f"{prefix}_{field}": row[field] for field in PARTICIPANT_FIELDS}


def _empty_designation() -> dict[str, Any]:
    return {
        **{f"home_{field}": pd.NA for field in PARTICIPANT_FIELDS},
        **{f"away_{field}": pd.NA for field in PARTICIPANT_FIELDS},
    }


def build_canonical_game_identity(raw: pd.DataFrame) -> pd.DataFrame:
    """Return one participant-complete row per game without inventing venue roles."""
    required = {"game_id", "game_date", "matchup", *PARTICIPANT_FIELDS}
    missing = sorted(required - set(raw.columns))
    if missing:
        raise ValueError(f"game identity source missing required columns: {missing}")

    rows: list[dict[str, Any]] = []
    for game_id, group in raw.groupby("game_id", sort=False, dropna=False):
        participants = (
            group.drop_duplicates(subset=["team_id"])
            .sort_values("team_id", kind="stable")
            .reset_index(drop=True)
        )
        if len(participants) != 2:
            raise ValueError(
                f"game_id={game_id} must have exactly two distinct team rows; "
                f"found {len(participants)}"
            )

        team_a = participants.iloc[0]
        team_b = participants.iloc[1]
        home_mask = participants["matchup"].astype(str).str.contains(" vs. ", regex=False)
        away_mask = participants["matchup"].astype(str).str.contains(" @ ", regex=False)

        row: dict[str, Any] = {
            "game_id": game_id,
            "game_date": participants.iloc[0]["game_date"],
            **_participant(team_a, "team_a"),
            **_participant(team_b, "team_b"),
        }

        if int(home_mask.sum()) == 1 and int(away_mask.sum()) == 1:
            home = participants.loc[home_mask].iloc[0]
            away = participants.loc[away_mask].iloc[0]
            row.update(_participant(home, "home"))
            row.update(_participant(away, "away"))
            row.update(
                {
                    "site_type": "standard",
                    "neutral_site": 0,
                    "home_away_designation_trusted": 1,
                    "home_away_source": "league_game_finder_matchup",
                }
            )
        else:
            row.update(_empty_designation())
            both_away = bool(away_mask.all())
            row.update(
                {
                    "site_type": "neutral" if both_away else "unknown",
                    "neutral_site": 1 if both_away else pd.NA,
                    "home_away_designation_trusted": 0,
                    "home_away_source": "league_game_finder_unresolved",
                }
            )

        rows.append(row)

    return pd.DataFrame(rows)


def apply_canonical_home_away_flags(raw: pd.DataFrame) -> pd.DataFrame:
    """Apply trusted relative venue flags without labeling neutral teams away."""
    identity_source = raw[["game_id", "game_date", "matchup", *PARTICIPANT_FIELDS]].drop_duplicates(
        subset=["game_id", "team_id"]
    )
    identity = build_canonical_game_identity(identity_source)[
        [
            "game_id",
            "home_team_id",
            "away_team_id",
            "home_away_designation_trusted",
        ]
    ]

    out = raw.drop(columns=["is_home", "is_away"], errors="ignore").merge(
        identity,
        on="game_id",
        how="left",
        validate="many_to_one",
    )
    trusted = out["home_away_designation_trusted"].eq(1)
    team_ids = pd.to_numeric(out["team_id"], errors="coerce")
    home_ids = pd.to_numeric(out["home_team_id"], errors="coerce").fillna(-1)
    away_ids = pd.to_numeric(out["away_team_id"], errors="coerce").fillna(-1)
    is_home = team_ids.eq(home_ids)
    is_away = team_ids.eq(away_ids)
    out["is_home"] = (trusted & is_home).astype(int)
    out["is_away"] = (trusted & is_away).astype(int)
    return out.drop(columns=["home_team_id", "away_team_id", "home_away_designation_trusted"])
