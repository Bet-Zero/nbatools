"""K07 filtering precedes grouping, bound to independently frozen source rows."""

import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest

from nbatools.commands import player_split_summary, team_split_summary
from nbatools.data_source import data_path, data_read_csv
from nbatools.query_service import execute_natural_query, execute_structured_query

pytestmark = [pytest.mark.needs_data, pytest.mark.query]
BINDING = Path(__file__).resolve().parents[1] / "working/nba-tools-completion-program"
ORACLE = json.loads((BINDING / "k07-raw-oracle.json").read_text())
CASES = ORACLE["cases"]


def _qualified_buckets(case):
    sources = {}
    for source, digest in ORACLE["sources"].items():
        path = "data/raw/" + source
        assert hashlib.sha256(data_path(path).read_bytes()).hexdigest() == digest
        kind, filename = source.split("/")
        season = filename[:7]
        frame = data_read_csv(path)
        keys = ["game_id", "team_id"] + (["player_id"] if kind.startswith("player") else [])
        assert not frame.empty and not frame[keys].isna().any().any()
        assert not frame.duplicated(keys).any()
        assert frame.season.eq(season).all()
        assert frame.season_type.eq("Regular Season").all()
        if kind.startswith("team"):
            assert len(frame.groupby("team_id")) == 30
            assert frame.groupby("team_id").size().eq(82).all()
        sources[(kind.split("_")[0], season)] = frame
    selected_seasons = []
    for season in case["seasons"]:
        raw = sources[(case["kind"], season)]
        selected = raw.loc[
            raw.player_id.eq(case["player_id"])
            if case["kind"] == "player"
            else raw.team_abbr.eq(case["team"])
        ].copy()
        teams = sources[("team", season)].set_index(["game_id", "team_id"])
        opponents, outcomes, homes = [], [], []
        for row in selected.itertuples():
            own = teams.loc[(row.game_id, row.team_id)]
            other = teams.loc[(row.game_id, own.opponent_team_id)]
            assert other.opponent_team_id == row.team_id
            opponents.append(other.team_abbr)
            outcomes.append(own.wl)
            homes.append(bool(own.is_home))
        selected["raw_opponent"] = opponents
        selected["raw_wl"] = outcomes
        selected["raw_home"] = homes
        counts = case["discrimination"][season]
        assert len(selected) == counts["unfiltered"]
        if case["opponent"]:
            selected = selected.loc[selected.raw_opponent.eq(case["opponent"])]
        if case["venue"]:
            selected = selected.loc[selected.raw_home.eq(case["venue"] == "home")]
        assert len(selected) == counts["before_stat"]
        if case["stat"]:
            selected = selected.loc[selected[case["stat"]].ge(case["min_inclusive"])]
            assert counts["threshold_excluded"] > 0
        assert len(selected) == counts["after_all_filters"]
        assert counts["before_stat"] - len(selected) == counts["threshold_excluded"]
        selected_seasons.append(selected)
    full = pd.concat(selected_seasons)
    for expected in case["buckets"]:
        selected = full.loc[
            full.season.eq(expected["season"])
            if case["split"] == "season"
            else full.raw_home.eq(expected["bucket"] == "home")
        ]
        _assert_frame(selected, expected)
        assert selected.raw_wl.eq("W").sum() == expected["wins"]
        assert selected.raw_wl.eq("L").sum() == expected["losses"]
    return full


def _assert_frame(frame, expected):
    assert len(frame) == expected["games"]
    assert sorted(frame[expected["key_columns"]].astype(int).values.tolist()) == expected["keys"]
    assert frame.season.eq(expected["season"]).all()
    for stat, total in expected["sums"].items():
        assert frame[stat].sum() == total
        assert frame[stat].mean() == pytest.approx(expected["means"][stat])


@pytest.mark.parametrize("case", CASES, ids=[case["id"] for case in CASES])
@pytest.mark.parametrize("wording", ["primary", "heldout"])
def test_k07_filter_before_split(case, wording, monkeypatch):
    qualified = _qualified_buckets(case)
    heldout = {
        row["id"]: row["query"]
        for row in json.loads((BINDING / "k07-heldout-wording.json").read_text())["cases"]
    }
    player = case["kind"] == "player"
    module = player_split_summary if player else team_split_summary
    compute = module._summarize_bucket
    captured = []

    def capture(frame, bucket):
        captured.append((bucket, frame.copy()))
        return compute(frame, bucket)

    identity = {"player": qualified.player_name.iloc[0]} if player else {"team": case["team"]}
    seasons = (
        {
            "start_season": case["seasons"][0],
            "end_season": case["seasons"][-1],
            "split_seasons": case["seasons"],
        }
        if case["split"] == "season"
        else {"season": case["seasons"][0]}
    )
    route = case["kind"] + "_split_summary"
    monkeypatch.setattr(module, "_summarize_bucket", capture)
    for mode in ("natural", "structured"):
        captured.clear()
        result = (
            execute_natural_query(case["query"] if wording == "primary" else heldout[case["id"]])
            if mode == "natural"
            else execute_structured_query(
                route,
                season_type="Regular Season",
                split=case["split"],
                **identity,
                **seasons,
                opponent=case["opponent"],
                stat=case["stat"],
                min_value=case["min_inclusive"],
                home_only=case["venue"] == "home",
            )
        )
        assert result.result_status == "ok", (result.result_reason, result.metadata)
        assert result.route == route
        assert result.metadata["split_type"] == case["split"]
        assert result.metadata["opponent"] == case["opponent"]
        assert result.metadata["season_type"] == "Regular Season"
        if case["split"] == "season":
            if mode == "natural":
                assert result.metadata["season_list"] == case["seasons"]
        else:
            assert result.metadata["season"] == case["seasons"][0]
        if case["stat"]:
            assert result.metadata["stat"] == case["stat"]
            assert result.metadata["min_value"] == case["min_inclusive"]
        sections = result.to_dict()["sections"]
        assert len(sections["summary"]) == 1
        name_field = "player_name" if player else "team_name"
        assert sections["summary"][0][name_field] == qualified[name_field].iloc[0]
        assert sections["summary"][0]["games_total"] == len(qualified)
        rows = {row["bucket"]: row for row in sections["split_comparison"]}
        frames = dict(captured)
        expected = {row["bucket"]: row for row in case["buckets"]}
        assert len(rows) == len(sections["split_comparison"]) == len(frames) == len(captured)
        assert rows.keys() == frames.keys() == expected.keys()
        for bucket, truth in expected.items():
            _assert_frame(frames[bucket], truth)
            values = {k: truth[k] for k in ("games", "wins", "losses")}
            values["win_pct"] = truth["wins"] / truth["games"]
            values.update({stat + "_avg": value for stat, value in truth["means"].items()})
            for field, value in values.items():
                assert rows[bucket][field] == pytest.approx(value, abs=0.001)
