"""Cross-row source invariants shared by ingestion, validation, and loaders."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass

import pandas as pd

TEAM_PAIR_REQUIRED_COLUMNS = frozenset(
    {
        "game_id",
        "team_id",
        "opponent_team_id",
        "wl",
        "pts",
        "plus_minus",
    }
)
PLAY_BY_PLAY_COMPLETENESS_REQUIRED_COLUMNS = frozenset(
    {
        "game_id",
        "action_number",
        "period",
        "clock_seconds_remaining",
        "score_home",
        "score_away",
        "pbp_source_trusted",
        "pbp_validation_reason",
    }
)

REGULATION_TEAM_MINUTES = 240.0
OVERTIME_TEAM_MINUTES = 25.0
TERMINAL_CLOCK_TOLERANCE = 0.01


@dataclass(frozen=True, slots=True)
class ExpectedGameTerminalState:
    """Score and period state required for one complete play-by-play game."""

    final_scores: tuple[int, int]
    final_period: int | None


def _require_columns(df: pd.DataFrame, required: Iterable[str], dataset: str) -> None:
    missing = sorted(set(required) - set(df.columns))
    if missing:
        raise ValueError(f"{dataset} missing columns required for paired invariants: {missing}")


def _game_key(value: object) -> str:
    text = str(value).strip()
    try:
        number = float(text)
    except ValueError:
        return text
    return str(int(number)) if number.is_integer() else text


def _id_key(value: object) -> str:
    if pd.isna(value):
        return "<missing>"
    return _game_key(value)


def _paired_team_rows(df: pd.DataFrame) -> pd.DataFrame:
    _require_columns(df, TEAM_PAIR_REQUIRED_COLUMNS, "team_game_stats")
    work = df.copy().reset_index(drop=True)
    work["_game_key"] = work["game_id"].map(_game_key)

    if work.duplicated(subset=["_game_key", "team_id"]).any():
        raise ValueError("team_game_stats has duplicate (game_id, team_id) rows")

    for column in ("team_id", "opponent_team_id", "pts"):
        work[column] = pd.to_numeric(work[column], errors="coerce")
        if work[column].isna().any():
            raise ValueError(f"team_game_stats {column} has invalid numeric values")

    counts = work.groupby("_game_key", sort=False).size()
    invalid_counts = counts[counts.ne(2)]
    if not invalid_counts.empty:
        games = ", ".join(invalid_counts.index.astype(str).tolist()[:5])
        raise ValueError(f"team_game_stats requires exactly two team rows per game: {games}")

    if work["team_id"].eq(work["opponent_team_id"]).any():
        raise ValueError("team_game_stats team_id cannot equal opponent_team_id")

    opponent = work[["_game_key", "team_id", "pts"]].rename(
        columns={"team_id": "opponent_team_id", "pts": "_opponent_pts"}
    )
    work = work.merge(
        opponent,
        on=["_game_key", "opponent_team_id"],
        how="left",
        validate="one_to_one",
    )
    if work["_opponent_pts"].isna().any():
        games = ", ".join(
            work.loc[work["_opponent_pts"].isna(), "_game_key"].astype(str).unique()[:5]
        )
        raise ValueError(f"team_game_stats opponent identity mismatch: {games}")

    work["_expected_plus_minus"] = work["pts"] - work["_opponent_pts"]
    if work["_expected_plus_minus"].eq(0).any():
        games = ", ".join(
            work.loc[work["_expected_plus_minus"].eq(0), "_game_key"].astype(str).unique()[:5]
        )
        raise ValueError(f"team_game_stats has tied final scores: {games}")
    work["_expected_wl"] = work["_expected_plus_minus"].map(lambda value: "W" if value > 0 else "L")

    observed_wl = work["wl"].fillna("").astype(str).str.strip().str.upper()
    wl_mismatch = observed_wl.ne(work["_expected_wl"])
    if wl_mismatch.any():
        row = work.loc[wl_mismatch].iloc[0]
        raise ValueError(
            "team_game_stats wl mismatch for "
            f"game_id={row['_game_key']} team_id={_id_key(row['team_id'])}"
        )

    for label_column, paired_column in (
        ("opponent_team_abbr", "team_abbr"),
        ("opponent_team_name", "team_name"),
    ):
        if label_column not in work.columns or paired_column not in work.columns:
            continue
        lookup = work[["_game_key", "team_id", paired_column]].rename(
            columns={"team_id": "opponent_team_id", paired_column: "_expected_opponent_label"}
        )
        work = work.merge(
            lookup,
            on=["_game_key", "opponent_team_id"],
            how="left",
            validate="one_to_one",
        )
        observed = work[label_column].fillna("").astype(str).str.strip()
        expected = work["_expected_opponent_label"].fillna("").astype(str).str.strip()
        if not observed.eq(expected).all():
            raise ValueError(f"team_game_stats {label_column} does not match paired team identity")
        work = work.drop(columns=["_expected_opponent_label"])

    if {"is_home", "is_away"}.issubset(work.columns):
        for column in ("is_home", "is_away"):
            work[column] = pd.to_numeric(work[column], errors="coerce")
            if not work[column].isin([0, 1]).all():
                raise ValueError(f"team_game_stats {column} must be 0/1")
        if work["is_home"].add(work["is_away"]).gt(1).any():
            raise ValueError("team_game_stats row cannot be both home and away")
        role_counts = work.groupby("_game_key")[["is_home", "is_away"]].sum()
        valid_roles = (role_counts["is_home"].eq(1) & role_counts["is_away"].eq(1)) | (
            role_counts["is_home"].eq(0) & role_counts["is_away"].eq(0)
        )
        if not valid_roles.all():
            games = ", ".join(role_counts.index[~valid_roles].astype(str).tolist()[:5])
            raise ValueError(f"team_game_stats paired home/away identity mismatch: {games}")

    return work


def canonicalize_team_game_pairs(df: pd.DataFrame) -> pd.DataFrame:
    """Derive canonical team plus-minus from each paired final score."""
    paired = _paired_team_rows(df)
    out = df.copy().reset_index(drop=True)
    out["plus_minus"] = paired["_expected_plus_minus"].to_numpy()
    validate_team_game_pair_invariants(out)
    return out


def validate_team_game_pair_invariants(
    df: pd.DataFrame,
    *,
    games: pd.DataFrame | None = None,
) -> None:
    """Fail when paired score, WL, plus-minus, opponent, or venue identity drifts."""
    paired = _paired_team_rows(df)
    plus_minus = pd.to_numeric(paired["plus_minus"], errors="coerce")
    mismatch = plus_minus.isna() | plus_minus.ne(paired["_expected_plus_minus"])
    if mismatch.any():
        row = paired.loc[mismatch].iloc[0]
        raise ValueError(
            "team_game_stats plus_minus mismatch for "
            f"game_id={row['_game_key']} team_id={_id_key(row['team_id'])}: "
            f"observed={row['plus_minus']} expected={row['_expected_plus_minus']:g}"
        )

    if games is None:
        return

    required = {"game_id", "home_team_id", "away_team_id"}
    _require_columns(games, required, "games")
    game_rows = games.copy()
    game_rows["_game_key"] = game_rows["game_id"].map(_game_key)
    if game_rows["_game_key"].duplicated().any():
        raise ValueError("games has duplicate game_id rows")

    game_lookup = game_rows.set_index("_game_key")
    observed_games = set(paired["_game_key"])
    expected_games = set(game_lookup.index)
    if observed_games != expected_games:
        missing = sorted(expected_games - observed_games)
        unexpected = sorted(observed_games - expected_games)
        raise ValueError(
            "team_game_stats game identity set mismatch: "
            f"missing={missing[:5]} unexpected={unexpected[:5]}"
        )

    for game_key, team_group in paired.groupby("_game_key", sort=False):
        game = game_lookup.loc[game_key]
        participant_values = (game["home_team_id"], game["away_team_id"])
        if any(pd.isna(value) for value in participant_values):
            if not {"team_a_id", "team_b_id"}.issubset(game.index):
                raise ValueError(f"games participant identity is incomplete for game_id={game_key}")
            participant_values = (game["team_a_id"], game["team_b_id"])
        expected_team_ids = {_id_key(value) for value in participant_values}
        observed_team_ids = {_id_key(value) for value in team_group["team_id"]}
        if observed_team_ids != expected_team_ids:
            raise ValueError(
                f"team_game_stats participant identity mismatch for game_id={game_key}"
            )

        if not {"is_home", "is_away"}.issubset(team_group.columns):
            continue
        trusted = True
        if "home_away_designation_trusted" in game.index:
            trusted_value = pd.to_numeric(
                pd.Series([game["home_away_designation_trusted"]]), errors="coerce"
            ).iloc[0]
            trusted = bool(trusted_value == 1)
        if trusted:
            home_id = _id_key(game["home_team_id"])
            for row in team_group.itertuples(index=False):
                is_home = int(getattr(row, "is_home"))
                is_away = int(getattr(row, "is_away"))
                expected_home = int(_id_key(getattr(row, "team_id")) == home_id)
                if (is_home, is_away) != (expected_home, 1 - expected_home):
                    raise ValueError(
                        f"team_game_stats trusted venue identity mismatch for game_id={game_key}"
                    )
        elif not team_group[["is_home", "is_away"]].eq(0).all().all():
            raise ValueError(
                "team_game_stats untrusted venue identity must use neutral flags "
                f"for game_id={game_key}"
            )


def expected_game_terminal_states(
    team_game_stats: pd.DataFrame,
) -> dict[str, ExpectedGameTerminalState]:
    """Build authoritative terminal score/period expectations from paired team rows."""
    validate_team_game_pair_invariants(team_game_stats)
    paired = _paired_team_rows(team_game_stats)
    states: dict[str, ExpectedGameTerminalState] = {}
    for game_key, group in paired.groupby("_game_key", sort=False):
        final_scores = tuple(sorted(int(value) for value in group["pts"].tolist()))
        final_period: int | None = None
        if "minutes" in group.columns:
            minutes = pd.to_numeric(group["minutes"], errors="coerce")
            if minutes.isna().any():
                raise ValueError(f"team_game_stats minutes invalid for game_id={game_key}")
            # LeagueGameFinder team minutes are player-minute sums and may differ
            # slightly between opponents because of source rounding. Their paired
            # mean still identifies regulation vs. each 25-team-minute OT period.
            paired_minutes = float(minutes.mean())
            overtime_periods = max(
                0,
                int(round((paired_minutes - REGULATION_TEAM_MINUTES) / OVERTIME_TEAM_MINUTES)),
            )
            final_period = 4 + overtime_periods
        states[game_key] = ExpectedGameTerminalState(
            final_scores=final_scores,
            final_period=final_period,
        )
    return states


def play_by_play_game_trust_decisions(
    events: pd.DataFrame,
    expected_states: Mapping[str, ExpectedGameTerminalState],
) -> dict[str, tuple[str, ...]]:
    """Return exact per-game reasons; an empty tuple means the game is trusted."""
    _require_columns(events, PLAY_BY_PLAY_COMPLETENESS_REQUIRED_COLUMNS, "play_by_play_events")
    work = events.copy()
    work["_game_key"] = work["game_id"].map(_game_key)
    observed_games = set(work["_game_key"])
    normalized_expected = {_game_key(key): value for key, value in expected_states.items()}
    decisions: dict[str, tuple[str, ...]] = {}

    for game_key in sorted(set(normalized_expected) | observed_games):
        if game_key not in observed_games:
            decisions[game_key] = ("missing_game_events",)
            continue
        if game_key not in normalized_expected:
            decisions[game_key] = ("unexpected_game_events",)
            continue

        group = work.loc[work["_game_key"].eq(game_key)].copy()
        reasons: list[str] = []
        for column in (
            "action_number",
            "period",
            "clock_seconds_remaining",
            "score_home",
            "score_away",
        ):
            group[column] = pd.to_numeric(group[column], errors="coerce")
            if group[column].isna().any():
                reasons.append(f"invalid_{column}")
        if reasons:
            decisions[game_key] = tuple(reasons)
            continue

        group = group.sort_values("action_number")
        terminal = group.iloc[-1]
        state = normalized_expected[game_key]
        if int(terminal["period"]) < 4:
            reasons.append("terminal_period_before_fourth")
        elif state.final_period is not None and int(terminal["period"]) != state.final_period:
            reasons.append("terminal_period_mismatch")
        if abs(float(terminal["clock_seconds_remaining"])) > TERMINAL_CLOCK_TOLERANCE:
            reasons.append("terminal_clock_not_zero")
        terminal_scores = tuple(sorted((int(terminal["score_home"]), int(terminal["score_away"]))))
        if terminal_scores != state.final_scores:
            reasons.append("terminal_score_mismatch")
        decisions[game_key] = tuple(reasons)

    return decisions


def apply_play_by_play_trust_decisions(
    events: pd.DataFrame,
    expected_states: Mapping[str, ExpectedGameTerminalState],
) -> tuple[pd.DataFrame, dict[str, tuple[str, ...]]]:
    """Stamp every present game with the independently derived trust decision."""
    out = events.copy()
    decisions = play_by_play_game_trust_decisions(out, expected_states)
    game_keys = out["game_id"].map(_game_key)
    for game_key in game_keys.unique():
        reasons = decisions[game_key]
        mask = game_keys.eq(game_key)
        out.loc[mask, "pbp_source_trusted"] = int(not reasons)
        out.loc[mask, "pbp_validation_reason"] = ";".join(reasons)
    return out, decisions


def validate_play_by_play_trust_decisions(
    events: pd.DataFrame,
    team_game_stats: pd.DataFrame,
) -> list[str]:
    """Recompute PBP trust from paired scores and return all exact failures."""
    states = expected_game_terminal_states(team_game_stats)
    decisions = play_by_play_game_trust_decisions(events, states)
    work = events.copy()
    work["_game_key"] = work["game_id"].map(_game_key)
    errors: list[str] = []
    for game_key, reasons in decisions.items():
        group = work.loc[work["_game_key"].eq(game_key)]
        if group.empty:
            errors.append(f"game_id={game_key}: {';'.join(reasons)}")
            continue
        expected_trusted = int(not reasons)
        observed_trust = pd.to_numeric(group["pbp_source_trusted"], errors="coerce")
        observed_reasons = group["pbp_validation_reason"].fillna("").astype(str)
        expected_reason = ";".join(reasons)
        if (
            not observed_trust.eq(expected_trusted).all()
            or not observed_reasons.eq(expected_reason).all()
        ):
            errors.append(
                f"game_id={game_key}: trust decision mismatch "
                f"(expected={expected_reason or 'trusted'})"
            )
        elif reasons:
            errors.append(f"game_id={game_key}: {expected_reason}")
    return errors
