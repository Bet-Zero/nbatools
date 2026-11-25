"""Team-scoped appearance predicates; membership/DNP semantics stay separate."""

import hashlib
import json
import re
import shutil
import tempfile
from pathlib import Path

import pandas as pd

from nbatools.commands._participation_observations import combined_observations
from nbatools.commands._player_identity import player_name_mask
from nbatools.commands.entity_resolution import player_ids_for_name
from nbatools.data_source import (
    data_exists,
    data_path,
    data_source_cache_key,
    verified_generation_files,
)
from nbatools.dataframe_cache import FRAME_CACHE


def _replay_unpublished_proof(proof, files, availability):
    from nbatools.commands.pipeline.team_appearance_coverage import (
        validate_complete_appearance_proof,
    )

    # Local and unverified generations still need original source qualification.
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        for relative, digest in files.items():
            raw = data_path("data/" + relative).read_bytes()
            if hashlib.sha256(raw).hexdigest() != digest:
                raise ValueError("Stale or altered complete appearance proof")
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
        for relative in availability:
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(data_path("data/" + relative), target)
        validate_complete_appearance_proof(root, proof)


def _coverage(seasons, kind, observations):
    def load():
        from nbatools.candidate_preview import appearance_load_event

        appearance_load_event()
        result = {}
        manifest = verified_generation_files()
        played_by_side = None
        for season in seasons:
            season_type = kind.lower().replace(" ", "_")
            suffix = f"{season}_{season_type}"
            path = f"data/raw/team_game_appearances/{suffix}.json"
            if not data_exists(path):
                continue
            proof = json.loads(data_path(path).read_bytes())
            if (
                proof.get("schema_version"),
                proof.get("season"),
                proof.get("season_type"),
                proof.get("scope"),
            ) != (1, season, kind, "complete_team_appearance_lists"):
                raise ValueError("Invalid complete appearance proof scope")
            expected_dependencies = {
                f"raw/{family}/{suffix}.csv"
                for family in ("games", "team_game_stats", "player_game_stats")
            }
            year = int(season[:4])
            previous = f"{year - 1}-{str(year)[-2:]}"
            allowed = expected_dependencies | {
                f"raw/rosters/{season}.csv",
                f"raw/rosters/{previous}.csv",
                f"raw/player_game_stats/{previous}_{season_type}.csv",
            }
            files = dict(proof["dependencies"])
            if not expected_dependencies <= files.keys() <= allowed:
                raise ValueError("Incomplete appearance proof dependencies")
            for side in proof["sides"]:
                if not side["source_files"]:
                    raise ValueError("Missing complete appearance original source")
                for relative, digest in side["source_files"].items():
                    if (
                        not relative.startswith("raw/player_game_availability_sources/")
                        or ".." in relative.split("/")
                        or relative in files
                        and files[relative] != digest
                    ):
                        raise ValueError("Invalid or conflicting appearance source dependency")
                    files[relative] = digest
            if any(not re.fullmatch(r"[a-f0-9]{64}", digest) for digest in files.values()):
                raise ValueError("Invalid appearance proof dependency checksum")
            availability = [
                f"raw/player_game_availability/{suffix}{ending}"
                for ending in (".csv", ".imports.json")
            ]
            if manifest is None:
                _replay_unpublished_proof(proof, files, availability)
            elif any(
                relative not in manifest or manifest[relative].sha256 != digest
                for relative, digest in files.items()
            ) or any(relative not in manifest for relative in availability):
                raise ValueError("Complete appearance provenance differs from published manifest")

            # Publication proved each list complete against the original container.
            # The pinned manifest authenticates the list and the rows used by this query.
            if played_by_side is None:
                positive = observations.loc[observations.participation_state.eq("played")]
                played_by_side = positive.groupby(["game_id", "team_id"]).player_id.agg(set)
            for side in proof["sides"]:
                played_ids = side["played_ids"]
                if any(type(x) is not int or x <= 0 for x in played_ids):
                    raise ValueError("Invalid complete appearance identities")
                ids = frozenset(played_ids)
                key = (int(side["game_id"]), int(side["team_id"]))
                if len(ids) != len(played_ids) or key in result:
                    raise ValueError("Conflicting complete appearance lists")
                if not ids.issuperset(played_by_side.get(key, ())):
                    raise ValueError("Appearance proof contradicts a positive appearance")
                result[key] = (side["game_date"], ids)
        frame = pd.DataFrame(
            [dict(game_id=g, team_id=t, day=d, players=ids) for (g, t), (d, ids) in result.items()]
        )
        appearance_load_event(completed=True)
        return frame

    frame = FRAME_CACHE.get_or_load(
        ("team-appearance-coverage", data_source_cache_key(), tuple(seasons), kind), load
    )
    return {(r.game_id, r.team_id): (r.day, r.players) for r in frame.itertuples()}


def select_appearances(candidates, names, seasons, kind, *, played, scope="team"):
    """Unknown is never the complement of played. Roles are exact-game sides."""
    if scope not in {"team", "opponent", "game"}:
        raise ValueError("Unknown appearance side scope")
    if candidates.empty:
        return candidates.copy()
    observations, _ = combined_observations(seasons, kind)
    complete = _coverage(seasons, kind, observations)
    keep = pd.Series(True, index=candidates.index)
    for name in re.split(r"\s+and\s+", names, flags=re.I):
        ids = {int(x) for x in player_ids_for_name(name)} | set(
            observations.loc[player_name_mask(observations, name), "player_id"].astype(int)
        )
        if len(ids) != 1:
            raise ValueError(f"Unavailable or ambiguous appearance identity for {name}")
        pid = ids.pop()
        actor = observations.loc[observations.player_id.eq(pid)]
        mask = []
        for row in candidates.itertuples():
            gid = int(row.game_id)
            opponent = getattr(row, "opponent_team_id", None)
            if scope != "team" and (opponent is None or pd.isna(opponent)):
                raise ValueError("Unavailable game opponent identity")
            valid_teams = {int(row.team_id)}
            if opponent is not None and not pd.isna(opponent):
                valid_teams.add(int(opponent))
            teams = (
                [int(row.team_id)]
                if scope == "team"
                else [int(row.opponent_team_id)]
                if scope == "opponent"
                else [int(row.team_id), int(row.opponent_team_id)]
            )
            day = pd.Timestamp(row.game_date).date().isoformat()
            states = []
            for team in teams:
                exact = actor.loc[actor.game_id.eq(gid)]
                if (
                    not exact.empty
                    and not pd.to_datetime(exact.game_date)
                    .dt.date.eq(pd.Timestamp(day).date())
                    .all()
                ):
                    raise ValueError("Appearance observation date mismatch")
                known = exact.loc[exact.participation_state.isin(["played", "did_not_play"])]
                if len(known):
                    if len(known) != 1 or int(known.team_id.iloc[0]) not in valid_teams:
                        raise ValueError("Conflicting exact-game appearance sides")
                    states.append(
                        bool(
                            int(known.team_id.iloc[0]) == team
                            and known.participation_state.iloc[0] == "played"
                        )
                    )
                elif (gid, team) in complete:
                    proof_day, players = complete[gid, team]
                    if proof_day != day:
                        raise ValueError("Complete appearance date mismatch")
                    states.append(pid in players)
                else:
                    states.append(None)
            if any(s is None for s in states):
                raise ValueError(
                    f"Incomplete team appearance coverage for {name}; no complete record returned"
                )
            mask.append(any(states) == played)
        keep &= pd.Series(mask, index=candidates.index)
    return candidates.loc[keep].copy()
