"""Offline, field-level corroboration; retained primary sources remain untouched."""

from __future__ import annotations

import hashlib
import io
import json
import math
import re
import zipfile
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

from nbatools.commands.pipeline.pull_play_by_play_events import parse_clock_seconds_remaining
from nbatools.commands.pipeline.pull_player_game_availability import _minutes
from nbatools.commands.pipeline.structured_participation import _table
from tools.collect_season_rollover import BLOB, BYTES, REVISION, SEASON
from tools.season_rollover_source_stats import qualify_frames, retained_stats_documents

FIELDS = dict(
    points="PTS",
    fieldGoalsMade="FGM",
    fieldGoalsAttempted="FGA",
    threePointersMade="FG3M",
    threePointersAttempted="FG3A",
    freeThrowsMade="FTM",
    freeThrowsAttempted="FTA",
    reboundsOffensive="OREB",
    reboundsDefensive="DREB",
    reboundsTotal="REB",
    assists="AST",
    steals="STL",
    blocks="BLK",
    turnovers="TOV",
    foulsPersonal="PF",
)


@dataclass(frozen=True)
class Source:
    path: str
    raw: bytes

    @property
    def document(self):
        return json.loads(self.raw)

    @property
    def sha256(self):
        return hashlib.sha256(self.raw).hexdigest()


def _integer(value):
    number = float(value)
    if not math.isfinite(number) or not number.is_integer() or number < 0:
        raise ValueError("Source count must be a nonnegative integer")
    return int(number)


def _literal_minutes(value):
    """Reject malformed source components before any denominator arithmetic."""
    if isinstance(value, str):
        text = value.strip()
        if ":" in text and re.fullmatch(r"\d+:[0-5]\d(?:\.\d+)?", text) is None:
            raise ValueError("Invalid Traditional box-score duration")
        if text.upper().startswith("PT"):
            match = re.fullmatch(r"PT(?:(\d+)M)?(?:(\d+(?:\.\d+)?)S)?", text.upper())
            if match is None or not any(match.groups()) or float(match[2] or 0) >= 60:
                raise ValueError("Invalid Traditional box-score duration")
    parsed = _minutes(value)
    return 0.0 if parsed is None else parsed


def _games(schedule, finder):
    games = {
        g["gameId"]: g
        for day in schedule["leagueSchedule"]["gameDates"]
        for g in day["games"]
        if g["gameStatus"] == 3 and str(g["gameId"]).startswith("002")
    }
    if finder.duplicated(["GAME_ID", "TEAM_ID"]).any():
        raise ValueError("Duplicate authoritative team key")
    for gid, game in games.items():
        rows = finder.loc[finder.GAME_ID.eq(gid)]
        if set(rows.TEAM_ID) != {game[s]["teamId"] for s in ["homeTeam", "awayTeam"]}:
            raise ValueError("Final game lacks paired source team rows")
        for side in ["homeTeam", "awayTeam"]:
            row = rows.loc[rows.TEAM_ID.eq(game[side]["teamId"])].iloc[0]
            if (
                row.PTS != game[side]["score"]
                or str(row.GAME_DATE)[:10] != game["gameDateEst"][:10]
            ):
                raise ValueError("Schedule/Finder score or date contradiction")
    return games


def _summary(source, game):
    box = source.document["boxScoreSummary"]
    if (
        box["gameId"] != game["gameId"]
        or box["gameStatus"] != 3
        or box["gameEt"][:10] != game["gameDateEst"][:10]
        or box["gameTimeUTC"] != game["gameDateTimeUTC"]
    ):
        raise ValueError("Summary final identity/date contradiction")
    for side in ["homeTeam", "awayTeam"]:
        if any(box[side][key] != game[side][key] for key in ["teamId", "score"]):
            raise ValueError("Summary final side/score contradiction")
    return box


def _pbp_facts(source, summary_source, game):
    """Replay all events; extract explicit FT actors without canonical PBP acceptance."""
    summary = _summary(summary_source, game)
    document = source.document["game"]
    if document["gameId"] != game["gameId"]:
        raise ValueError("PBP game identity contradiction")
    identities = {
        p["personId"]: summary[s]["teamId"]
        for s in ["homeTeam", "awayTeam"]
        for p in summary[s]["players"]
    }
    if len(identities) != sum(len(summary[s]["players"]) for s in ["homeTeam", "awayTeam"]):
        raise ValueError("Summary has duplicate same-game player identity")
    side_by_team = {game[s]["teamId"]: i for i, s in enumerate(["homeTeam", "awayTeam"])}
    totals = defaultdict(Counter)
    events = defaultdict(lambda: defaultdict(list))
    ft_actors = set()
    previous, last_period, last_clock = (0, 0), 1, 720
    starts, ends = set(), set()
    actions = document["actions"]
    for index, row in enumerate(actions, 1):
        period, clock = row["period"], parse_clock_seconds_remaining(row["clock"])
        if (
            row["actionId"] != index
            or period < last_period
            or period > last_period + 1
            or period == last_period
            and clock > last_clock
        ):
            raise ValueError("PBP source timeline is incomplete or unordered")
        if row["actionType"] == "period":
            if row["subType"] == "start" and clock == (720 if period <= 4 else 300):
                starts.add(period)
            elif row["subType"] == "end" and clock == 0:
                ends.add(period)
        last_period, last_clock = period, clock
        kind = row["actionType"]
        made = (
            kind == "Made Shot"
            or kind == "Free Throw"
            and not row["description"].startswith("MISS ")
        )
        value = 0
        if kind in {"Made Shot", "Missed Shot", "Free Throw"}:
            pid, tid = row["personId"], row["teamId"]
            if identities.get(pid) != tid or tid not in side_by_team:
                raise ValueError("PBP actor lacks exact same-game NBA identity")
            if kind == "Free Throw":
                if "Free Throw" not in row["description"]:
                    raise ValueError("Unqualified free-throw description")
                totals[pid]["FTA"] += 1
                ft_actors.add(pid)
                events[pid]["FTA"].append(row["actionId"])
                if made:
                    value = 1
                    totals[pid]["FTM"] += 1
                    events[pid]["FTM"].append(row["actionId"])
            elif made:
                if row["shotResult"] != "Made" or row["shotValue"] not in (2, 3):
                    raise ValueError("Unqualified made field goal")
                value = row["shotValue"]
            totals[pid]["PTS"] += value
            if value:
                events[pid]["PTS"].append(row["actionId"])
        a, b = row["scoreHome"], row["scoreAway"]
        if bool(a) != bool(b) or not a and made:
            raise ValueError("Scoring action lacks paired explicit scores")
        current = (_integer(a), _integer(b)) if a else previous
        expected = [0, 0]
        if made:
            expected[side_by_team[row["teamId"]]] = value
        if tuple(y - x for x, y in zip(previous, current, strict=True)) != tuple(expected):
            raise ValueError("PBP score delta lacks explicit same-event actor/value")
        previous = current
    if (
        last_period < 4
        or last_period != summary["period"]
        or last_clock != 0
        or starts != ends
        or ends != set(range(1, last_period + 1))
        or previous != tuple(game[s]["score"] for s in ["homeTeam", "awayTeam"])
    ):
        raise ValueError("PBP terminal score/clock/period coverage is incomplete")
    return [
        (
            pid,
            identities[pid],
            field,
            totals[pid][field],
            dict(
                action_ids=events[pid][field],
                source_field=f"complete_event_replay.{field}",
                summary_sha256=summary_source.sha256,
                statistical_basis="explicit_FT_actor_and_ordered_full_score_replay",
            ),
        )
        for pid in sorted(ft_actors)
        for field in ["PTS", "FTM", "FTA"]
    ]


def _traditional_teams(source, games):
    box = source.document["boxScoreTraditional"]
    gid = box["gameId"]
    if gid not in games:
        raise ValueError("Traditional source is outside exact final population")
    for side in ["homeTeam", "awayTeam"]:
        team = box[side]
        if any(team[key] != games[gid][side][key] for key in ["teamId"]):
            raise ValueError("Traditional source side identity differs")
        if team["statistics"]["points"] != games[gid][side]["score"]:
            raise ValueError("Traditional source final score differs")
        if len({p["personId"] for p in team["players"]}) != len(team["players"]):
            raise ValueError("Traditional source has duplicate player identities")
        if (
            sum(_integer(p["statistics"]["points"]) for p in team["players"])
            != team["statistics"]["points"]
        ):
            raise ValueError("Traditional player points do not reconcile to explicit final score")
        team_minutes = _literal_minutes(team["statistics"]["minutes"])
        player_minutes = [_literal_minutes(p["statistics"]["minutes"]) for p in team["players"]]
        if (
            not math.isfinite(team_minutes)
            or team_minutes < 240
            or not math.isclose(sum(player_minutes), team_minutes, abs_tol=2 / 60)
        ):
            raise ValueError("Traditional team/player clock denominators contradict")
        if any(minutes > team_minutes / 5 for minutes in player_minutes):
            raise ValueError("Traditional player clock exceeds full game duration")
        yield gid, team, team_minutes, player_minutes


def bridge_players(primary, schedule, finder, traditional=(), pbp=()):
    """Return staged rows and all corroborated cells; never infer from team sums."""
    games = _games(schedule, finder)
    result = primary.copy(deep=True)
    if primary.duplicated(["GAME_ID", "PLAYER_ID"]).any():
        raise ValueError("Duplicate primary player key")
    lookup = primary.set_index(["GAME_ID", "PLAYER_ID"])
    observations, ledger = {}, []

    def observe(source, gid, pid, tid, field, value, details):
        if (gid, pid) not in lookup.index:
            raise ValueError("Corroborator has no positive primary player row")
        before = lookup.loc[(gid, pid)]
        date = games[gid]["gameDateEst"][:10]
        if before.TEAM_ID != tid or str(before.GAME_DATE)[:10] != date or before.MIN <= 0:
            raise ValueError("Primary player identity/date/participation contradiction")
        value = float(value) if field == "MIN" else _integer(value)
        if field == "MIN" and (not math.isfinite(value) or value <= 0):
            raise ValueError("Invalid explicit positive player clock")
        if field == "MIN" and math.isclose(value, before.MIN, abs_tol=1 / 60):
            # Whole-second box clocks corroborate, but cannot replace the
            # primary log's finer time precision within one source second.
            details = dict(
                details,
                observed_source_minutes=value,
                clock_precision_policy="retain_primary_within_one_second",
            )
            value = float(before.MIN)
        key = (gid, pid, field)
        if key in observations and observations[key] != value:
            raise ValueError("Independent corroborators disagree on the same player field")
        observations[key] = value
        ledger.append(
            dict(
                game_id=gid,
                game_date=date,
                team_id=int(tid),
                player_id=int(pid),
                field=field,
                before=float(before[field]) if field == "MIN" else _integer(before[field]),
                after=value,
                source_file=source.path,
                source_sha256=source.sha256,
                **details,
            )
        )

    for source in traditional:
        for gid, team, team_minutes, player_minutes in _traditional_teams(source, games):
            for person, minutes in zip(team["players"], player_minutes, strict=True):
                if minutes == 0:
                    continue
                observe(
                    source,
                    gid,
                    person["personId"],
                    team["teamId"],
                    "MIN",
                    minutes,
                    dict(
                        source_field="minutes",
                        statistical_basis="explicit_Traditional_player_clock_in_minutes",
                    ),
                )
                stats = person["statistics"]
                if _integer(stats["points"]) != 2 * _integer(stats["fieldGoalsMade"]) + _integer(
                    stats["threePointersMade"]
                ) + _integer(stats["freeThrowsMade"]) or any(
                    _integer(stats[made]) > _integer(stats[attempted])
                    for made, attempted in [
                        ("fieldGoalsMade", "fieldGoalsAttempted"),
                        ("threePointersMade", "threePointersAttempted"),
                        ("freeThrowsMade", "freeThrowsAttempted"),
                    ]
                ):
                    raise ValueError("Traditional player shooting arithmetic contradicts")
                for source_field, field in FIELDS.items():
                    observe(
                        source,
                        gid,
                        person["personId"],
                        team["teamId"],
                        field,
                        person["statistics"][source_field],
                        dict(
                            source_field=source_field,
                            statistical_basis="explicit_whole_game_Traditional_player_statistic",
                        ),
                    )
    for source, summary in pbp:
        gid = source.document["game"]["gameId"]
        if gid not in games:
            raise ValueError("PBP source is outside exact final population")
        for pid, tid, field, value, details in _pbp_facts(source, summary, games[gid]):
            observe(source, gid, pid, tid, field, value, details)
    for (gid, pid, field), value in observations.items():
        if field == "MIN" and not float(value).is_integer():
            result["MIN"] = result.MIN.astype(float)
        result.loc[result.GAME_ID.eq(gid) & result.PLAYER_ID.eq(pid), field] = value
    if not result.PTS.eq(2 * result.FGM + result.FG3M + result.FTM).all() or any(
        (result[prefix + "M"] > result[prefix + "A"]).any() for prefix in ["FG", "FG3", "FT"]
    ):
        raise ValueError("Partial corroboration leaves contradictory player shooting counts")
    # Percentages follow their explicitly corroborated integer numerator/denominator.
    for prefix in ["FG", "FG3", "FT"]:
        column = prefix + "_PCT"
        if column in result:
            affected = {
                (gid, pid)
                for gid, pid, field in observations
                if field in {prefix + "M", prefix + "A"}
                and observations[(gid, pid, field)] != lookup.loc[(gid, pid), field]
            }
            for gid, pid in affected:
                mask = result.GAME_ID.eq(gid) & result.PLAYER_ID.eq(pid)
                row = result.loc[mask].iloc[0]
                value = round(row[prefix + "M"] / row[prefix + "A"], 3) if row[prefix + "A"] else 0
                if not float(value).is_integer():
                    result[column] = result[column].astype(float)
                result.loc[mask, column] = value
                evidence = [
                    dict(
                        source_file=x["source_file"],
                        source_sha256=x["source_sha256"],
                        source_field=x["source_field"],
                        field=x["field"],
                    )
                    for x in ledger
                    if x["game_id"] == gid
                    and x["player_id"] == pid
                    and x["field"] in {prefix + "M", prefix + "A"}
                ]
                ledger.append(
                    dict(
                        game_id=gid,
                        player_id=int(pid),
                        team_id=int(row.TEAM_ID),
                        game_date=str(row.GAME_DATE)[:10],
                        field=column,
                        before=float(lookup.loc[(gid, pid), column]),
                        after=float(value),
                        source_field=f"{prefix}M/{prefix}A",
                        source_file=evidence[0]["source_file"],
                        source_sha256=evidence[0]["source_sha256"],
                        evidence_inputs=evidence,
                        statistical_basis="ratio_of_corroborated_whole_game_counts",
                    )
                )
    return result, ledger


def bridge_teams(primary, schedule, traditional=()):
    """Reconcile team fields from explicit team observations, preserving their grain."""
    required = {"GAME_ID", "GAME_DATE", "TEAM_ID", *FIELDS.values()}
    if not required.issubset(primary.columns):
        raise ValueError("Primary team counts or identity columns are missing")
    games = _games(schedule, primary)
    lookup = primary.set_index(["GAME_ID", "TEAM_ID"])
    observations, ledger = {}, []
    for source in traditional:
        for gid, team, _, _ in _traditional_teams(source, games):
            tid, stats = team["teamId"], team["statistics"]
            if not set(FIELDS).issubset(stats):
                raise ValueError("Traditional explicit team count fields are missing")
            counts = {field: _integer(stats[key]) for key, field in FIELDS.items()}
            if (
                counts["PTS"] != 2 * counts["FGM"] + counts["FG3M"] + counts["FTM"]
                or counts["REB"] != counts["OREB"] + counts["DREB"]
                or any(counts[p + "M"] > counts[p + "A"] for p in ["FG", "FG3", "FT"])
                or counts["FG3M"] > counts["FGM"]
                or counts["FG3A"] > counts["FGA"]
            ):
                raise ValueError("Traditional explicit team count arithmetic contradicts")
            for source_field, field in FIELDS.items():
                key = gid, tid, field
                value = counts[field]
                if key in observations and observations[key] != value:
                    raise ValueError("Independent corroborators disagree on the same team field")
                observations[key] = value
                ledger.append(
                    dict(
                        game_id=gid,
                        game_date=games[gid]["gameDateEst"][:10],
                        team_id=int(tid),
                        field=field,
                        before=_integer(lookup.loc[(gid, tid), field]),
                        after=value,
                        source_file=source.path,
                        source_sha256=source.sha256,
                        source_field=source_field,
                        statistical_basis="explicit_whole_game_Traditional_team_statistic",
                    )
                )
    result = primary.copy(deep=True)
    for (gid, tid, field), value in observations.items():
        result.loc[result.GAME_ID.eq(gid) & result.TEAM_ID.eq(tid), field] = value
    for prefix in ["FG", "FG3", "FT"]:
        column = prefix + "_PCT"
        if column not in result:
            continue
        affected = {
            (gid, tid)
            for gid, tid, field in observations
            if field in {prefix + "M", prefix + "A"}
            and observations[(gid, tid, field)] != lookup.loc[(gid, tid), field]
        }
        for gid, tid in affected:
            mask = result.GAME_ID.eq(gid) & result.TEAM_ID.eq(tid)
            row = result.loc[mask].iloc[0]
            value = round(row[prefix + "M"] / row[prefix + "A"], 3) if row[prefix + "A"] else 0
            if not float(value).is_integer():
                result[column] = result[column].astype(float)
            result.loc[mask, column] = value
            inputs = [
                dict(
                    source_file=x["source_file"],
                    source_sha256=x["source_sha256"],
                    source_field=x["source_field"],
                    field=x["field"],
                )
                for x in ledger
                if x["game_id"] == gid
                and x["team_id"] == tid
                and x["field"] in {prefix + "M", prefix + "A"}
            ]
            ledger.append(
                dict(
                    game_id=gid,
                    game_date=str(row.GAME_DATE)[:10],
                    team_id=int(tid),
                    field=column,
                    before=float(lookup.loc[(gid, tid), column]),
                    after=float(value),
                    source_file=inputs[0]["source_file"],
                    source_sha256=inputs[0]["source_sha256"],
                    source_field=f"{prefix}M/{prefix}A",
                    evidence_inputs=inputs,
                    statistical_basis="ratio_of_corroborated_whole_game_team_counts",
                )
            )
    return result, ledger


def _additional_sources(evidence):
    extra = evidence / "game-0022600144"
    capture = json.loads((extra / "capture.json").read_text())
    if capture["archive_revision"] != REVISION or len(capture["files"]) != 2:
        raise ValueError("Additional original revision differs")
    sources = {}
    for item in capture["files"]:
        allowed = {"pbp.json": "playbyplayv3", "summary.json": "boxscoresummaryv3"}
        if (
            item["file"] not in allowed
            or item["file"] in sources
            or item["path"] != f"nba_stats/json/{allowed[item['file']]}/2027/0022600144.json"
        ):
            raise ValueError("Additional original path is outside approved same-game scope")
        path = item["path"]
        expected = f"https://raw.githubusercontent.com/sportsdataverse/hoopR-nba-stats-raw/{REVISION}/{path}"
        file = extra / item["file"]
        if file.is_symlink() or file.stat().st_size > 2_000_000:
            raise ValueError("Unsafe additional source original")
        raw = file.read_bytes()
        if (
            item["download_url"] != expected
            or len(raw) != item["size"]
            or hashlib.sha256(raw).hexdigest() != item["sha256"]
            or hashlib.sha1(f"blob {len(raw)}\0".encode() + raw).hexdigest() != item["sha"]
        ):
            raise ValueError("Additional original hash/size/pinned URL differs")
        sources[item["file"]] = Source(str(Path(extra.name) / item["file"]), raw)
    if set(sources) != {"pbp.json", "summary.json"}:
        raise ValueError("Unexpected additional original scope")
    return sources


def stage_retained_core(
    evidence: Path, output: Path, *, additional_traditional=(), reconcile_team_counts=False
):
    """Export partial staged rows; callers bind any additional retained originals.

    Team reconciliation remains explicit, and never supplies completeness flags.
    """
    documents, inputs, bundle_sha = retained_stats_documents(evidence)
    proof = json.loads((evidence / "schedule-qualification.json").read_text())
    bundle = (evidence / proof["retained_bundle"]).read_bytes()
    if (
        len(bundle) != proof["bundle_bytes"]
        or hashlib.sha256(bundle).hexdigest() != proof["bundle_sha256"]
    ):
        raise ValueError("Retained schedule bundle differs")
    with zipfile.ZipFile(io.BytesIO(bundle)) as archive:
        raw_schedule = archive.read(proof["original_member"])
    if (
        len(raw_schedule) != BYTES
        or hashlib.sha256(raw_schedule).hexdigest() != proof["original_sha256"]
        or hashlib.sha1(f"blob {len(raw_schedule)}\0".encode() + raw_schedule).hexdigest() != BLOB
    ):
        raise ValueError("Retained schedule original differs")
    schedule = json.loads(raw_schedule)
    source_report, _ = qualify_frames(schedule, documents)
    primary = _table(documents["player_game_logs"], "PlayerGameLogs")
    with zipfile.ZipFile(evidence / "stats-sources.zip") as archive:
        traditional = [
            Source(item["file"], archive.read(item["file"]))
            for name, item in inputs.items()
            if name.startswith("traditional_")
        ]
    traditional.extend(additional_traditional)
    sources = _additional_sources(evidence)
    finder = _table(documents["finder"], "LeagueGameFinderResults")
    staged, ledger = bridge_players(
        primary,
        schedule,
        finder,
        traditional,
        [(sources["pbp.json"], sources["summary.json"])],
    )
    report = dict(
        classification="field_corroborated_player_staging_not_full_dataset_acceptance",
        season=SEASON,
        season_type="Regular Season",
        production_writes=0,
        canonical_core_accepted=False,
        canonical_pbp_ingestion_accepted=False,
        primary_player_rows=len(primary),
        staged_player_rows=len(staged),
        primary_sha256=inputs["player_game_logs"]["sha256"],
        stats_bundle_sha256=bundle_sha,
        schedule_sha256=hashlib.sha256(raw_schedule).hexdigest(),
        corroborated_observations=len(ledger),
        changed_cells=[x for x in ledger if x["before"] != x["after"]],
        remaining_requirements=[
            "starter_roles_population",
            "all_game_player_row_quality",
            "qualified_full_periods",
            "other_required_dataset_qualification",
        ],
        uncorroborated_primary_values="retained; not independently fully verified",
        original_source_conflicts=source_report["player_team_conflicts"],
    )
    staged_teams, team_ledger = (
        bridge_teams(finder, schedule, traditional) if reconcile_team_counts else (None, [])
    )
    if reconcile_team_counts:
        report["team_reconciliation"] = dict(
            primary_team_rows=len(finder),
            staged_team_rows=len(staged_teams),
            corroborated_observations=len(team_ledger),
            changed_cells=[x for x in team_ledger if x["before"] != x["after"]],
            basis="explicit_Traditional_team_fields_not_player_sum_inference",
        )
    output.mkdir(parents=True, exist_ok=False)
    if reconcile_team_counts:
        finder.to_csv(output / "primary-team-game-logs.csv", index=False)
        staged_teams.to_csv(output / "staged-team-game-logs.csv", index=False)
        (output / "team-corroboration-ledger.json").write_text(
            json.dumps(team_ledger, indent=2) + "\n"
        )
    primary.to_csv(output / "primary-player-game-logs.csv", index=False)
    staged.to_csv(output / "staged-player-game-logs.csv", index=False)
    (output / "corroboration-ledger.json").write_text(json.dumps(ledger, indent=2) + "\n")
    (output / "qualification.json").write_text(json.dumps(report, indent=2) + "\n")
    return report
