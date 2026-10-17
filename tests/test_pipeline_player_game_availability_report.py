"""NBA final scorer's PDF is explicit game-day status, not inferred absence."""

from __future__ import annotations

import pandas as pd
import pytest

from nbatools.commands.pipeline import player_game_availability_report as report
from nbatools.commands.pipeline.pull_player_game_availability import (
    backfill,
    normalize_boxscore_availability,
)

pytestmark = pytest.mark.engine

PDF_TEXT = """NATIONAL BASKETBALL ASSOCIATION OFFICIAL SCORER'S REPORT
FINAL BOX
Tuesday, October 21, 2025 Crypto.com Arena, Los Angeles, CA
VISITOR: Golden State Warriors (1-0)
POS MIN FG FGA PTS
30 Stephen Curry G 32:04 6 14 23
32 Trayce Jackson-Davis DNP - Coach's Decision
240:00 38 78 17 40 119
HOME: LOS ANGELES LAKERS (0-1)
POS MIN FG FGA PTS
77 Luka Doncic G 40:59 17 27 43
9 Bronny James DNP - Coach's Decision
240:00 42 77 8 32 109
SCORE BY PERIOD Warriors 28 27 35 29 119
Lakers 22 32 25 30 109
Inactive: Warriors - Moody (Injury/Illness - Left Soleus; Strain)
Inactive: Lakers - James (Injury/Illness - Right Sciatica;)
Points in the Paint: Warriors 36, Lakers 62
"""


@pytest.fixture
def nba_rows(tmp_path, monkeypatch):
    root = tmp_path / "data"
    for data_type in ("player_game_stats", "team_game_stats", "games"):
        (root / "raw" / data_type).mkdir(parents=True)
    pd.DataFrame(
        [
            dict(game_id="0022500002", game_date="2025-10-21", season="2025-26",
                 season_type="Regular Season", is_final=True,
                 home_team_id=2, away_team_id=1)
        ]
    ).to_csv(root / "raw/games/2025-26_regular_season.csv", index=False)
    pd.DataFrame(
        [
            dict(game_id="0022500002", team_id=1, team_abbr="GSW",
                 team_name="Golden State Warriors", pts=119),
            dict(game_id="0022500002", team_id=2, team_abbr="LAL",
                 team_name="Los Angeles Lakers", pts=109),
        ]
    ).to_csv(root / "raw/team_game_stats/2025-26_regular_season.csv", index=False)
    pd.DataFrame(
        [
            dict(game_id="0022500002", team_id=1, player_id=30,
                 player_name="Stephen Curry", minutes=32.0),
            dict(game_id="0022500002", team_id=2, player_id=77,
                 player_name="Luka Doncic", minutes=40.0),
            dict(game_id="0022500003", team_id=1, player_id=32,
                 player_name="Trayce Jackson-Davis", minutes=4.0),
            dict(game_id="0022500003", team_id=1, player_id=4,
                 player_name="Moses Moody", minutes=10.0),
            dict(game_id="0022500003", team_id=2, player_id=9,
                 player_name="Bronny James", minutes=5.0),
            dict(game_id="0022500003", team_id=2, player_id=23,
                 player_name="LeBron James", minutes=30.0),
        ]
    ).to_csv(root / "raw/player_game_stats/2025-26_regular_season.csv", index=False)
    monkeypatch.setattr(report, "_fetch_report_text", lambda _: PDF_TEXT)
    return root


def _get(root):
    return report.official_report_as_v3(
        game_id=22500002, game_date="2025-10-21", season="2025-26",
        season_type="Regular Season", home_team_id=2, away_team_id=1, data_root=root,
    )


def test_official_report_includes_dnp_and_inactive_with_date_qualification(nba_rows):
    raw, reference = _get(nba_rows)
    assert reference == "20251021_GSWLAL"
    selected = normalize_boxscore_availability(
        raw, game_id=22500002, game_date="2025-10-21", season="2025-26",
        season_type="Regular Season", expected_team_ids={1, 2},
        source=f"nba_official_finalbox:{reference}",
    )
    assert len(selected) == 6
    status = dict(zip(selected.player_id, selected.participation_state))
    assert status == {30: "played", 32: "did_not_play", 4: "did_not_play",
                      77: "played", 9: "did_not_play", 23: "did_not_play"}
    # Two Lakers named James: Bronny's explicit DNP is consumed BEFORE the
    # inactive surname-only "James", which uniquely denotes LeBron here.
    assert selected.loc[selected.player_id.eq(23), "source_comment"].iloc[0] == (
        "INACTIVE - Injury/Illness - Right Sciatica;"
    )
    assert "James" not in selected.player_name.tolist()


def test_official_report_source_can_stage_one_final_game(nba_rows):
    rows = backfill("2025-26", root=nba_rows, source="report", limit=1)
    assert len(rows) == 6
    assert rows.source.eq("nba_official_finalbox:20251021_GSWLAL").all()
    again = backfill("2025-26", root=nba_rows, source="report", limit=1)
    assert len(again) == 6


@pytest.mark.parametrize(
    "text,match",
    [
        (PDF_TEXT.replace("October 21, 2025", "October 22, 2025"), "date"),
        (PDF_TEXT.replace("Warriors (1-0)", "Timberwolves (1-0)"), "heading"),
        (PDF_TEXT.replace("32 109", "32 110"), "score"),
        (PDF_TEXT.replace("Inactive: Lakers", "Inactive: Celtics"), "inactive list"),
        (PDF_TEXT.replace("Inactive: Warriors - Moody", "Inactive: Warriors - Unknown"),
         "identity unresolved"),
    ],
)
def test_mismatched_or_unresolved_pdf_source_refuses(nba_rows, monkeypatch, text, match):
    monkeypatch.setattr(report, "_fetch_report_text", lambda _: text)
    with pytest.raises(ValueError, match=match):
        _get(nba_rows)


def test_missed_game_is_not_a_stat_row_complement(nba_rows):
    raw, _ = _get(nba_rows)
    assert len(raw) == 6
    # An unlisted player is NOT automatically labeled DNP or injured.
    assert 99 not in raw["personId"].tolist()
    # Historical injury means "what the game-day report stated"; current
    # ESPN injury endpoint is not read or consulted.
    assert raw.loc[raw["personId"].eq(23), "comment"].iloc[0].startswith("INACTIVE")


def test_missing_identity_does_not_publish_incomplete_report(nba_rows):
    path = nba_rows / "raw/player_game_stats/2025-26_regular_season.csv"
    players = pd.read_csv(path)
    players = players[players.player_id.ne(4)]
    players.to_csv(path, index=False)
    with pytest.raises(ValueError, match="identity unresolved"):
        backfill("2025-26", root=nba_rows, source="report", limit=1)
    assert not (nba_rows / "raw/player_game_availability/2025-26_regular_season.csv").exists()
