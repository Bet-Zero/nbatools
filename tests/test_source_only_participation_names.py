"""Synthetic listed identities without appearances; identity is not coverage."""

import shutil
from pathlib import Path

import pandas as pd
import pytest

from nbatools.commands import _participation_observations as observations
from nbatools.commands.natural_query import parse_query
from nbatools.data_source import reset_data_source_cache
from nbatools.dataframe_cache import FRAME_CACHE
from nbatools.query_service import execute_natural_query

pytestmark = [pytest.mark.query, pytest.mark.fixture_data]
NAME = "Sample Prospect"
SEASON = "2025-26"


@pytest.fixture
def listed_root(tmp_path, monkeypatch):
    root = tmp_path / "fx"
    shutil.copytree(Path("qa/fixtures/query_engine_sample"), root)
    stats = root / "data/raw/player_game_stats/2025-26_regular_season.csv"
    players = pd.read_csv(stats)
    # A different indexed Prospect must not own the source-only condition.
    players.loc[players.player_name.eq("Austin Reaves"), "player_name"] = "Other Prospect"
    players.to_csv(stats, index=False)
    teams = pd.read_csv(root / "data/raw/team_game_stats/2025-26_regular_season.csv")
    games = teams.loc[teams.team_abbr.eq("LAL")].sort_values("game_date").iloc[:2].copy()
    rows = games[["game_id", "game_date", "team_id"]].copy()
    rows = rows.assign(
        season=SEASON,
        season_type="Regular Season",
        player_id=999001,
        player_name=NAME,
        participation_state=["did_not_play", "played"],
        coverage_scope="listed_player_rows_only",
        source="nba_stats_structured_archive:" + "a" * 40 + ":0022500001",
        source_sha256="b" * 64,
    )
    target = root / "data/raw/player_game_availability/2025-26_regular_season.csv"
    target.parent.mkdir(parents=True, exist_ok=True)
    rows.to_csv(target, index=False)
    monkeypatch.setenv("DATA_SOURCE", "local")
    monkeypatch.setenv("NBATOOLS_DATA_ROOT", str(root))
    reset_data_source_cache()
    yield root, target, rows, games
    reset_data_source_cache()


def bounded(query, games):
    day = games.game_date.iloc[0]
    return f"{query} in {SEASON} from {day} to {day}"


@pytest.mark.parametrize(
    "condition",
    [
        "without Sample Prospect",
        "while Sample Prospect did not play",
        "when Sample Prospect was out",
    ],
)
def test_source_only_condition_preserves_team_and_exact_game(listed_root, condition):
    _, _, _, games = listed_root
    query = bounded(f"Lakers record {condition}", games)
    parsed = parse_query(query)
    assert parsed["route"] == "team_record"
    assert parsed["route_kwargs"]["without_player"] == NAME
    assert not parsed.get("entity_ambiguity")
    result = execute_natural_query(query)
    assert result.result_status == "ok", result.metadata
    sections = result.result.to_dict()["sections"]
    expected = games.iloc[0]
    summary = sections["summary"][0]
    assert (summary["games"], summary["wins"], summary["losses"], summary["pts_avg"]) == (
        1,
        int(expected.wl == "W"),
        int(expected.wl == "L"),
        expected.pts,
    )
    assert [int(row["game_id"]) for row in sections["game_log"]] == [int(expected.game_id)]


@pytest.mark.parametrize(
    "query",
    [
        "LeBron James games with at least 1 point without Sample Prospect",
        "Without Sample Prospect, LeBron James games with at least 1 point",
    ],
)
def test_source_condition_never_replaces_primary_player(listed_root, query):
    root, _, _, games = listed_root
    query = bounded(query, games)
    parsed = parse_query(query)
    assert parsed["route_kwargs"]["player"] == "LeBron James"
    assert parsed["route"] == "player_game_finder"
    assert parsed["route_kwargs"]["without_player"] == NAME
    result = execute_natural_query(query)
    assert result.result_status == "ok", result.metadata
    actual = result.result.to_dict()["sections"]["finder"]
    expected = pd.read_csv(root / "data/raw/player_game_stats/2025-26_regular_season.csv")
    expected = expected.loc[
        expected.player_name.eq("LeBron James") & expected.game_id.eq(games.game_id.iloc[0])
    ].iloc[0]
    assert [(int(r["game_id"]), r["player_name"], r["pts"]) for r in actual] == [
        (int(expected.game_id), "LeBron James", expected.pts)
    ]


def test_identity_does_not_supply_missing_game_coverage_or_medical_state(listed_root):
    _, _, _, games = listed_root
    result = execute_natural_query(f"Lakers record without {NAME} in {SEASON}")
    assert result.result_status == "no_result"
    for condition in [f"when {NAME} was injured", f"without {NAME} and Blorg Example"]:
        result = execute_natural_query(bounded(f"Lakers record {condition}", games))
        assert result.result_status != "ok", result.metadata


def test_source_identity_is_scoped_and_not_a_primary_or_surname_index(listed_root):
    assert (
        observations.resolve_observed_name(NAME.lower(), [SEASON], "Regular Season").resolved
        == NAME
    )
    assert not observations.resolve_observed_name(
        "Prospect", [SEASON], "Regular Season"
    ).is_confident
    assert not observations.resolve_observed_name(NAME, ["2024-25"], "Regular Season").is_confident
    assert not observations.resolve_observed_name(NAME, [SEASON], "Playoffs").is_confident
    assert not observations.resolve_observed_name(
        NAME + " extra", [SEASON], "Regular Season"
    ).is_confident
    parsed = parse_query(f"{NAME} stats in {SEASON}")
    assert parsed.get("route_kwargs", {}).get("player") != NAME


@pytest.mark.parametrize("conflict", ["observed", "index"])
def test_duplicate_full_name_identity_is_unresolved(listed_root, monkeypatch, conflict):
    _, target, rows, games = listed_root
    if conflict == "observed":
        other = rows.copy().assign(player_id=999002)
        pd.concat([rows, other]).to_csv(target, index=False)
        reset_data_source_cache()
    else:
        monkeypatch.setattr(observations, "player_ids_for_name", lambda name: {"999002"})
    resolution = observations.resolve_observed_name(NAME, [SEASON], "Regular Season")
    assert resolution.is_ambiguous
    result = execute_natural_query(bounded(f"Lakers record without {NAME}", games))
    assert result.result_status != "ok", result.metadata


def test_unknown_state_and_opposite_side_remain_execution_checks(listed_root):
    _, target, rows, games = listed_root
    for changed in [rows.assign(participation_state="unknown"), rows.assign(team_id=1610612738)]:
        changed.to_csv(target, index=False)
        FRAME_CACHE.clear()
        reset_data_source_cache()
        assert observations.resolve_observed_name(NAME, [SEASON], "Regular Season").resolved == NAME
        result = execute_natural_query(bounded(f"Lakers record without {NAME}", games))
        assert result.result_status != "ok", result.metadata


def test_normalized_full_source_name_is_already_read_in_while_clause(listed_root):
    _, target, rows, games = listed_root
    rows.player_name = "Kellan Brówn"
    rows.to_csv(target, index=False)
    query = bounded("Lakers record while Kellan Brown did not play", games)
    result = execute_natural_query(query)
    assert result.result_status == "ok", result.metadata
    assert result.result.to_dict()["sections"]["summary"][0]["games"] == 1


def test_raw_answer_checker_preserves_source_condition_and_primary(listed_root):
    from tools.raw_query_answer_qa import run_case

    query = bounded("LeBron James games without Sample Prospect", listed_root[3])
    checked = run_case(
        dict(
            id="source_only_fixture",
            query=query,
            category="participation",
            priority="p1",
            expected_status="ok",
        ),
        top_rows=5,
    )
    assert checked["expectation_results"]["fail_count"] == 0, checked
    assert NAME in str(checked["query_output_snapshot"])
    assert checked["sections"]["summary"][0]["player_name"] == "LeBron James"


def test_malformed_observations_fail_closed_before_execution(listed_root):
    _, target, rows, games = listed_root
    rows[["player_id", "player_name"]].to_csv(target, index=False)
    result = execute_natural_query(bounded("Lakers record without Sample Prospect", games))
    assert result.result_status == "no_result", result.metadata


@pytest.fixture
def listed_pair(listed_root):
    root, target, rows, games = listed_root
    other = rows.copy().assign(player_id=999002, player_name="Alternate Newcomer")
    pd.concat([rows, other]).to_csv(target, index=False)
    return root, target, pd.concat([rows, other]), games


@pytest.mark.parametrize(
    "condition",
    [
        "without Sample Prospect and Alternate Newcomer",
        "without Alternate Newcomer and Sample Prospect",
        "with Sample Prospect and Alternate Newcomer both out",
    ],
)
def test_two_source_only_conditions_answer_complete_pair(listed_pair, condition):
    games = listed_pair[3]
    query = bounded(f"Lakers record with at least 1 point {condition}", games)
    result = execute_natural_query(query)
    assert result.result_status == "ok", result.metadata
    sections = result.result.to_dict()["sections"]
    assert [int(r["game_id"]) for r in sections["game_log"]] == [int(games.game_id.iloc[0])]
    assert sections["summary"][0]["pts_avg"] == games.pts.iloc[0]
    assert all(name in result.metadata["without_player"] for name in [NAME, "Alternate Newcomer"])


def test_leading_source_only_pair_does_not_replace_primary(listed_pair):
    query = bounded(
        "Without Sample Prospect and Alternate Newcomer, LeBron James games with at least 1 point",
        listed_pair[3],
    )
    parsed = parse_query(query)
    assert parsed["route_kwargs"]["player"] == "LeBron James"
    result = execute_natural_query(query)
    assert result.result_status == "ok", result.metadata
    sections = result.result.to_dict()["sections"]
    rows = sections.get("finder", sections.get("game_log"))
    assert [(int(r["game_id"]), r["player_name"], r["pts"]) for r in rows] == [
        (int(listed_pair[3].game_id.iloc[0]), "LeBron James", 30)
    ]


def test_shared_surname_fallback_cannot_collapse_two_source_names(listed_pair):
    _, target, rows, games = listed_pair
    rows.loc[rows.player_name.eq("Alternate Newcomer"), "player_name"] = "Second Prospect"
    rows.to_csv(target, index=False)
    result = execute_natural_query(
        bounded("Lakers record without Sample Prospect and Second Prospect", games)
    )
    assert result.result_status == "ok", result.metadata
    assert result.result.to_dict()["sections"]["summary"][0]["games"] == 1
    assert result.metadata["without_player"] == "Sample Prospect and Second Prospect"


@pytest.mark.parametrize(
    "damage",
    ["unknown_second", "missing_second", "global_conflict", "extra_source_condition", "medical"],
)
def test_source_pair_never_hides_missing_identity_state_or_extra_condition(
    listed_pair, monkeypatch, damage
):
    _, target, rows, games = listed_pair
    query = "Lakers record without Sample Prospect and Alternate Newcomer"
    if damage == "unknown_second":
        rows.loc[rows.player_name.eq("Alternate Newcomer"), "participation_state"] = "unknown"
    elif damage == "missing_second":
        rows = rows.loc[~rows.player_name.eq("Alternate Newcomer")]
    elif damage == "global_conflict":
        monkeypatch.setattr(
            observations,
            "player_ids_for_name",
            lambda name: (
                {"999003"}
                if name == "alternate newcomer" or name == "Alternate Newcomer"
                else set()
            ),
        )
    elif damage == "extra_source_condition":
        third = rows.iloc[:2].copy().assign(player_id=999004, player_name="Third Newcomer")
        rows = pd.concat([rows, third])
        query += " with Third Newcomer"
    else:
        query += " both injured"
    rows.to_csv(target, index=False)
    result = execute_natural_query(bounded(query, games))
    assert result.result_status != "ok", result.metadata


def test_leading_exact_pair_does_not_need_wrong_initial_primary_appearances(listed_pair):
    root, target, rows, games = listed_pair
    rows.loc[rows.player_name.eq(NAME), "player_name"] = "Ivo Curry"
    rows.loc[rows.player_name.eq("Alternate Newcomer"), "player_name"] = "Ken Curry"
    rows.to_csv(target, index=False)
    path = root / "data/raw/player_game_stats/2025-26_regular_season.csv"
    players = pd.read_csv(path)
    players.loc[~players.player_name.eq("Stephen Curry")].to_csv(path, index=False)
    reset_data_source_cache()
    query = bounded(
        "Without Ivo Curry and Ken Curry, LeBron James games with at least 2 points", games
    )
    result = execute_natural_query(query)
    assert result.result_status == "ok", result.metadata
    assert result.metadata["player"] == "LeBron James"
    sections = result.result.to_dict()["sections"]
    actual = sections.get("finder", sections.get("game_log"))
    assert [(int(r["game_id"]), r["pts"]) for r in actual] == [(int(games.game_id.iloc[0]), 30)]


@pytest.mark.parametrize("prefix", [False, True])
@pytest.mark.parametrize("second", ["missing", "ambiguous", "extra"])
def test_genuinely_unindexed_unread_pair_cannot_become_unfiltered_player_answer(
    listed_pair, monkeypatch, prefix, second
):
    _, target, rows, games = listed_pair
    rows.loc[rows.player_name.eq(NAME), "player_name"] = "Ivo Quill"
    rows.loc[rows.player_name.eq("Alternate Newcomer"), "player_name"] = "Ken Umber"
    if second == "missing":
        rows = rows.loc[~rows.player_name.eq("Ken Umber")]
    elif second == "ambiguous":
        rows = pd.concat(
            [rows, rows.loc[rows.player_name.eq("Ken Umber")].assign(player_id=999003)]
        )
    else:
        rows = pd.concat([rows, rows.iloc[:2].assign(player_id=999004, player_name="Third Fable")])
    rows.to_csv(target, index=False)
    condition = "without Ivo Quill and Ken Umber"
    query = (
        f"{condition}, LeBron James games with at least 2 points"
        if prefix
        else f"LeBron James games with at least 2 points {condition}"
    )
    if second == "extra":
        query += " with Third Fable"
    result = execute_natural_query(bounded(query, games))
    assert result.result_status == "no_result", result.metadata
    assert not result.result.to_dict()["sections"].get("finder")
    assert not result.result.to_dict()["sections"].get("game_log")


def test_genuinely_unknown_single_absence_is_not_an_unfiltered_player_summary(listed_root):
    query = bounded("LeBron James stats without Ivo Quill", listed_root[3])
    result = execute_natural_query(query)
    assert result.result_status == "no_result", result.metadata


@pytest.mark.parametrize("separator", [", ", " , ", " ; "])
def test_third_unindexed_comma_name_cannot_disappear_from_source_pair(listed_pair, separator):
    _, target, rows, games = listed_pair
    rows.loc[rows.player_name.eq(NAME), "player_name"] = "Ivo Quill"
    rows.loc[rows.player_name.eq("Alternate Newcomer"), "player_name"] = "Ken Umber"
    rows.to_csv(target, index=False)
    games = listed_pair[3]
    result = execute_natural_query(
        bounded(
            f"LeBron James games with at least 2 points without Ivo Quill and Ken Umber{separator}Third Fable",
            games,
        )
    )
    assert result.result_status == "no_result", result.metadata


@pytest.mark.parametrize(
    "second_name", ["J Umber", "J. Umber", "Ken Middle Umber", "Ken Middle Initial Umber"]
)
@pytest.mark.parametrize("known", [True, False])
def test_complete_name_grammar_is_preserved_before_scalar_lookup(listed_pair, second_name, known):
    _, target, rows, games = listed_pair
    rows.loc[rows.player_name.eq(NAME), "player_name"] = "Ivo Quill"
    rows.loc[rows.player_name.eq("Alternate Newcomer"), "player_name"] = second_name
    if not known:
        rows = rows.loc[rows.player_name.eq("Ivo Quill")]
    rows.to_csv(target, index=False)
    query = bounded(
        f"LeBron James games with at least 2 points without Ivo Quill and {second_name}", games
    )
    result = execute_natural_query(query)
    assert result.result_status == ("ok" if known else "no_result"), result.metadata
    if known:
        assert result.metadata["without_player"] == f"Ivo Quill and {second_name}"
        sections = result.result.to_dict()["sections"]
        actual = sections.get("finder", sections.get("game_log"))
        assert [(int(r["game_id"]), r["pts"]) for r in actual] == [(int(games.game_id.iloc[0]), 30)]


@pytest.mark.parametrize("arity", [1, 2])
@pytest.mark.parametrize("operation", ["games", "averages"])
def test_resolved_absence_predicates_do_not_choose_output_grain(listed_pair, arity, operation):
    condition = "without Sample Prospect" + (" and Alternate Newcomer" if arity == 2 else "")
    query = bounded(f"LeBron James {operation} with at least 29 points {condition}", listed_pair[3])
    result = execute_natural_query(query)
    assert result.result_status == "ok", result.metadata
    sections = result.result.to_dict()["sections"]
    if operation == "games":
        assert result.route == "player_game_finder"
        assert [(int(r["game_id"]), r["pts"]) for r in sections["finder"]] == [
            (int(listed_pair[3].game_id.iloc[0]), 30)
        ]
    else:
        assert result.route == "player_game_summary"
        assert (sections["summary"][0]["games"], sections["summary"][0]["pts_avg"]) == (1, 30)


@pytest.mark.parametrize("arity", [1, 2])
@pytest.mark.parametrize("day_index", [0, 1])
@pytest.mark.parametrize("subject", ["Lakers record", "LeBron James games with at least 1 point"])
def test_source_only_presence_selects_known_played_or_explicit_zero(
    listed_pair, arity, day_index, subject
):
    games = listed_pair[3]
    names = NAME + (" and Alternate Newcomer" if arity == 2 else "")
    day = games.game_date.iloc[day_index]
    prefix = "How many " if subject.startswith("LeBron") else ""
    query = f"{prefix}{subject} with {names} in {SEASON} on {day}"
    result = execute_natural_query(query)
    assert result.result_status == (
        "no_result" if subject.startswith("Lakers") and not day_index else "ok"
    ), result.metadata
    assert result.metadata["with_player"] == names
    sections = result.result.to_dict()["sections"]
    if subject.startswith("Lakers"):
        if day_index:
            assert sections["summary"][0]["games"] == 1
        else:
            assert result.result.result_reason == "no_match"
        actual = sections.get("game_log", [])
    else:
        assert result.route == "player_game_finder"
        assert sections["count"][0]["count"] == day_index
        actual = sections.get("finder", [])
    assert [int(r["game_id"]) for r in actual] == (
        [int(games.game_id.iloc[1])] if day_index else []
    )


@pytest.mark.parametrize(
    "damage", ["unknown", "missing", "other_game", "wrong_date", "conflicting_appearance"]
)
def test_source_presence_never_turns_unqualified_coverage_into_zero(listed_root, damage):
    root, target, rows, games = listed_root
    if damage == "unknown":
        rows.participation_state = "unknown"
    elif damage == "missing":
        rows = rows.iloc[1:]
    elif damage == "other_game":
        rows.game_id += 900
    elif damage == "wrong_date":
        rows.game_date = "2025-01-01"
    else:
        path = root / "data/raw/player_game_stats/2025-26_regular_season.csv"
        players = pd.read_csv(path)
        other = (
            players.loc[players.player_name.eq("LeBron James")]
            .iloc[:1]
            .assign(player_id=999001, player_name=NAME)
        )
        pd.concat([players, other]).to_csv(path, index=False)
    rows.to_csv(target, index=False)
    result = execute_natural_query(bounded(f"Lakers record with {NAME}", games))
    assert result.result_status == "no_result", result.metadata


def test_source_presence_pair_qualifies_unknown_before_false_sibling(listed_pair):
    _, target, rows, games = listed_pair
    rows.loc[rows.player_name.eq("Alternate Newcomer"), "participation_state"] = "unknown"
    rows.to_csv(target, index=False)
    for names in [
        "Sample Prospect and Alternate Newcomer",
        "Alternate Newcomer and Sample Prospect",
    ]:
        result = execute_natural_query(bounded(f"Lakers record with {names}", games))
        assert result.result_status == "no_result", result.metadata


@pytest.mark.parametrize("prefix", [True, False])
def test_unindexed_presence_pair_cannot_drop_unresolved_second_name(listed_pair, prefix):
    _, target, rows, games = listed_pair
    rows.loc[rows.player_name.eq(NAME), "player_name"] = "Ivo Quill"
    rows = rows.loc[rows.player_name.eq("Ivo Quill")]
    rows.to_csv(target, index=False)
    condition = "with Ivo Quill and Ken Umber"
    primary = "LeBron James games with at least 1 point"
    query = f"{condition}, {primary}" if prefix else f"{primary} {condition}"
    result = execute_natural_query(bounded(query, games))
    assert result.result_status == "no_result", result.metadata


@pytest.mark.parametrize("state", ["played", "unknown"])
def test_later_appearance_cannot_erase_exact_game_source_state(listed_root, state):
    root, target, rows, games = listed_root
    path = root / "data/raw/player_game_stats/2025-26_regular_season.csv"
    players = pd.read_csv(path)
    later = (
        players.loc[players.player_name.eq("LeBron James")]
        .iloc[2:3]
        .assign(player_id=999001, player_name=NAME)
    )
    assert not later.empty
    pd.concat([players, later]).to_csv(path, index=False)
    rows.loc[rows.game_id.eq(games.game_id.iloc[1]), "participation_state"] = state
    rows.to_csv(target, index=False)
    query = f"How many LeBron James games with {NAME} in {SEASON} on {games.game_date.iloc[1]}"
    result = execute_natural_query(query)
    assert result.result_status == ("ok" if state == "played" else "no_result"), result.metadata
    if state == "played":
        sections = result.result.to_dict()["sections"]
        assert sections["count"][0]["count"] == 1
        assert [int(r["game_id"]) for r in sections["finder"]] == [int(games.game_id.iloc[1])]


def test_unknown_presence_after_stat_clause_is_not_dropped(listed_root):
    query = bounded(
        "How many LeBron James games with at least 1 point with Ivo Quill", listed_root[3]
    )
    result = execute_natural_query(query)
    assert result.result_status == "no_result", result.metadata


@pytest.mark.parametrize(
    "condition", ["with Ivo Quill with Sample Prospect", "with Sample Prospect with Ivo Quill"]
)
def test_resolved_presence_cannot_hide_extra_unknown_name(listed_root, condition):
    query = bounded(f"How many LeBron James games {condition}", listed_root[3])
    result = execute_natural_query(query)
    assert result.result_status == "no_result", result.metadata


@pytest.mark.parametrize("damage", ["team", "date"])
def test_source_played_conflicting_exact_game_appearance_is_unavailable(listed_root, damage):
    root, _, _, games = listed_root
    path = root / "data/raw/player_game_stats/2025-26_regular_season.csv"
    players = pd.read_csv(path)
    other = players.loc[
        players.player_name.eq("LeBron James") & players.game_id.eq(games.game_id.iloc[1])
    ].assign(player_id=999001, player_name=NAME)
    assert len(other) == 1
    if damage == "team":
        other.team_id = 1610612738
    else:
        other.game_date = "2025-01-01"
    pd.concat([players, other]).to_csv(path, index=False)
    query = f"How many LeBron James games with {NAME} in {SEASON} on {games.game_date.iloc[1]}"
    result = execute_natural_query(query)
    assert result.result_status == "no_result", result.metadata
