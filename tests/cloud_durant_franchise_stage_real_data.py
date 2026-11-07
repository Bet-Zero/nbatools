"""Qualify the original full Seattle/Durant population on a pinned base, offline."""

import hashlib
import json
import os
from pathlib import Path
from zipfile import ZipFile

import pandas as pd
import pytest

from nbatools.commands.pipeline.pull_player_game_availability import validate_publication
from nbatools.data_source import data_generation_context, data_path, reset_data_source_cache
from nbatools.query_service import execute_natural_query, execute_structured_query
from tests.cloud_reported_rest_stage_real_data import _capture, _write_inventory
from tests.test_c2_franchise_identity_real_data import (
    ID44_EVIDENCE,
    assert_durant_record,
    qualified_durant_population,
)
from tests.test_c2_franchise_identity_real_data import (
    test_thunder_record_with_durant_in_2007_08_keeps_his_seattle_games as _test_with,
)
from tests.test_c2_franchise_identity_real_data import (
    test_thunder_record_without_durant_in_2007_08_is_seattle_games_he_missed as _test_without,
)
from tools.participation_coverage import build_report
from tools.stage_participation_collection import build_stage

pytestmark = [pytest.mark.needs_data, pytest.mark.engine]
BASE = "availability-lebron-season-v1-20261031"
MANIFEST = "3073653a50872a4c25bb573c3b4c0540e6e3204e8a4caef5c548eb2dff1e0cf3"
SUFFIX = "2007-08_regular_season.csv"


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _table(archive, name):
    doc = json.loads(archive.read("sources/" + name))
    table = doc["resultSets"][0]
    assert len(table["headers"]) == len(set(table["headers"]))
    return pd.DataFrame(table["rowSet"], columns=table["headers"])


def test_durant_full_population_and_original_franchise_consumers(tmp_path, monkeypatch):
    request = ID44_EVIDENCE.parents[1] / "collection-requests/sea-durant-participation-2007-08.json"
    output = Path(os.environ["NBATOOLS_ACQUISITION_OUTPUT"]) / "durant-franchise-stage"
    with data_generation_context() as generation:
        assert generation == BASE
        raw = data_path("data/metadata/generation_manifest.json").read_bytes()
        assert _sha(raw) == MANIFEST
        manifest = json.loads(raw)
        entries = {item["path"]: item for item in manifest["files"]}
        # The canonical catalog/schedule supplies the same full82 denominator;
        # archive file existence alone is not completeness.
        extra = {}
        for path in [f"raw/schedule/{SUFFIX}"]:
            item = entries[path]
            body = data_path("data/" + path).read_bytes()
            assert len(body) == item["size_bytes"] and _sha(body) == item["sha256"]
            extra[path] = body
        validation = build_stage(
            request_path=request,
            source_directory=ID44_EVIDENCE / "pair-sources",
            work=tmp_path / "stage",
            output=output,
            candidate_sha=os.environ["VALIDATION_SHA"],
        )
    root = tmp_path / "stage/data"
    for relative, body in extra.items():
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(body)
    validate_publication(root)
    assert len(pd.read_csv(root / f"raw/player_game_availability/{SUFFIX}")) == 57
    assert (
        _sha((ID44_EVIDENCE / "originals.zip").read_bytes())
        == "4c320f48fc82396ff2f1c3700208f70b347084d00b8e9664f14a97c3cfc8ba43"
    )
    with ZipFile(ID44_EVIDENCE / "originals.zip") as archive:
        receipts = json.loads(archive.read("log-source-receipts.json"))
        for receipt in receipts:
            body = archive.read("sources/" + receipt["url"].rsplit("/", 1)[1])
            assert len(body) == receipt["bytes"] and _sha(body) == receipt["sha256"]
            assert (
                hashlib.sha1(b"blob " + str(len(body)).encode() + b"\0" + body).hexdigest()
                == receipt["git_blob_sha"]
            )
        source_teams = _table(archive, "regular-season.json")
        source_players = _table(archive, "regular-season_p.json")
    # Full82 final fixture identities, date/venue/reciprocal sides, and outcomes.
    team = pd.read_csv(root / f"raw/team_game_stats/{SUFFIX}")
    own = team.loc[team.team_id.eq(1610612760)]
    source = source_teams.loc[source_teams.TEAM_ID.eq(1610612760)]
    assert len(own) == len(source) == own.game_id.nunique() == 82
    source = source.assign(game_id=pd.to_numeric(source.GAME_ID)).set_index("game_id")
    catalog = pd.read_csv(root / f"raw/games/{SUFFIX}").set_index("game_id")
    schedule = pd.read_csv(root / f"raw/schedule/{SUFFIX}").set_index("game_id")
    for row in own.itertuples():
        fact = source.loc[int(row.game_id)]
        assert (row.game_date, row.team_abbr, row.wl, row.pts) == (
            fact.GAME_DATE,
            fact.TEAM_ABBREVIATION,
            fact.WL,
            fact.PTS,
        )
        pair = team.loc[team.game_id.eq(row.game_id)]
        assert len(pair) == 2 and pair.team_id.nunique() == 2
        other = pair.loc[~pair.team_id.eq(row.team_id)].iloc[0]
        logged_pair = source_teams.loc[pd.to_numeric(source_teams.GAME_ID).eq(row.game_id)]
        assert len(logged_pair) == 2 and logged_pair.TEAM_ID.nunique() == 2
        for side in pair.itertuples():
            original = logged_pair.loc[logged_pair.TEAM_ID.eq(side.team_id)]
            assert len(original) == 1
            original = original.iloc[0]
            assert (side.team_abbr, side.game_date, side.wl, side.pts) == (
                original.TEAM_ABBREVIATION,
                original.GAME_DATE,
                original.WL,
                original.PTS,
            )
        assert fact.MATCHUP.split()[-1] == other.team_abbr
        assert row.opponent_team_id == other.team_id and other.opponent_team_id == row.team_id
        assert row.wl != other.wl and ((row.pts > other.pts) == (row.wl == "W"))
        game, planned = catalog.loc[row.game_id], schedule.loc[row.game_id]
        assert not isinstance(game, pd.DataFrame) and not isinstance(planned, pd.DataFrame)
        assert str(game.is_final).lower() in {"true", "1"}
        assert game.game_date == planned.game_date == row.game_date
        home = 1610612760 if " vs. " in fact.MATCHUP else int(other.team_id)
        away = int(other.team_id) if home == 1610612760 else 1610612760
        assert (int(game.home_team_id), int(game.away_team_id)) == (home, away)
        assert (int(planned.home_team_id), int(planned.away_team_id)) == (home, away)
    canonical_players = pd.read_csv(root / f"raw/player_game_stats/{SUFFIX}")
    played = canonical_players.loc[canonical_players.player_id.eq(201142)].copy()
    logged = source_players.loc[source_players.PLAYER_ID.eq(201142)].copy()
    assert len(played) == len(logged) == 80
    logged = logged.assign(game_id=pd.to_numeric(logged.GAME_ID)).set_index("game_id")
    for row in played.itertuples():
        fact = logged.loc[int(row.game_id)]
        assert (row.game_date, row.team_id, row.team_abbr, row.pts, row.reb, row.ast) == (
            fact.GAME_DATE,
            fact.TEAM_ID,
            fact.TEAM_ABBREVIATION,
            fact.PTS,
            fact.REB,
            fact.AST,
        )
        assert row.minutes > 0 and fact.MIN > 0
    receipt = dict(
        candidate_sha=os.environ["VALIDATION_SHA"],
        base_generation=BASE,
        base_manifest_sha256=MANIFEST,
        validation=validation,
        source_root_validation="passed",
        canonical_schedule_sha256=_sha(extra[f"raw/schedule/{SUFFIX}"]),
        source_oracle_sha256=_sha(
            (ID44_EVIDENCE / "independent/source-qualified-oracle.json").read_bytes()
        ),
        production_writes=0,
        nba_source_requests=0,
        deployed_acceptance=False,
        full_core1_accepted=False,
        answers=[],
        consumer_acceptance="pending",
    )
    try:
        _write_inventory(root)
        with monkeypatch.context() as isolated:
            isolated.setenv("DATA_SOURCE", "local")
            isolated.setenv("NBATOOLS_DATA_ROOT", str(root.parent))
            isolated.setenv("NBATOOLS_DATA_GENERATION", "legacy")
            reset_data_source_cache()
            oracle = qualified_durant_population()
            receipt["coverage"] = build_report(
                generation="legacy",
                manifest_sha256=_sha((root / "metadata/generation_manifest.json").read_bytes()),
                season="2007-08",
                team_id=1610612760,
                player_id=201142,
            )
            coverage = receipt["coverage"]
            assert coverage["complete_requested_population"] and not coverage["missing_keys"]
            assert coverage["counts"] == dict(
                played=80, did_not_play=2, same_game_other_side=0, unknown=0
            )
            assert {int(r["game_id"]): r["state"] for r in coverage["games"]} == {
                int(r["game_id"]): r["state"] for r in oracle["population"]
            }
            _test_without()
            _test_with()
            for text, polarity, franchise in [
                (
                    "How did the Thunder do in 2007-08 when Kevin Durant did not play?",
                    "without",
                    True,
                ),
                ("Thunder record in 2007-08 with Kevin Durant playing", "with", True),
                ("Seattle SuperSonics record without Kevin Durant in 2007-08", "without", False),
                ("Seattle record with Kevin Durant in 2007-08", "with", False),
            ]:
                result = execute_natural_query(text)
                assert_durant_record(result, oracle["expected"][polarity], franchise=franchise)
                receipt["answers"].append(dict(query=text, actual=_capture(result)))
            from fastapi.testclient import TestClient

            from nbatools.api import app

            client = TestClient(app)
            for polarity in ("with", "without"):
                kwargs = dict(
                    team="OKC", season="2007-08", **{f"{polarity}_player": "Kevin Durant"}
                )
                result = execute_structured_query("team_record", **kwargs)
                assert_durant_record(result, oracle["expected"][polarity])
                response = client.post(
                    "/query", json={"query": f"Thunder record {polarity} Kevin Durant in 2007-08"}
                )
                body = response.json()
                assert response.status_code == 200 and body["result_status"] == "ok"
                selected = [int(r["game_id"]) for r in body["result"]["sections"]["game_log"]]
                assert len(selected) == len(set(selected)) == oracle["expected"][polarity]["games"]
                assert set(selected) == {int(g) for g in oracle["expected"][polarity]["game_ids"]}
                receipt["answers"].append(
                    dict(command="team_record", kwargs=kwargs, actual=_capture(result), http=body)
                )
            receipt["consumer_acceptance"] = "passed"
    except Exception as exc:
        receipt["consumer_acceptance"] = "failed"
        receipt["failure"] = dict(type=type(exc).__name__, message=str(exc))
        raise
    finally:
        reset_data_source_cache()
        (output / "acceptance.json").write_text(json.dumps(receipt, indent=2) + "\n")
