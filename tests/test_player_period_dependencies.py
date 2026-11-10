"""Dependency reading against unchanged qualified v5 sources, plus labeled fault fixtures."""

import asyncio
import io
import json
import shutil
from pathlib import Path
from zipfile import ZipFile

import httpx
import pandas as pd
import pytest

from nbatools.api_handlers import natural_query_payload, query_result_to_payload
from nbatools.commands.aggregate_metrics import (
    add_aggregate_metric_fields,
    aggregate_metric_value,
    compute_grouped_rate_metrics,
    require_known_metric_inputs,
)
from nbatools.development_data import (
    MANIFEST,
    DevelopmentDataUnavailable,
    DevelopmentSnapshot,
    development_snapshot,
    sha256,
)
from nbatools.query_service import execute_structured_query
from tools.development_query import create_app

E = (
    Path(__file__).resolve().parents[1]
    / "working/nba-tools-completion-program/source-evidence/player-period-reader-20261110"
)
DATA = "data/raw/player_game_period_stats/2026-27_regular_season.csv"
PROOF = "data/metadata/player-period-input-qualification.json"
ORIGIN = "data/metadata/period-reader-origin.json"
ORACLE_SHA = "9b3c4cd26b12f8ac983e339275a28b3e5212c1d8deec8b55fb6d56fe6cc6a3dc"
pytestmark = [pytest.mark.served_seasons, pytest.mark.engine]


def unpack(output):
    binding = json.loads((E / "binding.json").read_bytes())
    raw = (E / binding["archive"]).read_bytes()
    assert sha256(raw) == binding["archive_sha256"]
    with ZipFile(io.BytesIO(raw)) as z:
        assert all(n.startswith("data/") and ".." not in Path(n).parts for n in z.namelist())
        z.extractall(output)
    DevelopmentSnapshot(output, binding["manifest_sha256"])
    return output, binding["manifest_sha256"]


@pytest.fixture(scope="module")
def qualified(tmp_path_factory):
    return unpack(tmp_path_factory.mktemp("qualified-period-inputs"))


@pytest.fixture(autouse=True)
def local(monkeypatch):
    monkeypatch.setenv("DATA_SOURCE", "local")


def source_oracle():
    raw = (E / "independent-source-oracles.json").read_bytes()
    assert sha256(raw) == ORACLE_SHA
    oracle = json.loads(raw)
    assert oracle["derived_from_app"] is False and oracle["known_unknown_count"] == 484
    return oracle


def kwargs(row):
    return dict(
        player=row["player_name"],
        season="2026-27",
        start_date="2026-11-04",
        end_date="2026-11-04",
        stat="pts",
        limit=None,
        **(
            {"half": "first"}
            if row["window"] == "h1"
            else {"quarter": "ot" if row["window"] == "ot" else 2}
        ),
    )


def run(**changes):
    args = dict(player="Kevin Durant", season="2026-27", quarter=4, stat="pts", limit=None)
    args.update(changes)
    return execute_structured_query("player_game_finder", **args)


def games(result):
    assert result.result_status == "ok", result.result.to_dict()
    return result.result.to_dict()["sections"]["finder"]


def assert_unknown(result):
    assert (result.result_status, result.result_reason) == ("no_result", "no_data"), (
        result.result.to_dict()
    )
    assert "unknown" in " ".join(result.result.notes).lower()


@pytest.mark.parametrize("index", range(8))
def test_independent_source_quarter_half_ot_counts_clocks_rates(qualified, index):
    row = source_oracle()["selected_rows"][index]
    with development_snapshot(*qualified):
        result = execute_structured_query("player_game_finder", **kwargs(row))
        actual = games(result)
        assert len(actual) == 1
        for field in (
            "game_id",
            "player_id",
            "pts",
            "reb",
            "ast",
            "minutes",
            "fgm",
            "fga",
            "fg3m",
            "fta",
            "tov",
            "usg_pct",
            "ast_pct",
            "reb_pct",
            "tov_pct",
            "efg_pct",
            "ts_pct",
        ):
            if (
                field in {"efg_pct", "ts_pct"}
                and row["fga"] == 0
                and (field == "efg_pct" or row["fta"] == 0)
            ):
                assert (
                    actual[0][field] is None
                )  # Undefined consumer ratio, original bytes unchanged.
                continue
            if row.get(field) is not None:
                assert actual[0][field] == pytest.approx(row[field], abs=1e-12), field
        payload = query_result_to_payload(result)
        quality = payload["result"]["metadata"]["data_quality"]
        assert quality["manifest_sha256"] == qualified[1]
        assert quality["snapshot"] == "current123-period-reader-development-v6"
        assert quality["production_accepted"] is False


@pytest.mark.parametrize(
    "query,count",
    [
        ("How many points did Austin Reaves score in second quarters on 2026-11-04?", 4),
        ("How many assists did Austin Reaves get in first halves on 2026-11-04?", 1),
        ("How many points did Saddiq Bey score in overtime on 2026-11-04?", 8),
    ],
)
def test_natural_stat_sum_and_http_preserve_period_not_whole_game(qualified, query, count):
    async def request():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=create_app(*qualified)), base_url="http://127.0.0.1"
        ) as client:
            response = await client.post("/query", json={"query": query})
            assert response.status_code == 200
            return response.json()

    with development_snapshot(*qualified):
        payload = natural_query_payload(query)
    assert payload["result_status"] == "ok", payload
    assert payload["result"]["sections"]["count"][0]["count"] == count
    http = asyncio.run(request())
    assert http["result_status"] == "ok"
    assert http["result"]["sections"]["count"] == payload["result"]["sections"]["count"]
    assert http["result"]["metadata"] == payload["result"]["metadata"]
    assert [
        (r["game_id"], r["pts"], r["reb"], r["ast"]) for r in http["result"]["sections"]["finder"]
    ] == [
        (r["game_id"], r["pts"], r["reb"], r["ast"])
        for r in payload["result"]["sections"]["finder"]
    ]


@pytest.mark.parametrize(
    "changes",
    [
        {"stat": "usg_pct"},
        {"stat": "tov_pct"},
        {"stat": "usg_pct", "min_value": 0},
        {"stat": "tov_pct", "max_value": 1},
        {"stat": "usg_pct", "sort_by": "stat", "limit": 1},
        {"stat": "tov_pct", "sort_by": "stat", "per_season_limit": 1},
        {"conditions": [{"stat": "pts", "min_value": 1000}, {"stat": "usg_pct", "min_value": 0}]},
        {"stat": "usg_pct", "min_value": 0, "last_n": 1, "last_n_scope": "qualifying"},
    ],
)
def test_unknowns_block_output_predicate_ranking_mixed_and_qualifying_sample(qualified, changes):
    with development_snapshot(*qualified):
        assert_unknown(run(**changes))


def test_unknown_rate_stays_null_when_unrequested_and_queries_do_not_leak(qualified):
    with development_snapshot(*qualified):
        assert_unknown(run(stat="usg_pct"))
        result = run(start_date="2026-10-21", end_date="2026-10-21")
        row = games(result)[0]
        assert row["usg_pct"] is None and row["tov_pct"] is None
        assert result.result.metadata["unknown_source_fields"] == ["usg_pct", "tov_pct"]
        assert "Unrequested source rates remain unknown" in " ".join(result.result.notes)


@pytest.mark.parametrize("index", range(14))
def test_exact_source_selected_samples_totals_rates_and_season_grouping(qualified, index):
    oracle = source_oracle()["finite_new16_aggregates"][index]
    frame = pd.read_csv(qualified[0] / DATA)
    name = frame.loc[frame.player_id.eq(oracle["player_id"]), "player_name"].iloc[0]
    window = oracle["window"]
    args = dict(
        player=name,
        season="2026-27",
        start_date="2026-11-04",
        end_date="2026-11-04",
        stat="pts",
        limit=None,
    )
    args.update(half="first" if window == "h1" else "second") if window.startswith(
        "h"
    ) else args.update(quarter="ot" if window == "ot" else window[1:])
    with development_snapshot(*qualified):
        result = execute_structured_query("player_game_finder", **args)
        rows = pd.DataFrame(games(result))
        assert sorted(rows.game_id.tolist()) == oracle["game_ids"]
        assert len(rows) == oracle["games"]
        for metric, expected in oracle["sums"].items():
            assert rows[metric].sum() == pytest.approx(expected, abs=1e-12)
        for metric in ("ts_pct", "efg_pct"):
            assert aggregate_metric_value(rows, metric) == pytest.approx(oracle[metric], abs=1e-12)
        grouped = execute_structured_query(
            "player_game_finder", **(args | {"sort_by": "stat", "per_season_limit": 1})
        )
        top = games(grouped)
        assert len(top) == 1 and top[0]["pts"] == rows.pts.max()


def test_natural_or_and_http_unknown_refuse_without_partial_branch_or_count(qualified):
    query = "Kevin Durant fourth quarter games with over 1000 points or over 0 usage percentage in 2026-27"
    with development_snapshot(*qualified):
        payload = natural_query_payload(query)
    assert payload["result_status"] == "no_result" and payload["result_reason"] == "no_data"
    assert payload["result"]["sections"] == {}

    async def request():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=create_app(*qualified)), base_url="http://127.0.0.1"
        ) as client:
            response = await client.post("/query", json={"query": query})
            assert response.status_code == 200
            body = response.json()
            assert body["result_status"] == "no_result" and body["result_reason"] == "no_data"
            assert body["result"]["sections"] == {}

    asyncio.run(request())


@pytest.mark.parametrize("metric", ["ts_pct", "efg_pct", "fg_pct", "fg3_pct", "ft_pct"])
def test_source_zero_attempt_denominator_is_undefined_not_a_requested_zero(qualified, metric):
    args = kwargs(source_oracle()["selected_rows"][4])
    with development_snapshot(*qualified):
        count = execute_structured_query("player_game_finder", **args)
        row = games(count)[0]
        assert (row["pts"], row["reb"], row["ast"]) == (0, 1, 1)
        assert row["ts_pct"] is None and row["efg_pct"] is None
        for changes in ({"stat": metric}, {"stat": metric, "min_value": 0}):
            result = execute_structured_query("player_game_finder", **(args | changes))
            assert result.result_reason == "no_data"
            assert "zero-attempt denominator" in " ".join(result.result.notes)


@pytest.mark.parametrize("metric", ["team_pts", "opponent_pts", "margin"])
def test_whole_game_context_cannot_silently_supply_period_metric_basis(qualified, metric):
    args = kwargs(source_oracle()["selected_rows"][0])
    with development_snapshot(*qualified):
        for changes in ({"stat": metric}, {"conditions": [{"stat": metric, "min_value": 0}]}):
            result = execute_structured_query("player_game_finder", **(args | changes))
            assert result.result_reason == "no_data"
            assert "period metric basis" in " ".join(result.result.notes)


def test_shooting_rank_checks_defined_ratios_on_independent_attempt_eligible_sample(qualified):
    with development_snapshot(*qualified):
        result = execute_structured_query(
            "player_game_finder",
            season="2026-27",
            half="first",
            start_date="2026-11-04",
            end_date="2026-11-04",
            stat="ts_pct",
            sort_by="stat",
            limit=3,
        )
        rows = games(result)
        assert rows and all(row["fga"] >= 10 and row["ts_pct"] is not None for row in rows)
        assert any("fewer than 10" in note for note in result.result.caveats)


def test_independent_date_head_and_original_window_samples_can_exclude_unknowns(qualified):
    with development_snapshot(*qualified):
        for changes in (
            {"limit": 1},
            {"last_n": 1, "last_n_scope": "window"},
            {"start_date": "2026-11-04", "end_date": "2026-11-04"},
        ):
            result = run(stat="usg_pct", **changes)
            rows = games(result)
            assert len(rows) == 1 and rows[0]["game_id"] == 22600181
            assert rows[0]["usg_pct"] is not None
        # Ranking still competes with the entire sample, including the unknown game.
        assert_unknown(run(stat="usg_pct", sort_by="stat", limit=1))


@pytest.mark.parametrize("operator", ["and", "or"])
def test_boolean_unknown_branch_cannot_be_hidden_by_known_points(qualified, operator):
    with development_snapshot(*qualified):
        result = run(
            stat=None, condition_expression=f"over 1000 points {operator} over 0 usage percentage"
        )
        assert_unknown(result)


def test_counts_aggregate_derived_denominators_and_grouping_propagate(qualified):
    # Explicitly synthetic arithmetic fixture, independent of NBA source claims.
    f = pd.DataFrame(
        {
            "season": ["A", "A"],
            "pts": [2.0, 8.0],
            "fgm": [1.0, 4.0],
            "fg3m": [0.0, 0.0],
            "fga": [1.0, 9.0],
            "fta": [0.0, 0.0],
            "ts_pct": [1.0, 4 / 9],
            "usg_pct": [0.1, None],
            "tov_pct": [0.0, None],
        }
    )
    with development_snapshot(*qualified):
        require_known_metric_inputs(
            f, ["pts", "ts_pct", "efg_pct"], operation="controlled mixed aggregate"
        )
        fields = add_aggregate_metric_fields(
            {}, f, ["pts", "ts_pct", "efg_pct", "usg_pct"], sum_metrics=["pts"]
        )
        assert fields == {
            "pts_avg": 5.0,
            "pts_sum": 10.0,
            "ts_pct_avg": 0.5,
            "efg_pct_avg": 0.5,
            "usg_pct_avg": None,
        }
        grouped = compute_grouped_rate_metrics(f, "season", ["ts_pct"]).to_dict("records")
        assert grouped == [{"season": "A", "ts_pct_avg": 0.5}]
        with pytest.raises(DevelopmentDataUnavailable):
            require_known_metric_inputs(
                f, ["pts", "usg_pct"], operation="mixed requested aggregate"
            )
        f.loc[1, "fga"] = None
        # A cached non-null derived field cannot disguise an unknown denominator.
        with pytest.raises(DevelopmentDataUnavailable):
            require_known_metric_inputs(f, ["ts_pct"], operation="derived statistic")
        assert aggregate_metric_value(f, "ts_pct") is None
        assert aggregate_metric_value(f, "tov_pct") is None
        f.loc[1, "pts"] = None
        fields = add_aggregate_metric_fields({}, f, ["pts"], sum_metrics=["pts"])
        assert fields == {"pts_avg": None, "pts_sum": None}


def test_missing_requested_coverage_cannot_be_hidden_by_stat_filter_head_or_aggregate(
    qualified, monkeypatch
):
    import nbatools.commands.player_game_finder as finder
    from nbatools.commands.data_utils import load_player_game_period_stats_for_seasons

    with development_snapshot(*qualified):
        frame = load_player_game_period_stats_for_seasons(["2026-27"], "Regular Season")
        # Controlled loader fault only; unchanged real immutable bytes remain pinned.
        incomplete = frame.loc[
            ~(
                frame.player_id.eq(1630559)
                & frame.game_id.eq(22600185)
                & frame.period_family.eq("quarter")
                & frame.period_value.astype(str).eq("2")
            )
        ]
        assert len(incomplete) == len(frame) - 1
        monkeypatch.setattr(
            finder, "load_player_game_period_stats_for_seasons", lambda *a, **k: incomplete
        )
        result = execute_structured_query(
            "player_game_finder",
            player="Austin Reaves",
            season="2026-27",
            quarter=2,
            stat="pts",
            min_value=1000,
            limit=1,
        )
        assert (
            result.result_status == "no_result" and result.result_reason == "filter_not_supported"
        )
        assert "coverage" in " ".join(result.result.notes).lower()


def test_companion_preserves_every_parent_byte_and_ordinary_strict_guard(qualified):
    root, digest = qualified
    snapshot = DevelopmentSnapshot(root, digest)
    parent = json.loads((root / ORIGIN).read_bytes())
    for path, expected in parent["files"].items():
        assert sha256((root / path).read_bytes()) == expected == snapshot.files[path]
    frame = snapshot.read_player_period_frame(DATA)
    assert frame[["usg_pct", "tov_pct"]].isna().sum().to_dict() == {"usg_pct": 242, "tov_pct": 242}
    assert len(frame) == 16783
    for method in (snapshot.resolve_path, snapshot.exists):
        with pytest.raises(DevelopmentDataUnavailable):
            method(DATA)


def test_corruption_after_warm_read_is_rejected(qualified, tmp_path):
    root, digest = qualified
    shutil.copytree(root, tmp_path / "fault")
    with development_snapshot(tmp_path / "fault", digest):
        assert games(run(start_date="2026-11-04"))
        path = tmp_path / "fault" / DATA
        path.write_bytes(path.read_bytes() + b"\n")
        result = run(start_date="2026-11-04")
        assert result.result_status == "no_result"
        assert "Pinned development bytes changed" in " ".join(result.result.notes)


@pytest.mark.parametrize(
    "field,value",
    [("pts", None), ("usg_pct", "broken"), ("tov_pct", float("inf")), ("game_date", None)],
)
def test_reattested_controlled_bad_numeric_and_identity_inputs_refuse(
    qualified, tmp_path, field, value
):
    root, _ = qualified
    fault = tmp_path / "fault"
    shutil.copytree(root, fault)
    frame = pd.read_csv(fault / DATA)
    frame[field] = frame[field].astype(object)
    frame.loc[0, field] = value
    frame.to_csv(fault / DATA, index=False)

    def write(path, body):
        (fault / path).write_text(json.dumps(body, indent=2) + "\n")
        return sha256((fault / path).read_bytes())

    origin = json.loads((fault / ORIGIN).read_bytes())
    origin["fixture"] = True
    origin["files"][DATA] = sha256((fault / DATA).read_bytes())
    origin_hash = write(ORIGIN, origin)
    proof = json.loads((fault / PROOF).read_bytes())
    proof.update(dataset_sha256=origin["files"][DATA], origin_manifest_sha256=origin_hash)
    proof_hash = write(PROOF, proof)
    document = json.loads((fault / MANIFEST).read_bytes())
    document["fixture"] = True
    document["files"].update({DATA: origin["files"][DATA], ORIGIN: origin_hash, PROOF: proof_hash})
    document["validation_reports"][-1]["sha256"] = proof_hash
    digest = write(MANIFEST, document)
    with development_snapshot(fault, digest):
        assert_unknown(run(start_date="2026-11-04"))


@pytest.mark.parametrize("name", ["current123-period-v4.zip", "current123-period-v5.zip"])
def test_old_versions_keep_strict_refusal_without_new_qualification(tmp_path, name):
    with ZipFile(E.parent / "current123-periods-20261107" / name) as z:
        z.extractall(tmp_path)
    digest = sha256((tmp_path / MANIFEST).read_bytes())
    with development_snapshot(tmp_path, digest):
        assert_unknown(run(start_date="2026-11-04"))


@pytest.mark.parametrize("environment", ["production", "prod", "preview"])
def test_new_companion_cannot_be_enabled_in_production(qualified, monkeypatch, environment):
    monkeypatch.setenv("ENVIRONMENT", environment)
    with pytest.raises(ValueError, match="isolated local"):
        with development_snapshot(*qualified):
            pass
