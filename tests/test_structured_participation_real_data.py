"""Retained real structured sources: four eras, exact rows and public consumers."""

import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest

from nbatools.commands.pipeline.pull_player_game_availability import validate_publication
from nbatools.commands.pipeline.structured_participation import stage_structured_game
from nbatools.data_source import data_read_csv, reset_data_source_cache
from nbatools.query_service import execute_natural_query, execute_structured_query

pytestmark = [pytest.mark.needs_data, pytest.mark.engine]
EVIDENCE = (
    Path(__file__).resolve().parents[1]
    / "working/nba-tools-completion-program/source-evidence/k08-structured"
)
SOURCE = EVIDENCE / "sources"
PROVENANCE = json.loads((EVIDENCE / "sources.json").read_text())
# Expectations fixed separately from producer; checker rederives originals.
CASES = [
    ("1997-98", 29700002, "NJN", "Kerry Kittles", 24, 20, 97, 95),
    ("2004-05", 20400001, "DET", "Darko Milicic", 24, 21, 87, 79),
    ("2014-15", 21400001, "NOP", "Darius Miller", 30, 23, 101, 84),
    ("2025-26", 22500002, "LAL", "LeBron James", 34, 20, 109, 119),
]


def stage(tmp_path, season, gid, version=2):
    root = tmp_path / "data"
    suffix = f"{season}_regular_season.csv"
    for kind in ["games", "team_game_stats", "player_game_stats"]:
        target = root / "raw" / kind / suffix
        target.parent.mkdir(parents=True, exist_ok=True)
        data_read_csv("data/raw/" + kind + "/" + suffix).to_csv(target, index=False)
    paths = []
    for ep in ["boxscoretraditionalv3", f"boxscoresummaryv{version}"]:
        name = f"{ep}_{gid:010d}.json"
        record = PROVENANCE["files"][name]
        path = SOURCE / name
        assert hashlib.sha256(path.read_bytes()).hexdigest() == record["sha256"]
        assert path.stat().st_size == record["size_bytes"]
        paths.append(path)
    captured = max(PROVENANCE["files"][p.name]["retrieved_at"] for p in paths)
    rows = stage_structured_game(
        root,
        season=season,
        season_type="Regular Season",
        game_id=gid,
        traditional=paths[0],
        summary=paths[1],
        summary_version=version,
        revision=PROVENANCE["revision"],
        retrieved_at=captured,
    )
    return root, rows


@pytest.mark.parametrize("season,gid,team,person,count,played,points,opponent_points", CASES)
def test_retained_structured_game_and_answers(
    tmp_path, monkeypatch, season, gid, team, person, count, played, points, opponent_points
):
    root, rows = stage(tmp_path, season, gid)
    assert len(rows) == count and rows.participation_state.eq("played").sum() == played
    assert rows.participation_state.eq("did_not_play").sum() == count - played
    assert rows.coverage_scope.eq("listed_player_rows_only").all()
    assert rows.loc[rows.player_name.eq(person), "participation_state"].item() == "did_not_play"
    validate_publication(root)
    monkeypatch.setenv("DATA_SOURCE", "local")
    monkeypatch.setenv("NBATOOLS_DATA_ROOT", str(tmp_path))
    monkeypatch.setenv("NBATOOLS_DATA_GENERATION", "legacy")
    reset_data_source_cache()
    day = rows.game_date.iloc[0]
    for result in [
        execute_structured_query(
            "team_record",
            team=team,
            season=season,
            without_player=person,
            start_date=day,
            end_date=day,
        ),
        execute_natural_query(f"{team} record without {person} in {season} from {day} to {day}"),
    ]:
        assert result.result_status == "ok", result.metadata
        sections = result.result.to_dict()["sections"]
        summary = sections["summary"][0]
        assert (summary["games"], summary["wins"], summary["losses"], summary["pts_avg"]) == (
            1,
            int(points > opponent_points),
            int(points < opponent_points),
            points,
        )
        assert [int(r["game_id"]) for r in sections["game_log"]] == [gid]
        assert sections["game_log"][0]["opponent_pts"] == opponent_points
    wider = execute_structured_query("team_record", team=team, season=season, without_player=person)
    assert wider.result_status == "no_result"
    reset_data_source_cache()


def test_summary_v3_matches_v2_and_existing_qualified_official_rows(tmp_path, monkeypatch):
    root, rows = stage(tmp_path, "2025-26", 22500002, version=3)
    baseline = data_read_csv("data/raw/player_game_availability/2025-26_regular_season.csv")
    baseline = baseline.loc[pd.to_numeric(baseline.game_id).eq(22500002)]
    keys = ["game_id", "team_id", "player_id", "participation_state"]
    assert set(map(tuple, rows[keys].to_numpy())) == set(map(tuple, baseline[keys].to_numpy()))
    assert len(rows) == len(baseline) == 34
    validate_publication(root)
    from nbatools.commands import _participation_observations as observations

    monkeypatch.setenv("DATA_SOURCE", "local")
    monkeypatch.setenv("NBATOOLS_DATA_ROOT", str(tmp_path))
    monkeypatch.setenv("NBATOOLS_DATA_GENERATION", "legacy")
    reset_data_source_cache()
    game = pd.Series(
        dict(
            game_id=22500002,
            team_id=1610612747,
            opponent_team_id=1610612744,
            game_date="2025-10-21",
        )
    )
    with pytest.raises(ValueError, match="precise report time"):
        observations.qualified_report_seconds(
            game, "Luka Doncic", ["2025-26"], "Regular Season", played=True
        )
    reset_data_source_cache()


def test_legacy_invalid_duration_remains_unqualified(tmp_path):
    with pytest.raises(ValueError, match="29:60"):
        stage(tmp_path, "1997-98", 29700001)
    assert not (tmp_path / "data/raw/player_game_availability/1997-98_regular_season.csv").exists()


def test_historical_pair_bound_and_same_game_other_team(tmp_path, monkeypatch):
    root, rows = stage(tmp_path, "1997-98", 29700002)
    monkeypatch.setenv("DATA_SOURCE", "local")
    monkeypatch.setenv("NBATOOLS_DATA_ROOT", str(tmp_path))
    monkeypatch.setenv("NBATOOLS_DATA_GENERATION", "legacy")
    reset_data_source_cache()
    result = execute_natural_query(
        "Nets record with at least 95 points without Kerry Kittles and Keith Van Horn in 1997-98 from 1997-10-31 to 1997-10-31"
    )
    assert result.result_status == "ok", result.metadata
    summary = result.result.to_dict()["sections"]["summary"][0]
    assert (summary["games"], summary["wins"], summary["pts_avg"]) == (1, 1, 97)
    result = execute_structured_query(
        "team_record",
        team="IND",
        season="1997-98",
        without_player="Kerry Kittles",
        start_date="1997-10-31",
        end_date="1997-10-31",
    )
    assert result.result_reason == "no_match"
    from fastapi.testclient import TestClient

    from nbatools.api import app

    response = TestClient(app).post(
        "/query",
        json={
            "query": "New Jersey Nets record without Kerry Kittles and Keith Van Horn in 1997-98 from 1997-10-31 to 1997-10-31"
        },
    )
    assert response.status_code == 200
    assert response.json()["result_status"] == "ok"
    assert response.json()["result"]["sections"]["summary"][0]["pts_avg"] == 97

    reset_data_source_cache()


def test_targeted_pdf_fallback_and_date_bounded_missed_counts(tmp_path, monkeypatch):
    from nbatools.commands.pipeline import player_game_availability_report as report
    from nbatools.commands.pipeline.pull_player_game_availability import backfill

    root, _ = stage(tmp_path, "2025-26", 22500002)
    for dataset, filename in [
        ("player_game_stats", "2024-25_regular_season.csv"),
        ("rosters", "2025-26.csv"),
        ("rosters", "2024-25.csv"),
    ]:
        destination = root / "raw" / dataset / filename
        destination.parent.mkdir(parents=True, exist_ok=True)
        data_read_csv(f"data/raw/{dataset}/{filename}").to_csv(destination, index=False)
    cache = EVIDENCE.parent / "k08-three-reports/acquired_data/raw/player_game_availability_sources"

    def no_fetch(*args, **kwargs):
        raise AssertionError("Retained fallback must never refetch any endpoint")

    monkeypatch.setattr(report.urllib.request, "urlopen", no_fetch)
    output = backfill(
        "2025-26",
        root=root,
        source="report",
        cached_reports=cache,
        game_ids=[22500019, 22500113, 22500122],
    )
    selected = output.loc[output.game_id.astype(int).isin([22500019, 22500113, 22500122])]
    # Checker used pdftotext and own ID/state parser: includes DND rows.
    assert selected.groupby("game_id").size().to_dict() == {
        "0022500019": 34,
        "0022500113": 35,
        "0022500122": 35,
    }
    assert selected.participation_state.eq("played").sum() == 70
    assert selected.participation_state.eq("did_not_play").sum() == 34
    validate_publication(root)
    monkeypatch.setenv("DATA_SOURCE", "local")
    monkeypatch.setenv("NBATOOLS_DATA_ROOT", str(tmp_path))
    monkeypatch.setenv("NBATOOLS_DATA_GENERATION", "legacy")
    reset_data_source_cache()
    record = execute_natural_query(
        "Lakers record without LeBron James from 2025-10-24 to 2025-10-27 in 2025-26"
    )
    assert record.result_status == "ok", record.metadata
    summary = record.result.to_dict()["sections"]["summary"][0]
    assert (summary["games"], summary["wins"], summary["losses"], summary["pts_avg"]) == (
        3,
        2,
        1,
        121,
    )
    assert [int(r["game_id"]) for r in record.result.to_dict()["sections"]["game_log"]] == [
        22500019,
        22500113,
        22500122,
    ]
    for query, expected in [
        ("how many games did LeBron James miss from 2025-10-24 to 2025-10-27 in 2025-26", 3),
        ("how many home games did LeBron miss between October 24 and October 27 in 2025-26", 2),
        ("number of games LeBron James missed on October 26, 2025", 1),
    ]:
        result = execute_natural_query(query)
        assert result.result_status == "ok", result.metadata
        assert result.route == "game_finder"
        assert result.result.to_dict()["sections"]["count"][0]["count"] == expected
        assert "LeBron James missed" in result.metadata["answer_phrase"]
    for dates in [
        "on 2025-10-24 and 2025-10-27",
        "on October 24 and October 27",
        "on October 27, October 24 and October 27",
    ]:
        query = f"how many games did LeBron James miss {dates} in 2025-26"
        counted = execute_natural_query(query)
        assert counted.result_status == "ok", counted.metadata
        sections = counted.result.to_dict()["sections"]
        assert sections["count"][0]["count"] == 2
        assert {int(r["game_id"]) for r in sections["finder"]} == {22500019, 22500122}
        assert "on 2025-10-24, 2025-10-27" in counted.metadata["answer_phrase"]
        assert "from 2025-10-24 to" not in counted.metadata["answer_phrase"]
    from fastapi.testclient import TestClient

    from nbatools.api import app
    from tools.raw_query_answer_qa import run_case

    query = "how many home games did LeBron miss on October 24 and October 27 in 2025-26"
    payload = TestClient(app).post("/query", json={"query": query}).json()
    assert payload["result_status"] == "ok", payload
    assert payload["result"]["sections"]["count"][0]["count"] == 2
    checked = run_case(
        dict(
            id="k08_disjoint_missed_dates",
            query=query,
            category="participation",
            priority="p1",
            expected_status="ok",
        ),
        top_rows=5,
    )
    assert checked["expectation_results"]["fail_count"] == 0, checked
    assert checked["sections"]["count"][0]["count"] == 2
    assert "Dates" in str(checked["query_output_snapshot"])
    pair = execute_natural_query(
        "Austin Reaves games with at least 40 points without LeBron James and Luka Doncic from 2025-10-24 to 2025-10-27 in 2025-26"
    )
    assert pair.result_status == "ok", pair.metadata
    rows = pair.result.to_dict()["sections"]["finder"]
    assert [(int(r["game_id"]), r["pts"], r["reb"], r["ast"]) for r in rows] == [
        (22500113, 51, 11, 9),
        (22500122, 41, 4, 5),
    ]
    unknown = execute_structured_query(
        "team_record", team="LAL", season="2025-26", without_player="LeBron James"
    )
    assert unknown.result_status == "no_result"  # full-season remaining unknowns are not zero
    reset_data_source_cache()


def test_structured_import_does_not_replace_existing_qualified_pdf(tmp_path):
    root, _ = stage(tmp_path, "2025-26", 22500002)
    target = root / "raw/player_game_availability/2025-26_regular_season.csv"
    # Existing authenticated-generation rows retain their stronger PDF source.
    baseline = data_read_csv("data/raw/player_game_availability/2025-26_regular_season.csv")
    baseline.to_csv(target, index=False)
    before = target.read_bytes()
    with pytest.raises(ValueError, match="downgrade qualified PDF clock authority"):
        stage_structured_game(
            root,
            season="2025-26",
            season_type="Regular Season",
            game_id=22500002,
            traditional=SOURCE / "boxscoretraditionalv3_0022500002.json",
            summary=SOURCE / "boxscoresummaryv3_0022500002.json",
            summary_version=3,
            revision=PROVENANCE["revision"],
            retrieved_at="2026-10-27T16:45:00+00:00",
        )
    assert target.read_bytes() == before


def test_source_only_inactive_name_preserves_subject_and_answers(tmp_path, monkeypatch):
    """Summary V2 lists Young; the qualified game has no Young appearance."""
    root, rows = stage(tmp_path, "2014-15", 21400001)
    young = rows.loc[rows.player_id.eq(203942)].iloc[0]
    assert (young.player_name, young.team_id, young.participation_state) == (
        "Patric Young",
        1610612740,
        "did_not_play",
    )
    players = pd.read_csv(root / "raw/player_game_stats/2014-15_regular_season.csv")
    assert not players.player_id.eq(203942).any()
    monkeypatch.setenv("DATA_SOURCE", "local")
    monkeypatch.setenv("NBATOOLS_DATA_ROOT", str(tmp_path))
    monkeypatch.setenv("NBATOOLS_DATA_GENERATION", "legacy")
    reset_data_source_cache()
    scope = "in 2014-15 from 2014-10-28 to 2014-10-28"
    for clause in [
        "without Patric Young",
        "while Patric Young did not play",
        "when Patric Young was out",
        "without Darius Miller and Patric Young",
        "without Patric Young and Darius Miller",
    ]:
        result = execute_natural_query(f"Pelicans record {clause} {scope}")
        assert result.result_status == "ok", result.metadata
        sections = result.result.to_dict()["sections"]
        summary = sections["summary"][0]
        assert (summary["games"], summary["wins"], summary["losses"], summary["pts_avg"]) == (
            1,
            1,
            0,
            101,
        )
        assert [int(r["game_id"]) for r in sections["game_log"]] == [21400001]
        assert sections["game_log"][0]["opponent_pts"] == 84
    from fastapi.testclient import TestClient

    from nbatools.api import app
    from tools.raw_query_answer_qa import run_case

    # Actual API plus the existing answer/snapshot checker on the same stage.
    query = f"Without Darius Miller and Patric Young, Anthony Davis games with at least 20 points {scope}"
    response = TestClient(app).post("/query", json={"query": query})
    assert response.status_code == 200
    payload = response.json()
    assert payload["result_status"] == "ok", payload
    assert payload["route"] == "player_game_finder", payload
    sections = payload["result"]["sections"]
    actual = sections["finder"]
    assert [(int(r["game_id"]), r["player_name"], r["pts"]) for r in actual] == [
        (21400001, "Anthony Davis", 26)
    ]
    scalar = execute_natural_query(
        f"Anthony Davis games with at least 20 points without Patric Young {scope}"
    )
    assert scalar.route == "player_game_finder"
    assert [
        (int(r["game_id"]), r["pts"]) for r in scalar.result.to_dict()["sections"]["finder"]
    ] == [(21400001, 26)]
    checked = run_case(
        dict(
            id="k08_source_only_young",
            query=query,
            category="participation",
            priority="p1",
            expected_status="ok",
        ),
        top_rows=5,
    )
    assert checked["result_status"] == "ok", checked
    assert checked["expectation_results"]["fail_count"] == 0, checked
    assert "Patric Young" in str(checked["query_output_snapshot"])
    wider = execute_natural_query("Pelicans record without Patric Young in 2014-15")
    assert wider.result_status == "no_result"
    reset_data_source_cache()


@pytest.mark.parametrize("names", ["Patric Young", "Darius Miller and Patric Young"])
def test_published_source_only_presence_count_is_verified_zero(names):
    """Existing qualified 2014 report: both DNP; Davis played and scored 26."""
    from fastapi.testclient import TestClient

    from nbatools.api import app
    from nbatools.commands._participation_observations import load_observations
    from tools.raw_query_answer_qa import run_case

    rows = load_observations(["2014-15"], "Regular Season")
    listed = rows.loc[rows.game_id.eq(21400001)]
    for pid, name in [(203121, "Darius Miller"), (203942, "Patric Young")]:
        row = listed.loc[listed.player_id.eq(pid)].iloc[0]
        assert (
            row.player_name,
            int(row.team_id),
            str(row.game_date)[:10],
            row.participation_state,
        ) == (name, 1610612740, "2014-10-28", "did_not_play")
    players = data_read_csv("data/raw/player_game_stats/2014-15_regular_season.csv")
    assert not players.player_id.eq(203942).any()
    davis = players.loc[players.game_id.eq(21400001) & players.player_id.eq(203076)].iloc[0]
    assert (int(davis.team_id), davis.pts) == (1610612740, 26)
    scope = "in 2014-15 on October 28 2014"
    queries = [
        f"How many Anthony Davis games with at least 20 points with {names} {scope}",
        f"With {names}, how many Anthony Davis games with at least 20 points {scope}",
    ]
    for query in queries:
        response = TestClient(app).post("/query", json={"query": query})
        assert response.status_code == 200
        payload = response.json()
        assert payload["result_status"] == "ok", payload
        assert payload["route"] == "player_game_finder"
        assert payload["result"]["sections"]["count"] == [{"count": 0}]
        assert payload["result"]["metadata"]["player"] == "Anthony Davis"
        assert payload["result"]["metadata"]["with_player"] == names
        checked = run_case(
            dict(
                id="k08_source_presence_zero",
                query=query,
                category="participation",
                priority="p1",
                expected_status="ok",
                expected_route="player_game_finder",
                hard_assertions=[dict(path="result.sections.count.0.count", equals=0)],
            ),
            top_rows=5,
        )
        assert checked["expectation_results"]["fail_count"] == 0, checked
        assert names in str(checked["query_output_snapshot"])
    # An actual nonempty counterpart prevents acceptance by always returning zero.
    absence = execute_natural_query(
        f"Anthony Davis games with at least 20 points without {names} {scope}"
    )
    assert absence.result_status == "ok", absence.metadata
    assert [
        (int(r["game_id"]), r["pts"]) for r in absence.result.to_dict()["sections"]["finder"]
    ] == [(21400001, 26)]
    # Positive played facts keep the same game when source and appearances agree.
    positive = execute_natural_query(
        f"How many Anthony Davis games with at least 20 points with Tyreke Evans {scope}"
    )
    assert positive.result_status == "ok", positive.metadata
    positive_sections = positive.result.to_dict()["sections"]
    assert positive_sections["count"] == [{"count": 1}]
    assert [(int(r["game_id"]), r["pts"]) for r in positive_sections["finder"]] == [(21400001, 26)]
    unknown = execute_natural_query(f"How many Anthony Davis games with {names} in 2014-15")
    assert unknown.result_status == "no_result", unknown.metadata


@pytest.mark.slow
def test_deployed_source_only_presence_on_published_snapshot():
    """Post-merge feature smoke only; no publication, acquisition or cold-start check."""
    import os
    import time
    import urllib.request

    from nbatools.commands._participation_observations import load_observations

    generation = "availability-k08-retained-v1-20261031"
    assert os.environ["NBATOOLS_DATA_GENERATION"] == generation
    source = load_observations(["2014-15"], "Regular Season")
    young = source.loc[source.game_id.eq(21400001) & source.player_id.eq(203942)].iloc[0]
    assert (young.team_id, young.participation_state) == (1610612740, "did_not_play")
    base = "https://nbatools.vercel.app"

    def request(path, body=None):
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(
            base + path,
            data=data,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "NBA-Tools-K08-feature-smoke",
            },
        )
        with urllib.request.urlopen(req, timeout=60) as response:
            assert response.status == 200
            return json.load(response)

    before = request("/readiness")
    assert before["ready"] is True and before["active_generation"] == generation
    scope = "in 2014-15 on October 28 2014"
    checks = []
    queries = [
        (
            "Patric Young",
            f"How many Anthony Davis games with at least 20 points with Patric Young {scope}",
        ),
        (
            "Darius Miller and Patric Young",
            f"With Darius Miller and Patric Young, how many Anthony Davis games with at least 20 points {scope}",
        ),
        (None, f"Anthony Davis games with at least 20 points without Patric Young {scope}"),
    ]
    for names, query in queries:
        # Respect the unchanged public query quota; no client retries hide errors.
        time.sleep(7)
        payload = request("/query", {"query": query})
        assert payload["result_status"] == "ok", payload
        assert payload["route"] == "player_game_finder", payload
        sections, metadata = payload["result"]["sections"], payload["result"]["metadata"]
        assert metadata["player"] == "Anthony Davis"
        if names:
            assert sections["count"] == [{"count": 0}]
            assert metadata["with_player"] == names
        else:
            assert [(int(r["game_id"]), r["pts"]) for r in sections["finder"]] == [(21400001, 26)]
            assert metadata["without_player"] == "Patric Young"
        checks.append(
            dict(
                query=query,
                route=payload["route"],
                sections=sections,
                filters=metadata["applied_filters"],
            )
        )
    after = request("/readiness")
    assert after["ready"] is True and after["active_generation"] == generation
    receipt = dict(
        generation=generation, readiness_before=before, readiness_after=after, checks=checks
    )
    output = os.environ.get("NBATOOLS_ACQUISITION_OUTPUT")
    if output:
        target = Path(output) / "k08-source-presence-live.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(receipt, indent=2, default=str) + "\n")
    print(json.dumps(receipt, default=str))


def test_published_absence_clauses_preserve_subject_bound_and_pair():
    """Reuse accepted original-row arithmetic, exercising the repaired interpreter."""
    from fastapi.testclient import TestClient

    from nbatools.api import app
    from nbatools.commands._participation_observations import load_observations

    observed = load_observations(["2025-26"], "Regular Season")
    games = {22500019, 22500113, 22500122}
    lebron = observed.loc[observed.game_id.isin(games) & observed.player_id.eq(2544)]
    assert set(lebron.game_id) == games
    assert (
        lebron.team_id.eq(1610612747).all() and lebron.participation_state.eq("did_not_play").all()
    )
    scope = "from 2025-10-24 to 2025-10-27 in 2025-26"
    for predicate in ["with LeBron James out", "with LeBron not playing", "with LeBron sitting"]:
        response = TestClient(app).post(
            "/query", json={"query": f"Lakers record {predicate} {scope}"}
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["result_status"] == "ok", payload
        sections = payload["result"]["sections"]
        assert {int(r["game_id"]) for r in sections["game_log"]} == games
        row = sections["summary"][0]
        assert (row["games"], row["wins"], row["losses"], row["pts_avg"]) == (3, 2, 1, 121)
        assert payload["result"]["metadata"]["without_player"] == "LeBron James"
        assert payload["result"]["metadata"]["with_player"] is None
    result = execute_natural_query(
        f"Austin Reaves games with at least 40 points without LeBron and Luka playing {scope}"
    )
    assert result.result_status == "ok", result.metadata
    assert [
        (int(r["game_id"]), r["pts"]) for r in result.result.to_dict()["sections"]["finder"]
    ] == [(22500113, 51), (22500122, 41)]
    source_only = execute_natural_query(
        "Anthony Davis games with at least 20 points with Patric Young out on October 28 2014 in 2014-15"
    )
    assert source_only.result_status == "ok", source_only.metadata
    assert [
        (int(r["game_id"]), r["pts"]) for r in source_only.result.to_dict()["sections"]["finder"]
    ] == [(21400001, 26)]
    # Completing 2025-26 participation does not qualify a different season.
    unknown = execute_natural_query("Lakers record with LeBron James out in 2024-25")
    assert unknown.result_status != "ok"
