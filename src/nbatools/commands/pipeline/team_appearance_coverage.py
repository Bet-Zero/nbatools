"""Offline, retained-only certification of complete team-side appearance lists."""

import hashlib
import json
import shutil
import tempfile
from pathlib import Path

import pandas as pd

from nbatools.commands.pipeline.pull_player_game_availability import (
    _game_digest,
    normalize_boxscore_availability,
)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def qualify_retained_appearances(
    root: Path, season: str, season_type: str, *, team_ids: set[int] | None = None
) -> dict:
    """Replay existing imports; return new proof, never edit sources or fetch.

    A listed-player receipt alone is insufficient. Structured full boxes and
    cached Final Box reports are replayed through their existing validators.
    Every listed row on a certified side must have an unambiguous state.
    """
    from nbatools.commands.pipeline.player_game_availability_report import official_report_as_v3
    from nbatools.commands.pipeline.structured_participation import _build

    root = Path(root)
    suffix = season + "_" + season_type.lower().replace(" ", "_")
    csv = f"raw/player_game_availability/{suffix}.csv"
    persisted = pd.read_csv(root / csv)
    ledger = json.loads((root / csv.replace(".csv", ".imports.json")).read_bytes())
    sources = root / "raw/player_game_availability_sources"
    dependencies = {
        f"raw/{kind}/{suffix}.csv": sha((root / f"raw/{kind}/{suffix}.csv").read_bytes())
        for kind in ("games", "team_game_stats", "player_game_stats")
    }
    start = int(season[:4])
    previous = f"{start - 1}-{str(start)[-2:]}"
    for relative in (
        f"raw/rosters/{season}.csv",
        f"raw/rosters/{previous}.csv",
        f"raw/player_game_stats/{previous}_{season_type.lower().replace(' ', '_')}.csv",
    ):
        if (root / relative).is_file():
            dependencies[relative] = sha((root / relative).read_bytes())
    games = pd.read_csv(root / f"raw/games/{suffix}.csv").set_index("game_id")
    target_games = (
        set(games.index)
        if team_ids is None
        else set(
            games.loc[games.home_team_id.isin(team_ids) | games.away_team_id.isin(team_ids)].index
        )
    )
    proof = dict(
        schema_version=1,
        season=season,
        season_type=season_type,
        scope="complete_team_appearance_lists",
        dependencies=dependencies,
        sides=[],
        unqualified=[],
        source_requests=0,
    )
    with tempfile.TemporaryDirectory() as temp:
        scratch = Path(temp)
        for relative in dependencies:
            target = scratch / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(root / relative, target)
        for gid, record in ledger.items():
            game_id = int(gid)
            if game_id not in target_games:
                continue
            old = persisted.loc[persisted.game_id.eq(game_id)]
            try:
                if _game_digest(old) != record["sha256"]:
                    raise ValueError("Existing import digest mismatch")
                files = {}
                if record["source"] == "structured":
                    hashes = old.source_sha256.unique()
                    if len(hashes) != 1:
                        raise ValueError("Ambiguous structured source")
                    packet_path = sources / f"{hashes[0]}.structured.json"
                    body = packet_path.read_bytes()
                    if sha(body) != hashes[0]:
                        raise ValueError("Structured packet hash mismatch")
                    packet = json.loads(body)
                    replay = _build(root, packet, sources, hashes[0])
                    files[str(packet_path.relative_to(root))] = sha(body)
                    for source in packet["sources"].values():
                        files[f"raw/player_game_availability_sources/{source['file']}"] = source[
                            "sha256"
                        ]
                elif record["source"] == "report":
                    game = games.loc[game_id]
                    identity_hashes = old.identity_source_sha256.fillna("").unique()
                    if len(identity_hashes) != 1:
                        raise ValueError("Inconsistent availability identity source")
                    raw, reference = official_report_as_v3(
                        game_id=game_id,
                        game_date=str(game.game_date),
                        season=season,
                        season_type=season_type,
                        home_team_id=int(game.home_team_id),
                        away_team_id=int(game.away_team_id),
                        data_root=scratch,
                        cached_reports=sources,
                        imported_team_ids=record.get("imported_team_ids"),
                        cached_identity_sha256=identity_hashes[0],
                    )
                    receipt_path = sources / f"{reference}.json"
                    receipt = json.loads(receipt_path.read_bytes())
                    files[str(receipt_path.relative_to(root))] = sha(receipt_path.read_bytes())
                    files[f"raw/player_game_availability_sources/{receipt['raw_file']}"] = receipt[
                        "sha256"
                    ]
                    files.update(
                        {
                            f"raw/player_game_availability_sources/{name}": digest
                            for name, digest in raw.attrs.get("identity_source_files", {}).items()
                        }
                    )
                    replay = normalize_boxscore_availability(
                        raw,
                        game_id=game_id,
                        game_date=str(game.game_date),
                        season=season,
                        season_type=season_type,
                        expected_team_ids=set(raw.teamId),
                        source=f"nba_official_finalbox:{reference}",
                    )
                else:
                    raise ValueError("Source is not a qualified complete box-score container")
                if _game_digest(replay) != _game_digest(old):
                    raise ValueError("Replayed source differs from accepted observations")
                for team, rows in replay.groupby("team_id"):
                    if team_ids is not None and int(team) not in team_ids:
                        continue
                    if rows.participation_state.eq("unknown").any():
                        proof["unqualified"].append(
                            dict(
                                game_id=game_id,
                                team_id=int(team),
                                reason="Ambiguous listed participation",
                            )
                        )
                        continue
                    proof["sides"].append(
                        dict(
                            game_id=game_id,
                            team_id=int(team),
                            game_date=str(rows.game_date.iloc[0]),
                            played_ids=sorted(
                                rows.loc[rows.participation_state.eq("played"), "player_id"].astype(
                                    int
                                )
                            ),
                            observation_sha256=_game_digest(rows),
                            source_files=files,
                        )
                    )
            except (ValueError, KeyError, FileNotFoundError) as exc:
                proof["unqualified"].append(
                    dict(
                        game_id=game_id,
                        reason=str(exc)
                        .replace(str(root), "<data_root>")
                        .replace(str(scratch), "<scratch>"),
                    )
                )
    return proof


def validate_complete_appearance_proof(root: Path, proof: dict) -> None:
    """A claim must equal a replay of its actual full source, not its own hashes."""
    replay = qualify_retained_appearances(
        root,
        proof["season"],
        proof["season_type"],
        team_ids={int(s["team_id"]) for s in proof["sides"]},
    )
    expected = {(s["game_id"], s["team_id"]): s for s in replay["sides"]}
    if proof["dependencies"] != replay["dependencies"]:
        raise ValueError("Complete appearance dependencies differ from replay")
    for side in proof["sides"]:
        if expected.get((side["game_id"], side["team_id"])) != side:
            raise ValueError("Complete appearance claim does not match replayed full source")
