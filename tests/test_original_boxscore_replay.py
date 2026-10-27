"""Original wire-response replay, with explicit controlled source populations."""

import hashlib
import json

import pandas as pd
import pytest

from nbatools.commands.pipeline.pull_player_game_availability import (
    _cached_boxscore,
    backfill,
    normalize_boxscore_availability,
)

pytestmark = pytest.mark.engine


def document():
    def player(pid, minutes, comment=""):
        return dict(
            personId=pid,
            firstName="Player",
            familyName=str(pid),
            comment=comment,
            statistics=dict(minutes=minutes),
        )

    return dict(
        boxScoreTraditional=dict(
            gameId="0022500001",
            homeTeamId=1,
            awayTeamId=2,
            homeTeam=dict(
                teamId=1,
                teamTricode="BOS",
                players=[player(10, "PT10M"), player(11, None, "DNP - Coach's Decision")],
            ),
            awayTeam=dict(teamId=2, teamTricode="NYK", players=[player(20, "PT0M")]),
        )
    )


def replay(tmp_path, doc):
    path = tmp_path / "boxscore_0022500001.json"
    path.write_text(json.dumps(doc))
    raw = _cached_boxscore(path)
    rows = normalize_boxscore_availability(
        raw,
        game_id=22500001,
        game_date="2025-10-22",
        season="2025-26",
        season_type="Regular Season",
        expected_team_ids={1, 2},
    )
    return path, rows


def test_original_wire_response_keeps_listed_population_and_byte_binding(tmp_path):
    path, rows = replay(tmp_path, document())
    assert rows.player_id.tolist() == [10, 11, 20]
    assert rows.participation_state.tolist() == ["played", "did_not_play", "unknown"]
    assert rows.source_sha256.eq(hashlib.sha256(path.read_bytes()).hexdigest()).all()
    assert rows.coverage_scope.eq("listed_player_rows_only").all()


@pytest.mark.parametrize(
    "mutation",
    [
        lambda d: d.pop("awayTeam"),
        lambda d: d["homeTeam"].update(teamId=2),
        lambda d: d["awayTeam"].update(players=[]),
        lambda d: d.update(playerStats=[]),
        lambda d: d["homeTeam"]["players"][0].update(personId=10.5),
        lambda d: d["awayTeam"]["players"][0].update(personId=10),
        lambda d: d["homeTeam"]["players"][1]["statistics"].update(minutes="PT1M"),
        lambda d: d.update(gameId="0022509999"),
    ],
)
def test_invalid_original_source_rejected(tmp_path, mutation):
    doc = document()
    mutation(doc["boxScoreTraditional"])
    with pytest.raises(ValueError):
        replay(tmp_path, doc)


def test_missing_minutes_stays_unknown(tmp_path):
    doc = document()
    doc["boxScoreTraditional"]["awayTeam"]["players"][0]["statistics"] = {}
    _, rows = replay(tmp_path, doc)
    assert rows.loc[rows.player_id.eq(20), "participation_state"].item() == "unknown"


def test_explicit_archive_replayed_on_resume_instead_of_stale_digest(tmp_path):
    root = tmp_path / "data"
    games = root / "raw/games"
    games.mkdir(parents=True)
    pd.DataFrame(
        [
            dict(
                game_id="0022500001",
                game_date="2025-10-22",
                season="2025-26",
                season_type="Regular Season",
                is_final=True,
                home_team_id=1,
                away_team_id=2,
            )
        ]
    ).to_csv(games / "2025-26_regular_season.csv", index=False)
    path, _ = replay(tmp_path, document())
    one = backfill("2025-26", root=root, cached_boxscores=tmp_path)
    doc = document()
    doc["boxScoreTraditional"]["awayTeam"]["players"][0]["comment"] = "INACTIVE"
    path.write_text(json.dumps(doc))
    two = backfill("2025-26", root=root, cached_boxscores=tmp_path)
    assert one.loc[one.player_id.eq(20), "participation_state"].item() == "unknown"
    assert two.loc[two.player_id.eq(20), "participation_state"].item() == "did_not_play"
    assert two.source_sha256.eq(hashlib.sha256(path.read_bytes()).hexdigest()).all()
    path.write_text("{}")
    with pytest.raises(ValueError):
        backfill("2025-26", root=root, cached_boxscores=tmp_path)
