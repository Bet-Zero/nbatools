"""Original K08 cases supported by the existing published served-default slice.

Expected samples come directly from pinned raw keys and previously qualified
source observations. No query consumer or participation filter builds an oracle.
Literal current-season questions are deliberately outside this finite subset.
"""

import ast
import hashlib
import io
import json
from pathlib import Path

import pandas as pd
import pytest

from nbatools.data_source import data_generation_context, data_path
from nbatools.development_data import selected_snapshot
from tests.test_opponent_played_real_data import ORACLE as OPPONENT

ROOT = Path(__file__).resolve().parents[1]
PROGRAM = ROOT / "working/nba-tools-completion-program"
EVIDENCE = PROGRAM / "source-evidence/core1-k08-served-default-20261110"
BASE = "availability-lebron-season-v1-20261031"
MANIFEST = "3073653a50872a4c25bb573c3b4c0540e6e3204e8a4caef5c548eb2dff1e0cf3"
SEASON = "2025-26"
LAL, BOS, LEBRON, TATUM = 1610612747, 1610612738, 2544, 1628369
STATS = ("pts", "reb", "ast", "fgm", "fga", "fg3m", "fg3a", "ftm", "fta", "tov")
ORIGINAL = PROGRAM / "source-evidence/owned-boolean-20261106/independent/k08-original-46.json"
QUALIFICATION = PROGRAM / "source-evidence/k08-lebron-remaining/qualification.json"
CASES = [
    dict(ordinal=7, query="games LeBron missed", route="game_finder", kind="missed"),
    dict(
        ordinal=8,
        query="how many home games did LeBron miss",
        route="game_finder",
        kind="home_missed",
    ),
    dict(
        ordinal=23,
        query="Lakers record vs Celtics with Tatum out",
        route="team_record",
        kind="record",
    ),
    dict(
        ordinal=24,
        query="Lakers record vs Celtics without Tatum",
        route="team_record",
        kind="record",
    ),
    dict(
        ordinal=25,
        query="Lakers record vs Celtics when Tatum sits",
        route="team_record",
        kind="record",
    ),
    dict(
        ordinal=30,
        query="Lakers 120 point games vs Celtics with Tatum out",
        route="game_summary",
        kind="threshold",
    ),
    dict(
        ordinal=31,
        query="Lakers 120 point games vs Celtics without Tatum",
        route="game_summary",
        kind="threshold",
    ),
    dict(
        ordinal=32,
        query="Lakers points per game vs Celtics without Tatum",
        route="game_summary",
        kind="summary",
    ),
    dict(
        ordinal=41,
        query="LeBron James stats vs Celtics without Jayson Tatum",
        route="player_game_summary",
        kind="player",
    ),
]


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def original_bindings():
    original = json.loads(ORIGINAL.read_bytes())
    assert original["count"] == len(original["node_ids"]) == 46
    assert (
        sha(("\n".join(original["node_ids"]) + "\n").encode())
        == "acc3d675811c80641aec64d60d76e90f7e6d8eb4dba66904fef5eff616cc1f96"
    )
    # ID41 is a non-parametrized original node, so bind its actual query literal
    # from the preserved test function instead of inventing a new wording.
    source_path = ROOT / "tests/test_c1_teammate_names.py"
    raw = source_path.read_bytes()
    assert sha(raw) == "beabe05ca617a9510ca1aedebdc685290b8eed6f75e380976added0dba834d98"
    source = raw.decode()
    (function,) = [
        node
        for node in ast.parse(source).body
        if isinstance(node, ast.FunctionDef) and node.name == "test_an_opponent_sitting"
    ]
    fragment = ast.get_source_segment(source, function)
    assert (
        fragment
        and sha(fragment.encode())
        == "99d5c8d9da62acdb5afd0bab0336482014cde6d42f4a8bc3bfebcc2e01f3c566"
    )
    (original_41_query,) = [
        node.args[0].value
        for node in ast.walk(function)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "_ok"
        and len(node.args) == 1
        and isinstance(node.args[0], ast.Constant)
        and isinstance(node.args[0].value, str)
    ]
    out = []
    for case in CASES:
        node = original["node_ids"][case["ordinal"] - 1]
        if case["ordinal"] == 41:
            assert node == "tests/test_c1_teammate_names.py::test_an_opponent_sitting"
            assert case["query"] == original_41_query
        else:
            assert case["query"] in node
        out.append(dict(case, id=f"original-k08-{case['ordinal']:02d}", original_node_id=node))
    assert len(out) == 9 and {c["ordinal"] for c in out} == {7, 8, 23, 24, 25, 30, 31, 32, 41}
    return out


def equivalent_structured_kwargs(case):
    """Use the independently qualified sample, not a data-free parser fallback.

    Source qualification proves the complete unique LAL cohort (82 games,
    60 played plus 22 explicit DNP). An unscoped membership chronology is a
    distinct contract and remains unavailable without its dated evidence.
    """
    kwargs = dict(
        season=SEASON,
        season_type="Regular Season",
        without_player="Jayson Tatum",
        opponent="BOS",
        team="LAL",
    )
    if case["kind"] in {"missed", "home_missed"}:
        return dict(
            season=SEASON,
            season_type="Regular Season",
            team="LAL",
            without_player="LeBron James",
            home_only=case["kind"] == "home_missed",
            limit=100000,
            sort_by="game_date",
        )
    if case["kind"] == "player":
        kwargs.pop("team")
        kwargs["player"] = "LeBron James"
    elif case["route"] == "game_summary":
        kwargs["stat"] = "pts"
        if case["kind"] == "threshold":
            kwargs["min_value"] = 120
    return kwargs


def _raw_frame(relative, entries, sources):
    raw = data_path(relative).read_bytes()
    entry = entries[relative]
    assert sha(raw) == entry["sha256"] and len(raw) == entry["size_bytes"]
    sources[relative] = dict(sha256=sha(raw), size_bytes=len(raw))
    return pd.read_csv(io.BytesIO(raw))


def _sample(frame, *, player=False):
    columns = [
        "game_id",
        "team_id",
        "game_date",
        "season",
        "season_type",
        "team_abbr",
        "opponent_team_id",
        "opponent_team_abbr",
        "wl",
        *STATS,
    ]
    if player:
        columns += ["player_id", "player_name"]
    assert set(columns).issubset(frame), (
        f"Missing sample fields: {sorted(set(columns) - set(frame))}; actual columns: {list(frame.columns)}"
    )
    assert frame[list(STATS)].apply(pd.to_numeric, errors="coerce").notna().all().all()
    keys = ["game_id", "team_id"] + (["player_id"] if player else [])
    assert not frame.duplicated(keys).any()
    return dict(
        keys=keys,
        rows=json.loads(
            frame.sort_values(keys)[columns].to_json(orient="records", double_precision=15)
        ),
        games=len(frame),
        wins=int(frame.wl.eq("W").sum()),
        losses=int(frame.wl.eq("L").sum()),
        sums={stat: float(frame[stat].sum()) for stat in STATS},
        means={stat: float(frame[stat].mean()) if len(frame) else None for stat in STATS},
    )


def player_team_context(players, teams, catalog):
    """Attach team-owned outcome facts through complete independent raw keys."""
    keys = ["game_id", "team_id", "game_date", "season", "season_type"]
    shared = ["team_abbr", "opponent_team_id", "opponent_team_abbr", "is_home", "is_away"]
    required = {*keys, *shared, "player_id", "player_name", *STATS}
    assert required.issubset(players), (
        f"Raw player fields missing: {sorted(required - set(players))}; actual: {list(players.columns)}"
    )
    assert players[list(required)].notna().all().all(), (
        "Incomplete raw player identity/context/metric"
    )
    assert not players.duplicated(["game_id", "player_id"]).any(), "Duplicate raw player key"
    assert {*keys, *shared, "wl"}.issubset(teams)
    assert not teams.duplicated(["game_id", "team_id"]).any(), "Duplicate team key"
    facts = teams[[*keys, *shared, "wl"]].rename(columns={c: "_team_" + c for c in [*shared, "wl"]})
    out = players.merge(
        facts, on=keys, how="left", validate="many_to_one", indicator="_team_join", sort=False
    )
    assert len(out) == len(players) and out._team_join.eq("both").all(), (
        "Incomplete exact game/team/date context join"
    )
    for field in shared:
        assert out[field].eq(out["_team_" + field]).all(), f"Contradictory team context: {field}"
    assert out._team_wl.isin(["W", "L"]).all(), "Unknown team outcome"
    if "wl" in players:
        assert out.wl.eq(out._team_wl).all(), "Contradictory existing player outcome"
    out["wl"] = out._team_wl
    out = out.drop(columns=["_team_join", *["_team_" + c for c in [*shared, "wl"]]])
    game_keys = ["game_id", "game_date", "season", "season_type"]
    identity = [
        "team_a_id",
        "team_b_id",
        "home_team_id",
        "away_team_id",
        "home_away_designation_trusted",
        "is_final",
    ]
    assert {*game_keys, *identity}.issubset(catalog)
    assert not catalog.game_id.duplicated().any(), "Duplicate final-game catalog key"
    final = catalog[[*game_keys, *identity]]
    joined = out.merge(
        final,
        on=game_keys,
        how="left",
        validate="many_to_one",
        indicator="_catalog_join",
        sort=False,
    )
    assert len(joined) == len(players) and joined._catalog_join.eq("both").all(), (
        "Incomplete exact final catalog join"
    )
    assert joined.is_final.astype(str).str.lower().isin(["true", "1", "1.0"]).all(), (
        "Player sample has nonfinal game"
    )
    own_home = joined.team_id.eq(joined.home_team_id) & joined.opponent_team_id.eq(
        joined.away_team_id
    )
    own_away = joined.team_id.eq(joined.away_team_id) & joined.opponent_team_id.eq(
        joined.home_team_id
    )
    side_a = joined.team_id.eq(joined.team_a_id) & joined.opponent_team_id.eq(joined.team_b_id)
    side_b = joined.team_id.eq(joined.team_b_id) & joined.opponent_team_id.eq(joined.team_a_id)
    assert (side_a | side_b).all(), "Player/team participants disagree with final catalog"
    trusted = (
        joined.home_away_designation_trusted.astype(str).str.lower().isin(["true", "1", "1.0"])
    )
    assert (own_home | own_away | ~trusted).all(), (
        "Trusted player/team sides disagree with final catalog"
    )
    home_flag = joined.is_home.astype(str).str.lower().isin(["true", "1", "1.0"])
    away_flag = joined.is_away.astype(str).str.lower().isin(["true", "1", "1.0"])
    assert home_flag.eq(own_home & trusted).all() and away_flag.eq(own_away & trusted).all(), (
        "Player home/away disagrees with final catalog"
    )
    return out


def source_oracle():
    """Qualify original inputs, then independently select all nine exact samples."""
    assert selected_snapshot() is None
    assert (
        sha(QUALIFICATION.read_bytes())
        == "772db656d061d8b459e62c24aa939a9cae13479492eb5c1d7f1b1a6973fb9c1c"
    )
    assert (
        sha((ROOT / "tests/fixtures/opponent_played/source_oracle.json").read_bytes())
        == "5a37f23e80b4799512cd336a81550260f2101e08895319cc58f356e33b3ed9d9"
    )
    accepted = json.loads(QUALIFICATION.read_bytes())
    with data_generation_context() as generation:
        assert generation == BASE
        manifest_raw = data_path("metadata/generation_manifest.json").read_bytes()
        assert sha(manifest_raw) == MANIFEST
        manifest = json.loads(manifest_raw)
        assert manifest["generation_id"] == BASE and len(manifest["files"]) == 775
        entries = {entry["path"]: entry for entry in manifest["files"]}
        sources = {}
        frames = {
            kind: _raw_frame(f"raw/{kind}/{SEASON}_regular_season.csv", entries, sources)
            for kind in (
                "games",
                "team_game_stats",
                "player_game_stats",
                "player_game_availability",
            )
        }
        teams, players, observed, catalog = [
            frames[k]
            for k in ("team_game_stats", "player_game_stats", "player_game_availability", "games")
        ]
        players = player_team_context(players, teams, catalog)
        lal = teams.loc[teams.team_id.eq(LAL)].copy()
        assert len(lal) == 82 and not lal.game_id.duplicated().any()
        assert lal.season.eq(SEASON).all() and lal.season_type.eq("Regular Season").all()
        own = players.loc[players.player_id.eq(LEBRON) & players.minutes.gt(0)]
        assert len(own) == 60 and own.team_id.eq(LAL).all() and not own.game_id.duplicated().any()
        dnp = observed.loc[
            observed.player_id.eq(LEBRON) & observed.participation_state.eq("did_not_play")
        ]
        assert dnp.team_id.eq(LAL).all() and not dnp.game_id.duplicated().any()
        absent = set(dnp.game_id.astype(int))
        assert absent == set(accepted["missed_game_ids"])
        assert set(own.game_id).isdisjoint(absent) and set(own.game_id) | absent == set(lal.game_id)
        for row in dnp.itertuples():
            (candidate,) = lal.loc[lal.game_id.eq(row.game_id)].itertuples()
            assert row.game_date == candidate.game_date
            assert row.coverage_scope == "listed_player_rows_only"
            assert isinstance(row.source_comment, str) and row.source_comment.strip()
            assert row.source_sha256 and any(row.source_sha256 in path for path in entries)
        missed = lal.loc[lal.game_id.isin(absent)].copy()
        home = missed.loc[missed.is_home.astype(str).str.lower().isin(["true", "1", "1.0"])].copy()
        assert set(home.game_id) == set(accepted["home_missed_game_ids"]) and len(home) == 11
        fixture = next(c for c in OPPONENT["primary_cases"] if c["query"].endswith(SEASON))
        pair = lal.loc[lal.opponent_team_id.eq(BOS)].copy()
        assert sorted(pair.game_id.astype(int)) == fixture["candidate_game_ids"]
        assert len(pair) == 2
        for fact in fixture["observations"]:
            rows = observed.loc[observed.game_id.eq(fact["game_id"]) & observed.player_id.eq(TATUM)]
            assert len(rows) == 1
            actual = rows.iloc[0]
            for key, value in fact.items():
                assert actual[key] == value
            assert actual.participation_state == "did_not_play" and actual.team_id == BOS
            assert players.loc[
                players.game_id.eq(actual.game_id)
                & players.player_id.eq(TATUM)
                & players.minutes.gt(0)
            ].empty
            relative = "raw/player_game_availability_sources/" + fact["source_sha256"] + ".pdf"
            raw = data_path(relative).read_bytes()
            assert sha(raw) == fact["source_sha256"] == entries[relative]["sha256"]
            sources[relative] = dict(sha256=sha(raw), size_bytes=len(raw))
            game = catalog.loc[catalog.game_id.eq(actual.game_id)]
            assert len(game) == 1 and str(game.iloc[0].is_final).lower() in {"1", "true", "1.0"}
            assert game.iloc[0].game_date == actual.game_date
            assert {int(game.iloc[0].home_team_id), int(game.iloc[0].away_team_id)} == {LAL, BOS}
            sides = teams.loc[teams.game_id.eq(actual.game_id)]
            assert len(sides) == 2 and set(sides.team_id) == {LAL, BOS}
            for side in sides.itertuples():
                other = sides.loc[sides.team_id.eq(side.opponent_team_id)].iloc[0]
                assert (
                    side.pts - other.pts == side.plus_minus and side.game_date == actual.game_date
                )
        threshold = pair.loc[pair.pts.ge(120)].copy()
        assert threshold.empty
        lebron_pair = own.loc[own.game_id.isin(pair.game_id)].copy()
        assert lebron_pair.game_id.astype(int).tolist() == [22500823]
        washington = players.loc[
            players.player_id.eq(1629023) & players.minutes.gt(0) & players.reb.gt(0)
        ].sort_values(["game_date", "game_id"])
        assert not washington.empty
        washington = washington.iloc[:1].copy()
        person = washington.iloc[0]
        assert person.player_name in {"P.J. Washington", "PJ Washington"}
        final = catalog.loc[catalog.game_id.eq(person.game_id)]
        assert len(final) == 1 and final.iloc[0].game_date == person.game_date
        assert str(final.iloc[0].is_final).lower() in {"true", "1", "1.0"}
        assert person.team_id in {final.iloc[0].home_team_id, final.iloc[0].away_team_id}
        supplement = dict(
            id="published-washington-ownership-control",
            classification="supplemental_changed_runtime_control_not_an_original46_case",
            query=f"P.J. Washington stats on {person.game_date} in {SEASON}",
            route="player_game_summary",
            kwargs=dict(
                player="P.J. Washington",
                season=SEASON,
                start_date=person.game_date,
                end_date=person.game_date,
            ),
            expected=_sample(washington, player=True),
        )
        samples = dict(
            missed=missed,
            home_missed=home,
            record=pair,
            threshold=threshold,
            summary=pair,
            player=lebron_pair,
        )
        cases = original_bindings()
        for case in cases:
            case["expected"] = _sample(samples[case["kind"]], player=case["kind"] == "player")
            case["kwargs"] = equivalent_structured_kwargs(case)
        # Keep ID26's entire multi-opponent population visible as a distinct
        # unfinished requirement; no other-game or omitted-player inference.
        id26 = lal.loc[lal.opponent_team_abbr.isin(["BOS", "NYK"])]
        unresolved_26 = []
        for row in id26.itertuples():
            facts = observed.loc[observed.game_id.eq(row.game_id) & observed.player_id.eq(TATUM)]
            unresolved_26.append(
                dict(
                    game_id=int(row.game_id),
                    game_date=row.game_date,
                    subject_team_id=LAL,
                    opponent_team_id=int(row.opponent_team_id),
                    opponent=row.opponent_team_abbr,
                    exact_listed_state=facts.iloc[0].participation_state
                    if len(facts) == 1
                    else "unknown",
                    qualified_dated_membership_not_inferred=True,
                )
            )
        return dict(
            generation=BASE,
            manifest_sha256=MANIFEST,
            original46_ids_sha256=sha(
                ("\n".join(json.loads(ORIGINAL.read_bytes())["node_ids"]) + "\n").encode()
            ),
            sources=sources,
            cases=cases,
            supplemental_ownership=supplement,
            accepted_lebron_qualification_sha256=sha(QUALIFICATION.read_bytes()),
            id26_open_scope=dict(
                original_id=26,
                query="Lakers record vs Celtics and Knicks without Tatum",
                candidate_games=unresolved_26,
                dated_membership_file_in_manifest=f"raw/player_team_membership/{SEASON}.csv"
                in entries,
                accepted=False,
                missing_fact="Qualified exclusive dated membership or named-team nonmembership on every selected Knicks date; another game's Boston appearance/inactive listing is not a contract substitute.",
            ),
            literal_current_accepted=False,
            all46_accepted=False,
        )


def assert_ownership_answer(body, control, *, natural=True):
    """A separate published positive must exercise the changed name ownership."""
    assert body["route"] == "player_game_summary"
    assert body["query"] == (control["query"] if natural else "structured:player_game_summary")
    assert body["result_status"] == "ok" and body["result_reason"] is None, compact_actual(body)
    meta, sections = body["result"]["metadata"], body["result"]["sections"]
    assert meta["season"] == SEASON and meta["player"] == "P.J. Washington"
    assert meta["player_context"]["player_id"] == 1629023
    assert meta["team"] is None and meta["opponent"] is None
    assert not any(
        meta.get(field) for field in ("without_player", "with_player", "quarter", "half")
    )
    assert not meta.get("data_quality") and not meta.get("unsupported_filters")
    assert meta["start_date"] == meta["end_date"] == control["kwargs"]["start_date"]
    expected = control["expected"]
    assert expected["games"] == 1 and expected["sums"]["reb"] > 0
    (summary,) = sections["summary"]
    assert summary["games"] == 1 and summary["reb_avg"] == expected["sums"]["reb"]
    for stat in STATS:
        assert summary[stat + "_avg"] == pytest.approx(expected["means"][stat], abs=0.001)
    (row,) = sections["game_log"]
    (original,) = expected["rows"]
    for key in ("game_id", "team_id", "player_id"):
        assert int(row[key]) == int(original[key])
    assert str(row["game_date"])[:10] == original["game_date"]
    assert row["reb"] == original["reb"] > 0


def compact_actual(body):
    """Portable failure diagnostics without full data rows or environment values."""
    meta = (body.get("result") or {}).get("metadata") or {}
    return json.dumps(
        dict(
            route=body.get("route"),
            query=body.get("query"),
            result_status=body.get("result_status"),
            result_reason=body.get("result_reason"),
            notes=body.get("notes"),
            metadata_notes=meta.get("notes"),
            team=meta.get("team"),
            without_player=meta.get("without_player"),
            season=meta.get("season"),
        ),
        default=str,
    )[:2000]


def assert_answer(body, case, *, natural=True):
    """Check identities, complete row keys, numerators, denominators and labels."""
    assert body["route"] == case["route"], compact_actual(body)
    assert body["query"] == (case["query"] if natural else "structured:" + case["route"]), (
        compact_actual(body)
    )
    expected = case["expected"]
    if expected["games"]:
        assert body["result_status"] == "ok" and body["result_reason"] is None, compact_actual(body)
    else:
        assert body["result_status"] == "no_result" and body["result_reason"] == "no_match", (
            compact_actual(body)
        )
    metadata, sections = body["result"]["metadata"], body["result"]["sections"]
    assert (
        metadata["season"] == SEASON
        and not metadata.get("start_season")
        and not metadata.get("end_season")
    )
    assert not metadata.get("data_quality") and not metadata.get("unsupported_filters")
    assert metadata["without_player"] == (
        "LeBron James" if case["kind"] in {"missed", "home_missed"} else "Jayson Tatum"
    )
    if not expected["games"]:
        assert not sections
        assert metadata["team"] == "LAL" and metadata["opponent"] == "BOS"
        assert metadata["stat"] == "pts" and metadata["min_value"] == 120
        return
    if case["kind"] in {"missed", "home_missed"}:
        assert metadata["team"] == "LAL"
        actual = sections["finder"]
        if natural:
            assert sections["count"] == [{"count": expected["games"]}]
    else:
        actual = sections["game_log"]
        assert metadata["opponent"] == "BOS"
        if case["kind"] == "player":
            assert metadata["player"] == "LeBron James"
            assert metadata["player_context"]["player_id"] == LEBRON
        else:
            assert metadata["team"] == "LAL" and metadata["team_context"]["team_id"] == LAL
        (summary,) = sections["summary"]
        for field in ("games", "wins", "losses"):
            assert summary[field] == expected[field]
        for stat in STATS:
            assert summary[stat + "_avg"] == pytest.approx(expected["means"][stat], abs=0.001)
            if stat + "_sum" in summary:
                assert summary[stat + "_sum"] == pytest.approx(expected["sums"][stat], abs=0.001)
    keys = expected["keys"]

    def actual_key(row):
        # The established team finder contract exposes team_abbr rather than
        # team_id. Bind that public identity to the source's qualified LAL key;
        # summary/player logs continue to require their explicit numeric IDs.
        if case["route"] == "game_finder" and "team_id" not in row:
            assert row["team_abbr"] == "LAL" and keys == ["game_id", "team_id"]
            return int(row["game_id"]), LAL
        return tuple(int(row[k]) for k in keys)

    assert len(actual) == expected["games"]
    assert {actual_key(row) for row in actual} == {
        tuple(int(row[k]) for k in keys) for row in expected["rows"]
    }
    by_key = {tuple(int(row[k]) for k in keys): row for row in expected["rows"]}
    for row in actual:
        original = by_key[actual_key(row)]
        assert row["season"] == SEASON and row["team_abbr"] == "LAL"
        assert str(row["game_date"])[:10] == original["game_date"]
        for stat in STATS:
            if stat in row:
                assert row[stat] == pytest.approx(original[stat], abs=0.001)
