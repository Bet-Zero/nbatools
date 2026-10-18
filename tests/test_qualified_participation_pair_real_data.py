"""K08 pair semantics against two retained official production report games."""

import hashlib
import json
from pathlib import Path

import pytest

from nbatools.data_source import data_path, data_read_csv
from nbatools.query_service import execute_natural_query, execute_structured_query

pytestmark = [pytest.mark.needs_data, pytest.mark.query]
ORACLE = json.loads(Path(__file__).with_name("k08_qualified_pair_oracle.json").read_text())
PAIR = "LeBron James and Anthony Davis"


def _qualified_source():
    excerpt = ORACLE["retained_source_rows"]
    assert (
        hashlib.sha256(Path(__file__).with_name(excerpt["path"]).read_bytes()).hexdigest()
        == excerpt["sha256"]
    )
    for path, digest in ORACLE["sources"].items():
        assert hashlib.sha256(data_path(path).read_bytes()).hexdigest() == digest
    suffix = "2023-24_regular_season.csv"
    teams = data_read_csv("raw/team_game_stats/" + suffix)
    players = data_read_csv("raw/player_game_stats/" + suffix)
    ledger = data_read_csv("raw/player_game_availability/" + suffix)
    teams = teams.loc[
        teams.team_id.eq(ORACLE["team_id"]) & teams.opponent_team_id.eq(ORACLE["opponent_team_id"])
    ]
    assert set(teams.game_id.astype(int)) == set(ORACLE["candidate_game_ids"])
    assert teams.season.eq(ORACLE["season"]).all()
    assert teams.season_type.eq(ORACLE["season_type"]).all()
    for game, report in ORACLE["retained_reports"].items():
        assert (
            hashlib.sha256(
                data_path(
                    "raw/player_game_availability_sources/" + report["sha256"] + ".pdf"
                ).read_bytes()
            ).hexdigest()
            == report["sha256"]
        )
        for name, pid in ORACLE["participant_ids"].items():
            observed = ledger.loc[ledger.game_id.eq(int(game)) & ledger.player_id.eq(pid)]
            assert len(observed) == 1
            row = observed.iloc[0]
            assert row.team_id == ORACLE["team_id"] and row.player_name == name
            assert row.game_date == teams.loc[teams.game_id.eq(int(game)), "game_date"].item()
            assert row.source == report["source"] and row.source_sha256 == report["sha256"]
            assert row.coverage_scope == "listed_player_rows_only"
            expected_state = (
                "played" if int(game) in ORACLE["both_played_game_ids"] else "did_not_play"
            )
            assert row.participation_state == expected_state
            appearances = players.loc[players.game_id.eq(int(game)) & players.player_id.eq(pid)]
            if expected_state == "played":
                assert len(appearances) == 1 and appearances.iloc[0].minutes > 0
            else:
                assert appearances.empty
                assert isinstance(row.source_comment, str) and row.source_comment.strip()
    team = teams.loc[teams.game_id.eq(ORACLE["selected_team"]["game_id"])].iloc[0]
    assert team.wl == "W"
    for stat in ("pts", "reb", "ast"):
        assert team[stat] == ORACLE["selected_team"][stat]
    player = players.loc[
        players.game_id.eq(team.game_id)
        & players.player_id.eq(ORACLE["selected_player"]["player_id"])
    ]
    assert len(player) == 1 and player.iloc[0].team_id == ORACLE["team_id"]
    for stat in ("pts", "reb", "ast"):
        assert player.iloc[0][stat] == ORACLE["selected_player"][stat]


def _assert_answer(result, *, player):
    assert result.result_status == "ok", (result.result_reason, result.metadata)
    sections = result.result.to_dict()["sections"]
    rows = sections["finder"] if player else sections["game_log"]
    assert len(rows) == 1 and int(rows[0]["game_id"]) == 22300684
    assert rows[0]["season"] == "2023-24" and rows[0]["opponent_team_abbr"] == "BOS"
    if player:
        assert rows[0]["player_id"] == 1630559
        for stat in ("pts", "reb", "ast"):
            assert rows[0][stat] == ORACLE["selected_player"][stat]
    else:
        row = sections["summary"][0]
        assert (row["games"], row["wins"], row["losses"]) == (1, 1, 0)
        for stat in ("pts", "reb", "ast"):
            assert row[stat + "_avg"] == ORACLE["selected_team"][stat]


def test_existing_source_qualifies_pair_and_independent_values():
    _qualified_source()


@pytest.mark.parametrize("player", [False, True], ids=["team", "player"])
def test_qualified_pair_structured_execution(player):
    _qualified_source()
    kwargs = (
        dict(player="Austin Reaves", stat="pts", min_value=20)
        if player
        else dict(team="LAL", stat="pts", min_value=110)
    )
    result = execute_structured_query(
        "player_game_finder" if player else "team_record",
        season="2023-24",
        opponent="BOS",
        without_player=PAIR,
        **kwargs,
    )
    _assert_answer(result, player=player)


@pytest.mark.parametrize(
    "query,player",
    [
        ("Lakers record vs Celtics with LeBron James and Anthony Davis both out in 2023-24", False),
        ("Lakers record vs Celtics with LeBron James and Anthony Davis DNP in 2023-24", False),
        (
            "Austin Reaves games with at least 20 points vs Celtics without LeBron James and Anthony Davis in 2023-24",
            True,
        ),
    ],
)
def test_qualified_pair_wording_and_subject_bound(query, player):
    _qualified_source()
    result = execute_natural_query(query)
    _assert_answer(result, player=player)
    assert result.metadata["without_player"] == PAIR
    assert result.metadata["with_player"] is None
    assert result.metadata["opponent"] == "BOS"
    assert result.metadata["season"] == "2023-24"
