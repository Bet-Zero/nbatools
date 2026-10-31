"""Observed population accounting uses production guards, never missing-row DNP."""

import hashlib
import json
import shutil
from pathlib import Path

import pandas as pd
import pytest

from nbatools.commands import entity_resolution
from nbatools.data_source import reset_data_source_cache
from tools.participation_coverage import build_report

pytestmark = pytest.mark.engine
SEASON = "2025-26"
SUFFIX = f"{SEASON}_regular_season.csv"
TEAM = 1610612747
PLAYER = 2544
GENERATION = "coverage-fixture"


@pytest.fixture
def snapshot(tmp_path, monkeypatch):
    root = tmp_path / "data/generations" / GENERATION
    shutil.copytree(Path("qa/fixtures/query_engine_sample/data"), root)
    # An independent 82-row controlled population: 60 positive appearances,
    # five explicitly listed DNPs, seventeen unknowns. This is not NBA evidence.
    source_games = pd.read_csv(root / "raw/games" / SUFFIX)
    base = source_games.loc[source_games.home_team_id.eq(TEAM)].iloc[0]
    games = pd.DataFrame([base] * 82).reset_index(drop=True)
    games["game_id"] = range(22510000, 22510082)
    games["game_date"] = pd.date_range("2025-10-21", periods=82).strftime("%Y-%m-%d")
    games.to_csv(root / "raw/games" / SUFFIX, index=False)
    source_players = pd.read_csv(root / "raw/player_game_stats" / SUFFIX)
    identity = source_players[["player_id", "player_name", "season"]].drop_duplicates().copy()
    identity["first_seen"] = range(len(identity))
    identity_path = root / "metadata/player_names.csv"
    identity_path.parent.mkdir(parents=True, exist_ok=True)
    identity.to_csv(identity_path, index=False)
    person = source_players.loc[source_players.player_id.eq(PLAYER)].iloc[0]
    players = pd.DataFrame([person] * 60).reset_index(drop=True)
    players["game_id"] = games.game_id.iloc[:60].to_numpy()
    players["game_date"] = games.game_date.iloc[:60].to_numpy()
    players["team_id"] = TEAM
    players.to_csv(root / "raw/player_game_stats" / SUFFIX, index=False)
    source_teams = pd.read_csv(root / "raw/team_game_stats" / SUFFIX)
    prototype = source_teams.loc[source_teams.team_id.eq(TEAM)].iloc[0]
    teams = pd.DataFrame([prototype] * 82).reset_index(drop=True)
    teams["game_id"] = games.game_id
    teams["game_date"] = games.game_date
    teams["opponent_team_id"] = games.away_team_id
    reciprocal = teams.copy()
    reciprocal["team_id"] = games.away_team_id
    reciprocal["opponent_team_id"] = TEAM
    teams = pd.concat([teams, reciprocal], ignore_index=True)
    teams.to_csv(root / "raw/team_game_stats" / SUFFIX, index=False)
    availability = (
        games.iloc[60:65][["game_id", "game_date"]]
        .copy()
        .assign(
            team_id=TEAM,
            player_id=PLAYER,
            player_name="LeBron James",
            season=SEASON,
            season_type="Regular Season",
            participation_state="did_not_play",
            coverage_scope="listed_player_rows_only",
            source="nba_official_finalbox:20251021_GSWLAL",
            source_sha256="a" * 64,
        )
    )
    path = root / "raw/player_game_availability" / SUFFIX
    path.parent.mkdir(parents=True, exist_ok=True)
    availability.to_csv(path, index=False)
    monkeypatch.setenv("DATA_SOURCE", "local")
    monkeypatch.setenv("NBATOOLS_DATA_ROOT", str(tmp_path))
    monkeypatch.setenv("NBATOOLS_DATA_GENERATION", GENERATION)

    def no_fallback_scan(*args, **kwargs):
        raise AssertionError("Coverage report must not scan historical player files")

    monkeypatch.setattr(entity_resolution, "data_glob", no_fallback_scan)

    def bind():
        entries = []
        for file in sorted(root.rglob("*.csv")):
            raw = file.read_bytes()
            entries.append(
                dict(
                    path=file.relative_to(root).as_posix(),
                    size_bytes=len(raw),
                    sha256=hashlib.sha256(raw).hexdigest(),
                )
            )
        raw = json.dumps(dict(generation_id=GENERATION, files=entries)).encode()
        target = root / "metadata/generation_manifest.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
        reset_data_source_cache()
        return hashlib.sha256(raw).hexdigest()

    yield root, games, bind
    reset_data_source_cache()


def report(snapshot, **kwargs):
    _, _, bind = snapshot
    return build_report(
        generation=GENERATION,
        manifest_sha256=bind(),
        season=SEASON,
        team_id=TEAM,
        player_id=PLAYER,
        **kwargs,
    )


def test_unknowns_prevent_full_season_missed_total_and_minimal_request_is_exact(snapshot):
    result = report(snapshot)
    assert result["requested_games"] == result["observed_team_games"] == 82
    assert result["counts"] == dict(played=60, did_not_play=5, same_game_other_side=0, unknown=17)
    assert result["missed_games"] is None
    assert not result["complete_requested_population"]
    assert result["missing_keys"] == [
        dict(game_id=f"{row.game_id:010d}", game_date=row.game_date, team_id=TEAM, player_id=PLAYER)
        for row in snapshot[1].iloc[65:].itertuples()
    ]
    assert "independent full-season completeness unknown" in result["denominator"]


def test_complete_requested_slice_uses_explicit_dnp_and_positive_play(snapshot):
    result = report(snapshot, game_ids=[22510000, 22510060])
    assert result["complete_requested_population"]
    assert result["missed_games"] == 1
    assert result["counts"] == dict(played=1, did_not_play=1, same_game_other_side=0, unknown=0)
    assert result["scope"] == "selected_observed_team_games"
    assert result["missing_keys"] == []


def test_same_game_opposite_side_is_nonmembership_not_absence(snapshot):
    root, games, _ = snapshot
    path = root / "raw/player_game_availability" / SUFFIX
    rows = pd.read_csv(path)
    game = games.iloc[60]
    rows.loc[rows.game_id.eq(game.game_id), "team_id"] = int(game.away_team_id)
    rows.to_csv(path, index=False)
    result = report(snapshot, game_ids=[int(game.game_id)])
    assert result["counts"]["same_game_other_side"] == 1
    assert result["missed_games"] == 0


def test_other_game_same_date_and_zero_minutes_do_not_qualify_absence(snapshot):
    root, games, _ = snapshot
    path = root / "raw/player_game_stats" / SUFFIX
    players = pd.read_csv(path)
    players.loc[0, "minutes"] = 0
    players.loc[0, "game_date"] = games.game_date.iloc[65]
    players.to_csv(path, index=False)
    result = report(snapshot, game_ids=[22510000, 22510065])
    assert result["counts"]["unknown"] == 2
    assert result["missed_games"] is None


def test_conflicting_positive_observation_never_certifies_population(snapshot):
    root, _, _ = snapshot
    path = root / "raw/player_game_availability" / SUFFIX
    rows = pd.read_csv(path)
    rows.loc[0, "game_id"] = 22510000
    rows.loc[0, "game_date"] = "2025-10-21"
    rows.to_csv(path, index=False)
    result = report(snapshot, game_ids=[22510000])
    assert result["counts"]["unknown"] == 1
    assert "Contradictory" in result["games"][0]["qualification_error"]


@pytest.mark.parametrize("damage", ["hash", "provenance", "requested_game"])
def test_unqualified_inputs_cannot_produce_report(snapshot, damage):
    root, _, bind = snapshot
    digest = bind()
    if damage == "hash":
        (root / "raw/games" / SUFFIX).write_text("changed")
    if damage == "provenance":
        path = root / "raw/player_game_availability" / SUFFIX
        rows = pd.read_csv(path).assign(source="unqualified_source")
        rows.to_csv(path, index=False)
        digest = bind()
    with pytest.raises((ValueError, KeyError)):
        build_report(
            generation=GENERATION,
            manifest_sha256=digest,
            season=SEASON,
            team_id=TEAM,
            player_id=PLAYER,
            game_ids=[999] if damage == "requested_game" else None,
        )


@pytest.mark.parametrize("dataset", ["player_game_availability", "player_season_advanced"])
def test_unmanifested_optional_runtime_dependency_is_rejected(snapshot, dataset):
    root, _, bind = snapshot
    bind()
    relative = f"raw/{dataset}/{SUFFIX}"
    assert (root / relative).is_file()
    manifest_path = root / "metadata/generation_manifest.json"
    manifest = json.loads(manifest_path.read_bytes())
    manifest["files"] = [entry for entry in manifest["files"] if entry["path"] != relative]
    raw = json.dumps(manifest).encode()
    manifest_path.write_bytes(raw)
    reset_data_source_cache()
    with pytest.raises(ValueError, match="Unmanifested participation dependency"):
        build_report(
            generation=GENERATION,
            manifest_sha256=hashlib.sha256(raw).hexdigest(),
            season=SEASON,
            team_id=TEAM,
            player_id=PLAYER,
        )


@pytest.mark.parametrize(
    "damage", ["missing", "unmanifested", "tampered", "missing_first_seen", "bad_first_seen"]
)
def test_identity_metadata_is_bound_and_usable_without_fallback(snapshot, damage):
    root, _, bind = snapshot
    identity_path = root / "metadata/player_names.csv"
    if damage == "missing":
        identity_path.unlink()
    elif damage == "missing_first_seen":
        pd.read_csv(identity_path).drop(columns="first_seen").to_csv(identity_path, index=False)
    elif damage == "bad_first_seen":
        pd.read_csv(identity_path).assign(first_seen="invalid").to_csv(identity_path, index=False)
    digest = bind()
    if damage == "unmanifested":
        manifest_path = root / "metadata/generation_manifest.json"
        manifest = json.loads(manifest_path.read_bytes())
        manifest["files"] = [
            item for item in manifest["files"] if item["path"] != "metadata/player_names.csv"
        ]
        raw = json.dumps(manifest).encode()
        manifest_path.write_bytes(raw)
        digest = hashlib.sha256(raw).hexdigest()
    elif damage == "tampered":
        identity_path.write_text("player_id,player_name,first_seen\n999,Wrong Player,0\n")
    with pytest.raises(ValueError, match="identity metadata|Snapshot bytes"):
        build_report(
            generation=GENERATION,
            manifest_sha256=digest,
            season=SEASON,
            team_id=TEAM,
            player_id=PLAYER,
        )


def test_missing_legacy_venue_sides_preserve_all_observed_team_games(snapshot):
    root, _, _ = snapshot
    path = root / "raw/games" / SUFFIX
    catalog = pd.read_csv(path)
    catalog[["home_team_id", "away_team_id"]] = float("nan")
    # An unrelated final catalog game with unknown venue does not establish
    # involvement for the requested team or add a candidate game.
    unrelated = catalog.iloc[[0]].assign(game_id=22520000)
    pd.concat([catalog, unrelated], ignore_index=True).to_csv(path, index=False)
    teams_path = root / "raw/team_game_stats" / SUFFIX
    teams = pd.read_csv(teams_path)
    extra = teams.iloc[[0, 82]].copy()
    extra["game_id"] = 22520000
    extra["team_id"], extra["opponent_team_id"] = [1, 2], [2, 1]
    pd.concat([teams, extra], ignore_index=True).to_csv(teams_path, index=False)
    result = report(snapshot)
    assert result["observed_team_games"] == result["requested_games"] == 82
    assert result["counts"] == dict(played=60, did_not_play=5, same_game_other_side=0, unknown=17)
    assert len(result["missing_keys"]) == 17


@pytest.mark.parametrize(
    "damage",
    [
        "missing_own",
        "missing_venue_and_own",
        "missing_opponent",
        "duplicate_opponent",
        "wrong_opponent",
        "own_opponent",
        "date",
        "opponent_date",
        "not_final",
        "not_cataloged",
        "venue",
        "invalid_side",
        "scope",
    ],
)
def test_candidate_team_games_require_exact_reciprocal_canonical_evidence(snapshot, damage):
    root, _, _ = snapshot
    teams_path = root / "raw/team_game_stats" / SUFFIX
    catalog_path = root / "raw/games" / SUFFIX
    teams, catalog = pd.read_csv(teams_path), pd.read_csv(catalog_path)
    own = teams.index[teams.game_id.eq(22510000) & teams.team_id.eq(TEAM)][0]
    other = teams.index[teams.game_id.eq(22510000) & ~teams.team_id.eq(TEAM)][0]
    if damage in ["missing_own", "missing_venue_and_own"]:
        teams = teams.drop(index=own)
        if damage == "missing_venue_and_own":
            catalog[["home_team_id", "away_team_id"]] = float("nan")
    elif damage == "missing_opponent":
        teams = teams.drop(index=other)
    elif damage == "duplicate_opponent":
        teams = pd.concat([teams, teams.loc[[other]]], ignore_index=True)
    elif damage == "wrong_opponent":
        teams.loc[other, "opponent_team_id"] = 1610612738
    elif damage == "own_opponent":
        teams.loc[own, "opponent_team_id"] = TEAM
    elif damage in ["date", "opponent_date"]:
        teams.loc[own if damage == "date" else other, "game_date"] = "2020-01-01"
    elif damage == "not_final":
        catalog.loc[0, "is_final"] = False
    elif damage == "not_cataloged":
        catalog = catalog.iloc[1:]
    elif damage == "venue":
        catalog.loc[0, "away_team_id"] = 1610612738
    elif damage == "invalid_side":
        teams.loc[other, "team_id"] = -1
    elif damage == "scope":
        teams.loc[other, "season_type"] = "Playoffs"
    teams.to_csv(teams_path, index=False)
    catalog.to_csv(catalog_path, index=False)
    with pytest.raises(ValueError):
        report(snapshot)
