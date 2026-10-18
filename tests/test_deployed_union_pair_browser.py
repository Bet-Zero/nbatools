"""Accepted opponent unions and qualified participation through the public UI."""

import hashlib
import json

import pytest

from nbatools.data_source import data_path, data_read_csv
from tests.test_core_identity_find_count_browser import ROOT, _capture_browser
from tests.test_qualified_participation_pair_real_data import ORACLE, _qualified_source

pytestmark = [pytest.mark.needs_data, pytest.mark.query, pytest.mark.slow]
FIXTURES = ROOT / "tests/fixtures/multi_opponent"
PAIR = "LeBron James and Anthony Davis"


def _load_oracle(name):
    oracle = json.loads((FIXTURES / name).read_text())
    for path, digest in oracle["sources"].items():
        assert hashlib.sha256(data_path(path).read_bytes()).hexdigest() == digest
    return oracle["cases"]


def _qualify_sample(expected, seasons, *, player=False):
    keys = ["game_id", "team_id", "opponent_team_id"] + (["player_id"] if player else [])
    rows = []
    for season in seasons:
        frame = data_read_csv(
            f"raw/{'player' if player else 'team'}_game_stats/{season}_regular_season.csv"
        )
        assert not frame.duplicated(keys).any()
        wanted = {tuple(key) for key in expected["keys"]}
        rows += [
            row
            for row in frame.to_dict("records")
            if tuple(int(row[key]) for key in keys) in wanted
        ]
    assert sorted([[int(row[key]) for key in keys] for row in rows]) == expected["keys"]
    assert len(rows) == expected["games"]
    for stat, total in expected["sums"].items():
        assert sum(row[stat] for row in rows) == total


def _identity(team, seasons, team_id):
    reference = data_read_csv("raw/teams/team_history_reference.csv")
    years = [int(season[:4]) for season in seasons]
    rows = reference.loc[
        reference.team_abbr.eq(team)
        & reference.season_start.le(min(years))
        & reference.season_end.ge(max(years))
    ]
    assert len(rows) == 1 and int(rows.iloc[0].team_id) == team_id
    return dict(team_id=team_id, team_abbr=team, team_name=str(rows.iloc[0].team_name))


def _owned_window_cases():
    oracle = json.loads(
        (ROOT / "tests/fixtures/list_owned_stats/window-qualifying-source-oracle.json").read_text()
    )
    for path, digest in oracle["sources"].items():
        assert hashlib.sha256(data_path(path).read_bytes()).hexdigest() == digest
    raw = data_read_csv("raw/team_game_stats/2023-24_regular_season.csv")
    base = raw.loc[raw.team_abbr.eq("LAL") & raw.opponent_team_abbr.isin(["BOS", "WAS"])]
    base = base.sort_values(["game_date", "game_id"]).copy()
    assert base.game_id.astype(int).tolist() == [row["game_id"] for row in oracle["base_rows"]]
    opponent_points = []
    for expected, (_, row) in zip(oracle["base_rows"], base.iterrows()):
        for key, value in expected.items():
            if key == "opponent_pts":
                opponent = raw.loc[
                    raw.game_id.eq(row.game_id) & raw.team_id.eq(row.opponent_team_id)
                ]
                assert len(opponent) == 1 and int(opponent.iloc[0].pts) == value
                opponent_points.append(int(opponent.iloc[0].pts))
            else:
                assert row[key] == value
    base["opponent_pts"] = opponent_points
    cases = []
    for scope, phrase in (("window", "in their last 3 games"), ("qualifying", "last 3 games")):
        selected = base.tail(3) if scope == "window" else base
        selected = selected.loc[
            selected.opponent_team_abbr.eq("BOS") & selected.opponent_pts.ge(110)
        ]
        if scope == "qualifying":
            selected = selected.tail(3)
        expected = oracle["cases"][f"last3_{scope}_named_BOS_110"]["expected"]
        assert selected.game_id.astype(int).tolist() == expected["game_ids"]
        assert len(selected) == expected["games"]
        assert int(selected.wl.eq("W").sum()) == expected["wins"]
        assert int(selected.wl.eq("L").sum()) == expected["losses"]
        for stat, value in expected["sums"].items():
            assert int(selected[stat].sum()) == value
        cases.append(
            dict(
                id="owned-" + scope,
                kind="owned-window",
                scope=scope,
                query=f"Lakers record {phrase} against Celtics and Wizards when Celtics score at least 110 in 2023-24",
                expected=expected,
                condition=oracle["proposed_named_predicate"],
                text=["No Matching Results"]
                if not expected["games"]
                else [
                    "Los Angeles Lakers",
                    "2023-24",
                    "BOS, WAS",
                    "110+ BOS OPP PTS",
                    "Last 3 games",
                    "Select the last 3 games matching the conditions",
                ],
                forbidden=["Unavailable Filter"],
            )
        )
    return cases


def _owned_player_cases():
    oracle = json.loads(
        (ROOT / "tests/fixtures/list_owned_stats/primary-source-oracle.json").read_text()
    )
    for path, digest in oracle["sources"].items():
        assert hashlib.sha256(data_path(path).read_bytes()).hexdigest() == digest
    players = data_read_csv("raw/player_game_stats/2023-24_regular_season.csv")
    teams = data_read_csv("raw/team_game_stats/2023-24_regular_season.csv")
    candidates = players.loc[
        players.player_id.eq(2544) & players.opponent_team_abbr.isin(oracle["opponents"])
    ]
    candidates = (
        candidates.merge(
            teams[["game_id", "team_id", "pts", "wl"]].rename(columns={"pts": "team_pts"}),
            on=["game_id", "team_id"],
            validate="many_to_one",
        )
        .merge(
            teams[["game_id", "team_id", "pts"]].rename(
                columns={"team_id": "opponent_team_id", "pts": "opponent_pts"}
            ),
            on=["game_id", "opponent_team_id"],
            validate="many_to_one",
        )
        .sort_values(["game_date", "game_id"])
    )
    assert len(candidates) == len(oracle["candidate_rows"])
    for (_, row), expected in zip(candidates.iterrows(), oracle["candidate_rows"]):
        assert all(row[key] == value for key, value in expected.items())
    cases = []
    for owner, stat in (("Lakers", "team_pts"), ("Celtics", "opponent_pts")):
        selected = candidates.loc[candidates[stat].ge(120)]
        if owner == "Celtics":
            selected = selected.loc[selected.opponent_team_abbr.eq("BOS")]
        rows = [
            row for row in oracle["candidate_rows"] if row["game_id"] in selected.game_id.tolist()
        ]
        expected = dict(
            rows=rows,
            games=len(rows),
            wins=sum(row["wl"] == "W" for row in rows),
            losses=sum(row["wl"] == "L" for row in rows),
            sums={stat: sum(row[stat] for row in rows) for stat in ("pts", "reb", "ast")},
        )
        if owner == "Lakers":
            assert expected == {key: oracle["expected"][key] for key in expected}
        condition = dict(stat=stat, min_value=120, max_value=None)
        if owner == "Celtics":
            condition["opponent_team"] = "BOS"
        cases.append(
            dict(
                id="owned-player-team" if owner == "Lakers" else "owned-player-opponent",
                kind="owned-player",
                owner=owner,
                condition=condition,
                expected=expected,
                query=oracle["query"].replace("when Lakers score", f"when {owner} score"),
                text=[
                    "LeBron James",
                    "BOS, WAS",
                    "FILTER\n120+ TEAM PTS" if owner == "Lakers" else "FILTER\n120+ BOS OPP PTS",
                ],
            )
        )
    return cases


def _cases():
    unions = {case["id"]: case for case in _load_oracle("primary-oracle.json")}
    comparisons = _load_oracle("comparison-primary-oracle.json")
    cases = []
    for ident, source_id, query in [
        (
            "union-record",
            "MO-A1",
            "What was New York’s away record against Miami and Washington in 2023-24?",
        ),
        ("union-seasons", "MO-A2", unions["MO-A2"]["query"]),
        ("union-opponent-split", "MO-B1", unions["MO-B1"]["query"]),
    ]:
        frozen = unions[source_id]
        for bucket in frozen["buckets"]:
            _qualify_sample(bucket, frozen["seasons"])
        identity = _identity(frozen["subject"], frozen["seasons"], frozen["subject_id"])
        cases.append(
            dict(
                id=ident,
                query=query,
                kind=frozen["operation"],
                expected=frozen,
                identity=identity,
                text=[identity["team_name"], ", ".join(frozen["opponents"])]
                + (["Away"] if frozen["venue"] == "away" else []),
            )
        )
    for frozen in comparisons:
        player = frozen["kind"] == "player"
        for sample in frozen["summaries"]:
            _qualify_sample(sample, ["2023-24"], player=player)
        cases.append(
            dict(
                id="union-player-comparison" if player else "union-team-comparison",
                query=frozen["query"],
                kind="comparison",
                expected=frozen,
                text=(
                    [sample["name"] for sample in frozen["summaries"]]
                    if player
                    else frozen["entities"]
                )
                + [", ".join(frozen["opponents"])],
            )
        )

    _qualified_source()  # Exact CSV/PDF hashes, player states, dates and row values.
    ledger = data_read_csv("raw/player_game_availability/2023-24_regular_season.csv")
    # These named observations distinguish genuine empty from unknown coverage.
    for game, state in [(22300403, "did_not_play"), (22300684, "played")]:
        wood = ledger.loc[ledger.game_id.eq(game) & ledger.player_id.eq(1626174)]
        assert len(wood) == 1 and wood.iloc[0].team_id == ORACLE["team_id"]
        assert wood.iloc[0].participation_state == state
        assert wood.iloc[0].source_sha256 == ORACLE["retained_reports"][str(game)]["sha256"]
    gabe = ledger.loc[ledger.game_id.eq(22300684) & ledger.player_id.eq(1629216)]
    assert len(gabe) == 1 and gabe.iloc[0].team_id == ORACLE["team_id"]
    assert gabe.iloc[0].participation_state == "did_not_play"
    assert gabe.iloc[0].source_sha256 == ORACLE["retained_reports"]["22300684"]["sha256"]
    for ident, query, mode, game in [
        (
            "pair-out",
            "Lakers record vs Celtics with LeBron James and Anthony Davis both out in 2023-24",
            "without",
            22300684,
        ),
        (
            "pair-playing",
            "Lakers record vs Celtics with LeBron James and Anthony Davis both playing in 2023-24",
            "with",
            22300403,
        ),
    ]:
        raw = data_read_csv("raw/team_game_stats/2023-24_regular_season.csv")
        row = raw.loc[raw.game_id.eq(game) & raw.team_id.eq(ORACLE["team_id"])].iloc[0]
        cases.append(
            dict(
                id=ident,
                query=query,
                kind="pair-record",
                mode=mode,
                pair=PAIR,
                expected=dict(
                    game_id=game,
                    games=1,
                    wins=int(row.wl == "W"),
                    losses=int(row.wl == "L"),
                    means={stat: int(row[stat]) for stat in ("pts", "reb", "ast")},
                ),
                text=["Los Angeles Lakers", mode.upper() + " PLAYER", PAIR],
            )
        )
    cases += [
        dict(
            id="pair-player-bound",
            kind="pair-player",
            mode="without",
            pair=PAIR,
            query="Austin Reaves games with at least 20 points vs Celtics without LeBron James and Anthony Davis in 2023-24",
            text=["Austin Reaves", "WITHOUT PLAYER", PAIR, "20+ PTS"],
        ),
        dict(
            id="pair-qualified-empty",
            kind="empty",
            mode="without",
            pair="LeBron James and Christian Wood",
            query="Lakers record against Celtics with LeBron James and Christian Wood both out in 2023-24",
            text=["No Matching Results"],
            forbidden=["Unavailable Filter"],
        ),
        dict(
            id="pair-third-player",
            kind="guard",
            mode="without",
            pair=PAIR,
            query="Lakers record vs Celtics with LeBron James and Anthony Davis both out while Gabe Vincent plays in 2023-24",
            text=["Unavailable Filter"],
            forbidden=["No Matching Results"],
        ),
    ]
    cases += _owned_window_cases()
    cases += _owned_player_cases()
    for case in cases:
        case["forbidden"] = case.get("forbidden", []) + ["undefined", "NaN", "Infinity"]
        if case["kind"] not in ("empty", "guard", "owned-window"):
            case["text"].append("2023-24")
        if case["kind"] == "season_split":
            case["text"].append(", ".join(case["expected"]["seasons"]))
            case["forbidden"].append("2023-24 to 2025-26")
    assert len(cases) == len({case["id"] for case in cases}) == 14
    return cases


def _summary(actual, expected):
    for field in ("games", "wins", "losses"):
        assert actual[field] == expected[field]
    means = expected.get("means") or {
        stat: total / expected["games"] for stat, total in expected["sums"].items()
    }
    for stat, value in means.items():
        assert actual[stat + "_avg"] == pytest.approx(value, abs=0.001)


def _table(item, label):
    tables = [table for table in item["tables"] if table["label"] == label]
    assert len(tables) == 1
    return tables[0]


def _union(item, case, metadata, sections):
    frozen = case["expected"]
    assert metadata["opponents"] == frozen["opponents"]
    assert metadata["opponent"] == ", ".join(frozen["opponents"])
    assert not metadata.get("opponent_context")
    assert {"label": "Opponent", "value": metadata["opponent"], "kind": "team"} in metadata[
        "applied_filters"
    ]
    assert all(isinstance(value["value"], str) for value in metadata["applied_filters"])
    if case["kind"] == "comparison":
        player = frozen["kind"] == "player"
        assert item["payload"]["route"] == frozen["kind"] + "_compare"
        assert metadata["season"] == "2023-24"
        names = [sample["name"] for sample in frozen["summaries"]] if player else frozen["entities"]
        contexts = metadata["players_context" if player else "teams_context"]
        assert [context["player_id" if player else "team_abbr"] for context in contexts] == frozen[
            "entities"
        ]
        assert metadata["team"] == (None if player else ", ".join(names))
        rows = sections["summary"]
        assert len(rows) == len(frozen["summaries"]) == 2
        table = _table(item, "Comparison metrics")
        assert table["headers"][1:3] == names
        displayed = {row[0]: row for row in table["rows"]}
        metrics = {row["metric"]: row for row in sections["comparison"]}
        assert len(metrics) == len(sections["comparison"])
        for column, (actual, expected, name) in enumerate(zip(rows, frozen["summaries"], names), 1):
            assert actual["player_name" if player else "team_name"] == name
            _summary(actual, expected)
            for metric in ("games", "wins", "losses"):
                assert metrics[metric][name] == expected[metric]
            assert int(displayed["Games"][column]) == expected["games"]
            assert displayed["Record"][column] == f"{expected['wins']}-{expected['losses']}"
            for stat, value in expected["sums"].items():
                assert actual[stat + "_sum"] == value
                assert metrics[stat + "_sum"][name] == value
                assert metrics[stat + "_avg"][name] == pytest.approx(
                    value / expected["games"], abs=0.001
                )
                assert float(displayed[stat.upper() + " Avg"][column]) == pytest.approx(
                    value / expected["games"], abs=0.051
                )
        return
    assert metadata["team"] == frozen["subject"]
    assert metadata["team_context"] == case["identity"]
    assert sections["summary"][0]["team_name"] == frozen["subject_name"]
    if frozen["venue"]:
        assert {
            "label": "Location",
            "value": frozen["venue"].title(),
            "kind": "location",
        } in metadata["applied_filters"]
    assert item["text"].splitlines()[0] in (
        frozen["subject"],
        frozen["subject_name"],
        case["identity"]["team_name"],
    )
    if case["kind"] == "record":
        assert item["payload"]["route"] == "team_record"
        assert metadata["season"] == frozen["seasons"][0]
        _summary(sections["summary"][0], frozen["buckets"][0])
        assert len(sections["summary"]) == 1
        table = _table(item, "Team record")
        cells = dict(zip(table["headers"], table["rows"][0]))
        expected = frozen["buckets"][0]
        assert len(table["rows"]) == 1
        assert cells["W-L"] == f"{expected['wins']}-{expected['losses']}"
        assert int(cells["Games"]) == expected["games"]
        assert float(cells["PPG"]) == pytest.approx(expected["means"]["pts"], abs=0.051)
        return
    assert item["payload"]["route"] == "team_split_summary"
    assert metadata["split_type"] == ("season" if case["kind"] == "season_split" else "opponent")
    if case["kind"] == "season_split":
        assert metadata["season_list"] == frozen["seasons"]
    else:
        assert metadata["season"] == frozen["seasons"][0]
    rows, expected = sections["split_comparison"], frozen["buckets"]
    assert [row["bucket"] for row in rows] == [bucket["bucket"] for bucket in expected]
    table = _table(item, "Split buckets")
    assert len(table["rows"]) == len(rows)
    for actual, truth, values in zip(rows, expected, table["rows"]):
        _summary(actual, truth)
        cells = dict(zip(table["headers"], values))
        assert cells["Split"].casefold() == truth["bucket"].casefold()
        assert int(cells["GP"]) == truth["games"]
        assert cells["Record"] == f"{truth['wins']}-{truth['losses']}"
        for stat, value in truth["means"].items():
            assert float(cells[stat.upper()]) == pytest.approx(value, abs=0.051)
    assert sections["summary"][0]["games_total"] == sum(bucket["games"] for bucket in expected)


def _participation(item, case, metadata, sections):
    assert metadata["opponent"] == "BOS" and metadata["season"] == "2023-24"
    assert metadata[case["mode"] + "_player"] == case["pair"]
    assert metadata[("with" if case["mode"] == "without" else "without") + "_player"] is None
    assert metadata["player"] == ("Austin Reaves" if case["kind"] == "pair-player" else None)
    assert metadata["opponent_context"]["team_id"] == ORACLE["opponent_team_id"]
    if case["kind"] != "pair-player":
        assert metadata["team"] == "LAL"
        assert metadata["team_context"]["team_id"] == ORACLE["team_id"]
        assert not metadata.get("player_context")
    if case["kind"] in ("empty", "guard"):
        assert item["payload"]["result_status"] == "no_result" and not sections
        assert item["payload"]["result_reason"] == (
            "no_match" if case["kind"] == "empty" else "filter_not_supported"
        )
        if case["kind"] == "guard":
            assert "multi_player_availability" in metadata["unsupported_filters"]
        assert not any(table["rows"] for table in item["tables"])
        return
    assert {"label": case["mode"].title() + " player", "value": PAIR, "kind": "player"} in metadata[
        "applied_filters"
    ]
    if case["kind"] == "pair-player":
        assert item["payload"]["route"] == "player_game_finder"
        assert metadata["team"] is None and metadata["player_context"]["player_id"] == 1630559
        assert metadata["stat"] == "pts" and metadata["min_value"] == 20
        rows = sections["finder"]
        assert len(rows) == 1
        row = rows[0]
        assert row["player_name"] == "Austin Reaves"
        assert (
            int(row["game_id"]),
            row["player_id"],
            row["team_abbr"],
            row["opponent_team_abbr"],
        ) == (22300684, 1630559, "LAL", "BOS")
        for stat in ("pts", "reb", "ast"):
            assert row[stat] == ORACLE["selected_player"][stat]
        table = _table(item, "Game log")
        cells = dict(zip(table["headers"], table["rows"][0]))
        assert len(table["rows"]) == 1 and int(cells["PTS"]) == 32
        return
    assert item["payload"]["route"] == "team_record"
    assert metadata["team"] == "LAL" and metadata["team_context"]["team_id"] == ORACLE["team_id"]
    assert not metadata.get("player_context")
    assert len(sections["summary"]) == 1
    assert sections["summary"][0]["team_name"] == "Los Angeles Lakers"
    _summary(sections["summary"][0], case["expected"])
    rows = sections["game_log"]
    assert len(rows) == 1
    assert [int(rows[0][key]) for key in ("game_id", "team_id", "opponent_team_id")] == [
        case["expected"]["game_id"],
        ORACLE["team_id"],
        ORACLE["opponent_team_id"],
    ]
    table = _table(item, "Team record")
    cells = dict(zip(table["headers"], table["rows"][0]))
    assert len(table["rows"]) == 1
    assert cells["W-L"] == f"{case['expected']['wins']}-{case['expected']['losses']}"
    assert int(cells["Games"]) == 1 and float(cells["PPG"]) == case["expected"]["means"]["pts"]


def _owned_window(item, case, metadata, sections):
    assert item["payload"]["route"] == "team_record"
    assert metadata["team"] == "LAL" and metadata["team_context"]["team_id"] == 1610612747
    assert metadata["player"] is None and not metadata.get("player_context")
    assert metadata["season"] == "2023-24"
    assert metadata["opponent"] == "BOS, WAS" and metadata["opponents"] == ["BOS", "WAS"]
    assert not metadata.get("opponent_context")
    assert metadata["last_n"] == 3 and metadata["last_n_scope"] == case["scope"]
    assert metadata["conditions"] == metadata["threshold_conditions"] == [case["condition"]]
    filters = metadata["applied_filters"]
    assert {"label": "Opponent", "value": "BOS, WAS", "kind": "team"} in filters
    assert any(f["label"] == "BOS OPP PTS min" and float(f["value"]) == 110 for f in filters)
    expected = case["expected"]
    if not expected["games"]:
        assert item["payload"]["result_status"] == "no_result"
        assert item["payload"]["result_reason"] == "no_match" and not sections
        assert not any(table["rows"] for table in item["tables"])
        return
    assert item["payload"]["result_status"] == "ok"
    assert len(sections["summary"]) == 1
    _summary(sections["summary"][0], expected)
    rows = sections["game_log"]
    assert [int(row["game_id"]) for row in rows] == expected["game_ids"]
    assert len(rows) == 1
    row = rows[0]
    assert (row["team_id"], row["opponent_team_id"], row["opponent_pts"]) == (
        1610612747,
        1610612738,
        126,
    )
    for stat, value in expected["sums"].items():
        assert row[stat] == value
    table = _table(item, "Team record")
    assert len(table["rows"]) == 1
    cells = dict(zip(table["headers"], table["rows"][0]))
    assert cells["W-L"] == "0-1" and int(cells["Games"]) == 1 and float(cells["PPG"]) == 115


def _owned_player(item, case, metadata, sections):
    assert item["payload"]["route"] == "player_game_summary"
    assert metadata["player"] == "LeBron James" and metadata["player_context"]["player_id"] == 2544
    assert metadata["season"] == "2023-24"
    assert metadata["opponents"] == ["BOS", "WAS"] and metadata["opponent"] == "BOS, WAS"
    assert not metadata.get("opponent_context")
    assert metadata["stat"] == case["condition"]["stat"] and metadata["min_value"] == 120
    assert metadata["conditions"] == metadata["threshold_conditions"] == [case["condition"]]
    threshold_label = "team_pts min" if case["owner"] == "Lakers" else "BOS OPP PTS min"
    assert any(
        f["label"] == threshold_label and f["kind"] == "threshold" and float(f["value"]) == 120
        for f in metadata["applied_filters"]
    )
    assert metadata["team"] == ("LAL" if case["owner"] == "Lakers" else None)
    if case["owner"] == "Lakers":
        assert metadata["team_context"]["team_id"] == 1610612747
    else:
        assert not metadata.get("team_context")
    expected = case["expected"]
    assert len(sections["summary"]) == 1
    summary = sections["summary"][0]
    assert summary["player_name"] == "LeBron James"
    _summary(summary, expected)
    for stat, value in expected["sums"].items():
        assert summary[stat + "_sum"] == value
    rows = sections["game_log"]
    assert len(rows) == expected["games"]
    for actual, truth in zip(rows, expected["rows"]):
        for field in (
            "game_id",
            "player_id",
            "team_id",
            "opponent_team_id",
            "pts",
            "reb",
            "ast",
            "wl",
        ):
            assert actual[field] == truth[field]
    table = _table(item, "Game log")
    assert len(table["rows"]) == expected["games"]
    # Public game logs show newest first; API sections retain chronological order.
    for displayed, truth in zip(table["rows"], reversed(expected["rows"])):
        cells = dict(zip(table["headers"], displayed))
        assert truth["team_abbr"] in cells["TM"]
        assert truth["opponent_team_abbr"] in cells["Opp"]
        assert cells["W/L"] == truth["wl"]
        for stat in ("pts", "reb", "ast"):
            assert float(cells[stat.upper()]) == truth[stat]
    footers = {row[0]: dict(zip(table["headers"], row)) for row in table["footers"]}
    assert set(footers) == {"Average", "Total"}
    for stat, value in expected["sums"].items():
        assert float(footers["Total"][stat.upper()]) == value
        assert float(footers["Average"][stat.upper()]) == pytest.approx(
            value / expected["games"], abs=0.051
        )


def _validate_answers(receipt, cases):
    by_id, seen = {case["id"]: case for case in cases}, set()
    assert not receipt["failures"]
    for item in receipt["receipts"]:
        pair = item["viewport"], item["id"]
        assert pair not in seen
        seen.add(pair)
        case = by_id[item["id"]]
        assert item["query"] == item["payload"]["query"] == case["query"]
        assert (
            item["http"] == 200
            and not item["errors"]
            and not item["missing"]
            and not item["forbidden"]
        )
        assert item["overflow"]["document"] <= item["overflow"]["viewport"]
        assert item["assets"]
        assert all(value in item["text"] for value in case["text"])
        assert not any(value in item["text"] for value in case["forbidden"])
        metadata, sections = (
            item["payload"]["result"]["metadata"],
            item["payload"]["result"]["sections"],
        )
        assert metadata["season_type"] == "Regular Season"
        if case["kind"] not in ("empty", "guard", "owned-window"):
            assert item["payload"]["result_status"] == "ok"
        if case["id"].startswith("union-"):
            _union(item, case, metadata, sections)
        elif case["kind"] == "owned-window":
            _owned_window(item, case, metadata, sections)
        elif case["kind"] == "owned-player":
            _owned_player(item, case, metadata, sections)
        else:
            _participation(item, case, metadata, sections)
    assert seen == {(viewport, ident) for viewport in ("desktop", "mobile") for ident in by_id}


def test_deployed_union_pair_desktop_and_mobile(tmp_path):
    cases = _cases()
    receipt = _capture_browser(cases, tmp_path, "union-pair-browser")
    assert receipt["base"] == "https://nbatools.vercel.app"
    _validate_answers(receipt, cases)
