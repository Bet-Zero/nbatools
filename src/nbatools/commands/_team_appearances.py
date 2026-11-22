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
from nbatools.data_source import data_exists, data_path, data_read_csv, data_source_cache_key
from nbatools.dataframe_cache import FRAME_CACHE


def _coverage(seasons, kind):
    from nbatools.commands.pipeline.pull_player_game_availability import _game_digest

    def load():
        result = {}
        checked = {}
        for season in seasons:
            suffix = season + "_" + kind.lower().replace(" ", "_")
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
                f"raw/player_game_stats/{previous}_{kind.lower().replace(' ', '_')}.csv",
            }
            if (
                not expected_dependencies <= set(proof["dependencies"])
                or set(proof["dependencies"]) - allowed
            ):
                raise ValueError("Incomplete appearance proof dependencies")
            from nbatools.commands.pipeline.team_appearance_coverage import (
                validate_complete_appearance_proof,
            )

            files = dict(proof["dependencies"])
            for side in proof["sides"]:
                for relative, digest in side["source_files"].items():
                    if relative in files and files[relative] != digest:
                        raise ValueError("Conflicting appearance source dependencies")
                    files[relative] = digest
            with tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                for relative, digest in files.items():
                    if not relative.startswith("raw/") or ".." in relative.split("/"):
                        raise ValueError("Invalid appearance source path")
                    raw = data_path("data/" + relative).read_bytes()
                    if hashlib.sha256(raw).hexdigest() != digest:
                        raise ValueError("Stale or altered complete appearance proof")
                    target = root / relative
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(raw)
                for relative in (
                    f"raw/player_game_availability/{suffix}.csv",
                    f"raw/player_game_availability/{suffix}.imports.json",
                ):
                    target = root / relative
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(data_path("data/" + relative), target)
                validate_complete_appearance_proof(root, proof)
            observations, _ = combined_observations([season], kind)
            listed = data_read_csv(f"data/raw/player_game_availability/{suffix}.csv")
            for side in proof["sides"]:
                for relative, digest in {**proof["dependencies"], **side["source_files"]}.items():
                    if (
                        not relative.startswith("raw/")
                        or ".." in relative.split("/")
                        or not re.fullmatch(r"[a-f0-9]{64}", digest)
                    ):
                        raise ValueError("Invalid appearance proof dependency")
                    if relative not in checked:
                        checked[relative] = hashlib.sha256(
                            data_path("data/" + relative).read_bytes()
                        ).hexdigest()
                    if checked[relative] != digest:
                        raise ValueError("Stale or altered complete appearance proof")
                if not side["source_files"] or any(
                    not p.startswith("raw/player_game_availability_sources/")
                    for p in side["source_files"]
                ):
                    raise ValueError("Missing complete appearance original source")
                if any(type(x) is not int or x <= 0 for x in side["played_ids"]) or len(
                    side["played_ids"]
                ) != len(set(side["played_ids"])):
                    raise ValueError("Invalid complete appearance identities")
                gid, team = int(side["game_id"]), int(side["team_id"])
                # Bind primary full-container rows; separate inactive additions
                # do not expand or replace this complete played-list proof.
                rows = listed.loc[listed.game_id.eq(gid) & listed.team_id.eq(team)]
                if (
                    rows.empty
                    or rows.participation_state.eq("unknown").any()
                    or _game_digest(rows) != side["observation_sha256"]
                ):
                    raise ValueError(
                        "Complete appearance proof does not match accepted source rows"
                    )
                ids = set(rows.loc[rows.participation_state.eq("played"), "player_id"].astype(int))
                if ids != set(side["played_ids"]) or (gid, team) in result:
                    raise ValueError("Conflicting complete appearance lists")
                positive = observations.loc[
                    observations.game_id.eq(gid)
                    & observations.team_id.eq(team)
                    & observations.participation_state.eq("played")
                ]
                if set(positive.player_id.astype(int)) - ids:
                    raise ValueError("Appearance proof contradicts a positive appearance")
                result[gid, team] = (side["game_date"], ids)
        return pd.DataFrame(
            [dict(game_id=g, team_id=t, day=d, players=ids) for (g, t), (d, ids) in result.items()]
        )

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
    complete = _coverage(seasons, kind)
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
                    if len(known) != 1 or int(known.team_id.iloc[0]) not in {
                        int(row.team_id),
                        int(row.opponent_team_id),
                    }:
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
