from __future__ import annotations

import pandas as pd
import pytest

from nbatools.commands.source_invariants import (
    ExpectedGameTerminalState,
    apply_play_by_play_trust_decisions,
    canonicalize_team_game_pairs,
    expected_game_terminal_states,
    play_by_play_game_trust_decisions,
    validate_play_by_play_trust_decisions,
    validate_team_game_pair_invariants,
)
from nbatools.commands.validation_control import validate_raw_coverage

pytestmark = pytest.mark.engine


def _team_game(
    game_id: str,
    *,
    first_team: int = 1,
    second_team: int = 2,
    first_pts: int = 100,
    second_pts: int = 110,
    first_plus_minus: float = -10,
    second_plus_minus: float = 10,
    minutes: float = 240,
) -> list[dict]:
    return [
        {
            "game_id": game_id,
            "team_id": first_team,
            "team_abbr": "AAA",
            "team_name": "Alpha",
            "opponent_team_id": second_team,
            "opponent_team_abbr": "BBB",
            "opponent_team_name": "Beta",
            "is_home": 1,
            "is_away": 0,
            "wl": "W" if first_pts > second_pts else "L",
            "minutes": minutes,
            "pts": first_pts,
            "plus_minus": first_plus_minus,
        },
        {
            "game_id": game_id,
            "team_id": second_team,
            "team_abbr": "BBB",
            "team_name": "Beta",
            "opponent_team_id": first_team,
            "opponent_team_abbr": "AAA",
            "opponent_team_name": "Alpha",
            "is_home": 0,
            "is_away": 1,
            "wl": "W" if second_pts > first_pts else "L",
            "minutes": minutes,
            "pts": second_pts,
            "plus_minus": second_plus_minus,
        },
    ]


def _games(game_id: str = "0022500001", *, trusted: int = 1) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "game_id": game_id,
                "home_team_id": 1,
                "away_team_id": 2,
                "home_away_designation_trusted": trusted,
            }
        ]
    )


def _pbp(
    game_id: str = "0022500001",
    *,
    final_period: int = 4,
    terminal_clock: float = 0,
    final_scores: tuple[int, int] = (100, 110),
) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "game_id": game_id,
                "action_number": 1,
                "period": final_period,
                "clock_seconds_remaining": 10,
                "score_home": final_scores[0] - 2,
                "score_away": final_scores[1],
                "pbp_source_trusted": 0,
                "pbp_validation_reason": "expected_final_score_not_validated",
            },
            {
                "game_id": game_id,
                "action_number": 2,
                "period": final_period,
                "clock_seconds_remaining": terminal_clock,
                "score_home": final_scores[0],
                "score_away": final_scores[1],
                "pbp_source_trusted": 0,
                "pbp_validation_reason": "expected_final_score_not_validated",
            },
        ]
    )


def test_three_reproduced_plus_minus_anomalies_are_canonicalized_from_paired_scores():
    rows = []
    rows.extend(_team_game("0022501227", first_plus_minus=-9.6))
    rows.extend(_team_game("0022500564", first_plus_minus=-5.8, first_pts=104, second_pts=110))
    rows.extend(
        _team_game(
            "0022500661",
            first_pts=111,
            second_pts=100,
            first_plus_minus=10.6,
            second_plus_minus=-11,
        )
    )
    source = pd.DataFrame(rows)

    with pytest.raises(ValueError, match="plus_minus mismatch"):
        validate_team_game_pair_invariants(source)

    canonical = canonicalize_team_game_pairs(source)

    assert canonical.loc[canonical["game_id"].eq("0022501227"), "plus_minus"].tolist() == [
        -10,
        10,
    ]
    assert canonical.loc[canonical["game_id"].eq("0022500564"), "plus_minus"].tolist() == [
        -6,
        6,
    ]
    assert canonical.loc[canonical["game_id"].eq("0022500661"), "plus_minus"].tolist() == [
        11,
        -11,
    ]
    validate_team_game_pair_invariants(canonical)


def test_team_pair_validation_rejects_wl_opponent_and_trusted_venue_identity_drift():
    valid = pd.DataFrame(_team_game("0022500001"))
    validate_team_game_pair_invariants(valid, games=_games())

    bad_wl = valid.copy()
    bad_wl.loc[0, "wl"] = "W"
    with pytest.raises(ValueError, match="wl mismatch"):
        validate_team_game_pair_invariants(bad_wl)

    bad_opponent = valid.copy()
    bad_opponent.loc[0, "opponent_team_id"] = 3
    with pytest.raises(ValueError, match="opponent identity mismatch"):
        validate_team_game_pair_invariants(bad_opponent)

    bad_venue = valid.copy()
    bad_venue[["is_home", "is_away"]] = bad_venue[["is_away", "is_home"]]
    with pytest.raises(ValueError, match="trusted venue identity mismatch"):
        validate_team_game_pair_invariants(bad_venue, games=_games())


def test_team_pair_validation_accepts_untrusted_neutral_participants_only_with_zero_roles():
    neutral = pd.DataFrame(_team_game("0022500001"))
    neutral[["is_home", "is_away"]] = 0

    validate_team_game_pair_invariants(neutral, games=_games(trusted=0))

    neutral.loc[0, "is_home"] = 1
    neutral.loc[1, "is_away"] = 1
    with pytest.raises(ValueError, match="untrusted venue identity"):
        validate_team_game_pair_invariants(neutral, games=_games(trusted=0))


def test_play_by_play_trust_requires_every_expected_game_and_complete_terminal_state():
    expected = {
        "22500001": ExpectedGameTerminalState(final_scores=(100, 110), final_period=4),
        "22500002": ExpectedGameTerminalState(final_scores=(99, 105), final_period=4),
    }
    events = _pbp()

    decisions = play_by_play_game_trust_decisions(events, expected)

    assert decisions["22500001"] == ()
    assert decisions["22500002"] == ("missing_game_events",)


@pytest.mark.parametrize(
    ("events", "reason"),
    [
        (_pbp(terminal_clock=1.2), "terminal_clock_not_zero"),
        (_pbp(final_scores=(100, 109)), "terminal_score_mismatch"),
        (_pbp(final_period=3), "terminal_period_before_fourth"),
    ],
)
def test_play_by_play_trust_rejects_incomplete_terminal_actions(events, reason):
    expected = {"22500001": ExpectedGameTerminalState(final_scores=(100, 110), final_period=4)}

    trusted, decisions = apply_play_by_play_trust_decisions(events, expected)

    assert reason in decisions["22500001"]
    assert trusted["pbp_source_trusted"].eq(0).all()
    assert trusted["pbp_validation_reason"].str.contains(reason, regex=False).all()


def test_play_by_play_trust_uses_team_minutes_to_require_overtime_terminal_period():
    team = pd.DataFrame(
        _team_game(
            "0022500001",
            first_pts=120,
            second_pts=121,
            first_plus_minus=-1,
            second_plus_minus=1,
            minutes=265,
        )
    )
    expected = expected_game_terminal_states(team)

    regulation_terminal = _pbp(final_period=4, final_scores=(120, 121))
    overtime_terminal = _pbp(final_period=5, final_scores=(120, 121))

    assert play_by_play_game_trust_decisions(regulation_terminal, expected)["22500001"] == (
        "terminal_period_mismatch",
    )
    assert play_by_play_game_trust_decisions(overtime_terminal, expected)["22500001"] == ()


def test_play_by_play_validation_recomputes_instead_of_trusting_row_flags():
    team = pd.DataFrame(_team_game("0022500001"))
    spoofed = _pbp(terminal_clock=5)
    spoofed["pbp_source_trusted"] = 1
    spoofed["pbp_validation_reason"] = ""

    errors = validate_play_by_play_trust_decisions(spoofed, team)

    assert errors == [
        "game_id=22500001: trust decision mismatch (expected=terminal_clock_not_zero)"
    ]


def test_raw_control_plane_enforces_paired_and_terminal_invariants():
    games = _games()
    team = pd.DataFrame(_team_game("0022500001"))
    events, decisions = apply_play_by_play_trust_decisions(
        _pbp(), expected_game_terminal_states(team)
    )
    assert decisions == {"22500001": ()}

    validate_raw_coverage(
        {
            "games": games,
            "team_game_stats": team,
            "play_by_play_events": events,
        }
    )

    events.loc[events["action_number"].eq(2), "clock_seconds_remaining"] = 2
    with pytest.raises(ValueError, match="terminal_clock_not_zero"):
        validate_raw_coverage(
            {
                "games": games,
                "team_game_stats": team,
                "play_by_play_events": events,
            }
        )
