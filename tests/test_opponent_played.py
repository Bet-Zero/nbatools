"""Qualified same-game side facts, including known negative and unknown controls."""

import pandas as pd
import pytest

from nbatools.commands import _participation_observations as observations
from nbatools.commands import data_utils

pytestmark = pytest.mark.fixture_data
LAL, BOS, TATUM = 1610612747, 1610612738, 1628369


@pytest.fixture
def matchup(monkeypatch):
    candidates = pd.DataFrame(
        [
            dict(game_id=11, team_id=LAL, opponent_team_id=BOS, game_date="2024-01-01"),
            dict(game_id=12, team_id=LAL, opponent_team_id=BOS, game_date="2024-01-03"),
        ]
    )
    ledger = pd.DataFrame(
        [
            dict(
                game_id=game,
                team_id=BOS,
                player_id=TATUM,
                player_name="Jayson Tatum",
                game_date=date,
                participation_state=state,
            )
            for game, date, state in [
                (11, "2024-01-01", "played"),
                (12, "2024-01-03", "did_not_play"),
            ]
        ]
    )
    appearances = ledger.iloc[:1].copy()
    appearances["minutes"] = 30
    appearances["team_abbr"] = "BOS"
    monkeypatch.setattr(observations, "load_observations", lambda *args: ledger.copy())
    monkeypatch.setattr(
        data_utils, "load_player_games_for_seasons", lambda *args: appearances.copy()
    )
    return candidates, ledger, appearances


def select(candidates):
    return data_utils.filter_with_player(
        candidates,
        "Jayson Tatum",
        ["2023-24"],
        "Regular Season",
        team="LAL",
        strict_team_match=True,
        opponent="BOS",
    )


def test_positive_opposing_membership_is_exactly_one_game(matchup):
    candidates, _, _ = matchup
    assert select(candidates).game_id.tolist() == [11]
    assert candidates.game_id.tolist() == [11, 12]


def test_two_explicit_dnp_observations_qualify_a_true_empty(matchup):
    candidates, ledger, appearances = matchup
    ledger["participation_state"] = "did_not_play"
    appearances.drop(appearances.index, inplace=True)
    assert select(candidates).empty


@pytest.mark.parametrize(
    "damage",
    ["unknown", "missing", "wrong_date", "wrong_game", "wrong_team", "conflict", "ambiguous_name"],
)
def test_unqualified_membership_cannot_become_a_negative_or_partial_answer(matchup, damage):
    candidates, ledger, _ = matchup
    if damage == "unknown":
        ledger.loc[1, "participation_state"] = "unknown"
    elif damage == "missing":
        ledger.drop(index=1, inplace=True)
    elif damage == "wrong_date":
        ledger.loc[1, "game_date"] = "2024-01-02"
    elif damage == "wrong_game":
        ledger.loc[1, "game_id"] = 99
    elif damage == "wrong_team":
        ledger.loc[1, "team_id"] = 1610612765
    elif damage == "conflict":
        ledger.loc[0, "participation_state"] = "did_not_play"
    else:
        extra = ledger.iloc[1].copy()
        extra["player_id"] = 999999
        ledger.loc[2] = extra
    with pytest.raises(ValueError):
        select(candidates)


def test_without_explicit_opponent_context_played_keeps_same_team_meaning(matchup):
    candidates, _, _ = matchup
    result = data_utils.filter_with_player(
        candidates, "Jayson Tatum", ["2023-24"], "Regular Season"
    )
    assert result.empty
