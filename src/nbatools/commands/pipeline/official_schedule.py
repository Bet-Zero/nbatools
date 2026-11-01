"""Normalize retained official schedule bodies without inventing played games.

Future rows stay in schedule only. Canonical completed games/stats remain a
separate population. The source's EST fields are Eastern wall times despite Z.
"""

from __future__ import annotations

import hashlib
import json
import re

import pandas as pd

SOURCE = "nba_schedule_league_v2"


def normalize_official_schedule(raw: bytes, season: str) -> pd.DataFrame:
    document = json.loads(raw)
    schedule = document["leagueSchedule"]
    if (
        not re.fullmatch(r"\d{4}-\d{2}", season)
        or int(season[-2:]) != (int(season[:4]) + 1) % 100
        or schedule["seasonYear"] != season
        or schedule["leagueId"] != "00"
    ):
        raise ValueError("Official schedule season/league mismatch")
    digest = hashlib.sha256(raw).hexdigest()
    prefix = "002" + season[2:4]
    rows = []
    seen = set()
    for day in schedule["gameDates"]:
        for game in day["games"]:
            gid = game["gameId"]
            if not isinstance(gid, str) or not re.fullmatch(r"\d{10}", gid):
                raise ValueError("Malformed official schedule game identity")
            if gid[3:5] != season[2:4]:
                raise ValueError("Mixed seasons in official schedule body")
            if not gid.startswith(prefix):
                continue  # Preseason/cup-final/playoff rows do not become regular games.
            if gid in seen:
                raise ValueError("Duplicate official schedule game identity")
            seen.add(gid)
            status = game["gameStatus"]
            if type(status) is not int or status not in (1, 2, 3):
                raise ValueError("Unknown official schedule status")
            if game.get("postponedStatus") != "N" or any(
                word in str(game.get("gameStatusText", "")).lower()
                for word in ("postpon", "cancel", "suspend")
            ):
                raise ValueError("Unqualified postponement/cancellation representation")
            instant = pd.Timestamp(game["gameDateTimeUTC"])
            eastern = pd.Timestamp(game["gameDateTimeEst"]).tz_localize(None)
            eastern = eastern.tz_localize("America/New_York")
            day_est = pd.Timestamp(game["gameDateEst"]).date()
            outer_day = pd.Timestamp(day["gameDate"]).date()
            if (
                pd.isna(instant)
                or instant.tzinfo is None
                or instant != eastern.tz_convert("UTC")
                or day_est != eastern.date()
                or outer_day != day_est
                or not (
                    pd.Timestamp(f"{season[:4]}-08-01").date()
                    <= day_est
                    < pd.Timestamp(f"{int(season[:4]) + 1}-08-01").date()
                )
            ):
                raise ValueError("Official schedule UTC/Eastern date contradiction")
            home, away = game["homeTeam"], game["awayTeam"]
            participants = [home["teamId"], away["teamId"]]
            if any(
                type(team) is not int or team not in {0, *range(1610612737, 1610612767)}
                for team in participants
            ):
                raise ValueError("Unknown official schedule team identity")
            known = all(participants)
            if (known and participants[0] == participants[1]) or (status != 1 and not known):
                raise ValueError("Unresolved or self matchup in played official schedule")
            if type(game["isNeutral"]) is not bool:
                raise ValueError("Unknown official schedule neutral-site flag")
            neutral = game["isNeutral"]
            if known:
                for side in (home, away):
                    if not re.fullmatch(r"[A-Z]{3}", side["teamTricode"]):
                        raise ValueError("Unknown official schedule team abbreviation")
                    if not side["teamName"] or not side["teamCity"]:
                        raise ValueError("Missing official schedule team name")
                expected_code = (
                    day_est.strftime("%Y%m%d/") + away["teamTricode"] + home["teamTricode"]
                )
                if game["gameCode"] != expected_code:
                    raise ValueError("Official schedule code/date/sides contradiction")
            elif game.get("gameCode"):
                raise ValueError("Unresolved future matchup has an invented game code")
            scores = [home["score"], away["score"]]
            if any(type(score) is not int or score < 0 for score in scores) or (
                status == 3 and (not all(scores) or scores[0] == scores[1])
            ):
                raise ValueError("Invalid official schedule score")
            row = dict(
                game_id=int(gid),
                season=season,
                season_type="Regular Season",
                game_date=str(day_est),
                game_datetime=instant.tz_convert("UTC").isoformat(),
                status={1: "Scheduled", 2: "In Progress", 3: "Final"}[status],
                site_type="neutral" if neutral else "standard" if known else "unknown",
                neutral_site=int(neutral),
                home_away_designation_trusted=int(known and not neutral),
                home_away_source=SOURCE,
                arena=game.get("arenaName", ""),
                city=game.get("arenaCity", ""),
                schedule_source=SOURCE,
                schedule_source_sha256=digest,
                source_game_status=status,
                source_home_team_id=home["teamId"],
                source_away_team_id=away["teamId"],
                source_is_neutral=int(neutral),
                source_postponed_status=game["postponedStatus"],
                source_game_status_text=game.get("gameStatusText", ""),
                home_score=scores[0],
                away_score=scores[1],
            )
            for label, side in (("home", home), ("away", away)):
                trusted_side = known and not neutral
                row[f"{label}_team_id"] = side["teamId"] if trusted_side else pd.NA
                row[f"{label}_team_abbr"] = side["teamTricode"] if trusted_side else pd.NA
                row[f"{label}_team_name"] = (
                    f"{side['teamCity']} {side['teamName']}" if trusted_side else pd.NA
                )
            for label, side in zip(
                ("team_a", "team_b"), sorted((home, away), key=lambda s: s["teamId"])
            ):
                row[f"{label}_id"] = side["teamId"] or pd.NA
                row[f"{label}_abbr"] = side.get("teamTricode") if side["teamId"] else pd.NA
                row[f"{label}_name"] = (
                    f"{side['teamCity']} {side['teamName']}" if side["teamId"] else pd.NA
                )
            broadcasters = game.get("broadcasters", {}).get("nationalBroadcasters", [])
            row["national_tv"] = "; ".join(
                sorted(
                    {
                        b["broadcasterDisplay"]
                        for b in broadcasters
                        if b.get("broadcasterMedia") == "tv" and b.get("broadcasterDisplay")
                    }
                )
            )
            rows.append(row)
    if not rows:
        raise ValueError("No regular-season official schedule games")
    return pd.DataFrame(rows).sort_values(["game_date", "game_id"]).reset_index(drop=True)


def official_final_rows(schedule: pd.DataFrame) -> pd.DataFrame | None:
    """Recognize the explicit source contract; legacy schedules keep exact IDs.

    This does not declare a source independent or fresh. The retained-source
    replay/qualification binds that claim before any protected publication.
    """
    if "schedule_source" not in schedule:
        return None
    required = {
        "game_id",
        "game_date",
        "game_datetime",
        "season",
        "season_type",
        "status",
        "schedule_source_sha256",
        "source_game_status",
        "source_postponed_status",
        "team_a_id",
        "team_b_id",
        "home_score",
        "away_score",
        "source_home_team_id",
        "source_away_team_id",
        "source_is_neutral",
    }
    if schedule.empty or not required.issubset(schedule):
        raise ValueError("Official schedule contract is incomplete")
    if (
        not schedule.schedule_source.eq(SOURCE).all()
        or schedule.schedule_source_sha256.nunique(dropna=False) != 1
        or not schedule.schedule_source_sha256.astype(str).str.fullmatch(r"[a-f0-9]{64}").all()
        or schedule.season.nunique(dropna=False) != 1
        or not schedule.season_type.eq("Regular Season").all()
        or not schedule.source_postponed_status.eq("N").all()
    ):
        raise ValueError("Official schedule provenance/scope is unqualified")
    codes = pd.to_numeric(schedule.source_game_status, errors="coerce")
    mapped = codes.map({1: "Scheduled", 2: "In Progress", 3: "Final"})
    if mapped.isna().any() or not mapped.eq(schedule.status).all():
        raise ValueError("Official schedule final/scheduled status contradiction")
    season = str(schedule.season.iloc[0])
    if not re.fullmatch(r"[0-9]{4}-[0-9]{2}", season) or (
        int(season[-2:]) != (int(season[:4]) + 1) % 100
    ):
        raise ValueError("Official schedule season is invalid")
    ids = pd.to_numeric(schedule.game_id, errors="coerce")
    if not (ids.notna() & ids.gt(0) & ids.lt(10**10) & ids.mod(1).eq(0)).all():
        raise ValueError("Official schedule game ID is invalid")
    keys = ids.astype("int64").astype(str).str.zfill(10)
    if keys.duplicated().any() or not keys.str.fullmatch("002" + season[2:4] + r"[0-9]{5}").all():
        raise ValueError("Official schedule duplicate or wrong-season game ID")
    days = pd.to_datetime(schedule.game_date, errors="coerce", utc=True)
    instants = pd.to_datetime(schedule.game_datetime, errors="coerce", utc=True)
    if (
        days.isna().any()
        or instants.isna().any()
        or not instants.dt.tz_convert("America/New_York").dt.date.eq(days.dt.date).all()
    ):
        raise ValueError("Official schedule UTC/Eastern dates are inconsistent")
    neutral = pd.to_numeric(schedule.source_is_neutral, errors="coerce")
    if not neutral.isin([0, 1]).all():
        raise ValueError("Official schedule neutral-site evidence is invalid")
    final = schedule.loc[codes.eq(3)].copy()
    for field in (
        "team_a_id",
        "team_b_id",
        "source_home_team_id",
        "source_away_team_id",
        "home_score",
        "away_score",
    ):
        values = pd.to_numeric(final[field], errors="coerce")
        if not (values.notna() & values.gt(0) & values.mod(1).eq(0)).all():
            raise ValueError("Official final schedule has unresolved participant/score")
    for _, row in final.iterrows():
        participants = {row.team_a_id, row.team_b_id}
        if (
            participants != {row.source_home_team_id, row.source_away_team_id}
            or len(participants) != 2
            or not participants.issubset(range(1610612737, 1610612767))
        ):
            raise ValueError("Official final side and participant identities disagree")
    if final.team_a_id.eq(final.team_b_id).any() or final.home_score.eq(final.away_score).any():
        raise ValueError("Official final schedule is self matchup or tied")
    return final


def validate_schedule_game_coverage(schedule: pd.DataFrame, games: pd.DataFrame) -> None:
    """Match exactly source-final games; never require future fabricated stats."""
    final = official_final_rows(schedule)
    if final is None:
        if set(schedule.game_id) != set(games.game_id):
            raise ValueError("Mismatch between schedule and games game_id sets")
        return
    required = {"game_id", "game_date", "is_final"}
    if not required.issubset(games) or games.game_id.duplicated().any():
        raise ValueError("Completed-game catalog is missing identity/final fields")
    if not pd.to_numeric(games.is_final, errors="coerce").eq(1).all():
        raise ValueError("Official completed-game catalog contains unplayed games")
    observed_ids = pd.to_numeric(games.game_id, errors="coerce")
    if not (observed_ids.notna() & observed_ids.gt(0) & observed_ids.mod(1).eq(0)).all():
        raise ValueError("Completed-game catalog has invalid game ID")
    if observed_ids.duplicated().any():
        raise ValueError("Completed-game catalog has duplicate normalized game IDs")
    expected_ids = pd.to_numeric(final.game_id, errors="raise").astype("int64")
    if set(observed_ids) != set(expected_ids):
        raise ValueError("Completed-game catalog differs from exact official final population")
    observed = games.assign(_game_key=observed_ids.astype("int64")).set_index("_game_key")
    expected = final.assign(_game_key=expected_ids).set_index("_game_key")
    for key, source in expected.iterrows():
        row = observed.loc[key]
        if pd.Timestamp(row.game_date).date() != pd.Timestamp(source.game_date).date():
            raise ValueError("Completed-game catalog date differs from official schedule")
        participant_columns = (
            ("team_a_id", "team_b_id")
            if {"team_a_id", "team_b_id"}.issubset(games)
            else ("home_team_id", "away_team_id")
        )
        if not set(participant_columns).issubset(games) or {
            row[participant_columns[0]],
            row[participant_columns[1]],
        } != {source.team_a_id, source.team_b_id}:
            raise ValueError("Completed-game participants differ from official schedule")
        if not {
            "home_team_id",
            "away_team_id",
            "neutral_site",
            "home_away_designation_trusted",
        }.issubset(games):
            raise ValueError("Completed-game venue identity is unqualified")
        if source.source_is_neutral == 1:
            if row.neutral_site != 1 or row.home_away_designation_trusted != 0:
                raise ValueError("Neutral official schedule conflicts with completed-game venue")
        elif (
            row.home_away_designation_trusted != 1
            or row.neutral_site != 0
            or row.home_team_id != source.source_home_team_id
            or row.away_team_id != source.source_away_team_id
        ):
            raise ValueError("Completed-game home/away identity differs from official schedule")


def validate_schedule_team_coverage(schedule: pd.DataFrame, team: pd.DataFrame) -> None:
    """Require both source-final sides/scores, without future team-stat rows."""
    final = official_final_rows(schedule)
    if final is None:
        return
    required = {"game_id", "team_id", "game_date", "pts"}
    if not required.issubset(team):
        raise ValueError("Official team coverage lacks game/team/date/score")
    ids = pd.to_numeric(team.game_id, errors="coerce")
    teams = pd.to_numeric(team.team_id, errors="coerce")
    if (
        ids.isna().any()
        or teams.isna().any()
        or not ids.mod(1).eq(0).all()
        or not teams.mod(1).eq(0).all()
    ):
        raise ValueError("Official team coverage has invalid identity")
    observed = team.assign(_game=ids, _team=teams).set_index(["_game", "_team"])
    if observed.index.duplicated().any():
        raise ValueError("Official team coverage has duplicate game/team")
    expected = {
        (int(row.game_id), int(row[f"source_{side}_team_id"]))
        for _, row in final.iterrows()
        for side in ("home", "away")
    }
    if set(observed.index) != expected:
        raise ValueError("Team games differ from exact official final side population")
    for _, row in final.iterrows():
        for side in ("home", "away"):
            result = observed.loc[(int(row.game_id), int(row[f"source_{side}_team_id"]))]
            if (
                pd.Timestamp(result.game_date).date() != pd.Timestamp(row.game_date).date()
                or result.pts != row[f"{side}_score"]
            ):
                raise ValueError("Team date/score differs from official final schedule")
