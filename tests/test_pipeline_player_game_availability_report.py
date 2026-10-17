"""NBA final scorer's PDF is explicit game-day status, not inferred absence."""

from __future__ import annotations

import hashlib
import json

import pandas as pd
import pytest

from nbatools.commands.pipeline import player_game_availability_report as report
from nbatools.commands.pipeline.pull_player_game_availability import (
    backfill,
    normalize_boxscore_availability,
)

pytestmark = pytest.mark.engine

_DOWNLOAD_IDENTITIES = report._fetch_live_identities

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
            dict(
                game_id="0022500002",
                game_date="2025-10-21",
                season="2025-26",
                season_type="Regular Season",
                is_final=True,
                home_team_id=2,
                away_team_id=1,
            )
        ]
    ).to_csv(root / "raw/games/2025-26_regular_season.csv", index=False)
    pd.DataFrame(
        [
            dict(
                game_id="0022500002",
                team_id=1,
                team_abbr="GSW",
                team_name="Golden State Warriors",
                pts=119,
            ),
            dict(
                game_id="0022500002",
                team_id=2,
                team_abbr="LAL",
                team_name="Los Angeles Lakers",
                pts=109,
            ),
        ]
    ).to_csv(root / "raw/team_game_stats/2025-26_regular_season.csv", index=False)
    pd.DataFrame(
        [
            dict(
                game_id="0022500002",
                team_id=1,
                player_id=30,
                player_name="Stephen Curry",
                minutes=32.0,
            ),
            dict(
                game_id="0022500002",
                team_id=2,
                player_id=77,
                player_name="Luka Doncic",
                minutes=40.0,
            ),
            dict(
                game_id="0022500003",
                team_id=1,
                player_id=32,
                player_name="Trayce Jackson-Davis",
                minutes=4.0,
            ),
            dict(
                game_id="0022500003",
                team_id=1,
                player_id=4,
                player_name="Moses Moody",
                minutes=10.0,
            ),
            dict(
                game_id="0022500003",
                team_id=2,
                player_id=9,
                player_name="Bronny James",
                minutes=5.0,
            ),
            dict(
                game_id="0022500003",
                team_id=2,
                player_id=23,
                player_name="LeBron James",
                minutes=30.0,
            ),
        ]
    ).to_csv(root / "raw/player_game_stats/2025-26_regular_season.csv", index=False)
    monkeypatch.setattr(report, "_fetch_report_text", lambda _, **kwargs: PDF_TEXT)
    monkeypatch.setattr(
        report,
        "_fetch_live_identities",
        lambda *args, **kwargs: (
            pd.DataFrame(columns=["team_id", "player_id", "player_name", "normalized"]),
            "a" * 64,
        ),
    )
    return root


def _get(root):
    return report.official_report_as_v3(
        game_id=22500002,
        game_date="2025-10-21",
        season="2025-26",
        season_type="Regular Season",
        home_team_id=2,
        away_team_id=1,
        data_root=root,
    )


def test_official_report_includes_dnp_and_inactive_with_date_qualification(nba_rows):
    raw, reference = _get(nba_rows)
    assert reference == "20251021_GSWLAL"
    selected = normalize_boxscore_availability(
        raw,
        game_id=22500002,
        game_date="2025-10-21",
        season="2025-26",
        season_type="Regular Season",
        expected_team_ids={1, 2},
        source=f"nba_official_finalbox:{reference}",
    )
    assert len(selected) == 6
    status = dict(zip(selected.player_id, selected.participation_state))
    assert status == {
        30: "played",
        32: "did_not_play",
        4: "did_not_play",
        77: "played",
        9: "did_not_play",
        23: "did_not_play",
    }
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
        (
            PDF_TEXT.replace("Inactive: Warriors - Moody", "Inactive: Warriors - Unknown"),
            "identity unresolved",
        ),
    ],
)
def test_mismatched_or_unresolved_pdf_source_refuses(nba_rows, monkeypatch, text, match):
    monkeypatch.setattr(report, "_fetch_report_text", lambda _, **kwargs: text)
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


def test_played_minutes_are_read_from_report_not_local_game_log(nba_rows):
    raw, _ = _get(nba_rows)
    assert raw.loc[raw.personId.eq(30), "minutes"].iloc[0] == "32:04"
    assert raw.loc[raw.personId.eq(77), "minutes"].iloc[0] == "40:59"


def test_missing_played_report_row_is_not_filled_from_local_stats(nba_rows, monkeypatch):
    text = PDF_TEXT.replace("30 Stephen Curry G 32:04 6 14 23\n", "")
    monkeypatch.setattr(report, "_fetch_report_text", lambda _, **kwargs: text)
    with pytest.raises(ValueError, match="played identities"):
        _get(nba_rows)


def test_original_report_receipt_preserves_bytes_url_and_checksum(tmp_path):
    content = b"%PDF synthetic receipt storage fixture"
    url = "https://statsdmz.nba.com/pdfs/20251021/20251021_GSWLAL.pdf"
    report._archive_report(content, url, tmp_path)
    receipt = json.loads((tmp_path / "20251021_GSWLAL.json").read_text())
    assert receipt["source_url"] == url
    assert receipt["sha256"] == hashlib.sha256(content).hexdigest()
    assert receipt["size_bytes"] == len(content)
    assert (tmp_path / receipt["raw_file"]).read_bytes() == content
    assert receipt["retrieved_at"]


def test_prior_season_resolves_identity_only_for_source_listed_inactive(nba_rows, monkeypatch):
    path = nba_rows / "raw/player_game_stats/2025-26_regular_season.csv"
    players = pd.read_csv(path)
    prior = players[players.player_id.eq(4)]
    prior.to_csv(nba_rows / "raw/player_game_stats/2024-25_regular_season.csv", index=False)
    players[players.player_id.ne(4)].to_csv(path, index=False)
    raw, _ = _get(nba_rows)
    assert raw.loc[raw.personId.eq(4), "comment"].iloc[0].startswith("INACTIVE")
    # Keeping the identity in old rows does not manufacture a missing report row.
    text = PDF_TEXT.replace("Moody (Injury/Illness - Left Soleus; Strain)", "NONE")
    monkeypatch.setattr(report, "_fetch_report_text", lambda _, **kwargs: text)
    raw, _ = _get(nba_rows)
    assert 4 not in raw.personId.tolist()


def _live_payload(root):
    canonical = pd.read_csv(root / "raw/player_game_stats/2025-26_regular_season.csv")
    teams = {}
    for side, ident, abbr, score in (("awayTeam", 1, "GSW", 119), ("homeTeam", 2, "LAL", 109)):
        players = []
        for row in canonical[canonical.team_id.eq(ident)].itertuples():
            first, _, last = row.player_name.partition(" ")
            players.append(dict(personId=row.player_id, firstName=first, familyName=last))
        teams[side] = dict(teamId=ident, teamTricode=abbr, score=score, players=players)
    teams["awayTeam"]["players"].append(dict(personId=99, firstName="Alex", familyName="Toohey"))
    return dict(
        game=dict(gameId="0022500002", gameStatus=3, gameTimeUTC="2025-10-22T02:00:00Z", **teams)
    )


def _live_scope():
    return dict(
        game_id=22500002,
        game_date="2025-10-21",
        home_team_id=2,
        away_team_id=1,
        by_id={1: ("GSW", 119), 2: ("LAL", 109)},
    )


def test_live_identity_supplies_only_source_listed_rookie(nba_rows, monkeypatch):
    payload = _live_payload(nba_rows)
    extra = report.live_identity_rows(payload, **_live_scope())
    monkeypatch.setattr(report, "_fetch_live_identities", lambda *a, **k: (extra, "a" * 64))
    monkeypatch.setattr(
        report, "_fetch_report_text", lambda *a, **k: PDF_TEXT.replace("Moody (", "Toohey (")
    )
    rows, _ = _get(nba_rows)
    assert rows[rows.personId.eq(99)].iloc[0]["comment"].startswith("INACTIVE")
    assert not rows.personId.eq(4).any()  # Moody is in identity index but not this PDF.
    assert rows.attrs["identity_source_sha256"] == "a" * 64


@pytest.mark.parametrize(
    "field,value",
    [
        ("gameId", "0022500003"),
        ("gameStatus", 2),
        ("gameTimeUTC", "2025-10-21T02:00:00Z"),
        ("gameTimeUTC", "2025-10-22T02:00:00"),
    ],
)
def test_live_identity_rejects_wrong_game(nba_rows, field, value):
    payload = _live_payload(nba_rows)
    payload["game"][field] = value
    with pytest.raises(ValueError):
        report.live_identity_rows(payload, **_live_scope())


@pytest.mark.parametrize("field,value", [("teamId", 2), ("score", 120), ("teamTricode", "BOS")])
def test_live_identity_rejects_wrong_team(nba_rows, field, value):
    payload = _live_payload(nba_rows)
    payload["game"]["awayTeam"][field] = value
    with pytest.raises(ValueError):
        report.live_identity_rows(payload, **_live_scope())


def test_live_identity_rejects_duplicate_and_conflicting_ids(nba_rows, monkeypatch):
    payload = _live_payload(nba_rows)
    players = payload["game"]["awayTeam"]["players"]
    players[-1]["personId"] = 30
    with pytest.raises(ValueError, match="Ambiguous"):
        report.live_identity_rows(payload, **_live_scope())
    players[-1]["personId"] = 99
    players[0]["personId"] = 999
    extra = report.live_identity_rows(payload, **_live_scope())
    monkeypatch.setattr(report, "_fetch_live_identities", lambda *a, **k: (extra, "a" * 64))
    monkeypatch.setattr(
        report, "_fetch_report_text", lambda *a, **k: PDF_TEXT.replace("Moody (", "Toohey (")
    )
    with pytest.raises(ValueError, match="conflicts"):
        _get(nba_rows)


def test_canonical_identities_do_not_fetch_live_source(nba_rows, monkeypatch):
    def unexpected(*a, **k):
        pytest.fail("Unnecessary identity source request")

    monkeypatch.setattr(report, "_fetch_live_identities", unexpected)
    _get(nba_rows)


def test_identity_download_retains_exact_bytes(nba_rows, monkeypatch):
    import io

    raw = json.dumps(_live_payload(nba_rows)).encode()
    monkeypatch.setattr(report.urllib.request, "urlopen", lambda *a, **k: io.BytesIO(raw))
    directory = nba_rows / "raw/player_game_availability_sources"
    rows, digest = _DOWNLOAD_IDENTITIES(directory, **_live_scope())
    receipt = json.loads((directory / f"{digest}.receipt.json").read_text())
    assert (directory / receipt["raw_file"]).read_bytes() == raw
    assert receipt["sha256"] == hashlib.sha256(raw).hexdigest()
    assert receipt["size_bytes"] == len(raw)
    assert rows.player_id.eq(99).any()


def test_live_identity_global_id_conflict_rejects_but_trade_is_valid(nba_rows, monkeypatch):
    path = nba_rows / "raw/player_game_stats/2025-26_regular_season.csv"
    canonical = pd.read_csv(path)
    extra = report.live_identity_rows(_live_payload(nba_rows), **_live_scope())
    monkeypatch.setattr(report, "_fetch_live_identities", lambda *a, **k: (extra, "a" * 64))
    monkeypatch.setattr(
        report, "_fetch_report_text", lambda *a, **k: PDF_TEXT.replace("Moody (", "Toohey (")
    )
    other = dict(
        game_id=22500003, team_id=2, player_id=99, player_name="Different Person", minutes=10
    )
    pd.concat([canonical, pd.DataFrame([other])]).to_csv(path, index=False)
    with pytest.raises(ValueError, match="conflicts"):
        _get(nba_rows)
    other["player_name"] = "Alex Toohey"
    pd.concat([canonical, pd.DataFrame([other])]).to_csv(path, index=False)
    rows, _ = _get(nba_rows)
    assert rows[rows.personId.eq(99)].iloc[0].teamId == 1
