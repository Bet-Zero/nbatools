"""Explicit individual observations repair staged answers, without team-sum guesses."""

import copy
import hashlib
import json

import pandas as pd
import pytest

from tools.season_rollover_core_bridge import FIELDS, Source, bridge_players

GID = "0022600001"


def source(path, document):
    return Source(path, json.dumps(document).encode())


def fixture():
    game = dict(
        gameId=GID,
        gameStatus=3,
        period=4,
        gameDateEst="2026-10-20T00:00:00Z",
        gameDateTimeUTC="2026-10-20T23:00:00Z",
        homeTeam=dict(teamId=1, score=11),
        awayTeam=dict(teamId=2, score=8),
    )
    schedule = dict(leagueSchedule=dict(gameDates=[dict(games=[game])]))
    primary, finder = [], []
    traditional = dict(gameId=GID)
    summary = dict(
        gameId=GID,
        gameStatus=3,
        period=4,
        gameEt="2026-10-20T19:00:00Z",
        gameTimeUTC=game["gameDateTimeUTC"],
    )
    for tid, side in [(1, "homeTeam"), (2, "awayTeam")]:
        players = []
        for index in range(6):
            pid = tid * 10 + index + 1
            points = ([3, 2, 2, 2, 2, 0] if tid == 1 else [2, 2, 2, 2, 0, 0])[index]
            stats = dict.fromkeys(FIELDS, 0)
            stats.update(
                points=points,
                fieldGoalsMade=points // 2,
                fieldGoalsAttempted=points // 2,
                freeThrowsMade=points % 2,
                freeThrowsAttempted=points % 2,
                minutes=f"{42 if tid == 1 and index == 0 else 38 if tid == 1 and index == 1 else 40}:00",
            )
            players.append(dict(personId=pid, statistics=stats))
            row = {field: stats[key] for key, field in FIELDS.items()}
            row.update(
                GAME_ID=GID,
                GAME_DATE="2026-10-20",
                TEAM_ID=tid,
                PLAYER_ID=pid,
                PLAYER_NAME=f"Fixture {pid}",
                MIN=40.0,
                FG_PCT=1 if points // 2 else 0,
                FT_PCT=points % 2,
                FG3_PCT=0,
            )
            if pid == 11:
                row.update(PTS=2, FTM=0, FTA=0, FT_PCT=0)
            primary.append(row)
        traditional[side] = dict(
            teamId=tid,
            statistics=dict(points=game[side]["score"], minutes="240:00"),
            players=players,
        )
        summary[side] = dict(**game[side], players=[dict(personId=p["personId"]) for p in players])
        finder.append(
            dict(GAME_ID=GID, GAME_DATE="2026-10-20", TEAM_ID=tid, PTS=game[side]["score"])
        )
    actions = []
    score = [0, 0]

    def event(period, clock, kind, subtype="", pid=0, tid=0, value=0):
        if value:
            score[tid - 1] += value
        actions.append(
            dict(
                actionId=len(actions) + 1,
                actionNumber=len(actions) + 1,
                period=period,
                clock=clock,
                actionType=kind,
                subType=subtype,
                personId=pid,
                teamId=tid,
                description="Fixture Free Throw Technical (3 PTS)"
                if kind == "Free Throw"
                else "fixture",
                scoreHome=str(score[0]),
                scoreAway=str(score[1]),
                shotValue=value,
                shotResult="Made" if kind == "Made Shot" else "",
            )
        )

    for period in range(1, 5):
        event(period, "PT12M00S", "period", "start")
        if period == 1:
            for pid in [11, 12, 13, 14, 15, 21, 22, 23, 24]:
                event(period, "PT11M00S", "Made Shot", pid=pid, tid=pid // 10, value=2)
            event(period, "PT10M00S", "Free Throw", pid=11, tid=1, value=1)
        event(period, "PT00M00S", "period", "end")
    return (
        pd.DataFrame(primary),
        schedule,
        pd.DataFrame(finder),
        traditional,
        dict(game=dict(gameId=GID, actions=actions)),
        dict(boxScoreSummary=summary),
    )


def run(data, traditional=True, pbp=True):
    primary, schedule, finder, box, events, summary = data
    return bridge_players(
        primary,
        schedule,
        finder,
        [source("traditional.json", dict(boxScoreTraditional=box))] if traditional else [],
        [(source("pbp.json", events), source("summary.json", summary))] if pbp else [],
    )


def test_staged_player_date_minute_question_uses_observations_and_preserves_primary():
    from nbatools.commands.player_game_finder import _apply_filters

    data = fixture()
    original = data[0].copy(deep=True)
    staged, ledger = run(data)
    pd.testing.assert_frame_equal(data[0], original)
    assert len(staged) == len(original) == 12
    assert staged.set_index("PLAYER_ID").loc[11, ["PTS", "FTM", "FTA", "MIN"]].tolist() == [
        3,
        1,
        1,
        42,
    ]

    def answer(rows):
        rows = rows.rename(
            columns={
                "GAME_ID": "game_id",
                "GAME_DATE": "game_date",
                "PLAYER_ID": "player_id",
                "PLAYER_NAME": "player_name",
                "PTS": "pts",
                "MIN": "minutes",
            }
        )
        return _apply_filters(
            rows,
            player="Fixture 11",
            stat="pts",
            min_value=3,
            conditions=[dict(stat="minutes", op=">=", value=41)],
            start_date="2026-10-20",
            end_date="2026-10-20",
        )

    assert answer(original).empty and answer(staged).game_id.tolist() == [GID]
    facts = [r for r in ledger if r["field"] == "FTM" and r["player_id"] == 11]
    assert len(facts) == 2 and all(r["before"] == 0 and r["after"] == 1 for r in facts)
    assert (
        facts[0]["source_sha256"]
        == source("traditional.json", dict(boxScoreTraditional=data[3])).sha256
    )
    assert facts[1]["action_ids"] == [11] and facts[1]["summary_sha256"]


@pytest.mark.parametrize(
    "damage",
    ["game", "date", "side", "duplicate", "clock", "arithmetic", "unknown_player", "contradiction"],
)
def test_traditional_unknown_or_conflicting_observations_fail(damage):
    data = fixture()
    primary, _, _, box, _, _ = data
    person = box["homeTeam"]["players"][0]
    if damage == "game":
        box["gameId"] = "0022600002"
    elif damage == "date":
        primary.loc[0, "GAME_DATE"] = "2026-10-19"
    elif damage == "side":
        box["homeTeam"]["teamId"] = 2
    elif damage == "duplicate":
        box["homeTeam"]["players"].append(copy.deepcopy(person))
    elif damage == "clock":
        person["statistics"]["minutes"] = "1:00"
    elif damage == "arithmetic":
        person["statistics"]["fieldGoalsMade"] = 0
    elif damage == "unknown_player":
        person["personId"] = 99
    elif damage == "contradiction":
        person["statistics"].update(points=1, fieldGoalsMade=0, fieldGoalsAttempted=0)
        box["homeTeam"]["players"][1]["statistics"].update(
            points=4, fieldGoalsMade=2, fieldGoalsAttempted=2
        )
    with pytest.raises(ValueError):
        run(data)


@pytest.mark.parametrize(
    "damage", ["sequence", "clock", "score", "actor", "summary_date", "terminal", "scoreless_made"]
)
def test_selected_ft_facts_require_full_original_ordered_score_replay(damage):
    data = fixture()
    events = data[4]["game"]["actions"]
    if damage == "sequence":
        events[3]["actionId"] += 1
    elif damage == "clock":
        events[2]["clock"] = "PT12M00S"
    elif damage == "score":
        events[10]["scoreHome"] = "12"
    elif damage == "actor":
        events[10]["personId"] = 99
    elif damage == "summary_date":
        data[5]["boxScoreSummary"]["gameEt"] = "2026-10-19T19:00:00Z"
    elif damage == "terminal":
        events.pop()
    elif damage == "scoreless_made":
        events[10].update(scoreHome="", scoreAway="")
    with pytest.raises(ValueError):
        run(data, traditional=False)


def test_team_difference_and_missing_sources_never_fabricate_individual_correction():
    data = fixture()
    unchanged, ledger = run(data, traditional=False, pbp=False)
    pd.testing.assert_frame_equal(unchanged, data[0])
    assert ledger == []
    primary, _, _, _, _, _ = data
    primary.loc[0, "GAME_DATE"] = "2026-10-19"
    with pytest.raises(ValueError):
        run(data, traditional=False)


@pytest.mark.parametrize(
    "damage", [None, "sha256", "size", "blob", "url", "revision", "path", "duplicate", "symlink"]
)
def test_additional_original_bindings_are_checked_before_semantic_use(tmp_path, damage):
    from tools.season_rollover_core_bridge import REVISION, _additional_sources

    directory = tmp_path / "game-0022600144"
    directory.mkdir()
    rows = []
    for name, endpoint in [("pbp.json", "playbyplayv3"), ("summary.json", "boxscoresummaryv3")]:
        raw = json.dumps(dict(fixture=name)).encode()
        (directory / name).write_bytes(raw)
        path = f"nba_stats/json/{endpoint}/2027/0022600144.json"
        rows.append(
            dict(
                file=name,
                path=path,
                size=len(raw),
                sha256=hashlib.sha256(raw).hexdigest(),
                sha=hashlib.sha1(f"blob {len(raw)}\0".encode() + raw).hexdigest(),
                download_url=f"https://raw.githubusercontent.com/sportsdataverse/hoopR-nba-stats-raw/{REVISION}/{path}",
            )
        )
    capture = dict(archive_revision=REVISION, files=rows)
    if damage == "sha256":
        rows[0]["sha256"] = "0" * 64
    elif damage == "size":
        rows[0]["size"] += 1
    elif damage == "blob":
        rows[0]["sha"] = "0" * 40
    elif damage == "url":
        rows[0]["download_url"] = rows[0]["download_url"].replace(REVISION, "main")
    elif damage == "revision":
        capture["archive_revision"] = "0" * 40
    elif damage == "path":
        rows[0]["path"] = "nba_stats/json/playbyplayv3/2027/0022600001.json"
    elif damage == "duplicate":
        rows[1] = copy.deepcopy(rows[0])
    elif damage == "symlink":
        (directory / "pbp.json").unlink()
        (directory / "pbp.json").symlink_to(directory / "summary.json")
    (directory / "capture.json").write_text(json.dumps(capture))
    if damage:
        with pytest.raises(ValueError):
            _additional_sources(tmp_path)
    else:
        assert set(_additional_sources(tmp_path)) == {"pbp.json", "summary.json"}


def test_box_whole_second_precision_does_not_replace_finer_primary_clock():
    data = fixture()
    data[0].loc[0, "MIN"] = 42.005
    staged, ledger = run(data)
    assert staged.MIN.iloc[0] == 42.005
    observed = next(row for row in ledger if row["player_id"] == 11 and row["field"] == "MIN")
    assert observed["observed_source_minutes"] == 42
    assert observed["before"] == observed["after"] == 42.005


def test_partial_facts_cannot_hide_an_uncorroborated_shooting_contradiction():
    data = fixture()
    data[0].loc[0, "FGM"] = 0
    with pytest.raises(ValueError, match="contradictory player shooting"):
        run(data, traditional=False)


def test_fractional_clock_correction_handles_integer_primary_minutes():
    data = fixture()
    data[0]["MIN"] = data[0].MIN.astype(int)
    players = data[3]["homeTeam"]["players"]
    players[0]["statistics"]["minutes"] = "42:30"
    players[1]["statistics"]["minutes"] = "37:30"
    staged, _ = run(data)
    assert staged.MIN.iloc[0] == 42.5 and staged.MIN.iloc[1] == 37.5


def test_team_clock_sum_does_not_allow_a_player_longer_than_the_game():
    data = fixture()
    players = data[3]["homeTeam"]["players"]
    players[0]["statistics"]["minutes"] = "49:00"
    players[1]["statistics"]["minutes"] = "31:00"
    with pytest.raises(ValueError, match="exceeds full game"):
        run(data)


def test_zero_score_overtime_cannot_extend_summary_final_period():
    data = fixture()
    events = data[4]["game"]["actions"]
    for clock, subtype in [("PT05M00S", "start"), ("PT00M00S", "end")]:
        row = copy.deepcopy(events[-1])
        row.update(
            actionId=len(events) + 1,
            actionNumber=len(events) + 1,
            period=5,
            clock=clock,
            subType=subtype,
        )
        events.append(row)
    with pytest.raises(ValueError, match="terminal score/clock/period"):
        run(data, traditional=False)


@pytest.mark.parametrize(
    "literal",
    ["10:60", "41:60", "42:-1", "PT41M60S", "pt41m60s", "Pt41M60S", "pT41m60s", "nonsense"],
)
def test_malformed_player_clock_cannot_be_promoted_by_corroboration(literal):
    data = fixture()
    data[3]["homeTeam"]["players"][0]["statistics"]["minutes"] = literal
    original = data[0].copy(deep=True)
    with pytest.raises(ValueError, match="duration"):
        run(data, pbp=False)
    pd.testing.assert_frame_equal(data[0], original)


def test_malformed_team_clock_cannot_be_carried_to_a_valid_denominator():
    data = fixture()
    data[3]["homeTeam"]["statistics"]["minutes"] = "239:60"
    with pytest.raises(ValueError, match="duration"):
        run(data, pbp=False)


@pytest.mark.parametrize(
    "clocks", [(42, 38), ("PT42M00S", "PT38M00S"), ("pt42m00s", "Pt38M00S"), ("42:00.5", "37:59.5")]
)
def test_valid_literal_clock_precision_still_corroborates(clocks):
    data = fixture()
    for player, clock in zip(data[3]["homeTeam"]["players"], clocks):
        player["statistics"]["minutes"] = clock
    staged, _ = run(data, pbp=False)
    assert staged.MIN.iloc[0] == pytest.approx(42 + (0.5 / 60 if clocks[0] == "42:00.5" else 0))
