"""Offline qualification of retained structured NBA box scores.

Traditional V3 contributes played/DNP rows; Summary V2/V3 contributes explicit
inactive identities and a dated final-game envelope. Omission remains unknown.
No network, publication or season-wide membership inference occurs here.
"""

from __future__ import annotations

import hashlib
import io
import json
import re
from datetime import datetime
from pathlib import Path

import pandas as pd

from nbatools.commands.pipeline.player_game_availability_espn import _name
from nbatools.commands.pipeline.pull_player_game_availability import (
    COLUMNS,
    _atomic_csv,
    _cached_boxscore,
    _game_digest,
    normalize_boxscore_availability,
    validate_availability,
)

PREFIX = "nba_stats_structured_archive"
ARCHIVE = "https://raw.githubusercontent.com/sportsdataverse/hoopR-nba-stats-raw"


def _integer(value):
    if isinstance(value, bool):
        raise ValueError("Boolean structured identity/count")
    number = float(value)
    if not pd.notna(number) or number % 1 or number < 0:
        raise ValueError("Invalid structured identity/count")
    return int(number)


def _table(document, name):
    matches = [x for x in document["resultSets"] if x["name"] == name]
    if len(matches) != 1:
        raise ValueError(f"Missing/duplicate structured table {name}")
    item = matches[0]
    if len(item["headers"]) != len(set(item["headers"])):
        raise ValueError("Duplicate structured headers")
    if any(len(row) != len(item["headers"]) for row in item["rowSet"]):
        raise ValueError("Truncated structured row")
    return pd.DataFrame(item["rowSet"], columns=item["headers"])


def _canonical(root, season, kind, game_id):
    suffix = f"{season}_{kind.lower().replace(' ', '_')}.csv"
    games = pd.read_csv(root / "raw/games" / suffix)
    games = games.loc[pd.to_numeric(games.game_id).eq(game_id)]
    if len(games) != 1:
        raise ValueError("Structured source requires unique canonical game")
    game = games.iloc[0]
    if (
        str(game.is_final).lower() not in {"true", "1"}
        or game.season != season
        or game.season_type != kind
    ):
        raise ValueError("Structured source requires canonical final season/game")
    teams = pd.read_csv(root / "raw/team_game_stats" / suffix)
    teams = teams.loc[pd.to_numeric(teams.game_id).eq(game_id)]
    ids = {int(game.home_team_id), int(game.away_team_id)}
    if len(ids) != 2 or len(teams) != 2 or set(teams.team_id) != ids:
        raise ValueError("Structured canonical sides incomplete")
    players = pd.read_csv(root / "raw/player_game_stats" / suffix)
    identities = players[["player_id", "player_name"]].drop_duplicates()
    players = players.loc[pd.to_numeric(players.game_id).eq(game_id)]
    if players.empty or players.player_id.duplicated().any():
        raise ValueError("Structured canonical played identities incomplete")
    return game, teams.set_index("team_id"), players, identities


def _summary(document, version, game, teams):
    gid, day = int(game.game_id), str(game.game_date)
    home, away = int(game.home_team_id), int(game.away_team_id)
    inactive = []
    if version == 2:
        # Multiple broadcast records are valid, but every scope field must agree.
        scope = _table(document, "GameSummary")
        required = ["GAME_ID", "GAME_DATE_EST", "GAME_STATUS_ID", "HOME_TEAM_ID", "VISITOR_TEAM_ID"]
        if scope.empty or not set(required).issubset(scope):
            raise ValueError("Structured summary scope missing")
        if not (
            scope.GAME_ID.map(_integer).eq(gid)
            & scope.GAME_DATE_EST.astype(str).str[:10].eq(day)
            & scope.GAME_STATUS_ID.map(_integer).eq(3)
            & scope.HOME_TEAM_ID.map(_integer).eq(home)
            & scope.VISITOR_TEAM_ID.map(_integer).eq(away)
        ).all():
            raise ValueError("Structured summary wrong game/date/finality/sides")
        scores = _table(document, "LineScore")
        if len(scores) != 2 or set(scores.TEAM_ID.map(_integer)) != {home, away}:
            raise ValueError("Structured summary line scores incomplete")
        for row in scores.itertuples():
            ident = _integer(row.TEAM_ID)
            if (
                _integer(row.GAME_ID) != gid
                or str(row.GAME_DATE_EST)[:10] != day
                or _integer(row.PTS) != _integer(teams.loc[ident, "pts"])
                or row.TEAM_ABBREVIATION != teams.loc[ident, "team_abbr"]
            ):
                raise ValueError("Structured summary score/team mismatch")
        for row in _table(document, "InactivePlayers").itertuples():
            if (
                _integer(row.TEAM_ID) not in teams.index
                or row.TEAM_ABBREVIATION != teams.loc[_integer(row.TEAM_ID), "team_abbr"]
            ):
                raise ValueError("Structured inactive team abbreviation mismatch")
            inactive.append(
                dict(
                    teamId=_integer(row.TEAM_ID),
                    personId=_integer(row.PLAYER_ID),
                    firstName=row.FIRST_NAME,
                    familyName=row.LAST_NAME,
                )
            )
    elif version == 3:
        scope = document["boxScoreSummary"]
        if (
            _integer(scope["gameId"]) != gid
            or str(scope["gameEt"])[:10] != day
            or _integer(scope["gameStatus"]) != 3
            or _integer(scope["homeTeamId"]) != home
            or _integer(scope["awayTeamId"]) != away
        ):
            raise ValueError("Structured summary wrong game/date/finality/sides")
        for side, ident in (("homeTeam", home), ("awayTeam", away)):
            team = scope[side]
            if (
                _integer(team["teamId"]) != ident
                or _integer(team["score"]) != _integer(teams.loc[ident, "pts"])
                or team["teamTricode"] != teams.loc[ident, "team_abbr"]
                or not isinstance(team["inactives"], list)
            ):
                raise ValueError("Structured summary score/team mismatch")
            for player in team["inactives"]:
                inactive.append(
                    dict(
                        teamId=ident,
                        personId=_integer(player["personId"]),
                        firstName=player["firstName"],
                        familyName=player["familyName"],
                    )
                )
    else:
        raise ValueError("Structured summary version must be 2 or 3")
    for row in inactive:
        if row["teamId"] not in {home, away} or row["personId"] <= 0:
            raise ValueError("Structured inactive has wrong identity/side")
        row.update(
            gameId=gid,
            teamTricode=teams.loc[row["teamId"], "team_abbr"],
            minutes=None,
            comment=f"INACTIVE - BoxScoreSummaryV{version} explicit listed row",
        )
    return inactive


def _build(root, packet, source_dir, packet_hash):
    game_id, season, kind = packet["game_id"], packet["season"], packet["season_type"]
    if (
        type(game_id) is not int
        or game_id <= 0
        or not re.fullmatch(r"[a-f0-9]{40}", packet["revision"])
    ):
        raise ValueError("Invalid structured packet identity")
    if packet.get("source_kind") != "retained_nba_stats_archive":
        raise ValueError("Unrecognized structured source kind")
    if datetime.fromisoformat(packet["retrieved_at"]).tzinfo is None:
        raise ValueError("Structured capture time requires timezone")
    paths = []
    for endpoint in ("boxscoretraditionalv3", f"boxscoresummaryv{packet['summary_version']}"):
        item = packet["sources"][endpoint]
        digest = item["sha256"]
        year = int(season[:4]) + 1
        expected = (
            f"{ARCHIVE}/{packet['revision']}/nba_stats/json/{endpoint}/{year}/{game_id:010d}.json"
        )
        if (
            not re.fullmatch(r"[a-f0-9]{64}", digest)
            or item["url"] != expected
            or item["file"] != f"{digest}.json"
        ):
            raise ValueError("Structured archive provenance mismatch")
        path = source_dir / item["file"]
        if path.stat().st_size > 2_000_000:
            raise ValueError("Structured source exceeds byte bound")
        raw = path.read_bytes()
        if len(raw) != item["size_bytes"] or hashlib.sha256(raw).hexdigest() != digest:
            raise ValueError("Structured original bytes differ from receipt")
        paths.append(path)
    game, teams, appearances, identities = _canonical(root, season, kind, game_id)
    traditional = json.loads(paths[0].read_bytes())["boxScoreTraditional"]
    if int(traditional["homeTeamId"]) != int(game.home_team_id) or int(
        traditional["awayTeamId"]
    ) != int(game.away_team_id):
        raise ValueError("Structured traditional sides differ from canonical game")
    source = f"{PREFIX}:{packet['revision']}:{game_id:010d}"
    raw = _cached_boxscore(paths[0])
    for side in ("homeTeam", "awayTeam"):
        team = traditional[side]
        if team["teamTricode"] != teams.loc[int(team["teamId"]), "team_abbr"]:
            raise ValueError("Structured traditional team abbreviation mismatch")
        if _integer(team["statistics"]["points"]) != _integer(
            teams.loc[int(team["teamId"]), "pts"]
        ):
            raise ValueError("Structured traditional team score mismatch")
    extra = _summary(json.loads(paths[1].read_bytes()), packet["summary_version"], game, teams)
    if extra:
        raw = pd.concat([raw, pd.DataFrame(extra)], ignore_index=True)
    raw.attrs["source_sha256"] = packet_hash
    result = normalize_boxscore_availability(
        raw,
        game_id=game_id,
        game_date=str(game.game_date),
        season=season,
        season_type=kind,
        expected_team_ids=set(teams.index),
        source=source,
    )
    # Known identities constrain every listed row, not only participants. An
    # identity in another game is a name reference, never membership evidence.
    for person in raw.to_dict("records"):
        known = identities.loc[identities.player_id.eq(int(person["personId"])), "player_name"]
        names = set(known.map(_name))
        variants = {
            _name(person["firstName"] + " " + person["familyName"]),
            _name(person["familyName"] + " " + person["firstName"]),
        }
        if names and not names.intersection(variants):
            raise ValueError("Structured listed name disagrees with known canonical identity")
    nonplayers = set(result.loc[result.participation_state.eq("did_not_play"), "player_id"])
    activity = (
        "points",
        "fieldGoalsMade",
        "fieldGoalsAttempted",
        "threePointersMade",
        "threePointersAttempted",
        "freeThrowsMade",
        "freeThrowsAttempted",
        "reboundsOffensive",
        "reboundsDefensive",
        "reboundsTotal",
        "assists",
        "steals",
        "blocks",
        "turnovers",
        "foulsPersonal",
    )
    for side in ("homeTeam", "awayTeam"):
        for person in traditional[side]["players"]:
            if int(person["personId"]) in nonplayers and any(
                _integer(person["statistics"].get(key) or 0) != 0 for key in activity
            ):
                raise ValueError("Structured nonparticipant contradicts positive activity")
    played = result.loc[result.participation_state.eq("played")]
    if set(zip(played.team_id, played.player_id)) != set(
        zip(appearances.team_id, appearances.player_id)
    ):
        raise ValueError("Structured played identities differ from canonical appearances")
    original_players = {
        int(p["personId"]): p
        for side in ("homeTeam", "awayTeam")
        for p in traditional[side]["players"]
    }
    for row in appearances.itertuples():
        person = original_players[int(row.player_id)]
        if _name(row.player_name) not in {
            _name(person["firstName"] + " " + person["familyName"]),
            _name(person["familyName"] + " " + person["firstName"]),
        }:
            raise ValueError("Structured played name disagrees with canonical identity")
        if _integer(original_players[int(row.player_id)]["statistics"]["points"]) != _integer(
            row.pts
        ):
            raise ValueError("Structured player points differ from canonical appearances")
    validate_availability(result)
    return result


def stage_structured_game(
    root: Path,
    *,
    season: str,
    season_type: str,
    game_id: int,
    traditional: Path,
    summary: Path,
    summary_version: int,
    revision: str,
    retrieved_at: str,
) -> pd.DataFrame:
    """Stage a full exact-game listed population after original-source qualification."""
    directory = root / "raw/player_game_availability_sources"
    directory.mkdir(parents=True, exist_ok=True)
    packet = dict(
        game_id=game_id,
        season=season,
        season_type=season_type,
        summary_version=summary_version,
        revision=revision,
        retrieved_at=retrieved_at,
        source_kind="retained_nba_stats_archive",
        sources={},
    )
    for endpoint, path in (
        ("boxscoretraditionalv3", traditional),
        (f"boxscoresummaryv{summary_version}", summary),
    ):
        if path.stat().st_size > 2_000_000:
            raise ValueError("Structured source exceeds byte bound")
        raw = path.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        (directory / f"{digest}.json").write_bytes(raw)
        packet["sources"][endpoint] = dict(
            sha256=digest,
            size_bytes=len(raw),
            file=f"{digest}.json",
            url=(
                f"{ARCHIVE}/{revision}/nba_stats/json/{endpoint}/"
                f"{int(season[:4]) + 1}/{game_id:010d}.json"
            ),
        )
    content = (json.dumps(packet, sort_keys=True, indent=2) + "\n").encode()
    digest = hashlib.sha256(content).hexdigest()
    rows = _build(root, packet, directory, digest)
    target = (
        root
        / "raw/player_game_availability"
        / f"{season}_{season_type.lower().replace(' ', '_')}.csv"
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    old = pd.read_csv(target) if target.exists() else pd.DataFrame(columns=COLUMNS)
    if not old.empty:
        validate_availability(old)
        previous = old.loc[pd.to_numeric(old.game_id).eq(game_id)]
        if not previous.empty:
            if previous.source.astype(str).str.startswith("nba_official_finalbox:").any():
                raise ValueError(
                    "Structured replacement would downgrade qualified PDF clock authority"
                )
            shared = previous.merge(
                rows, on=["game_id", "team_id", "player_id"], suffixes=("_old", "_new")
            )
            if (
                len(shared) != len(previous)
                or not shared.participation_state_old.eq(shared.participation_state_new).all()
                or not shared.game_date_old.eq(shared.game_date_new).all()
            ):
                raise ValueError(
                    "Structured replacement drops or contradicts existing qualified evidence"
                )
    output = pd.concat([old.loc[~pd.to_numeric(old.game_id).eq(game_id)], rows], ignore_index=True)
    validate_availability(output)
    (directory / f"{digest}.structured.json").write_bytes(content)
    receipt_path = target.with_suffix(".imports.json")
    receipts = json.loads(receipt_path.read_text()) if receipt_path.exists() else {}
    receipts[str(game_id)] = dict(source="structured", sha256=_game_digest(rows))
    _atomic_csv(output, target)
    receipt_path.write_text(json.dumps(receipts, sort_keys=True) + "\n")
    return rows


def validate_structured_import(root, game_id, rows, receipt):
    """Rebuild against retained originals and canonical rows before publication."""
    if rows.source_sha256.nunique() != 1 or receipt.get("sha256") != _game_digest(rows):
        raise ValueError("Structured import digest mismatch")
    digest = str(rows.source_sha256.iloc[0])
    if not re.fullmatch(r"[a-f0-9]{64}", digest):
        raise ValueError("Structured packet digest missing")
    directory = root / "raw/player_game_availability_sources"
    content = (directory / f"{digest}.structured.json").read_bytes()
    if hashlib.sha256(content).hexdigest() != digest:
        raise ValueError("Structured packet bytes differ from digest")
    packet = json.loads(content)
    if packet["game_id"] != int(game_id):
        raise ValueError("Structured packet has wrong game")
    expected = _build(root, packet, directory, digest)
    if _game_digest(expected) != _game_digest(rows):
        raise ValueError("Structured rows differ from original qualified sources")


INACTIVE_PREFIX = "sportsdataverse_nba_inactive_archive"
INACTIVE_ROOT = "raw/player_game_inactive"
INACTIVE_SOURCES = "raw/player_game_inactive_sources"
INACTIVE_FIELDS = (
    "player_id",
    "first_name",
    "last_name",
    "jersey_num",
    "team_id",
    "team_city",
    "team_name",
    "team_abbreviation",
    "season",
    "game_id",
    "season_type_id",
)


def inactive_dependencies(season):
    if not isinstance(season, str) or not re.fullmatch(r"(?:19|20)\d{2}-\d{2}", season):
        raise ValueError("Invalid inactive season")
    if season[-2:] != str(int(season[:4]) + 1)[-2:]:
        raise ValueError("Invalid inactive season ending year")
    suffix = f"{season}_regular_season.csv"
    return [f"raw/{kind}/{suffix}" for kind in ("games", "team_game_stats", "player_game_stats")]


def qualify_season_inactive(raw, receipt, season, dependencies):
    """Qualify explicit archived SummaryV2 inactive rows, never source omissions.

    This is the publisher's season CSV, not reconstructed NBA wire responses.
    Canonical scope, known identities and appearances constrain every record.
    No continuous membership, complete roster or absence reason is derived.
    """
    policy = receipt.get("identity_name_policy")
    if policy not in (None, "quarantine_known_conflicts_v1"):
        raise ValueError("Unknown inactive identity-name policy")
    if policy is None and "identity_name_rejections" in receipt:
        raise ValueError("Inactive identity rejections require an explicit policy")
    paths = inactive_dependencies(season)
    year = int(season[:4]) + 1
    digest = hashlib.sha256(raw).hexdigest()
    url = (
        "https://github.com/sportsdataverse/sportsdataverse-data/releases/download/"
        f"nba_stats_game_rosters/game_rosters_{year}.csv"
    )
    asset = receipt["publisher_asset"]
    if (
        not 0 < len(raw) <= 16_000_000
        or receipt.get("schema_version") != 1
        or receipt.get("source_kind") != "archive_derived_summary_v2_inactive_rows"
        or receipt.get("origin_table") != "BoxScoreSummaryV2.InactivePlayers"
        or receipt.get("source_url") != url
        or receipt.get("sha256") != digest
        or receipt.get("size_bytes") != len(raw)
        or receipt.get("original_nba_capture_time") is not None
        or datetime.fromisoformat(receipt["retrieved_at"]).tzinfo is None
        or not re.fullmatch(r"[a-f0-9]{40}", receipt["schema_reference_revision"])
        or type(asset["id"]) is not int
        or asset["id"] <= 0
        or asset["name"] != f"game_rosters_{year}.csv"
        or asset["browser_download_url"] != url
        or asset["digest"] != "sha256:" + digest
        or asset["size"] != len(raw)
        or set(dependencies) != set(paths)
        or set(receipt["canonical_file_sha256"]) != set(paths)
        or any(
            hashlib.sha256(dependencies[p]).hexdigest() != receipt["canonical_file_sha256"][p]
            for p in paths
        )
    ):
        raise ValueError("Inactive archive provenance/dependency mismatch")
    frame = pd.read_csv(io.BytesIO(raw), dtype=str, keep_default_na=False)
    if tuple(frame.columns) != INACTIVE_FIELDS or frame.empty:
        raise ValueError("Unrecognized inactive archive schema")
    if not (
        frame.game_id.str.fullmatch(r"\d{10}")
        & frame.season.eq(str(year))
        & frame.season_type_id.eq(frame.game_id.str[2])
        & frame.first_name.str.strip().ne("")
        & frame.last_name.str.strip().ne("")
    ).all():
        raise ValueError("Malformed inactive archive identity/season")
    from nbatools.commands._participation_observations import _ids

    for key in ("game_id", "player_id", "team_id"):
        frame[key] = _ids(frame[key])
    if frame.duplicated(["game_id", "player_id"]).any():
        raise ValueError("Duplicate/conflicting inactive archive keys")
    frame = frame.loc[frame.season_type_id.eq("2")].copy()
    if frame.empty:
        raise ValueError("Inactive archive has no regular-season observations")
    games, teams, players = [pd.read_csv(io.BytesIO(dependencies[p])) for p in paths]
    for table in (games, teams, players):
        if not (table.season.eq(season) & table.season_type.eq("Regular Season")).all():
            raise ValueError("Inactive canonical season/type mismatch")
    if games.game_id.duplicated().any() or teams.duplicated(["game_id", "team_id"]).any():
        raise ValueError("Duplicate inactive canonical game/team keys")
    games = games.set_index("game_id")
    teams = teams.set_index(["game_id", "team_id"])
    known = players.groupby("player_id").player_name.agg(lambda ns: {_name(n) for n in ns})
    rejected, rejected_indices = [], []
    for row in frame.itertuples():
        if row.game_id not in games.index or (row.game_id, row.team_id) not in teams.index:
            raise ValueError("Inactive archive outside canonical game/team sides")
        game, team = games.loc[row.game_id], teams.loc[(row.game_id, row.team_id)]
        if (
            str(game.is_final).lower() not in {"true", "1"}
            or row.team_id not in {int(game.home_team_id), int(game.away_team_id)}
            or row.team_abbreviation != team.team_abbr
            or str(team.game_date) != str(game.game_date)
        ):
            raise ValueError("Inactive archive canonical envelope mismatch")
        # Unknown NBA IDs are allowed just as in native Summary imports; some
        # two-way players never appear in the canonical appearance/name index.
        if (
            row.player_id in known
            and _name(row.first_name + " " + row.last_name) not in known[row.player_id]
        ):
            if policy is None:
                raise ValueError("Inactive name conflicts with known NBA identity")
            rejected_indices.append(row.Index)
            rejected.append(
                dict(
                    game_id=int(row.game_id),
                    team_id=int(row.team_id),
                    player_id=int(row.player_id),
                    reason="identity_name_conflict",
                )
            )
    if not frame.merge(players, on=["game_id", "player_id"]).empty:
        raise ValueError("Inactive archive contradicts a canonical appearance")
    # Quarantine only this precisely defined identity uncertainty. Every source
    # row still passes the scope, side, duplicate and appearance guards above.
    rejected.sort(key=lambda r: (r["game_id"], r["team_id"], r["player_id"]))
    if "identity_name_rejections" in receipt and json.dumps(
        receipt["identity_name_rejections"], sort_keys=True
    ) != json.dumps(rejected, sort_keys=True):
        raise ValueError("Inactive identity rejection ledger differs from source")
    frame = frame.drop(index=rejected_indices)
    if frame.empty:
        raise ValueError("No qualified inactive rows remain")
    result = pd.DataFrame(
        {
            "game_id": frame.game_id,
            "game_date": frame.game_id.map(games.game_date),
            "season": season,
            "season_type": "Regular Season",
            "team_id": frame.team_id,
            "team_abbr": frame.team_abbreviation,
            "player_id": frame.player_id,
            "player_name": frame.first_name + " " + frame.last_name,
            "participation_state": "did_not_play",
            "source_minutes": None,
            "source_comment": "INACTIVE - archived BoxScoreSummaryV2 listed row",
            "source": INACTIVE_PREFIX + ":" + digest,
            "source_sha256": digest,
            "identity_source_sha256": "",
            "coverage_scope": "listed_player_rows_only",
        },
        columns=COLUMNS,
    )
    result = result.sort_values(["game_id", "player_id"]).reset_index(drop=True)
    if policy is not None:
        result.attrs["identity_name_rejections"] = rejected
    return result


def stage_season_inactive(root, raw, receipt, season):
    """Add a separate immutable batch to an isolated data root; no acquisition.

    Existing per-game/PDF rows and import ledgers are never overwritten.
    """
    root = Path(root)
    if (root / "metadata/generation_manifest.json").exists():
        raise ValueError("Inactive staging cannot modify a published generation")
    paths = inactive_dependencies(season)
    rows = qualify_season_inactive(
        raw, receipt, season, {p: (root / p).read_bytes() for p in paths}
    )
    target = root / INACTIVE_ROOT / f"{season}_regular_season.csv"
    existing = root / "raw/player_game_availability" / target.name
    if existing.exists():
        validate_inactive_overlap(pd.read_csv(existing), rows)
    provenance = target.with_suffix(".source.json")
    if target.exists() or provenance.exists():
        raise ValueError("Inactive staging requires a new immutable season dataset")
    original = root / INACTIVE_SOURCES / f"{receipt['sha256']}.csv"
    if original.exists() and original.read_bytes() != raw:
        raise ValueError("Inactive original conflicts with retained bytes")
    original.parent.mkdir(parents=True, exist_ok=True)
    target.parent.mkdir(parents=True, exist_ok=True)
    original.write_bytes(raw)
    receipt = dict(receipt)
    if receipt.get("identity_name_policy") is not None:
        receipt["identity_name_rejections"] = rows.attrs["identity_name_rejections"]
    provenance.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    _atomic_csv(rows, target)
    return rows


def validate_inactive_overlap(existing, inactive):
    shared = existing.merge(inactive, on=["game_id", "player_id"], suffixes=("", "_inactive"))
    if (
        not shared.empty
        and not (
            shared.team_id.eq(shared.team_id_inactive)
            & shared.game_date.eq(shared.game_date_inactive)
            & shared.participation_state.isin(["did_not_play", "unknown"])
        ).all()
    ):
        raise ValueError("Season inactive archive contradicts qualified game observations")


def _inactive_replay(derived, original, receipt, season, dependencies):
    if (
        receipt.get("identity_name_policy") is not None
        and "identity_name_rejections" not in receipt
    ):
        raise ValueError("Inactive identity policy requires a replayable rejection ledger")
    expected = qualify_season_inactive(original, receipt, season, dependencies)
    if set(derived) != set(COLUMNS):
        raise ValueError("Inactive derived schema differs from qualified source")

    def cells(frame):
        from nbatools.commands._participation_observations import _ids

        frame = frame.copy()
        for key in ("game_id", "team_id", "player_id"):
            frame[key] = _ids(frame[key])
        return (
            frame[list(COLUMNS)]
            .sort_values(["game_id", "player_id"])
            .fillna("")
            .astype(str)
            .reset_index(drop=True)
        )

    if not cells(expected).equals(cells(derived)):
        raise ValueError("Inactive derived rows differ from qualified original")
    return expected


def validate_season_inactive(root):
    directory = Path(root) / INACTIVE_ROOT
    if not directory.exists():
        return
    for path in directory.iterdir():
        if not re.fullmatch(
            r"(?:19|20)\d{2}-\d{2}_regular_season\.(?:csv|source\.json)", path.name
        ):
            raise ValueError("Unfinished/unrecognized inactive staging file")
        season = path.name[:7]
        target = directory / f"{season}_regular_season.csv"
        receipt = json.loads(target.with_suffix(".source.json").read_bytes())
        if not re.fullmatch(r"[a-f0-9]{64}", str(receipt.get("sha256", ""))):
            raise ValueError("Malformed inactive original digest")
        if path != target:
            if not target.exists():
                raise ValueError("Inactive provenance lacks derived rows")
            continue
        expected = _inactive_replay(
            pd.read_csv(target),
            (Path(root) / INACTIVE_SOURCES / f"{receipt['sha256']}.csv").read_bytes(),
            receipt,
            season,
            {p: (Path(root) / p).read_bytes() for p in inactive_dependencies(season)},
        )
        existing = Path(root) / "raw/player_game_availability" / target.name
        if existing.exists():
            validate_inactive_overlap(pd.read_csv(existing), expected)


def load_season_inactive(seasons):
    """Serve only replayed source rows, cached by immutable generation identity."""
    from nbatools.data_source import data_exists, data_path, data_source_cache_key
    from nbatools.dataframe_cache import FRAME_CACHE

    frames = []
    for season in seasons:
        paths = inactive_dependencies(season)
        target = f"data/{INACTIVE_ROOT}/{season}_regular_season.csv"
        provenance = target.removesuffix(".csv") + ".source.json"

        def load(target=target, provenance=provenance, paths=paths, season=season):
            if data_exists(target) != data_exists(provenance):
                raise ValueError("Partial inactive season dataset")
            if not data_exists(target):
                return pd.DataFrame(columns=COLUMNS)
            receipt = json.loads(data_path(provenance).read_bytes())
            if not re.fullmatch(r"[a-f0-9]{64}", str(receipt.get("sha256", ""))):
                raise ValueError("Malformed inactive original digest")
            original = f"data/{INACTIVE_SOURCES}/{receipt['sha256']}.csv"
            return _inactive_replay(
                pd.read_csv(data_path(target)),
                data_path(original).read_bytes(),
                receipt,
                season,
                {p: data_path("data/" + p).read_bytes() for p in paths},
            )

        frames.append(
            FRAME_CACHE.get_or_load(("season_inactive", data_source_cache_key(), season), load)
        )
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=COLUMNS)
