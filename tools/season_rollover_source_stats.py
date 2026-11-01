"""Offline qualification of retained 2026-27 season sources; no acquisition or publication."""

from __future__ import annotations

import hashlib
import io
import json
import stat
import zipfile
from pathlib import Path

import pandas as pd

from nbatools.commands.pipeline import pull_player_season_advanced as player_advanced
from nbatools.commands.pipeline import pull_standings_snapshots, pull_team_season_advanced
from nbatools.commands.pipeline.structured_participation import _table
from tools.cloud_season_sources import check_parameters
from tools.collect_season_rollover import BLOB, BYTES, REVISION, SEASON, schedule_population


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def retained_stats_documents(evidence):
    binding = json.loads((evidence / "stats-bundle.json").read_text())
    if binding["bundle"] != "stats-sources.zip" or binding["archive_revision"] != REVISION:
        raise ValueError("Unexpected retained stats bundle identity")
    bundle_path = evidence / "stats-sources.zip"
    if bundle_path.is_symlink() or bundle_path.stat().st_size > 8_000_000:
        raise ValueError("Invalid retained source bundle file")
    payload = bundle_path.read_bytes()
    if len(payload) != binding["bundle_bytes"] or _sha(payload) != binding["bundle_sha256"]:
        raise ValueError("Retained stats bundle differs")
    expected = {item["path"]: item for item in binding["files"]}
    documents, inputs = {}, {}
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        members = archive.infolist()
        if (
            len(expected) != len(binding["files"])
            or len(members) != len(expected)
            or set(archive.namelist()) != set(expected)
            or sum(item.file_size for item in members) > 8_000_000
            or any(
                stat.S_ISLNK(item.external_attr >> 16)
                or item.is_dir()
                or Path(item.filename).is_absolute()
                or ".." in Path(item.filename).parts
                or not item.filename.endswith(".json")
                for item in members
            )
        ):
            raise ValueError("Unsafe or unexpected data-only source bundle")
        for name, item in expected.items():
            raw = archive.read(name)
            if len(raw) != item["size_bytes"] or _sha(raw) != item["sha256"]:
                raise ValueError("Retained source bundle member differs")
        referenced = {"archive-metadata.json", "stats-capture.json", "supplemental-capture.json"}
        for name in ["stats-capture.json", "supplemental-capture.json"]:
            capture = json.loads(archive.read(name))
            if (
                capture["revision"] != REVISION
                or capture["season"] != SEASON
                or capture.get("season_type") != "Regular Season"
                or capture.get("repository") != "sportsdataverse/hoopR-nba-stats-raw"
            ):
                raise ValueError("Retained stats capture revision/season mismatch")
            for key, item in capture["source_files"].items():
                if key in documents:
                    raise ValueError("Duplicate retained source identity")
                raw = archive.read(item["file"])
                referenced.add(item["file"])
                expected_url = f"https://raw.githubusercontent.com/sportsdataverse/hoopR-nba-stats-raw/{REVISION}/{item['path']}"
                if (
                    item["url"] != expected_url
                    or len(raw) != item["size_bytes"]
                    or _sha(raw) != item["sha256"]
                    or hashlib.sha1(f"blob {len(raw)}\0".encode() + raw).hexdigest()
                    != item["git_blob_sha"]
                ):
                    raise ValueError("Retained stats original differs")
                inputs[key], documents[key] = item, json.loads(raw)
        if referenced != set(expected):
            raise ValueError("Unreferenced source bundle member")
    return documents, inputs, binding["bundle_sha256"]


def _scoped(document, expected):
    check_parameters(document, expected)
    # Every other endpoint-specific filter in these retained responses must be
    # unset/default. A scoped subset cannot masquerade as the league population.
    for key, value in document["parameters"].items():
        if key not in expected and value not in (None, "", 0, "0", "N"):
            raise ValueError(f"Unexpected season source filter: {key}")


def representative_findings(documents, finder, players):
    """Corroborate sampled fields without silently replacing any canonical row."""
    lookup = finder.set_index(["GAME_ID", "TEAM_ID"])
    player_lookup = players.set_index(["GAME_ID", "PLAYER_ID"])
    fields = {
        "points": "PTS",
        "fieldGoalsMade": "FGM",
        "fieldGoalsAttempted": "FGA",
        "threePointersMade": "FG3M",
        "threePointersAttempted": "FG3A",
        "freeThrowsMade": "FTM",
        "freeThrowsAttempted": "FTA",
        "reboundsOffensive": "OREB",
        "reboundsDefensive": "DREB",
        "reboundsTotal": "REB",
        "assists": "AST",
        "steals": "STL",
        "blocks": "BLK",
        "turnovers": "TOV",
        "foulsPersonal": "PF",
    }
    findings = {}
    for name, document in documents.items():
        if name.startswith("traditional_"):
            box = document["boxScoreTraditional"]
            game_id = name.removeprefix("traditional_")
            if box["gameId"] != game_id:
                raise ValueError("Representative traditional game identity mismatch")
            teams = []
            for side in ["homeTeam", "awayTeam"]:
                team = box[side]
                row = lookup.loc[(game_id, team["teamId"])]
                stats = team["statistics"]
                if stats["points"] != row.PTS:
                    raise ValueError("Representative traditional final score mismatch")
                teams.append(
                    dict(
                        team_id=team["teamId"],
                        points=stats["points"],
                        team_clock=stats["minutes"],
                        turnovers=stats["turnovers"],
                        summed_player_turnovers=sum(
                            p["statistics"]["turnovers"] for p in team["players"]
                        ),
                        summed_player_points=sum(
                            p["statistics"]["points"] for p in team["players"]
                        ),
                    )
                )
                differences = []
                for person in team["players"]:
                    key = (game_id, person["personId"])
                    if key not in player_lookup.index:
                        continue  # A listed source identity is not an appearance/missed-game fact.
                    for source_field, field in fields.items():
                        value = person["statistics"][source_field]
                        recorded = player_lookup.loc[key, field].item()
                        if value != recorded:
                            differences.append(
                                dict(
                                    player_id=person["personId"],
                                    field=field,
                                    player_game_logs=recorded,
                                    traditional=value,
                                )
                            )
                teams[-1]["player_row_differences"] = differences
            findings[name] = dict(scope="whole_game_sample_only", teams=teams)
        elif name.startswith("period_"):
            gid = name.removeprefix("period_")
            if set(document) != {"1", "2", "3", "4"}:
                raise ValueError("Unexpected representative period envelope")
            scores = []
            for value in document.values():
                box = value["boxScoreTraditional"]
                if box["gameId"] != gid:
                    raise ValueError("Representative period game identity mismatch")
                scores.extend(
                    box[side]["statistics"]["points"] for side in ["homeTeam", "awayTeam"]
                )
            findings[name] = dict(
                scope="unqualified_period_sample",
                quarter_team_points=scores,
                all_zero=not any(scores),
                canonical_period_accepted=False,
                reason=(
                    "Quarter-labeled bodies do not establish correct period parameters or activity"
                ),
            )
    return findings


def qualify_frames(schedule, documents):
    """Check original row keys/arithmetic; retain cross-source differences explicitly."""
    _, population = schedule_population(schedule)
    finals = {row["game_id"]: row for row in population if row["game_status"] == 3}
    if not finals:
        raise ValueError("No explicit final schedule population")
    raw_games = {
        game["gameId"]: game
        for day in schedule["leagueSchedule"]["gameDates"]
        for game in day["games"]
    }
    common = dict(LeagueID="00", Season=SEASON, SeasonType="Regular Season")
    _scoped(documents["finder"], {**common, "PlayerOrTeam": "T", "GameID": "0000000000"})
    _scoped(
        documents["gamelog"], {**common, "PlayerOrTeam": "T", "Sorter": "DATE", "Direction": "ASC"}
    )
    advanced_scope = {**common, "MeasureType": "Advanced", "PerMode": "PerGame"}
    for name in ["players_advanced", "teams_advanced"]:
        _scoped(documents[name], advanced_scope)
    _scoped(
        documents["standings"], dict(LeagueID="00", SeasonYear=SEASON, SeasonType="Regular Season")
    )
    _scoped(
        documents["player_game_logs"],
        dict(
            LeagueID="00",
            SeasonYear=SEASON,
            SeasonType="Regular Season",
            MeasureType="Base",
            PerMode="Totals",
        ),
    )
    finder = _table(documents["finder"], "LeagueGameFinderResults")
    gamelog = _table(documents["gamelog"], "LeagueGameLog")
    key = ["GAME_ID", "TEAM_ID"]
    expected = {
        (gid, row[side]) for gid, row in finals.items() for side in ["home_team_id", "away_team_id"]
    }
    for rows in [finder, gamelog]:
        if (
            rows.duplicated(key).any()
            or set(map(tuple, rows[key].to_numpy())) != expected
            or not rows.SEASON_ID.astype(str).eq("22026").all()
        ):
            raise ValueError("Team rows differ from exact final schedule season/population")
        for gid, group in rows.groupby("GAME_ID"):
            game = finals[gid]
            dates = pd.to_datetime(group.GAME_DATE, errors="raise").dt.strftime("%Y-%m-%d")
            if not dates.eq(game["game_date_est"]).all() or set(group.WL) != {"W", "L"}:
                raise ValueError("Team rows have wrong final date/outcome")
            scores = dict(zip(group.TEAM_ID, group.PTS))
            for row in group.itertuples():
                opponent = next(value for ident, value in scores.items() if ident != row.TEAM_ID)
                side = "homeTeam" if row.TEAM_ID == game["home_team_id"] else "awayTeam"
                if (
                    row.PTS != 2 * row.FGM + row.FG3M + row.FTM
                    or row.PTS != raw_games[gid][side]["score"]
                    or row.PLUS_MINUS != row.PTS - opponent
                    or (row.WL == "W") != (row.PTS > opponent)
                ):
                    raise ValueError("Team score/shooting/margin arithmetic is inconsistent")
    left, right = finder.set_index(key).sort_index(), gamelog.set_index(key).sort_index()
    differences = []
    for field in sorted(set(finder.columns) & set(gamelog.columns) - set(key)):
        bad = left.loc[~left[field].eq(right[field])]
        if not bad.empty and field not in {"MIN", "TOV"}:
            raise ValueError(f"Team-source contradiction outside disclosed MIN/TOV: {field}")
        for index in bad.index:
            differences.append(
                dict(
                    game_id=index[0],
                    team_id=int(index[1]),
                    field=field,
                    finder=left.loc[index, field].item(),
                    gamelog=right.loc[index, field].item(),
                )
            )
    players = _table(documents["player_game_logs"], "PlayerGameLogs")
    if (
        players.empty
        or players.duplicated(["GAME_ID", "PLAYER_ID"]).any()
        or not players.SEASON_YEAR.eq(SEASON).all()
        or set(map(tuple, players[key].drop_duplicates().to_numpy())) != expected
        or not pd.to_numeric(players.MIN, errors="raise").gt(0).all()
    ):
        raise ValueError("Player source is not exact positive player-game population")
    for row in players.itertuples():
        if (
            pd.Timestamp(row.GAME_DATE).strftime("%Y-%m-%d") != finals[row.GAME_ID]["game_date_est"]
            or row.PTS != 2 * row.FGM + row.FG3M + row.FTM
        ):
            raise ValueError("Player date/shooting arithmetic differs")
        if row.WL != left.loc[(row.GAME_ID, row.TEAM_ID), "WL"]:
            raise ValueError("Player outcome differs from its team game")
    fields = [
        "PTS",
        "FGM",
        "FGA",
        "FG3M",
        "FG3A",
        "FTM",
        "FTA",
        "OREB",
        "DREB",
        "REB",
        "AST",
        "STL",
        "BLK",
        "TOV",
        "PF",
    ]
    sums = players.groupby(key)[fields].sum().sort_index()
    core_conflicts = []
    for field in fields:
        for index in left.index[~left[field].eq(sums[field])]:
            core_conflicts.append(
                dict(
                    game_id=index[0],
                    team_id=int(index[1]),
                    field=field,
                    team=int(left.loc[index, field]),
                    player_sum=int(sums.loc[index, field]),
                )
            )
    totals = (
        finder.assign(W=finder.WL.eq("W").astype(int), L=finder.WL.eq("L").astype(int))
        .groupby("TEAM_ID")[["W", "L"]]
        .sum()
        .sort_index()
    )
    team_adv = (
        _table(documents["teams_advanced"], "LeagueDashTeamStats").set_index("TEAM_ID").sort_index()
    )
    standings = _table(documents["standings"], "Standings").set_index("TeamID").sort_index()
    player_adv = (
        _table(documents["players_advanced"], "LeagueDashPlayerStats")
        .set_index("PLAYER_ID")
        .sort_index()
    )
    if (
        team_adv.index.has_duplicates
        or standings.index.has_duplicates
        or set(team_adv.index) != set(totals.index)
        or set(standings.index) != set(totals.index)
        or not team_adv[["W", "L"]].eq(totals).all().all()
        or not standings[["WINS", "LOSSES"]].set_axis(["W", "L"], axis=1).eq(totals).all().all()
        or not team_adv.GP.eq(totals.W + totals.L).all()
        or not standings.SeasonID.astype(str).eq("22026").all()
        or not standings.LeagueID.eq("00").all()
    ):
        raise ValueError("Team advanced/standings identities or records differ from game rows")
    counts = players.groupby("PLAYER_ID").size().sort_index()
    player_records = (
        players.assign(W=players.WL.eq("W").astype(int), L=players.WL.eq("L").astype(int))
        .groupby("PLAYER_ID")[["W", "L"]]
        .sum()
        .sort_index()
    )
    if (
        player_adv.index.has_duplicates
        or set(player_adv.index) != set(counts.index)
        or not player_adv.GP.eq(counts).all()
        or not player_adv[["W", "L"]].eq(player_records).all().all()
        or not player_adv.GP.eq(player_adv.W + player_adv.L).all()
        or not player_adv.USG_PCT.between(0, 1).all()
        or not player_adv.TS_PCT.between(0, 2).all()
    ):
        raise ValueError("Player advanced population/counts/rates differ from player-game rows")
    if not (team_adv.OFF_RATING - team_adv.DEF_RATING - team_adv.NET_RATING).abs().lt(0.5).all():
        raise ValueError("Team advanced net rating is inconsistent")
    as_of = max(row["game_date_est"] for row in finals.values())
    snapshots = dict(
        player_season_advanced=player_advanced.normalize(
            player_adv.reset_index(), SEASON, "Regular Season", as_of
        ),
        team_season_advanced=pull_team_season_advanced.normalize(
            team_adv.reset_index(), SEASON, "Regular Season", as_of
        ),
        standings_snapshots=pull_standings_snapshots.normalize(
            standings.reset_index(), SEASON, "Regular Season", as_of
        ),
    )
    report = dict(
        classification="partial_source_qualification_not_canonical_or_published",
        season=SEASON,
        season_type="Regular Season",
        final_game_ids=sorted(finals),
        team_game_rows=len(finder),
        player_game_rows=len(players),
        player_ids=len(counts),
        team_ids=len(totals),
        final_points_total=int(finder.PTS.sum()),
        source_team_differences=differences,
        player_team_conflicts=core_conflicts,
        team_mode_gamelog_is_player_data=False,
        qualified_snapshot_rows={name: len(frame) for name, frame in snapshots.items()},
        observed_as_of_game_date=as_of,
        period_coverage="not_established",
        canonical_core_accepted=False,
        production_writes=0,
        representatives=representative_findings(documents, finder, players),
    )
    return report, snapshots


def qualify_stats_sources(evidence: Path, output: Path) -> dict:
    """Replay only retained authenticated bytes, preserving all data-quality gaps."""
    qualification = json.loads((evidence / "schedule-qualification.json").read_text())
    bundle = (evidence / qualification["retained_bundle"]).read_bytes()
    if (
        len(bundle) != qualification["bundle_bytes"]
        or _sha(bundle) != qualification["bundle_sha256"]
    ):
        raise ValueError("Retained schedule bundle differs")
    with zipfile.ZipFile(io.BytesIO(bundle)) as archive:
        raw_schedule = archive.read(qualification["original_member"])
    if (
        len(raw_schedule) != BYTES
        or _sha(raw_schedule) != qualification["original_sha256"]
        or hashlib.sha1(f"blob {len(raw_schedule)}\0".encode() + raw_schedule).hexdigest() != BLOB
    ):
        raise ValueError("Retained schedule original differs")
    documents, inputs, bundle_sha = retained_stats_documents(evidence)
    report, snapshots = qualify_frames(json.loads(raw_schedule), documents)
    report.update(
        archive_revision=REVISION,
        source_inputs=inputs,
        schedule_sha256=_sha(raw_schedule),
        stats_bundle_sha256=bundle_sha,
    )
    output.mkdir(parents=True, exist_ok=False)
    for name, frame in snapshots.items():
        frame.to_csv(output / f"{name}.csv", index=False)
    (output / "qualification.json").write_text(json.dumps(report, indent=2) + "\n")
    return report
