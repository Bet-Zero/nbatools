"""Franchise identity across relocations and renames.

Team rows carry the abbreviation and name the team had that season (SEA,
NJN, VAN, CHH, NOH/NOK) while the NBA ``team_id`` stays with the franchise.
A team asked for by its current abbreviation keeps its earlier seasons.
"""

from __future__ import annotations

import pandas as pd

from nbatools.commands import _nba_alignment


def franchise_team_id(team: str | None) -> int | None:
    """The NBA franchise ``team_id`` behind a current abbreviation.

    Abbreviations change with relocations and renames (SEA/OKC, NJN/BKN,
    VAN/MEM, CHH/CHA, NOH/NOK/NOP) while the franchise id stays, so a current
    team asked for by its present abbreviation keeps its earlier seasons.
    """
    if not team:
        return None
    value = getattr(_nba_alignment, str(team).strip().upper(), None)
    wanted = str(team).strip().upper()
    if len(wanted) == 3 and wanted.isalpha() and isinstance(value, int):
        return value
    return None


def team_value_mask(df: pd.DataFrame, team: str, *, prefix: str = "") -> pd.Series:
    """Rows of ``team`` (or, with ``prefix="opponent_"``, against it).

    Matches the abbreviation or full name as the row has it, plus every row of
    the same franchise under an earlier name: "Thunder" covers the Seattle
    SuperSonics seasons, "Nets" the New Jersey seasons.
    """
    wanted = str(team).strip().upper()
    mask = pd.Series(False, index=df.index)
    for column in (f"{prefix}team_abbr", f"{prefix}team_name"):
        if column in df.columns:
            mask |= df[column].astype(str).str.upper().eq(wanted)
    franchise = franchise_team_id(wanted)
    id_column = f"{prefix}team_id"
    if franchise is not None and id_column in df.columns:
        mask |= pd.to_numeric(df[id_column], errors="coerce").eq(franchise)
    return mask


def franchise_earlier_names(df: pd.DataFrame, team: str | None) -> list[str]:
    """Names other than the current one that ``team``'s rows in ``df`` carry."""
    franchise = franchise_team_id(team)
    if franchise is None or not {"team_id", "team_abbr"}.issubset(df.columns):
        return []
    rows = df[pd.to_numeric(df["team_id"], errors="coerce").eq(franchise)]
    rows = rows[rows["team_abbr"].astype(str).str.upper().ne(str(team).strip().upper())]
    if rows.empty:
        return []
    column = "team_name" if "team_name" in rows.columns else "team_abbr"
    return sorted(rows[column].astype(str).unique())


def franchise_caveat(df: pd.DataFrame, team: str | None) -> str | None:
    """ "includes the franchise's seasons as the Seattle SuperSonics"."""
    names = franchise_earlier_names(df, team)
    if not names:
        return None
    return f"includes the franchise's seasons as the {' and the '.join(names)}"
