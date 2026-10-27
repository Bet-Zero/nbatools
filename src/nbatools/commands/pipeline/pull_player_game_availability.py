"""Archive explicit NBA box-score participation and DNP evidence.

Unlike player_game_stats, the source includes some non-playing player rows.
This is an additive, listed-player-only dataset: no record is invented for a
person omitted from the official game box score. Consequently these records
alone do NOT establish a complete roster or all missed games.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from datetime import datetime
from pathlib import Path

import pandas as pd

from nbatools.commands.pipeline.pull_player_game_starter_roles import (
    fetch_starter_role_rows_for_game,
)

SOURCE = "nba_stats_boxscoretraditionalv3"
ESPN_SOURCE = "espn_game_summary"
REPORT_SOURCE = "nba_official_finalbox"
COVERAGE = "listed_player_rows_only"
COLUMNS = (
    "game_id",
    "game_date",
    "season",
    "season_type",
    "team_id",
    "team_abbr",
    "player_id",
    "player_name",
    "participation_state",
    "source_minutes",
    "source_comment",
    "source",
    "source_sha256",
    "identity_source_sha256",
    "coverage_scope",
)
_DNP = re.compile(
    r"^(?:DNP|DND|NWT|INACTIVE|DID NOT PLAY|DID NOT DRESS|"
    r"NOT WITH TEAM|NOT PLAYING)(?:\b|[-:/])",
    re.IGNORECASE,
)
_DURATION = re.compile(
    r"PT(?:(\d+(?:\.\d+)?)H)?(?:(\d+(?:\.\d+)?)M)?(?:(\d+(?:\.\d+)?)S)?",
    re.IGNORECASE,
)


def _minutes(value: object) -> float | None:
    if value is None or (not isinstance(value, (list, dict)) and pd.isna(value)):
        return None
    text = str(value).strip()
    if not text:
        return None
    if text.upper().startswith("PT"):
        matched = _DURATION.fullmatch(text)
        if matched is None or not any(group is not None for group in matched.groups()):
            raise ValueError(f"Invalid box-score duration: {text}")
        hour, minute, seconds = (float(n or 0) for n in matched.groups())
        minutes = hour * 60 + minute + seconds / 60
    elif ":" in text:
        parts = text.split(":")
        if len(parts) != 2:
            raise ValueError(f"Invalid box-score duration: {text}")
        try:
            minute, seconds = (float(n) for n in parts)
        except ValueError as exc:
            raise ValueError(f"Invalid box-score duration: {text}") from exc
        if not 0 <= seconds < 60:
            raise ValueError(f"Invalid box-score duration: {text}")
        minutes = minute + seconds / 60
    else:
        try:
            minutes = float(text)
        except ValueError as exc:
            raise ValueError(f"Invalid box-score duration: {text}") from exc
    if not math.isfinite(minutes) or minutes < 0:
        raise ValueError(f"Invalid box-score duration: {text}")
    return minutes


def normalize_boxscore_availability(
    raw: pd.DataFrame,
    *,
    game_id: int,
    game_date: str,
    season: str,
    season_type: str,
    expected_team_ids: set[int],
    source: str = SOURCE,
) -> pd.DataFrame:
    """Preserve source-listed played, DNP and unknown rows without inferring gaps."""
    names = {
        "gameId": "game_id",
        "teamId": "team_id",
        "teamTricode": "team_abbr",
        "personId": "player_id",
        "firstName": "first_name",
        "familyName": "family_name",
        "minutes": "source_minutes",
        "comment": "source_comment",
    }
    frame = raw.rename(columns=names).copy()
    required = set(names.values())
    if frame.empty or not required.issubset(frame.columns):
        raise ValueError(f"Box score missing required player rows/columns: {required - set(frame)}")
    identity_columns = sorted(required - {"source_minutes", "source_comment"})
    if frame[identity_columns].isna().any().any():
        raise ValueError("Box score has missing player/team identity fields")
    for key in ("game_id", "team_id", "player_id"):
        values = pd.to_numeric(frame[key], errors="raise")
        if values.isna().any() or (values <= 0).any() or (values % 1 != 0).any():
            raise ValueError("Box-score identities must be positive integers")
        frame[key] = values.astype("int64")
    if not frame["game_id"].eq(int(game_id)).all():
        raise ValueError("Box-score game ID does not match requested game")
    if set(frame["team_id"]) != set(expected_team_ids):
        raise ValueError("Box-score teams do not match the finalized game catalog")
    if frame.duplicated(["game_id", "player_id"]).any():
        raise ValueError("Duplicate player in official box-score game")
    for key in ("team_abbr", "first_name", "family_name"):
        frame[key] = frame[key].fillna("").astype(str).str.strip()
    frame["player_name"] = (frame["first_name"] + " " + frame["family_name"]).str.strip()
    if frame["team_abbr"].eq("").any() or frame["player_name"].eq("").any():
        raise ValueError("Box-score player/team name is blank")
    frame["source_comment"] = frame["source_comment"].fillna("").astype(str).str.strip()
    frame["source_minutes"] = frame["source_minutes"].map(_minutes)

    def state(row: pd.Series) -> str:
        dnp = bool(_DNP.match(row["source_comment"]))
        minutes = row["source_minutes"]
        if minutes is not None and not pd.isna(minutes) and minutes > 0:
            if dnp:
                raise ValueError("Contradictory box-score minutes and explicit DNP")
            return "played"
        if dnp:
            return "did_not_play"
        return "unknown"

    frame["participation_state"] = frame.apply(state, axis=1)
    frame["game_date"] = str(game_date)
    frame["season"] = str(season)
    frame["season_type"] = str(season_type)
    if source != SOURCE and not re.fullmatch(
        r"(?:espn_game_summary:\d+|nba_official_finalbox:\d{8}_[A-Z]{4,8}|"
        r"nba_stats_structured_archive:[a-f0-9]{40}:\d{10})",
        source,
    ):
        raise ValueError("Unrecognized availability source")
    frame["source"] = source
    frame["source_sha256"] = raw.attrs.get("source_sha256", "")
    frame["identity_source_sha256"] = raw.attrs.get("identity_source_sha256", "")
    frame["coverage_scope"] = COVERAGE
    return frame[list(COLUMNS)].sort_values(["team_id", "player_id"]).reset_index(drop=True)


def validate_availability(frame: pd.DataFrame) -> None:
    """Fail closed on duplicate/conflicting or falsely expanded source coverage."""
    if not set(COLUMNS).issubset(frame.columns):
        raise ValueError("Availability data missing required columns")
    if frame.empty:
        raise ValueError("Availability data has no official listed-player evidence")
    if frame.duplicated(["game_id", "player_id"]).any():
        raise ValueError("Conflicting duplicate player-game availability")
    if not frame["participation_state"].isin(["played", "did_not_play", "unknown"]).all():
        raise ValueError("Unknown participation state")
    allowed = frame["source"].eq(SOURCE) | frame["source"].str.fullmatch(
        r"(?:espn_game_summary:\d+|nba_official_finalbox:\d{8}_[A-Z]{4,8}|"
        r"nba_stats_structured_archive:[a-f0-9]{40}:\d{10})"
    )
    if not allowed.all() or not frame["coverage_scope"].eq(COVERAGE).all():
        raise ValueError("Untrusted availability source or completeness claim")
    hashes = frame[["source_sha256", "identity_source_sha256"]].fillna("").astype(str).stack()
    if not hashes.str.fullmatch(r"(?:[a-f0-9]{64})?").all():
        raise ValueError("Invalid source SHA256")
    if frame[["game_id", "team_id", "player_id", "season", "season_type"]].isna().any().any():
        raise ValueError("Null availability identity")
    for field in ("game_id", "team_id", "player_id"):
        pd.to_numeric(frame[field], errors="raise")
    played = frame["participation_state"].eq("played")
    minutes = pd.to_numeric(frame["source_minutes"], errors="coerce")
    if (played & minutes.le(0)).any() or (played & minutes.isna()).any():
        raise ValueError("Played requires verified positive minutes")
    if (frame["participation_state"].eq("did_not_play") & minutes.gt(0)).any():
        raise ValueError("DNP conflicts with played minutes")
    is_dnp = frame["participation_state"].eq("did_not_play")
    has_explicit_dnp = frame["source_comment"].fillna("").str.match(_DNP)
    if (is_dnp & ~has_explicit_dnp).any():
        raise ValueError("DNP requires an explicit nonparticipant statement")


def _cached_boxscore(path: Path) -> pd.DataFrame:
    """Read retained NBA Stats V3 response JSON, not an invented player roster."""
    content = path.read_bytes()
    document = json.loads(content)
    if not isinstance(document, dict):
        raise ValueError("Expected NBA Stats V3 object")
    parent = document.get("boxScoreTraditional", document)
    if not isinstance(parent, dict):
        raise ValueError("Expected NBA Stats V3 boxScoreTraditional object")
    nested = any(key in parent for key in ("homeTeam", "awayTeam"))
    if nested:
        if "playerStats" in parent:
            raise ValueError("Ambiguous nested and flattened box-score player rows")
        # Original V3 responses have players inside each team; playerStats is
        # the SDK's flattened dataset, not the original wire response.
        rows = []
        try:
            game_id = parent["gameId"]
            side_ids = [parent["homeTeamId"], parent["awayTeamId"]]
            if side_ids[0] == side_ids[1]:
                raise ValueError("Box-score sides must identify distinct teams")
            for side, expected in zip(("homeTeam", "awayTeam"), side_ids):
                team = parent[side]
                if team["teamId"] != expected:
                    raise ValueError("Box-score side identity contradicts envelope")
                players = team["players"]
                if not isinstance(players, list) or not players:
                    raise ValueError("Box-score side has no listed player rows")
                for player in players:
                    rows.append(
                        dict(
                            gameId=game_id,
                            teamId=team["teamId"],
                            teamTricode=team["teamTricode"],
                            personId=player["personId"],
                            firstName=player["firstName"],
                            familyName=player["familyName"],
                            comment=player["comment"],
                            minutes=player["statistics"].get("minutes"),
                        )
                    )
        except (KeyError, TypeError, AttributeError) as exc:
            raise ValueError("Incomplete NBA Stats V3 original response") from exc
    else:
        rows = parent.get("playerStats")
        if not isinstance(rows, list) or not rows:
            raise ValueError(f"Expected NBA Stats V3 listed player rows: {path}")
    frame = pd.DataFrame(rows)
    frame.attrs["source_sha256"] = hashlib.sha256(content).hexdigest()
    return frame


def _game_digest(frame: pd.DataFrame) -> str:
    """Bind a completed import to all persisted rows, independent of CSV dtypes."""
    stable = frame[list(COLUMNS)].copy()
    for column in ("game_id", "team_id", "player_id"):
        stable[column] = pd.to_numeric(stable[column], errors="raise").astype("int64")
    stable["source_minutes"] = pd.to_numeric(stable["source_minutes"], errors="raise")
    stable = stable.sort_values(["team_id", "player_id"])
    payload = stable.to_csv(index=False, float_format="%.9g", na_rep="")
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _atomic_csv(frame: pd.DataFrame, path: Path) -> None:
    temporary = path.with_suffix(".tmp.csv")
    frame.to_csv(temporary, index=False)
    temporary.replace(path)


def validate_publication(root: Path) -> None:
    """Validate availability scope and retained source bytes before publication."""
    directory = root / "raw/player_game_availability"
    if not directory.exists():
        return
    for staging in (directory, root / "raw/player_game_availability_sources"):
        if staging.exists() and any(
            ".partial." in p.name or ".tmp" in p.name for p in staging.iterdir()
        ):
            raise ValueError("Availability staging contains unfinished imports")
    for path in directory.glob("*.csv"):
        frame = pd.read_csv(path, dtype={"game_id": str})
        validate_availability(frame)
        receipts = json.loads(path.with_suffix(".imports.json").read_text())
        catalogs = {}
        team_catalogs = {}
        for game_id, rows in frame.groupby("game_id"):
            if rows.season.nunique() != 1 or rows.season_type.nunique() != 1:
                raise ValueError("Availability game spans multiple season scopes")
            season, kind = rows.iloc[0][["season", "season_type"]]
            filename = f"{season}_{str(kind).lower().replace(' ', '_')}.csv"
            if filename != path.name:
                raise ValueError("Availability filename does not match row season/type")
            if filename not in catalogs:
                catalogs[filename] = pd.read_csv(root / "raw/games" / filename)
                team_catalogs[filename] = pd.read_csv(root / "raw/team_game_stats" / filename)
            catalog = catalogs[filename]
            game = catalog[pd.to_numeric(catalog.game_id).eq(int(game_id))]
            if len(game) != 1:
                raise ValueError("Availability game has no unique canonical game")
            game = game.iloc[0]
            if str(game.is_final).lower() not in {"true", "1"}:
                raise ValueError("Availability game is not final")
            receipt = receipts.get(str(int(game_id)), {})
            canonical_teams = {int(game.home_team_id), int(game.away_team_id)}
            scope = receipt.get("imported_team_ids")
            if scope is not None and (
                not isinstance(scope, list)
                or not scope
                or any(type(team) is not int for team in scope)
                or len(scope) != len(set(scope))
                or not set(scope).issubset(canonical_teams)
            ):
                raise ValueError("Invalid availability import team scope")
            expected_teams = canonical_teams if scope is None else set(scope)
            if (
                game.season != season
                or game.season_type != kind
                or not rows.game_date.eq(str(game.game_date)).all()
                or set(rows.team_id.map(int)) != expected_teams
            ):
                raise ValueError("Availability date/team/season differs from canonical game")
            if receipt.get("source") == "structured":
                from nbatools.commands.pipeline.structured_participation import (
                    validate_structured_import,
                )

                validate_structured_import(root, game_id, rows, receipt)
                continue
            if receipt.get("source") != "report" or receipt.get("sha256") != _game_digest(rows):
                raise ValueError("Availability import is incomplete or lacks source provenance")
            if rows.source.nunique() != 1 or rows.source_sha256.nunique() != 1:
                raise ValueError("Availability game has inconsistent source identity")
            source = str(rows.iloc[0].source)
            matched = re.fullmatch(r"nba_official_finalbox:(\d{8}_[A-Z]{4,8})", source)
            digest = str(rows.iloc[0].source_sha256)
            if matched is None or re.fullmatch(r"[a-f0-9]{64}", digest) is None:
                raise ValueError("Availability publication requires retained official source")
            reference = matched.group(1)
            day = str(game.game_date).replace("-", "")
            teams = team_catalogs[filename]
            teams = teams[pd.to_numeric(teams.game_id).eq(int(game_id))]
            if len(teams) != 2 or teams.team_id.nunique() != 2:
                raise ValueError("Availability lacks canonical team-game identities")
            abbrs = dict(zip(teams.team_id.map(int), teams.team_abbr))
            if not rows.team_abbr.eq(rows.team_id.map(abbrs)).all():
                raise ValueError("Availability team abbreviations differ from canonical teams")
            expected_reference = (
                f"{day}_{abbrs[int(game.away_team_id)]}{abbrs[int(game.home_team_id)]}"
            )
            if reference != expected_reference:
                raise ValueError("Availability source matchup differs from canonical game")
            source_dir = root / "raw/player_game_availability_sources"
            source_receipt = json.loads((source_dir / f"{reference}.json").read_text())
            retrieved = datetime.fromisoformat(str(source_receipt.get("retrieved_at", "")))
            expected_url = f"https://statsdmz.nba.com/pdfs/{day}/{reference}.pdf"
            if (
                not reference.startswith(day + "_")
                or source_receipt.get("source_url") != expected_url
                or source_receipt.get("sha256") != digest
                or source_receipt.get("raw_file") != f"{digest}.pdf"
                or retrieved.tzinfo is None
            ):
                raise ValueError("Availability original-source receipt is inconsistent")
            raw = (source_dir / f"{digest}.pdf").read_bytes()
            if (
                not raw.startswith(b"%PDF")
                or len(raw) != source_receipt.get("size_bytes")
                or hashlib.sha256(raw).hexdigest() != digest
            ):
                raise ValueError("Availability original-source bytes differ from receipt")

            identity_hashes = rows.identity_source_sha256.fillna("").unique()
            if len(identity_hashes) != 1:
                raise ValueError("Inconsistent availability identity source")
            if identity_hashes[0]:
                from nbatools.commands.pipeline.player_game_availability_report import (
                    IDENTITY_ROOT,
                    _name,
                    live_identity_rows,
                )

                identity_hash = identity_hashes[0]
                identity_receipt = json.loads(
                    (source_dir / f"{identity_hash}.receipt.json").read_text()
                )
                identity_raw = (source_dir / f"{identity_hash}.identity.json").read_bytes()
                retrieved = datetime.fromisoformat(identity_receipt["retrieved_at"])
                identity_payload = json.loads(identity_raw)
                profiles = identity_payload.get("source_kind") == "official_player_profiles"
                expected_identity_url = (
                    "derived:official_profile_identities_v1"
                    if profiles
                    else f"{IDENTITY_ROOT}/boxscore_{int(game_id):010d}.json"
                )
                if (
                    identity_receipt.get("source_url") != expected_identity_url
                    or identity_receipt.get("sha256") != identity_hash
                    or identity_receipt.get("raw_file") != f"{identity_hash}.identity.json"
                    or identity_receipt.get("size_bytes") != len(identity_raw)
                    or retrieved.tzinfo is None
                    or hashlib.sha256(identity_raw).hexdigest() != identity_hash
                ):
                    raise ValueError("Availability identity source receipt/bytes mismatch")
                if profiles:
                    from nbatools.commands.pipeline.player_game_availability_espn import (
                        _nba_players,
                    )
                    from nbatools.commands.pipeline.player_game_availability_profiles import (
                        validate_profile_index,
                    )

                    identities = validate_profile_index(identity_payload, source_dir)
                    canonical = _nba_players(root, season, str(kind).lower().replace(" ", "_"))
                    for item in identities.itertuples():
                        if (
                            canonical.player_id.eq(item.player_id)
                            & ~canonical.normalized.eq(item.normalized)
                        ).any():
                            raise ValueError(
                                "Official profile conflicts with canonical NBA identity"
                            )
                        if not (
                            rows.player_id.eq(item.player_id) & rows.team_id.eq(item.team_id)
                        ).any():
                            raise ValueError("Official profile identity is not used by this report")
                    identities = pd.concat(
                        [canonical, identities], ignore_index=True
                    ).drop_duplicates()
                else:
                    identities = live_identity_rows(
                        identity_payload,
                        game_id=int(game_id),
                        game_date=str(game.game_date),
                        home_team_id=int(game.home_team_id),
                        away_team_id=int(game.away_team_id),
                        by_id={int(t.team_id): (t.team_abbr, t.pts) for t in teams.itertuples()},
                    )
                for row in rows.itertuples():
                    match = identities[
                        identities.player_id.eq(row.player_id) & identities.team_id.eq(row.team_id)
                    ]
                    if match.empty or set(match.normalized) != {_name(row.player_name)}:
                        raise ValueError("Availability row differs from retained official identity")


def backfill(
    season: str,
    season_type: str = "Regular Season",
    *,
    root: Path = Path("data"),
    cached_boxscores: Path | None = None,
    cached_reports: Path | None = None,
    game_ids: list[int] | None = None,
    limit: int | None = None,
    source: str = "stats",
    imported_team_ids: list[int] | None = None,
) -> pd.DataFrame:
    """Fetch/cache official listed-player evidence with resumable, atomic output.

    This collects DNP rows without changing the existing starter-role importer.
    No R2 publication or whole-sample without-player activation occurs here.
    """
    if source not in {"stats", "espn", "report"}:
        raise ValueError("Source must be stats or espn")
    if cached_boxscores is not None and source != "stats":
        raise ValueError("Cached NBA Stats JSON is incompatible with ESPN source")
    if cached_reports is not None and source != "report":
        raise ValueError("Cached reports only support the report source")
    if imported_team_ids is not None and (
        source != "report"
        or cached_reports is None
        or not imported_team_ids
        or any(type(team) is not int for team in imported_team_ids)
        or len(imported_team_ids) != len(set(imported_team_ids))
    ):
        raise ValueError("Explicit team scope requires a retained official report and team IDs")
    if limit is not None and limit < 1:
        raise ValueError("limit must be positive")
    safe = season_type.lower().replace(" ", "_")
    games_path = root / "raw" / "games" / f"{season}_{safe}.csv"
    games = pd.read_csv(games_path, dtype={"game_id": str})
    required = {
        "game_id",
        "game_date",
        "season",
        "season_type",
        "is_final",
        "home_team_id",
        "away_team_id",
    }
    if not required.issubset(games.columns) or games.empty:
        raise ValueError("Finalized game catalog missing required columns/rows")
    if games["game_id"].duplicated().any():
        raise ValueError("Duplicate game in catalog")
    if not games["season"].eq(season).all() or not games["season_type"].eq(season_type).all():
        raise ValueError("Wrong season/type in game catalog")
    if game_ids is not None:
        selected = {int(i) for i in game_ids}
        if not selected:
            raise ValueError("Requested game IDs cannot be empty")
        games = games[games["game_id"].map(int).isin(selected)].copy()
        if set(games["game_id"].map(int)) != selected:
            raise ValueError("Requested game not in finalized catalog")
    if not games["is_final"].astype(str).str.lower().isin(["true", "1"]).all():
        raise ValueError("Availability requires final games")
    if limit is not None:
        games = games.head(limit)
    if games.empty:
        raise ValueError("No final games selected")

    directory = root / "raw" / "player_game_availability"
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / f"{season}_{safe}.csv"
    checkpoint = target.with_suffix(".partial.csv")
    receipts_path = target.with_suffix(".imports.json")
    receipts = json.loads(receipts_path.read_text()) if receipts_path.exists() else {}
    frames = []
    # The checkpoint is an atomic full snapshot, not a potentially torn append.
    # It supersedes the last completed target when an import was interrupted.
    for path in (checkpoint,) if checkpoint.exists() else (target,):
        if path.exists():
            old = pd.read_csv(path, dtype={"game_id": str})
            for column in ("source_sha256", "identity_source_sha256"):
                if column not in old:
                    old[column] = ""
            if not old.empty:
                validate_availability(old)
                frames.append(old)
    if frames:
        existing = pd.concat(frames, ignore_index=True)
        # An interrupted append may repeat a full game; identical rows are safe.
        existing = existing.drop_duplicates()
        validate_availability(existing)
    else:
        existing = pd.DataFrame(columns=COLUMNS)

    for row in games.itertuples(index=False):
        ident = int(row.game_id)
        expected = {int(row.home_team_id), int(row.away_team_id)}
        if len(expected) != 2:
            raise ValueError("Game does not identify two distinct teams")
        previous = existing[existing["game_id"].map(int).eq(ident)]
        if imported_team_ids is not None:
            selected = set(imported_team_ids)
            if not selected.issubset(expected):
                raise ValueError("Requested report team is not in the canonical game")
            if not set(previous.team_id.map(int)).issubset(selected):
                raise ValueError(
                    "Scoped import cannot replace existing outside-scope team evidence"
                )
            expected = selected
        receipt = receipts.get(str(ident), {})
        # An explicitly supplied retained source must be verified and replayed,
        # even when existing normalized rows have a valid local import digest.
        if (
            cached_reports is None
            and cached_boxscores is None
            and not previous.empty
            and receipt.get("source") == source
        ):
            if (
                receipt.get("sha256") == _game_digest(previous)
                and previous["game_date"].eq(str(row.game_date)).all()
                and previous["season"].eq(season).all()
                and previous["season_type"].eq(season_type).all()
                and set(previous["team_id"].map(int)) == expected
                and set(
                    receipt.get("imported_team_ids", [int(row.home_team_id), int(row.away_team_id)])
                )
                == expected
            ):
                continue
        source_name = SOURCE
        if source == "report":
            from nbatools.commands.pipeline.player_game_availability_report import (
                official_report_as_v3,
            )

            raw, report_ref = official_report_as_v3(
                game_id=ident,
                game_date=str(row.game_date),
                season=season,
                season_type=season_type,
                home_team_id=int(row.home_team_id),
                away_team_id=int(row.away_team_id),
                data_root=root,
                cached_reports=cached_reports,
                imported_team_ids=imported_team_ids,
            )
            source_name = f"{REPORT_SOURCE}:{report_ref}"
        elif source == "espn":
            from nbatools.commands.pipeline.player_game_availability_espn import (
                espn_boxscore_as_v3,
            )

            raw, event_id = espn_boxscore_as_v3(
                game_id=ident,
                game_date=str(row.game_date),
                season=season,
                season_type=season_type,
                home_team_id=int(row.home_team_id),
                away_team_id=int(row.away_team_id),
                data_root=root,
            )
            source_name = f"{ESPN_SOURCE}:{event_id}"
        elif cached_boxscores is not None:
            path = cached_boxscores / f"boxscore_{ident:010d}.json"
            if not path.is_file():
                raise FileNotFoundError(
                    f"Official box-score archive missing for game {ident:010d}: {path}"
                )
            raw = _cached_boxscore(path)
        else:
            raw = fetch_starter_role_rows_for_game(ident)
        new = normalize_boxscore_availability(
            raw,
            game_id=ident,
            game_date=str(row.game_date),
            season=season,
            season_type=season_type,
            expected_team_ids=expected,
            source=source_name,
        )
        # Replace this game's old rows only after successful reacquisition.
        # A source switch must fetch its own evidence, including added inactives.
        existing = existing[~existing["game_id"].map(int).eq(ident)]
        existing = pd.concat([existing, new], ignore_index=True)
        validate_availability(existing)
        _atomic_csv(existing, checkpoint)
        receipts[str(ident)] = {"source": source, "sha256": _game_digest(new)}
        if imported_team_ids is not None:
            receipts[str(ident)]["imported_team_ids"] = sorted(expected)
        receipt_tmp = receipts_path.with_suffix(".tmp.json")
        receipt_tmp.write_text(json.dumps(receipts, sort_keys=True) + "\n")
        receipt_tmp.replace(receipts_path)

    if existing.empty:
        raise ValueError("No verified source rows acquired")
    existing = existing.sort_values(["game_date", "game_id", "team_id", "player_id"])
    existing["game_id"] = existing["game_id"].map(lambda x: str(int(x)).zfill(10))
    validate_availability(existing)
    _atomic_csv(existing, target)
    checkpoint.unlink(missing_ok=True)
    return existing.reset_index(drop=True)


def run(
    season: str,
    season_type: str = "Regular Season",
    *,
    cached_boxscores: Path | None = None,
    cached_reports: Path | None = None,
    game_ids: list[int] | None = None,
    limit: int | None = None,
    source: str = "stats",
    imported_team_ids: list[int] | None = None,
) -> None:
    result = backfill(
        season,
        season_type,
        cached_boxscores=cached_boxscores,
        cached_reports=cached_reports,
        game_ids=game_ids,
        limit=limit,
        source=source,
        imported_team_ids=imported_team_ids,
    )
    print(
        f"Saved {len(result)} official player-game status observations "
        f"({int(result.participation_state.eq('did_not_play').sum())} explicit DNP). "
        "Coverage: listed players only; not all missed games."
    )
    if imported_team_ids is not None:
        print(
            f"Team-scoped import only: {', '.join(map(str, imported_team_ids))}; "
            "not a full-game import."
        )
