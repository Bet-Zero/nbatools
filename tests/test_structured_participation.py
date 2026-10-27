"""Discriminating source-envelope, provenance and absence controls."""

import json

import pandas as pd
import pytest

from nbatools.commands.pipeline.pull_player_game_availability import validate_publication
from nbatools.commands.pipeline.structured_participation import stage_structured_game

pytestmark = pytest.mark.engine
REV = "2e44b7c039f104bc6b41a1de494411e83a03714e"


@pytest.fixture
def source(tmp_path):
    def player(pid, name, minutes, points, comment=""):
        return dict(
            personId=pid,
            firstName=name,
            familyName="Player",
            comment=comment,
            statistics=dict(minutes=minutes, points=points),
        )

    traditional = dict(
        boxScoreTraditional=dict(
            gameId="0022500002",
            homeTeamId=1,
            awayTeamId=2,
            homeTeam=dict(
                teamId=1,
                teamTricode="AAA",
                statistics=dict(points=10),
                players=[
                    player(11, "A", "10:00", 10),
                    player(12, "DNP", None, 0, "DNP - Coach's Decision"),
                ],
            ),
            awayTeam=dict(
                teamId=2,
                teamTricode="BBB",
                statistics=dict(points=8),
                players=[player(21, "B", "11:00", 8)],
            ),
        )
    )

    def table(name, rows):
        return dict(
            name=name,
            headers=list(rows[0]) if rows else [],
            rowSet=[list(x.values()) for x in rows],
        )

    summary = dict(
        resultSets=[
            table(
                "GameSummary",
                [
                    dict(
                        GAME_ID="0022500002",
                        GAME_DATE_EST="2025-10-21T00:00:00",
                        GAME_STATUS_ID=3,
                        HOME_TEAM_ID=1,
                        VISITOR_TEAM_ID=2,
                    )
                ],
            ),
            table(
                "LineScore",
                [
                    dict(
                        GAME_ID="0022500002",
                        GAME_DATE_EST="2025-10-21",
                        TEAM_ID=1,
                        TEAM_ABBREVIATION="AAA",
                        PTS=10,
                    ),
                    dict(
                        GAME_ID="0022500002",
                        GAME_DATE_EST="2025-10-21",
                        TEAM_ID=2,
                        TEAM_ABBREVIATION="BBB",
                        PTS=8,
                    ),
                ],
            ),
            table(
                "InactivePlayers",
                [
                    dict(
                        PLAYER_ID=13,
                        FIRST_NAME="Inactive",
                        LAST_NAME="Player",
                        TEAM_ID=1,
                        TEAM_ABBREVIATION="AAA",
                    )
                ],
            ),
        ]
    )
    root = tmp_path / "data"
    suffix = "2025-26_regular_season.csv"
    tables = {
        "games": [
            dict(
                game_id=22500002,
                game_date="2025-10-21",
                is_final=True,
                home_team_id=1,
                away_team_id=2,
                season="2025-26",
                season_type="Regular Season",
            )
        ],
        "team_game_stats": [
            dict(game_id=22500002, team_id=1, team_abbr="AAA", pts=10),
            dict(game_id=22500002, team_id=2, team_abbr="BBB", pts=8),
        ],
        "player_game_stats": [
            dict(game_id=22500002, team_id=1, player_id=11, player_name="A Player", pts=10),
            dict(game_id=22500002, team_id=2, player_id=21, player_name="B Player", pts=8),
        ],
    }
    for kind, rows in tables.items():
        folder = root / "raw" / kind
        folder.mkdir(parents=True)
        pd.DataFrame(rows).to_csv(folder / suffix, index=False)
    return root, tmp_path / "traditional.json", tmp_path / "summary.json", traditional, summary


def run(source):
    root, t, s, trad, summ = source
    t.write_text(json.dumps(trad))
    s.write_text(json.dumps(summ))
    return stage_structured_game(
        root,
        season="2025-26",
        season_type="Regular Season",
        game_id=22500002,
        traditional=t,
        summary=s,
        summary_version=2,
        revision=REV,
        retrieved_at="2026-10-27T16:45:00+00:00",
    )


def test_explicit_states_and_publication_rebuild(source):
    rows = run(source)
    assert dict(zip(rows.player_id, rows.participation_state)) == {
        11: "played",
        12: "did_not_play",
        13: "did_not_play",
        21: "played",
    }
    assert rows.coverage_scope.eq("listed_player_rows_only").all()
    assert 99 not in set(rows.player_id)
    validate_publication(source[0])


@pytest.mark.parametrize(
    "damage",
    [
        "date",
        "game",
        "side",
        "score",
        "duplicate",
        "conflict",
        "fraction",
        "duration",
        "name",
        "points",
        "missing_table",
        "abbreviation",
    ],
)
def test_malformed_or_conflicting_sources_cannot_qualify(source, damage):
    _, _, _, trad, summary = source
    scope, score, inactive = summary["resultSets"]
    if damage == "date":
        scope["rowSet"][0][1] = "2025-10-22"
    elif damage == "game":
        scope["rowSet"][0][0] = "0022509999"
    elif damage == "side":
        scope["rowSet"][0][3] = 2
    elif damage == "score":
        score["rowSet"][0][-1] = 999
    elif damage == "duplicate":
        inactive["rowSet"] *= 2
    elif damage == "conflict":
        inactive["rowSet"][0][0] = 11
    elif damage == "fraction":
        inactive["rowSet"][0][0] = 13.5
    elif damage == "duration":
        trad["boxScoreTraditional"]["homeTeam"]["players"][0]["statistics"]["minutes"] = "29:60"
    elif damage == "name":
        trad["boxScoreTraditional"]["homeTeam"]["players"][0]["firstName"] = "Different"
    elif damage == "points":
        trad["boxScoreTraditional"]["homeTeam"]["players"][0]["statistics"]["points"] = 9
    elif damage == "missing_table":
        summary["resultSets"].pop()
    else:
        inactive["rowSet"][0][-1] = "BBB"
    with pytest.raises((ValueError, KeyError)):
        run(source)
    assert not (source[0] / "raw/player_game_availability/2025-26_regular_season.csv").exists()


def test_original_byte_tampering_rejected_before_publication(source):
    run(source)
    directory = source[0] / "raw/player_game_availability_sources"
    raw = next(p for p in directory.glob("*.json") if not p.name.endswith(".structured.json"))
    raw.write_bytes(raw.read_bytes() + b" ")
    with pytest.raises(ValueError, match="original bytes"):
        validate_publication(source[0])


def test_multiple_broadcast_records_require_identical_scope(source):
    scope = source[-1]["resultSets"][0]
    scope["headers"].append("BROADCAST")
    row = scope["rowSet"][0]
    row.append("NBC")
    scope["rowSet"].append([*row[:-1], "Peacock"])
    run(source)
    scope["rowSet"][1][2] = 1
    with pytest.raises(ValueError, match="game/date/finality/sides"):
        run(source)


def test_empty_inactive_is_no_completeness_claim(source):
    source[-1]["resultSets"][2]["rowSet"] = []
    rows = run(source)
    assert set(rows.player_id) == {11, 12, 21}
    assert rows.participation_state.eq("did_not_play").sum() == 1


def test_replacement_cannot_drop_stronger_existing_evidence(source):
    run(source)
    target = source[0] / "raw/player_game_availability/2025-26_regular_season.csv"
    rows = pd.read_csv(target)
    extra = rows.loc[rows.player_id.eq(13)].assign(player_id=99, player_name="Other Inactive")
    pd.concat([rows, extra], ignore_index=True).to_csv(target, index=False)
    with pytest.raises(ValueError, match="drops or contradicts"):
        run(source)


def test_nonparticipant_cannot_have_positive_boxscore_activity(source):
    source[3]["boxScoreTraditional"]["homeTeam"]["players"][1]["statistics"]["points"] = 1
    with pytest.raises(ValueError, match="nonparticipant.*activity"):
        run(source)


def test_inactive_identity_cannot_conflict_with_known_other_game_name(source):
    path = source[0] / "raw/player_game_stats/2025-26_regular_season.csv"
    rows = pd.read_csv(path)
    other = pd.DataFrame(
        [dict(game_id=22500999, team_id=1, player_id=13, player_name="Known Person", pts=3)]
    )
    pd.concat([rows, other], ignore_index=True).to_csv(path, index=False)
    with pytest.raises(ValueError, match="listed name.*identity"):
        run(source)


@pytest.mark.parametrize("side", ["homeTeam", "awayTeam"])
def test_traditional_abbreviation_must_match_canonical_side(source, side):
    source[3]["boxScoreTraditional"][side]["teamTricode"] = "WRONG"
    with pytest.raises(ValueError, match="abbreviation"):
        run(source)


def test_nonparticipant_cannot_have_personal_fouls(source):
    source[3]["boxScoreTraditional"]["homeTeam"]["players"][1]["statistics"]["foulsPersonal"] = 3
    with pytest.raises(ValueError, match="nonparticipant.*activity"):
        run(source)
