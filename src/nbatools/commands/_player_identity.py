"""Select one player's rows by identity (``player_id``), not by display name.

A name is not an identity. In the 1996-97+ data twelve names belong to two
different players each (Mike James, Patrick Ewing, Glen Rice, Marcus Williams,
...), and some players are stored under more than one spelling over time
("Bobby Portis" / "Bobby Portis Jr.", "Jonas Valančiūnas" / "Jonas
Valanciunas"). Filtering game rows by name merged the first group and split the
second. Every named-player filter goes through ``select_player_rows``:

1. the name finds its ``player_id`` values (in the rows themselves and in the
   data-wide index), and the rows are selected by id, so every spelling of
   that player is kept;
2. when the name belongs to several players in the rows in scope, one player
   is chosen: a requested team narrows the candidates, then the player with
   the most games in scope wins (ties go to the most recent). A note names
   the other player and how to ask about them, so the choice is never silent.
"""

from __future__ import annotations

import pandas as pd

from nbatools.commands.entity_resolution import (
    _normalize_for_matching,
    canonical_player_names_by_id,
    player_ids_for_name,
)

_MAX_TEAMS_IN_NOTE = 4

_DASHES = str.maketrans({dash: "-" for dash in "\u2010\u2011\u2012\u2013\u2014\u2015\u2212"})


def player_name_key(value: object) -> str:
    """Normalized name key: case, accents, dashes and letter periods ignored."""
    return _normalize_for_matching(str(value).translate(_DASHES))


def player_name_mask(df: pd.DataFrame, player: str) -> pd.Series:
    """Rows whose stored name matches ``player`` under ``player_name_key``."""
    names = df["player_name"].astype(str)
    key = player_name_key(player)
    matching = {name for name in names.unique() if player_name_key(name) == key}
    return names.isin(matching)


def _id_text(ids: pd.Series) -> pd.Series:
    """Player ids as the index stores them: integer text ("1626171", not "1626171.0")."""
    numeric = pd.to_numeric(ids, errors="coerce")
    if numeric.notna().all() and (numeric % 1 == 0).all():
        return numeric.astype("int64").astype(str)
    return ids.astype(str)


def canonicalize_player_names(df: pd.DataFrame) -> pd.DataFrame:
    """Give every row of one ``player_id`` that player's single display name.

    Returns ``df`` unchanged when nothing needs renaming, otherwise a copy.
    """
    if df.empty or "player_id" not in df.columns or "player_name" not in df.columns:
        return df
    names = canonical_player_names_by_id()
    if not names:
        return df
    canonical = _id_text(df["player_id"]).map(names)
    current = df["player_name"]
    differs = canonical.notna() & canonical.ne(current)
    if not differs.any():
        return df
    out = df.copy()
    out.loc[differs, "player_name"] = canonical[differs]
    return out


def _team_mask(df: pd.DataFrame, team: str) -> pd.Series:
    team_upper = str(team).upper()
    mask = pd.Series(False, index=df.index)
    for column in ("team_abbr", "team_name"):
        if column in df.columns:
            mask |= df[column].astype(str).str.upper().eq(team_upper)
    return mask


def _season_span(rows: pd.DataFrame) -> str:
    if "season" not in rows.columns or rows["season"].dropna().empty:
        return ""
    seasons = sorted(rows["season"].dropna().astype(str).unique())
    if len(seasons) == 1:
        return seasons[0]
    return f"{seasons[0]} to {seasons[-1]}"


def _teams(rows: pd.DataFrame) -> str:
    if "team_abbr" not in rows.columns:
        return ""
    teams = sorted(rows["team_abbr"].dropna().astype(str).unique())
    if len(teams) > _MAX_TEAMS_IN_NOTE:
        return ", ".join(teams[:_MAX_TEAMS_IN_NOTE]) + ", ..."
    return ", ".join(teams)


def _describe(rows: pd.DataFrame) -> str:
    parts = [part for part in (_teams(rows), _season_span(rows)) if part]
    games = len(rows)
    parts.append(f"{games} game{'s' if games != 1 else ''}")
    return ", ".join(parts)


def _last_date(rows: pd.DataFrame) -> pd.Timestamp:
    if "game_date" not in rows.columns:
        return pd.Timestamp.min
    value = pd.to_datetime(rows["game_date"], errors="coerce").max()
    return pd.Timestamp.min if pd.isna(value) else value


def select_player_rows(
    df: pd.DataFrame,
    player: str,
    *,
    team: str | None = None,
    notes: list[str] | None = None,
) -> pd.DataFrame:
    """Rows of the one player ``player`` names, selected by ``player_id``.

    ``team`` (abbreviation or name) narrows a shared name to the player who
    played for that team. When a shared name still leaves several players,
    the one with the most games in ``df`` is kept and an explanatory note is
    appended to ``notes``.
    """
    if df.empty or not player:
        return df.iloc[0:0].copy() if df.empty else df.copy()

    name_mask = player_name_mask(df, player)
    if "player_id" not in df.columns:
        # Rows already carry one display name per player (leaderboard output),
        # so the typed spelling also matches that player's canonical name.
        canonical = canonical_player_names_by_id()
        names = {canonical[pid] for pid in player_ids_for_name(player) if pid in canonical}
        return df[name_mask | df["player_name"].astype(str).isin(names)].copy()

    id_text = _id_text(df["player_id"])
    ids = set(id_text[name_mask].unique()) | set(player_ids_for_name(player))
    rows = df[id_text.isin(ids)]
    row_ids = id_text[rows.index]
    candidates = list(row_ids.unique())
    if len(candidates) <= 1:
        return rows.copy()

    groups = {player_id: rows[row_ids == player_id] for player_id in candidates}
    if team:
        on_team = [pid for pid, group in groups.items() if _team_mask(group, team).any()]
        if on_team:
            candidates = on_team
    chosen = max(
        candidates,
        key=lambda pid: (len(groups[pid]), _last_date(groups[pid])),
    )

    others = [pid for pid in groups if pid != chosen]
    if notes is not None and others:
        display = str(groups[chosen]["player_name"].mode().iloc[0])
        other_text = "; ".join(_describe(groups[pid]) for pid in others)
        noun = "Another player" if len(others) == 1 else "Other players"
        notes.append(
            f"More than one player is named {display}. Showing the one with "
            f"{_describe(groups[chosen])}. {noun} with that name: {other_text}. "
            "Add a team or season to ask about a different one."
        )
    return groups[chosen].copy()


def player_rows_prefilter(frames: list[pd.DataFrame], player: str) -> list[pd.DataFrame]:
    """Each season frame cut to the rows ``select_player_rows`` could keep.

    A career query loads every season; concatenating whole league frames
    before selecting one player held ~700 MB. The kept ids are the same
    union ``select_player_rows`` uses (any id stored under a matching name in
    any season, plus the index's ids for the name), so selecting from the
    cut frames gives identical rows, shared-name notes included.
    """
    ids = set(player_ids_for_name(player))
    for frame in frames:
        if "player_id" not in frame.columns or "player_name" not in frame.columns:
            return frames
        ids |= set(_id_text(frame["player_id"])[player_name_mask(frame, player)].unique())
    return [frame[_id_text(frame["player_id"]).isin(ids)] for frame in frames]


def player_game_ids(df: pd.DataFrame, player: str, *, team: str | None = None) -> pd.DataFrame:
    """``game_id``/``team_abbr`` pairs for the one player ``player`` names."""
    rows = select_player_rows(df, player, team=team)
    return rows.loc[:, ["game_id", "team_abbr"]].drop_duplicates()
