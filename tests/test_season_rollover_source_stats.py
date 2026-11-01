"""Controlled independent row arithmetic for season-source qualification."""

import copy
import hashlib
import json
import zipfile

import pytest

from tools.season_rollover_source_stats import REVISION, qualify_frames, retained_stats_documents


def sources():
    def table(name, rows, parameters):
        return dict(
            parameters=parameters,
            resultSets=[
                dict(name=name, headers=list(rows[0]), rowSet=[list(row.values()) for row in rows])
            ],
        )

    schedule = dict(
        leagueSchedule=dict(
            seasonYear="2026-27",
            leagueId="00",
            gameDates=[
                dict(
                    games=[
                        dict(
                            gameId="0022600001",
                            gameStatus=3,
                            gameDateEst="2026-10-20T00:00:00Z",
                            homeTeam=dict(teamId=1, score=10),
                            awayTeam=dict(teamId=2, score=8),
                        )
                    ]
                )
            ],
        )
    )
    base = dict(
        SEASON_ID="22026",
        GAME_ID="0022600001",
        GAME_DATE="2026-10-20",
        MIN=240,
        FGA=10,
        FG3M=1,
        FG3A=3,
        FTM=1,
        FTA=2,
        OREB=2,
        DREB=3,
        REB=5,
        AST=2,
        STL=1,
        BLK=1,
        TOV=1,
        PF=2,
    )
    team = [
        dict(
            **base,
            TEAM_ID=1,
            TEAM_ABBREVIATION="AAA",
            TEAM_NAME="Team A",
            MATCHUP="AAA vs. BBB",
            WL="W",
            PTS=10,
            FGM=4,
            PLUS_MINUS=2,
        ),
        dict(
            **base,
            TEAM_ID=2,
            TEAM_ABBREVIATION="BBB",
            TEAM_NAME="Team B",
            MATCHUP="BBB @ AAA",
            WL="L",
            PTS=8,
            FGM=3,
            PLUS_MINUS=-2,
        ),
    ]
    common = dict(LeagueID="00", Season="2026-27", SeasonType="Regular Season")
    documents = dict(
        finder=table(
            "LeagueGameFinderResults", team, dict(**common, PlayerOrTeam="T", GameID="0000000000")
        ),
        gamelog=table(
            "LeagueGameLog",
            copy.deepcopy(team),
            dict(**common, PlayerOrTeam="T", Sorter="DATE", Direction="ASC"),
        ),
    )
    players = []
    for row, pid, name in zip(team, [11, 21], ["A Player", "B Player"]):
        player = {key: value for key, value in row.items() if key != "SEASON_ID"}
        player.update(SEASON_YEAR="2026-27", PLAYER_ID=pid, PLAYER_NAME=name, MIN=30)
        players.append(player)
    documents["player_game_logs"] = table(
        "PlayerGameLogs",
        players,
        dict(
            LeagueID="00",
            SeasonYear="2026-27",
            SeasonType="Regular Season",
            MeasureType="Base",
            PerMode="Totals",
        ),
    )
    advanced = []
    player_advanced = []
    standing = []
    for row, pid in zip(team, [11, 21]):
        advanced.append(
            dict(
                TEAM_ID=row["TEAM_ID"],
                TEAM_ABBREVIATION=row["TEAM_ABBREVIATION"],
                GP=1,
                W=int(row["WL"] == "W"),
                L=int(row["WL"] == "L"),
                W_PCT=int(row["WL"] == "W"),
                OFF_RATING=100,
                DEF_RATING=90,
                NET_RATING=10,
                PACE=100,
            )
        )
        player_advanced.append(
            dict(
                PLAYER_ID=pid,
                PLAYER_NAME="A Player" if pid == 11 else "B Player",
                TEAM_ID=row["TEAM_ID"],
                GP=1,
                W=int(row["WL"] == "W"),
                L=int(row["WL"] == "L"),
                MIN=30,
                USG_PCT=0.2,
                TS_PCT=0.5,
            )
        )
        standing.append(
            dict(
                TeamID=row["TEAM_ID"],
                TeamAbbreviation=row["TEAM_ABBREVIATION"],
                LeagueID="00",
                SeasonID="22026",
                WINS=int(row["WL"] == "W"),
                LOSSES=int(row["WL"] == "L"),
                WinPCT=int(row["WL"] == "W"),
                PlayoffRank=1,
                DivisionRank=1,
                ConferenceGamesBack=0,
                strCurrentStreak="W1",
            )
        )
    scope = dict(**common, MeasureType="Advanced", PerMode="PerGame")
    documents["teams_advanced"] = table("LeagueDashTeamStats", advanced, scope)
    documents["players_advanced"] = table("LeagueDashPlayerStats", player_advanced, scope)
    documents["standings"] = table(
        "Standings",
        standing,
        dict(LeagueID="00", SeasonYear="2026-27", SeasonType="Regular Season"),
    )
    return schedule, documents


def mutate(document, field, value, row=0):
    table = document["resultSets"][0]
    table["rowSet"][row][table["headers"].index(field)] = value


def test_qualified_snapshots_use_exact_game_and_player_denominators():
    report, snapshots = qualify_frames(*sources())
    assert report["team_game_rows"] == report["player_game_rows"] == 2
    assert report["final_points_total"] == 18 and report["final_game_ids"] == ["0022600001"]
    assert report["qualified_snapshot_rows"] == {key: 2 for key in snapshots}
    assert snapshots["team_season_advanced"].wins.tolist() == [1, 0]
    assert report["player_team_conflicts"] == []
    assert report["team_mode_gamelog_is_player_data"] is False
    assert not report["canonical_core_accepted"] and report["production_writes"] == 0


def test_known_grain_difference_and_player_correction_are_explicit_unresolved_rows():
    schedule, documents = sources()
    mutate(documents["gamelog"], "TOV", 2)
    mutate(documents["gamelog"], "MIN", 239)
    mutate(documents["player_game_logs"], "DREB", 2)
    report, _ = qualify_frames(schedule, documents)
    assert {row["field"] for row in report["source_team_differences"]} == {"MIN", "TOV"}
    assert report["player_team_conflicts"] == [
        dict(game_id="0022600001", team_id=1, field="DREB", team=3, player_sum=2)
    ]
    assert report["canonical_core_accepted"] is False


def test_quarter_labels_with_zero_bodies_do_not_establish_real_period_coverage():
    schedule, documents = sources()
    box = dict(
        gameId="0022600001",
        homeTeam=dict(statistics=dict(points=0)),
        awayTeam=dict(statistics=dict(points=0)),
    )
    documents["period_0022600001"] = {
        str(n): dict(boxScoreTraditional=copy.deepcopy(box)) for n in range(1, 5)
    }
    report, _ = qualify_frames(schedule, documents)
    finding = report["representatives"]["period_0022600001"]
    assert finding["quarter_team_points"] == [0] * 8 and finding["all_zero"]
    assert finding["canonical_period_accepted"] is False
    assert report["period_coverage"] == "not_established"


@pytest.mark.parametrize(
    "damage",
    [
        "old_scope",
        "filter",
        "player_mode",
        "team_mode_as_player",
        "missing_team",
        "duplicate",
        "wrong_date",
        "wrong_points",
        "player_outcome",
        "advanced_gp",
        "advanced_record",
        "standings",
        "net_rating",
        "schedule_score",
    ],
)
def test_unqualified_source_cannot_silently_change_scope_or_counts(damage):
    schedule, documents = sources()
    if damage == "old_scope":
        documents["finder"]["parameters"]["Season"] = "2025-26"
    elif damage == "filter":
        documents["players_advanced"]["parameters"]["TeamID"] = 1
    elif damage == "player_mode":
        documents["player_game_logs"]["parameters"]["PerMode"] = "PerGame"
    elif damage == "team_mode_as_player":
        documents["player_game_logs"] = documents["gamelog"]
    elif damage == "missing_team":
        documents["finder"]["resultSets"][0]["rowSet"].pop()
    elif damage == "duplicate":
        documents["finder"]["resultSets"][0]["rowSet"].append(
            documents["finder"]["resultSets"][0]["rowSet"][0].copy()
        )
    elif damage == "wrong_date":
        mutate(documents["finder"], "GAME_DATE", "2026-10-21")
    elif damage == "wrong_points":
        mutate(documents["finder"], "PTS", 11)
    elif damage == "player_outcome":
        mutate(documents["player_game_logs"], "WL", "L")
    elif damage == "advanced_gp":
        mutate(documents["players_advanced"], "GP", 2)
    elif damage == "advanced_record":
        mutate(documents["players_advanced"], "W", 0)
    elif damage == "standings":
        mutate(documents["standings"], "WINS", 0)
    elif damage == "net_rating":
        mutate(documents["teams_advanced"], "NET_RATING", 100)
    elif damage == "schedule_score":
        schedule["leagueSchedule"]["gameDates"][0]["games"][0]["homeTeam"]["score"] = 9
    with pytest.raises((ValueError, KeyError)):
        qualify_frames(schedule, documents)


@pytest.mark.parametrize(
    "damage", [None, "archive", "member", "blob", "url", "unreferenced", "unsafe"]
)
def test_data_only_bundle_replays_exact_originals_and_rejects_changed_provenance(tmp_path, damage):
    raw = b'{"fixture": true}'
    item = dict(
        file="stats-sources/finder.json",
        path="nba_stats/json/leaguegamefinder/2027/regular-season.json",
        size_bytes=len(raw),
        sha256=hashlib.sha256(raw).hexdigest(),
        git_blob_sha=hashlib.sha1(f"blob {len(raw)}\0".encode() + raw).hexdigest(),
    )
    item["url"] = (
        f"https://raw.githubusercontent.com/sportsdataverse/hoopR-nba-stats-raw/{REVISION}/{item['path']}"
    )
    if damage == "blob":
        item["git_blob_sha"] = "bad"
    elif damage == "url":
        item["url"] = "https://unrecognized.invalid/finder.json"
    capture = dict(
        revision=REVISION,
        season="2026-27",
        season_type="Regular Season",
        repository="sportsdataverse/hoopR-nba-stats-raw",
        source_files=dict(finder=item),
    )
    files = {
        item["file"]: raw,
        "stats-capture.json": json.dumps(capture).encode(),
        "supplemental-capture.json": json.dumps(capture | {"source_files": {}}).encode(),
        "archive-metadata.json": b"{}",
    }
    if damage == "unreferenced":
        files["extra.json"] = b"{}"
    elif damage == "unsafe":
        files["../outside.json"] = b"{}"
    entries = []
    bundle = tmp_path / "stats-sources.zip"
    with zipfile.ZipFile(bundle, "w") as archive:
        for name, body in files.items():
            archive.writestr(name, body)
            entries.append(
                dict(path=name, size_bytes=len(body), sha256=hashlib.sha256(body).hexdigest())
            )
    if damage == "member":
        entries[0]["sha256"] = "bad"
    binding = dict(
        bundle="stats-sources.zip",
        archive_revision=REVISION,
        files=entries,
        bundle_bytes=bundle.stat().st_size,
        bundle_sha256="bad"
        if damage == "archive"
        else hashlib.sha256(bundle.read_bytes()).hexdigest(),
    )
    (tmp_path / "stats-bundle.json").write_text(json.dumps(binding))
    if damage:
        with pytest.raises(ValueError):
            retained_stats_documents(tmp_path)
    else:
        documents, originals, digest = retained_stats_documents(tmp_path)
        assert documents == dict(finder=dict(fixture=True))
        assert originals["finder"]["sha256"] == hashlib.sha256(raw).hexdigest()
        assert digest == binding["bundle_sha256"]
