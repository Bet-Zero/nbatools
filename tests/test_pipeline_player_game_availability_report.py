"""NBA final scorer's PDF is explicit game-day status, not inferred absence."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

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


def _profile_html(ident=99, name="Alex Toohey"):
    first, _, last = name.partition(" ")
    info = dict(
        PERSON_ID=ident,
        FIRST_NAME=first,
        LAST_NAME=last,
        DISPLAY_FIRST_LAST=name,
        TEAM_ID=999,
        ROSTERSTATUS="Active",
    )
    payload = dict(props=dict(pageProps=dict(player=dict(info=info))))
    return (
        '<script id="__NEXT_DATA__" type="application/json">' + json.dumps(payload) + "</script>"
    ).encode()


def test_profile_structure_checks_id_name_and_ignores_current_status():
    from nbatools.commands.pipeline.player_game_availability_profiles import profile_identity

    assert profile_identity(_profile_html(), 99, "Alex Toohey") == "Alex Toohey"
    for ident, name in ((100, "Alex Toohey"), (99, "Different Person")):
        with pytest.raises(ValueError, match="differs"):
            profile_identity(_profile_html(), ident, name)
    with pytest.raises(ValueError, match="structured"):
        profile_identity(b"<title>Alex Toohey</title>", 99, "Alex Toohey")


def test_profile_fallback_retains_source_and_blocks_corrupt_publication(nba_rows, monkeypatch):
    import io
    import urllib.error

    from nba_api.stats.static import players

    from nbatools.commands.pipeline.pull_player_game_availability import validate_publication

    def unavailable(*a, **k):
        raise urllib.error.HTTPError("https://cdn.nba.com", 403, "Forbidden", {}, None)

    def pdf(url, *, archive):
        report._archive_report(b"%PDF controlled profile fixture", url, archive)
        return PDF_TEXT.replace("Moody (", "Toohey (")

    monkeypatch.setattr(report, "_fetch_live_identities", unavailable)
    monkeypatch.setattr(report, "_fetch_report_text", pdf)
    monkeypatch.setattr(players, "get_players", lambda: [dict(id=99, full_name="Alex Toohey")])
    monkeypatch.setattr(
        report.urllib.request, "urlopen", lambda *a, **k: io.BytesIO(_profile_html())
    )
    rows = backfill("2025-26", root=nba_rows, source="report")
    player = rows[rows.player_id.eq(99)].iloc[0]
    assert player.team_id == 1  # current profile deliberately names team999
    assert player.participation_state == "did_not_play"
    assert len(rows) == 6
    validate_publication(nba_rows)
    source = nba_rows / "raw/player_game_availability_sources"
    html = next(source.glob("*.profile.html"))
    html.write_bytes(b"changed")
    with pytest.raises(ValueError, match="receipt/bytes"):
        validate_publication(nba_rows)


def test_profile_candidate_ambiguity_never_fetches(nba_rows, monkeypatch):
    from nba_api.stats.static import players

    from nbatools.commands.pipeline.player_game_availability_profiles import fetch_profile_for_name

    monkeypatch.setattr(
        players,
        "get_players",
        lambda: [dict(id=99, full_name="Alex Toohey"), dict(id=100, full_name="Other Toohey")],
    )
    with pytest.raises(ValueError, match="unique"):
        fetch_profile_for_name("Toohey", 1, True, nba_rows)


def test_inactive_surname_preserves_compound_name_and_true_ambiguity():
    people = pd.DataFrame(
        [
            dict(team_id=2, player_id=10, player_name="Nick Smith Jr."),
            dict(team_id=2, player_id=20, player_name="Dorian Finney-Smith"),
        ]
    )
    people["normalized"] = people.player_name.map(report._name)
    assert report._identify(people, 2, "Smith Jr.", set(), surname=True) == (10, "Nick Smith Jr.")
    assert report._identify(people, 2, "Finney-Smith", set(), surname=True) == (
        20,
        "Dorian Finney-Smith",
    )
    another = pd.DataFrame(
        [dict(team_id=2, player_id=30, player_name="Dennis Smith Jr.", normalized="dennis smith")]
    )
    with pytest.raises(ValueError, match="candidate IDs=2"):
        report._identify(pd.concat([people, another]), 2, "Smith Jr.", set(), surname=True)


@pytest.mark.parametrize(
    "heading", ["SCORE BY PERIOD", "SCORE BYPERIOD", "SCORE  BY  PERIOD", "SCORE BY PERIODCeltics"]
)
def test_report_scoreboard_tolerates_pdf_word_spacing(heading):
    text = PDF_TEXT.replace("SCORE BY PERIOD", heading)
    names, sections, _ = report._parse_sections(text, "2025-10-21")
    assert names == ["Golden State Warriors", "LOS ANGELES LAKERS"]
    assert [report._score(section) for section in sections] == [119, 109]
    assert not any(heading in line for section in sections for line in section)


def test_report_without_scoreboard_still_rejected():
    with pytest.raises(ValueError, match="missing scoreboard"):
        report._parse_sections(PDF_TEXT.replace("SCORE BY PERIOD", "UNRECOGNIZED"), "2025-10-21")


@pytest.fixture
def retained_report(tmp_path):
    source = (
        Path(__file__).resolve().parents[1]
        / "working/nba-tools-completion-program/source-evidence/tatum-20260201"
        / "acquired_data/raw/player_game_availability_sources"
    )
    cache = tmp_path / "retained"
    shutil.copytree(source, cache)
    return cache


def _no_network(*args, **kwargs):
    raise AssertionError("Cached report replay must not use the network")


def test_cached_original_replays_without_network_or_new_capture_time(
    retained_report, tmp_path, monkeypatch
):
    monkeypatch.setattr(report.urllib.request, "urlopen", _no_network)
    url = "https://statsdmz.nba.com/pdfs/20260201/20260201_MILBOS.pdf"
    archive = tmp_path / "archive"
    text = report._cached_report_text(url, retained_report, archive)
    names, sections, _ = report._parse_sections(text, "2026-02-01")
    assert [name.casefold() for name in names] == ["milwaukee bucks", "boston celtics"]
    assert [report._score(section) for section in sections] == [79, 107]
    receipt = json.loads((archive / "20260201_MILBOS.json").read_text())
    for name in ("20260201_MILBOS.json", receipt["raw_file"]):
        assert (archive / name).read_bytes() == (retained_report / name).read_bytes()


@pytest.mark.parametrize("damage", ["url", "path", "sha", "time", "size", "bytes", "missing"])
def test_cached_report_corruption_never_falls_back_online(
    retained_report, tmp_path, monkeypatch, damage
):
    monkeypatch.setattr(report.urllib.request, "urlopen", _no_network)
    path = retained_report / "20260201_MILBOS.json"
    receipt = json.loads(path.read_text())
    if damage == "url":
        receipt["source_url"] = receipt["source_url"].replace("MILBOS", "BOSMIL")
    elif damage == "path":
        receipt["raw_file"] = "../outside.pdf"
    elif damage == "sha":
        receipt["sha256"] = "invalid"
    elif damage == "time":
        receipt["retrieved_at"] = "2026-10-18T21:28:17"
    elif damage == "size":
        receipt["size_bytes"] += 1
    elif damage == "bytes":
        (retained_report / receipt["raw_file"]).write_bytes(b"%PDF changed")
    else:
        (retained_report / receipt["raw_file"]).unlink()
    path.write_text(json.dumps(receipt))
    archive = tmp_path / "archive"
    with pytest.raises((ValueError, FileNotFoundError)):
        report._cached_report_text(
            receipt["source_url"]
            if damage != "url"
            else "https://statsdmz.nba.com/pdfs/20260201/20260201_MILBOS.pdf",
            retained_report,
            archive,
        )
    assert not archive.exists()


def test_cached_import_uses_receipt_and_refuses_unresolved_identity(
    nba_rows, tmp_path, monkeypatch
):
    cache = tmp_path / "cache"
    report._archive_report(
        b"%PDF controlled importer fixture",
        "https://statsdmz.nba.com/pdfs/20251021/20251021_GSWLAL.pdf",
        cache,
    )
    monkeypatch.setattr(report, "_report_text", lambda _: PDF_TEXT)
    monkeypatch.setattr(report.urllib.request, "urlopen", _no_network)
    monkeypatch.setattr(report, "_fetch_live_identities", _no_network)
    rows = backfill("2025-26", root=nba_rows, source="report", cached_reports=cache)
    assert len(rows) == 6
    assert rows.source_sha256.eq(
        hashlib.sha256(b"%PDF controlled importer fixture").hexdigest()
    ).all()
    path = nba_rows / "raw/player_game_stats/2025-26_regular_season.csv"
    players = pd.read_csv(path)
    players.loc[players.player_id.ne(4)].to_csv(path, index=False)
    with pytest.raises(report.UnresolvedIdentity):
        report.official_report_as_v3(
            game_id=22500002,
            game_date="2025-10-21",
            season="2025-26",
            season_type="Regular Season",
            home_team_id=2,
            away_team_id=1,
            data_root=nba_rows,
            cached_reports=cache,
        )


def test_cached_report_option_rejects_other_sources(tmp_path):
    with pytest.raises(ValueError, match="Cached reports only"):
        backfill("2025-26", source="stats", cached_reports=tmp_path)


@pytest.mark.parametrize("change", ["corrupt", "missing", "revised"])
def test_cached_repeat_import_revalidates_supplied_source(nba_rows, tmp_path, monkeypatch, change):
    cache = tmp_path / "cache"
    url = "https://statsdmz.nba.com/pdfs/20251021/20251021_GSWLAL.pdf"
    report._archive_report(b"%PDF first controlled source", url, cache)
    monkeypatch.setattr(report, "_report_text", lambda _: PDF_TEXT)
    monkeypatch.setattr(report.urllib.request, "urlopen", _no_network)
    first = backfill("2025-26", root=nba_rows, source="report", cached_reports=cache)
    target = nba_rows / "raw/player_game_availability/2025-26_regular_season.csv"
    previous = target.read_bytes()
    receipt = json.loads((cache / "20251021_GSWLAL.json").read_text())
    pdf = cache / receipt["raw_file"]
    if change == "revised":
        content = b"%PDF revised controlled source"
        report._archive_report(content, url, cache)
        replayed = backfill("2025-26", root=nba_rows, source="report", cached_reports=cache)
        assert replayed.source_sha256.eq(hashlib.sha256(content).hexdigest()).all()
        assert not replayed.source_sha256.equals(first.source_sha256)
    else:
        if change == "missing":
            pdf.unlink()
        else:
            pdf.write_bytes(b"%PDF corrupt source")
        with pytest.raises((ValueError, FileNotFoundError)):
            backfill("2025-26", root=nba_rows, source="report", cached_reports=cache)
        assert target.read_bytes() == previous


def _controlled_retained_cache(tmp_path, monkeypatch, text=PDF_TEXT):
    cache = tmp_path / "controlled-cache"
    report._archive_report(
        b"%PDF controlled importer fixture",
        "https://statsdmz.nba.com/pdfs/20251021/20251021_GSWLAL.pdf",
        cache,
    )
    monkeypatch.setattr(report, "_report_text", lambda _: text)
    monkeypatch.setattr(report.urllib.request, "urlopen", _no_network)
    return cache


@pytest.mark.parametrize("scope", [[], [3], [2, 2], ["2"], [True]])
def test_explicit_report_scope_rejects_invalid_teams(nba_rows, tmp_path, monkeypatch, scope):
    cache = _controlled_retained_cache(tmp_path, monkeypatch)
    with pytest.raises(ValueError):
        backfill(
            "2025-26", root=nba_rows, source="report", cached_reports=cache, imported_team_ids=scope
        )
    assert not list((nba_rows / "raw/player_game_availability").glob("*.csv"))


@pytest.mark.parametrize(
    "damage",
    [
        "away_score",
        "home_score",
        "away_inactive_team",
        "selected_identity",
        "missing_played",
        "duplicate_dnp",
    ],
)
def test_team_scope_keeps_envelope_and_selected_identity_checks(
    nba_rows, tmp_path, monkeypatch, damage
):
    text = PDF_TEXT
    if damage == "away_score":
        text = text.replace("240:00 38 78 17 40 119", "240:00 38 78 17 40 118")
    elif damage == "home_score":
        text = text.replace("240:00 42 77 8 32 109", "240:00 42 77 8 32 108")
    elif damage == "away_inactive_team":
        text = text.replace("Inactive: Warriors -", "Inactive: Celtics -")
    elif damage == "selected_identity":
        text = text.replace("9 Bronny James DNP", "9 Unknown Person DNP")
    elif damage == "missing_played":
        text = text.replace("77 Luka Doncic G 40:59 17 27 43\n", "")
    else:
        text = text.replace(
            "9 Bronny James DNP", "9 Bronny James DNP - Coach's Decision\n9 Bronny James DNP"
        )
    cache = _controlled_retained_cache(tmp_path, monkeypatch, text)
    with pytest.raises(ValueError):
        backfill(
            "2025-26", root=nba_rows, source="report", cached_reports=cache, imported_team_ids=[2]
        )
    assert not list((nba_rows / "raw/player_game_availability").glob("*.csv"))


def test_scoped_refresh_cannot_delete_existing_other_team_evidence(nba_rows, tmp_path, monkeypatch):
    from nbatools.commands.pipeline.pull_player_game_availability import validate_publication

    cache = _controlled_retained_cache(tmp_path, monkeypatch)
    backfill("2025-26", root=nba_rows, source="report", cached_reports=cache)
    target = nba_rows / "raw/player_game_availability/2025-26_regular_season.csv"
    receipts = target.with_suffix(".imports.json")
    before = target.read_bytes(), receipts.read_bytes()
    validate_publication(nba_rows)  # Existing full-game receipt remains valid.
    with pytest.raises(ValueError, match="outside-scope"):
        backfill(
            "2025-26", root=nba_rows, source="report", cached_reports=cache, imported_team_ids=[2]
        )
    assert (target.read_bytes(), receipts.read_bytes()) == before
    validate_publication(nba_rows)


def test_explicit_team_scope_requires_offline_report(nba_rows):
    with pytest.raises(ValueError, match="retained official report"):
        backfill("2025-26", root=nba_rows, source="report", imported_team_ids=[2])
    with pytest.raises(ValueError, match="retained official report"):
        backfill("2025-26", root=nba_rows, source="stats", imported_team_ids=[2])


def test_explicit_inactive_with_unreported_reason_is_not_dropped():
    # Actual Oct26,2025 Kings report: Stevens (). The enclosing inactive list
    # establishes nonparticipation; empty parentheses establish no medical cause.
    assert report._split_inactives("Stevens ()") == [("Stevens", "INACTIVE - ")]
    with pytest.raises(ValueError):
        report._split_inactives("Stevens (")
