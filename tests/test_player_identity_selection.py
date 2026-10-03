"""A named player's rows are that one player's rows, chosen by ``player_id``.

The real 1996-97+ data has twelve names shared by two different players and
five players stored under two spellings (see ``test_player_identity_real_data``
for those exact rows). Filtering by name merged the first group (a "Mike James
career" answer added two careers together) and split the second ("Bobby
Portis" lost his 2024-25 games stored as "Bobby Portis Jr."; leaderboards
listed him twice). These data-free tests use controlled frames shaped like
those cases, with ids and spellings taken from the real data.
"""

from __future__ import annotations

import pandas as pd
import pytest

from nbatools.commands import entity_resolution
from nbatools.commands._parse_helpers import detect_lineup_query
from nbatools.commands._player_identity import (
    canonicalize_player_names,
    player_game_ids,
    select_player_rows,
)
from nbatools.commands.entity_resolution import resolve_players_in_query

# (player_id, stored name) pairs in season order, as the index reads them.
ROSTER = [
    ("2229", "Mike James"),
    ("1628455", "Mike James"),
    ("121", "Patrick Ewing"),
    ("201607", "Patrick Ewing"),
    ("200766", "Marcus Williams"),
    ("201173", "Marcus Williams"),
    ("1626171", "Bobby Portis"),
    ("1626171", "Bobby Portis Jr."),
    ("202685", "Jonas Valančiūnas"),
    ("202685", "Jonas Valanciunas"),
    ("1631311", "Lester Quinones"),
    ("1631311", "Lester Quiñones"),
    ("1628973", "Jalen Brunson"),
    ("1628404", "Josh Hart"),
    ("1630166", "Deni Avdija"),
    ("201950", "Jrue Holiday"),
    ("202331", "Paul George"),
    ("2544", "LeBron James"),
    # Real players whose surnames are ordinary words, and a second Hart.
    ("2133", "Jason Hart"),
    ("203516", "Cleanthony Early"),
    ("1501", "Derek Strong"),
    ("201567", "Kevin Love"),
]


@pytest.fixture
def roster_index(monkeypatch, request):
    """Install the data-backed identity caches for ``ROSTER``."""
    entity_resolution.reset_player_index()
    request.addfinalizer(entity_resolution.reset_player_index)
    monkeypatch.setattr(entity_resolution, "data_source_cache_key", lambda: "roster-test")
    ids_by_name: dict[str, set[str]] = {}
    name_by_id: dict[str, str] = {}
    for player_id, name in ROSTER:
        key = entity_resolution._normalize_for_matching(name)
        ids_by_name.setdefault(key, set()).add(player_id)
        name_by_id[player_id] = entity_resolution._preferred_spelling(
            name_by_id.get(player_id), name
        )
    entity_resolution._player_index_generation_key = "roster-test"
    entity_resolution._player_names_cache = {name for _, name in ROSTER}
    entity_resolution._player_ids_by_name_cache = {
        key: frozenset(ids) for key, ids in ids_by_name.items()
    }
    entity_resolution._player_name_by_id_cache = name_by_id


def _rows(player_id: int, name: str, team: str, seasons_games: dict[str, int]) -> list[dict]:
    rows = []
    for season, games in seasons_games.items():
        year = int(season[:4])
        for n in range(games):
            rows.append(
                {
                    "game_id": f"{player_id}-{season}-{n}",
                    "game_date": pd.Timestamp(year=year, month=11, day=1) + pd.Timedelta(days=n),
                    "season": season,
                    "player_id": player_id,
                    "player_name": name,
                    "team_abbr": team,
                    "team_name": team,
                    "pts": 10,
                }
            )
    return rows


def _frame(*groups: list[dict]) -> pd.DataFrame:
    return pd.DataFrame([row for group in groups for row in group])


def test_shared_name_keeps_one_player_with_most_games_and_says_so(roster_index):
    df = _frame(
        _rows(2229, "Mike James", "DET", {"2005-06": 8, "2006-07": 6}),
        _rows(1628455, "Mike James", "PHX", {"2017-18": 4}),
    )
    notes: list[str] = []

    rows = select_player_rows(df, "mike james", notes=notes)

    assert set(rows["player_id"]) == {2229}
    assert len(rows) == 14
    assert len(notes) == 1
    assert "More than one player is named Mike James" in notes[0]
    assert "DET, 2005-06 to 2006-07, 14 games" in notes[0]
    assert "PHX, 2017-18, 4 games" in notes[0]


def test_shared_name_in_scope_of_one_player_is_unambiguous(roster_index):
    """A season where only one Mike James played answers about him, silently."""
    df = _frame(
        _rows(1628455, "Mike James", "PHX", {"2017-18": 4}),
        _rows(1628973, "Jalen Brunson", "DAL", {"2017-18": 5}),
    )
    notes: list[str] = []

    rows = select_player_rows(df, "Mike James", notes=notes)

    assert set(rows["player_id"]) == {1628455}
    assert notes == []


def test_team_narrows_a_shared_name_to_the_player_on_that_team(roster_index):
    df = _frame(
        _rows(200766, "Marcus Williams", "NJN", {"2007-08": 9}),
        _rows(201173, "Marcus Williams", "SAS", {"2007-08": 2}),
    )
    notes: list[str] = []

    spurs = select_player_rows(df, "Marcus Williams", team="SAS", notes=notes)
    default = select_player_rows(df, "Marcus Williams")

    assert set(spurs["player_id"]) == {201173}
    assert len(spurs) == 2
    assert "SAS, 2007-08, 2 games" in notes[0]
    assert set(default["player_id"]) == {200766}


def test_tie_on_games_goes_to_the_most_recent_player(roster_index):
    df = _frame(
        _rows(121, "Patrick Ewing", "NYK", {"2001-02": 3}),
        _rows(201607, "Patrick Ewing", "NOH", {"2010-11": 3}),
    )

    rows = select_player_rows(df, "Patrick Ewing")

    assert set(rows["player_id"]) == {201607}


@pytest.mark.parametrize(
    ("typed", "expected_games"),
    [
        ("Bobby Portis", 9),
        ("bobby portis jr", 9),
        ("Bobby Portis Jr.", 9),
    ],
)
def test_every_spelling_of_one_player_is_kept(roster_index, typed, expected_games):
    df = _frame(
        _rows(1626171, "Bobby Portis", "MIL", {"2024-25": 5}),
        _rows(1626171, "Bobby Portis Jr.", "MIL", {"2025-26": 4}),
    )

    rows = select_player_rows(df, typed)

    assert len(rows) == expected_games


def test_spelling_known_only_from_other_seasons_still_finds_the_player(roster_index):
    """Rows in scope are all "Bobby Portis Jr."; the typed name is the old one."""
    df = _frame(_rows(1626171, "Bobby Portis Jr.", "MIL", {"2025-26": 4}))

    assert len(select_player_rows(df, "Bobby Portis")) == 4


def test_accent_variants_of_one_player_are_one_player(roster_index):
    df = _frame(
        _rows(202685, "Jonas Valančiūnas", "TOR", {"2015-16": 3}),
        _rows(202685, "Jonas Valanciunas", "WAS", {"2024-25": 2}),
    )

    assert len(select_player_rows(df, "jonas valanciunas")) == 5
    assert len(select_player_rows(df, "Jonas Valančiūnas")) == 5


def test_canonical_name_is_the_latest_spelling_keeping_accents(roster_index):
    df = _frame(
        _rows(1626171, "Bobby Portis", "MIL", {"2024-25": 2}),
        _rows(1626171, "Bobby Portis Jr.", "MIL", {"2024-25": 1}),
        _rows(202685, "Jonas Valanciunas", "WAS", {"2024-25": 1}),
        _rows(1631311, "Lester Quinones", "GSW", {"2023-24": 1}),
        _rows(2229, "Mike James", "DET", {"2005-06": 1}),
    )

    out = canonicalize_player_names(df)

    names = out.groupby("player_id")["player_name"].unique().map(list).to_dict()
    assert names == {
        1626171: ["Bobby Portis Jr."],
        202685: ["Jonas Valančiūnas"],
        1631311: ["Lester Quiñones"],
        2229: ["Mike James"],
    }
    # One leaderboard row per player, not one per spelling.
    assert out.groupby(["player_id", "player_name"]).ngroups == 4
    assert df["player_name"].tolist()[0] == "Bobby Portis", "input frame is not mutated"


def test_cross_filters_use_the_same_single_player(roster_index):
    df = _frame(
        _rows(2229, "Mike James", "DET", {"2005-06": 8}),
        _rows(1628455, "Mike James", "PHX", {"2005-06": 2}),
    )

    pairs = player_game_ids(df, "Mike James")
    on_phx = player_game_ids(df, "Mike James", team="PHX")

    assert set(pairs["team_abbr"]) == {"DET"} and len(pairs) == 8
    assert set(on_phx["team_abbr"]) == {"PHX"} and len(on_phx) == 2


def test_frames_without_ids_still_filter_by_name(roster_index):
    df = pd.DataFrame({"player_name": ["Mike James", "Josh Hart"], "pts": [1, 2]})

    assert select_player_rows(df, "mike james")["pts"].tolist() == [1]


# ---------------------------------------------------------------------------
# Several players named in one question (lineups)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        # Neither player has a curated alias: the scan used to find nobody.
        ("lineups with deni avdija and jrue holiday", ["Deni Avdija", "Jrue Holiday"]),
        ("jalen brunson and josh hart together", ["Jalen Brunson", "Josh Hart"]),
        # A curated nickname still works next to a data full name.
        ("lineups with pg and deni avdija", ["Paul George", "Deni Avdija"]),
    ],
)
def test_lineup_members_resolve_through_the_shared_resolver(roster_index, text, expected):
    assert resolve_players_in_query(text) == expected


def test_lineup_query_carries_data_backed_members(roster_index):
    parsed = detect_lineup_query("lineups with deni avdija and jrue holiday 2024-25")

    assert parsed is not None
    assert parsed["lineup_members"] == ["Deni Avdija", "Jrue Holiday"]
    assert parsed["unit_size"] == 2
    assert parsed["route"] == "lineup_summary"


def test_shared_last_names_never_become_a_lineup_member(roster_index):
    """ "james" is two players here: it is kept as typed, never guessed or dropped."""
    parsed = detect_lineup_query("lineups with james and brunson")
    assert parsed["lineup_members"] == ["james", "Jalen Brunson"]


@pytest.mark.parametrize(
    "text",
    [
        "knicks lineups early in the season",
        "lineups with a strong net rating",
        "lineups fans love",
        "best 5-man lineups with at least 200 minutes",
    ],
)
def test_ordinary_words_that_are_surnames_are_not_lineup_members(roster_index, text):
    parsed = detect_lineup_query(text)
    assert parsed is not None
    assert parsed["lineup_members"] == []


def test_listed_unique_last_names_resolve_in_question_order(roster_index):
    parsed = detect_lineup_query("best lineups with avdija and brunson")
    assert parsed["lineup_members"] == ["Deni Avdija", "Jalen Brunson"]


def test_a_listed_shared_last_name_keeps_the_lineup_size(roster_index):
    """Josh and Jason Hart both exist: the lineup stays two members, not Brunson alone."""
    parsed = detect_lineup_query("knicks lineups with brunson and hart")
    assert parsed["lineup_members"] == ["Jalen Brunson", "hart"]
    assert parsed["unit_size"] == 2


def test_float_ids_match_the_index(roster_index):
    df = _frame(_rows(1626171, "Bobby Portis Jr.", "MIL", {"2025-26": 3}))
    df["player_id"] = df["player_id"].astype(float)

    assert len(select_player_rows(df, "Bobby Portis")) == 3
    assert set(canonicalize_player_names(df)["player_name"]) == {"Bobby Portis Jr."}


def test_player_count_matches_every_spelling(roster_index, monkeypatch):
    """ "How many 20-point games did Bobby Portis have" counts his "Jr." games too."""
    from nbatools.commands import player_occurrence_leaders
    from nbatools.query_service import _apply_count_intent

    df = _frame(
        _rows(1626171, "Bobby Portis", "MIL", {"2024-25": 5}),
        _rows(1626171, "Bobby Portis Jr.", "MIL", {"2024-25": 4}),
    )
    df["game_id"] = [f"g{n}" for n in range(len(df))]
    df["pts"] = 25
    df["is_home"] = 1
    df["is_away"] = 0
    df["wl"] = "W"
    df = canonicalize_player_names(df)
    monkeypatch.setattr(
        player_occurrence_leaders, "load_player_games_for_seasons", lambda *a, **k: df
    )

    result = player_occurrence_leaders.build_result(
        stat="pts", min_value=20, season="2024-25", player="Bobby Portis", min_games=1
    )
    counted = _apply_count_intent(
        result, {"count_intent": True, "player": "Bobby Portis"}, allow_stat_total=False
    )

    assert counted.to_dict()["sections"]["count"][0]["count"] == 9


# ---------------------------------------------------------------------------
# Published name list (metadata/player_names.csv) instead of the full scan
# ---------------------------------------------------------------------------


def _patch_source(monkeypatch, published: pd.DataFrame | None, season_rows: list[pd.DataFrame]):
    entity_resolution.reset_player_index()
    monkeypatch.setattr(entity_resolution, "data_source_cache_key", lambda: "published-test")
    globbed: list[bool] = []

    def fake_exists(path):
        return published is not None and str(path) == str(entity_resolution.PLAYER_NAMES_PATH)

    def fake_glob(pattern):
        globbed.append(True)
        return [f"raw/player_game_stats/{n}.csv" for n in range(len(season_rows))]

    def fake_read(path, *args, **kwargs):
        if str(path) == str(entity_resolution.PLAYER_NAMES_PATH):
            return published.astype(str)
        frame = season_rows[int(str(path).rsplit("/", 1)[1].split(".")[0])].astype(str)
        usecols = kwargs.get("usecols")
        return frame[[c for c in frame.columns if usecols(c)]] if callable(usecols) else frame

    monkeypatch.setattr(entity_resolution, "data_exists", fake_exists)
    monkeypatch.setattr(entity_resolution, "data_glob", fake_glob)
    monkeypatch.setattr(entity_resolution, "data_read_csv", fake_read)
    return globbed


def test_published_name_list_replaces_the_full_scan(monkeypatch, request):
    request.addfinalizer(entity_resolution.reset_player_index)
    published = pd.DataFrame(
        {
            "player_id": [1626171, 2229, 1628455, 1626171],
            "player_name": ["Bobby Portis", "Mike James", "Mike James", "Bobby Portis Jr."],
            "season": ["2023-24", "2005-06", "2017-18", "2025-26"],
        }
    )
    globbed = _patch_source(monkeypatch, published, [])

    assert entity_resolution.player_ids_for_name("Mike James") == {"2229", "1628455"}
    assert entity_resolution.player_ids_for_name("bobby portis") == {"1626171"}
    assert entity_resolution.canonical_player_names_by_id()["1626171"] == "Bobby Portis Jr."
    assert globbed == []


def test_name_list_without_ids_falls_back_to_the_full_scan(monkeypatch, request):
    request.addfinalizer(entity_resolution.reset_player_index)
    published = pd.DataFrame({"player_name": ["Mike James"]})
    season = pd.DataFrame({"player_id": [2229], "player_name": ["Mike James"], "pts": [1]})
    globbed = _patch_source(monkeypatch, published, [season])

    assert entity_resolution.player_ids_for_name("Mike James") == {"2229"}
    assert globbed == [True]
