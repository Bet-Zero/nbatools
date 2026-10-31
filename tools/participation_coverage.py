"""Read-only participation coverage against a pinned observed-game catalog.

This diagnoses unresolved qualification keys before collection. It does not infer DNP,
tenure, injury, or independently complete seasons, and never publishes data.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

import pandas as pd

from nbatools.commands import _participation_observations as participation
from nbatools.commands import entity_resolution
from nbatools.commands.data_utils import load_player_games_for_seasons
from nbatools.data_source import data_exists, data_generation_context, data_path


def _observed_team_games(catalog, teams, season, season_type, team_id):
    """Use reciprocal team rows; venue metadata is corroboration, not a denominator."""
    catalog_fields = {"game_id", "game_date", "season", "season_type", "is_final"}
    team_fields = {"game_id", "game_date", "season", "season_type", "team_id", "opponent_team_id"}
    if not catalog_fields.issubset(catalog) or not team_fields.issubset(teams):
        raise ValueError("Incomplete canonical catalog/team schema")
    if not (catalog.season.eq(season) & catalog.season_type.eq(season_type)).all():
        raise ValueError("Canonical season/type mismatch")
    catalog = catalog.copy()
    catalog["game_id"] = participation._ids(catalog.game_id)
    if catalog.game_id.duplicated().any():
        raise ValueError("Duplicate canonical game catalog")
    catalog = catalog.set_index("game_id")
    teams = teams.copy()
    teams["game_id"] = pd.to_numeric(teams.game_id, errors="coerce")
    own = teams.loc[pd.to_numeric(teams.team_id, errors="coerce").eq(team_id)].copy()
    own["game_id"] = participation._ids(own.game_id)
    if own.game_id.duplicated().any():
        raise ValueError("Duplicate requested team game")
    opposing = teams.loc[pd.to_numeric(teams.opponent_team_id, errors="coerce").eq(team_id)]
    if not set(participation._ids(opposing.game_id)) <= set(own.game_id):
        raise ValueError("Opposing team involvement lacks requested team row")
    final = catalog.is_final.astype(str).str.lower().isin(["true", "1"])
    known_side = pd.Series(False, index=catalog.index)
    for field in ["home_team_id", "away_team_id"]:
        if field in catalog:
            known_side |= pd.to_numeric(catalog[field], errors="coerce").eq(team_id)
    if not set(catalog.index[final & known_side]) <= set(own.game_id):
        raise ValueError("Known canonical team involvement lacks team row")
    result = []
    for game_id, group in teams.loc[teams.game_id.isin(own.game_id)].groupby("game_id"):
        if game_id not in catalog.index or not final.loc[game_id]:
            raise ValueError("Team game lacks unique final canonical game")
        game = catalog.loc[game_id]
        day = pd.to_datetime(game.game_date, errors="raise")
        dates = pd.to_datetime(group.game_date, errors="raise")
        if (
            pd.isna(day)
            or dates.isna().any()
            or not dates.dt.date.eq(day.date()).all()
            or not (group.season.eq(season) & group.season_type.eq(season_type)).all()
        ):
            raise ValueError("Team game date/season differs from canonical game")
        ids, opponents = (
            participation._ids(group.team_id),
            participation._ids(group.opponent_team_id),
        )
        if len(group) != 2 or ids.nunique() != 2 or set(ids) != set(opponents):
            raise ValueError("Team game lacks unique reciprocal sides")
        opponent = int(opponents.loc[ids.eq(team_id)].item())
        if opponent == team_id or not opponents.loc[ids.eq(opponent)].eq(team_id).all():
            raise ValueError("Team game sides are not reciprocal")
        known = [
            game[field]
            for field in ["home_team_id", "away_team_id"]
            if field in game and pd.notna(game[field])
        ]
        if known:
            venue = participation._ids(pd.Series(known))
            if venue.duplicated().any() or not set(venue) <= {team_id, opponent}:
                raise ValueError("Populated canonical venue sides contradict team rows")
        result.append(
            dict(
                game_id=int(game_id),
                game_date=day.strftime("%Y-%m-%d"),
                team_id=team_id,
                opponent_team_id=opponent,
            )
        )
    return pd.DataFrame(result, columns=["game_id", "game_date", "team_id", "opponent_team_id"])


def build_report(
    *,
    generation: str,
    manifest_sha256: str,
    season: str,
    team_id: int,
    player_id: int,
    season_type: str = "Regular Season",
    game_ids: list[int] | None = None,
) -> dict:
    """Qualify each requested game using the engine's existing participation rules."""
    if team_id <= 0 or player_id <= 0:
        raise ValueError("Positive team/player identities are required")
    with data_generation_context() as pinned:
        if pinned != generation:
            raise ValueError("Configured generation differs from requested generation")
        raw_manifest = data_path("data/metadata/generation_manifest.json").read_bytes()
        if hashlib.sha256(raw_manifest).hexdigest() != manifest_sha256:
            raise ValueError("Generation manifest differs from expected hash")
        manifest = json.loads(raw_manifest)
        if manifest["generation_id"] != generation:
            raise ValueError("Manifest generation differs from requested generation")
        entries = {entry["path"]: entry for entry in manifest["files"]}
        if len(entries) != len(manifest["files"]):
            raise ValueError("Duplicate manifest paths")
        hashes = {}

        def verified(relative, *, optional=False):
            if optional and relative not in entries:
                if data_exists("data/" + relative):
                    raise ValueError(f"Unmanifested participation dependency: {relative}")
                return None
            entry = entries[relative]
            path = data_path("data/" + relative)
            raw = path.read_bytes()
            digest = hashlib.sha256(raw).hexdigest()
            if len(raw) != entry["size_bytes"] or digest != entry["sha256"]:
                raise ValueError(f"Snapshot bytes differ from manifest: {relative}")
            hashes[relative] = digest
            return path

        identity_path = "metadata/player_names.csv"
        if identity_path not in entries:
            raise ValueError("Missing manifest-bound published player identity metadata")
        verified(identity_path)
        if entity_resolution._read_published_player_names() is None:
            raise ValueError("Unusable published player identity metadata; full scan is forbidden")
        suffix = f"{season}_{season_type.lower().replace(' ', '_')}.csv"
        catalog = pd.read_csv(verified("raw/games/" + suffix))
        verified("raw/player_game_stats/" + suffix)
        teams = pd.read_csv(verified("raw/team_game_stats/" + suffix))
        verified("raw/player_season_advanced/" + suffix, optional=True)
        verified("raw/player_game_availability/" + suffix, optional=True)
        games = _observed_team_games(catalog, teams, season, season_type, team_id)
        observed_count = len(games)
        if game_ids is not None:
            if len(set(game_ids)) != len(game_ids) or not set(game_ids) <= set(games.game_id):
                raise ValueError("Requested games are duplicate or outside observed final sample")
            games = games.loc[games.game_id.isin(game_ids)]
        if games.empty:
            raise ValueError("No requested observed final team games")
        appearances = load_player_games_for_seasons([season], season_type)
        observations = participation.load_observations([season], season_type)
        identities = pd.concat([appearances, observations], ignore_index=True)
        names = identities.loc[pd.to_numeric(identities.player_id).eq(player_id), "player_name"]
        names = names.dropna().astype(str).unique()
        if len(names) != 1:
            raise ValueError("Requested player has unavailable or conflicting name identity")
        name = names[0]
        rows = []
        for _, game in games.sort_values(["game_date", "game_id"]).iterrows():
            row = dict(
                game_id=f"{int(game.game_id):010d}",
                game_date=game.game_date,
                team_id=team_id,
                player_id=player_id,
                state="unknown",
            )
            candidate = game.to_frame().T
            try:
                absent = participation.filter_absent(candidate, name, [season], season_type)
                played = participation.filter_played(candidate, name, [season], season_type)
                row["state"] = (
                    "did_not_play"
                    if not absent.empty
                    else "played"
                    if not played.empty
                    else "same_game_other_side"
                )
            except (ValueError, FileNotFoundError) as exc:
                row["qualification_error"] = str(exc)
            rows.append(row)
        counts = Counter(row["state"] for row in rows)
        missing = [
            {key: row[key] for key in ("game_id", "game_date", "team_id", "player_id")}
            for row in rows
            if row["state"] == "unknown"
        ]
        return dict(
            schema_version=1,
            generation=generation,
            manifest_sha256=manifest_sha256,
            season=season,
            season_type=season_type,
            team_id=team_id,
            player_id=player_id,
            player_name=name,
            source_hashes=hashes,
            denominator="observed final team games; independent full-season completeness unknown",
            scope="all_observed_team_games" if game_ids is None else "selected_observed_team_games",
            observed_team_games=observed_count,
            requested_games=len(rows),
            counts={
                key: counts[key]
                for key in ["played", "did_not_play", "same_game_other_side", "unknown"]
            },
            complete_requested_population=not missing,
            missed_games=counts["did_not_play"] if not missing else None,
            games=rows,
            missing_keys=missing,
            collection_requirement=(
                "missing_keys are unresolved qualification keys; inspect qualification_error "
                "and repair contradictory existing evidence before requesting new sources; "
                "no acquisition authorization"
            ),
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--generation", required=True)
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument("--season", required=True)
    parser.add_argument("--season-type", default="Regular Season")
    parser.add_argument("--team-id", type=int, required=True)
    parser.add_argument("--player-id", type=int, required=True)
    parser.add_argument("--game-ids", type=int, nargs="+")
    parser.add_argument("--output", type=Path, required=True)
    args = vars(parser.parse_args())
    output = args.pop("output")
    if output.exists():
        raise ValueError("Refusing to overwrite an existing report")
    report = build_report(**args)
    with output.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
