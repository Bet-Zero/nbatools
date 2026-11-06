"""Required bounded consumers without a qualified interval ledger in their stage.

No NBA acquisition, publication, or synthetic membership data. The three scoped
answers use exact-game association on every selected game. The ordinary combined
season positive is unavailable in THIS source-only stage. A separately qualified
full-season stage is checked by cloud_poeltl_full_season_real_data.py.
"""

import hashlib
import json
from pathlib import Path
from zipfile import ZipFile

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from nbatools.api import app
from nbatools.commands.pipeline import pull_games, pull_player_game_stats, pull_team_game_stats
from nbatools.commands.pipeline.pull_player_game_availability import validate_publication
from nbatools.commands.pipeline.structured_participation import stage_structured_game
from nbatools.commands.pipeline.validate_raw import validate_team_game_stats_df
from nbatools.data_source import data_path, reset_data_source_cache
from nbatools.query_service import execute_natural_query, execute_structured_query
from tools.cloud_nba_archive import PIN, _official_table

pytestmark = [pytest.mark.needs_data, pytest.mark.query]
EVIDENCE = (
    Path(__file__).resolve().parents[1]
    / "working/nba-tools-completion-program/source-evidence/multi-team-absence-20261106"
)
ZIP_SHA = "6e4b06650519da0b9bfc46269fff5e4f0c231949d8922585e7f4590fbac9d6a1"
MISSED = {22200247, 22200319, 22200333, 22200345, 22200375, 22200387, 22200406, 22200420, 22200591}


def build_native_stage(destination, monkeypatch):
    """Replay retained originals through unchanged producers and qualifiers."""
    archive = EVIDENCE / "archive-originals.zip"
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == ZIP_SHA
    sources = destination / "originals"
    sources.mkdir(parents=True)
    with ZipFile(archive) as zipped:
        assert len(zipped.infolist()) == len(set(zipped.namelist())) == 22
        assert sum(item.file_size for item in zipped.infolist()) < 20_000_000
        for item in zipped.infolist():
            relative = Path(item.filename)
            assert not relative.is_absolute() and ".." not in relative.parts
            assert relative.suffix == ".json" and item.file_size <= 8_000_000
            target = sources / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(zipped.read(item))
    for key, record in json.loads((sources / "receipt.json").read_bytes()).items():
        if key == "captured_at":
            continue
        assert (
            hashlib.sha256((sources / f"{key}.json").read_bytes()).hexdigest() == record["sha256"]
        )
    pairs = json.loads((sources / "pairs/receipt.json").read_bytes())
    for filename, record in pairs.items():
        raw = (sources / "pairs" / filename).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == record["sha256"]
        assert record["url"].startswith(
            f"https://raw.githubusercontent.com/sportsdataverse/hoopR-nba-stats-raw/{PIN}/"
        )
    teams = _official_table(sources / "teams.json", "LeagueGameFinderResults")
    teams = teams.loc[
        teams.SEASON_ID.astype(str).eq("22022") & teams.GAME_ID.astype(str).str.startswith("002")
    ]
    players = _official_table(sources / "players.json", "LeagueGameLog")
    assert players.SEASON_ID.astype(str).eq("22022").all()
    assert len(teams) == 2460 and not teams.duplicated(["GAME_ID", "TEAM_ID"]).any()
    assert len(players) == 25895 and not players.duplicated(["GAME_ID", "PLAYER_ID"]).any()
    root = destination / "native-stage"
    root.mkdir()
    with monkeypatch.context() as local:
        local.chdir(root)
        for module, frame in (
            (pull_games, teams),
            (pull_team_game_stats, teams),
            (pull_player_game_stats, players),
        ):
            module.run("2022-23", "Regular Season", raw_frame=frame)
    data = root / "data"
    for gid in sorted(MISSED):
        stem = f"{gid:010d}"
        rows = stage_structured_game(
            data,
            season="2022-23",
            season_type="Regular Season",
            game_id=gid,
            traditional=sources / "pairs" / f"boxscoretraditionalv3_{stem}.json",
            summary=sources / "pairs" / f"boxscoresummaryv2_{stem}.json",
            summary_version=2,
            revision=PIN,
            retrieved_at=pairs[f"boxscoretraditionalv3_{stem}.json"]["retrieved_at"],
        )
        target = rows.loc[rows.player_id.eq(1627751)]
        assert len(target) == 1 and target.participation_state.item() == "did_not_play"
        assert target.team_id.item() == 1610612759
    suffix = "2022-23_regular_season.csv"
    canonical = pd.read_csv(data / "raw/team_game_stats" / suffix)
    validate_team_game_stats_df(canonical, games=pd.read_csv(data / "raw/games" / suffix))
    validate_publication(data)
    people = pd.read_csv(data / "raw/player_game_stats" / suffix)
    metadata = data / "metadata"
    metadata.mkdir()
    people[["player_id", "player_name", "season"]].drop_duplicates().to_csv(
        metadata / "player_names.csv", index=False
    )
    return root, canonical, people


def _ids(result):
    assert result.result_status == "ok", result.metadata
    return {int(row["game_id"]) for row in result.to_dict()["sections"].get("finder", [])}


def test_native_exact_game_date_scopes_and_single_club_control(tmp_path, monkeypatch):
    # The hosted execution additionally authenticates its existing published base;
    # local replay is useful but is not relabeled as an R2 execution.
    base_manifest = None
    if __import__("os").environ.get("DATA_SOURCE") == "r2":
        base_manifest = hashlib.sha256(
            data_path("data/metadata/generation_manifest.json").read_bytes()
        ).hexdigest()
        assert base_manifest == "3073653a50872a4c25bb573c3b4c0540e6e3204e8a4caef5c548eb2dff1e0cf3"
    root, teams, players = build_native_stage(tmp_path, monkeypatch)
    monkeypatch.setenv("DATA_SOURCE", "local")
    monkeypatch.setenv("NBATOOLS_DATA_ROOT", str(root))
    monkeypatch.setenv("NBATOOLS_DATA_GENERATION", "legacy")
    reset_data_source_cache()
    try:
        sas = teams.loc[teams.team_abbr.eq("SAS") & teams.game_date.le("2023-02-08")]
        tor = teams.loc[teams.team_abbr.eq("TOR") & teams.game_date.ge("2023-02-10")]
        person = players.loc[players.player_id.eq(1627751)]
        assert len(sas) == 55 and len(tor) == 26
        assert set(sas.game_id) - set(person.game_id) == MISSED
        assert set(tor.game_id) <= set(person.game_id)
        cases = [
            (
                "How many games did Jakob Poeltl miss for the Spurs in 2022-23 before February 9, 2023?",
                "SAS",
                None,
                "2023-02-08",
                MISSED,
            ),
            (
                "How many games did Jakob Poeltl miss for the Raptors in 2022-23 from February 10 to April 9, 2023?",
                "TOR",
                "2023-02-10",
                "2023-04-09",
                set(),
            ),
        ]
        receipts = []
        client = TestClient(app)
        for question, club, start, end, expected in cases:
            answer = execute_natural_query(question)
            assert _ids(answer) == expected
            assert answer.to_dict()["sections"]["count"] == [{"count": len(expected)}]
            response = client.post("/query", json={"query": question})
            assert response.status_code == 200 and response.json()["result_status"] == "ok", (
                response.json()
            )
            assert response.json()["result"]["sections"]["count"] == [{"count": len(expected)}]
            structured = execute_structured_query(
                "game_finder",
                season="2022-23",
                team=club,
                membership_player="Jakob Poeltl",
                start_date=start,
                end_date=end,
                limit=1000,
            )
            if expected:
                assert _ids(structured) == expected
            else:
                assert structured.result_reason == "no_match"
                assert structured.result.metadata["membership_coverage"]["missed_games"] == 0
            receipts.append(
                dict(
                    query=question,
                    game_ids=sorted(expected),
                    count=len(expected),
                    answer=answer.metadata["answer_phrase"],
                )
            )
        # A complete, independently selected single-club population: all82 exact
        # appearances. This requires no inference from missing player rows.
        looney = players.loc[players.player_id.eq(1626172)]
        warriors = teams.loc[teams.team_abbr.eq("GSW")]
        assert len(looney) == len(warriors) == 82 and set(looney.game_id) == set(warriors.game_id)
        control = execute_natural_query("How many games did Kevon Looney miss in 2022-23?")
        assert control.result_status == "ok" and control.to_dict()["sections"]["count"] == [
            {"count": 0}
        ]
        # Missing-ledger control only; the separately qualified stage remains positive.
        full = execute_natural_query("How many games did Jakob Poeltl miss in 2022-23?")
        assert full.result_status == "no_result" and full.result_reason == "no_data"
        assert full.result.metadata["membership_coverage"]["missed_games"] is None
        output = (
            Path(
                __import__("os").environ.get(
                    "NBATOOLS_ACQUISITION_OUTPUT", str(tmp_path / "evidence")
                )
            )
            / "multi-team-absence"
        )
        output.mkdir(parents=True, exist_ok=True)
        (output / "bounded-acceptance.json").write_text(
            json.dumps(
                dict(
                    native_source_zip_sha256=ZIP_SHA,
                    base_manifest=base_manifest,
                    answers=receipts,
                    single_club_control=dict(player="Kevon Looney", played=82, missed=0),
                    ordinary_combined_season_positive="unavailable in this source-only stage; see separately qualified full-season acceptance",
                    full_season_nba_acceptance=False,
                    production_writes=0,
                ),
                indent=2,
            )
            + "\n"
        )
    finally:
        reset_data_source_cache()
