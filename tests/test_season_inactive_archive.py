"""Listed inactive facts can supplement game sources, never fill omissions."""

import hashlib
import json

import pandas as pd
import pytest

from nbatools.commands._dated_membership import COLUMNS as MEMBERSHIP_COLUMNS
from nbatools.commands._participation_observations import game_participation, load_observations
from nbatools.commands.pipeline.structured_participation import (
    INACTIVE_FIELDS,
    inactive_dependencies,
    qualify_season_inactive,
    stage_season_inactive,
    validate_season_inactive,
)
from nbatools.data_source import reset_data_source_cache
from nbatools.dataframe_cache import clear_frame_cache


@pytest.fixture
def sample(tmp_path, monkeypatch):
    root = tmp_path / "snapshot/data"
    paths = inactive_dependencies("2023-24")
    games = pd.DataFrame(
        [
            dict(
                game_id=g,
                game_date=d,
                season="2023-24",
                season_type="Regular Season",
                is_final=True,
                home_team_id=10,
                away_team_id=20,
            )
            for g, d in [(22300001, "2023-11-03"), (22300002, "2023-11-04")]
        ]
    )
    teams = pd.DataFrame(
        [
            dict(
                game_id=g.game_id,
                game_date=g.game_date,
                season="2023-24",
                season_type="Regular Season",
                team_id=t,
                team_abbr=a,
            )
            for g in games.itertuples()
            for t, a in [(10, "AAA"), (20, "BBB")]
        ]
    )
    played = pd.DataFrame(
        [
            dict(
                game_id=g.game_id,
                game_date=g.game_date,
                season="2023-24",
                season_type="Regular Season",
                team_id=10,
                player_id=1,
                player_name="One Player",
                minutes=20,
            )
            for g in games.itertuples()
        ]
    )
    dependencies = {}
    for path, table in zip(paths, (games, teams, played)):
        raw = table.to_csv(index=False).encode()
        dependencies[path] = raw
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
    frame = pd.DataFrame(
        [
            dict(
                zip(
                    INACTIVE_FIELDS,
                    [
                        2,
                        "Two",
                        "Player",
                        "",
                        10,
                        "A City",
                        "A Name",
                        "AAA",
                        2024,
                        "0022300001",
                        "2",
                    ],
                )
            )
        ]
    )

    def inputs(frame=frame):
        raw = frame.to_csv(index=False).encode()
        digest = hashlib.sha256(raw).hexdigest()
        url = (
            "https://github.com/sportsdataverse/sportsdataverse-data/releases/download/"
            "nba_stats_game_rosters/game_rosters_2024.csv"
        )
        receipt = dict(
            schema_version=1,
            source_kind="archive_derived_summary_v2_inactive_rows",
            origin_table="BoxScoreSummaryV2.InactivePlayers",
            source_url=url,
            sha256=digest,
            size_bytes=len(raw),
            retrieved_at="2026-11-15T10:00:00+00:00",
            original_nba_capture_time=None,
            schema_reference_revision="a" * 40,
            publisher_asset=dict(
                id=1,
                name="game_rosters_2024.csv",
                browser_download_url=url,
                digest="sha256:" + digest,
                size=len(raw),
            ),
            canonical_file_sha256={
                p: hashlib.sha256(b).hexdigest() for p, b in dependencies.items()
            },
        )
        return raw, receipt

    monkeypatch.setenv("DATA_SOURCE", "local")
    monkeypatch.setenv("NBATOOLS_DATA_ROOT", str(root.parent))
    monkeypatch.setenv("NBATOOLS_DATA_GENERATION", "legacy")
    reset_data_source_cache()
    clear_frame_cache()
    yield root, frame, dependencies, inputs
    reset_data_source_cache()
    clear_frame_cache()


def test_source_is_one_explicit_inactive_fact_and_omission_stays_unknown(sample):
    root, frame, dependencies, inputs = sample
    raw, receipt = inputs()
    rows = stage_season_inactive(root, raw, receipt, "2023-24")
    validate_season_inactive(root)
    assert len(rows) == 1 and rows.source_minutes.isna().all()
    observations = load_observations(["2023-24"], "Regular Season")
    from datetime import date

    empty = pd.DataFrame(columns=MEMBERSHIP_COLUMNS)
    for gid, day, expected in [(22300001, 3, "did_not_play"), (22300002, 4, "unknown")]:
        state, member = game_participation(
            observations, empty, 2, gid, 10, date(2023, 11, day), other_team=20
        )
        assert state == expected
        assert member.state == ("member" if day == 3 else "unknown")


@pytest.mark.parametrize(
    "field,value",
    [
        ("player_id", "2.5"),
        ("game_id", "22300001"),
        ("team_id", 99),
        ("season", 2023),
        ("season_type_id", "4"),
        ("team_abbreviation", "BBB"),
    ],
)
def test_malformed_or_wrong_scope_records_cannot_qualify(sample, field, value):
    root, frame, dependencies, inputs = sample
    changed = frame.copy()
    changed[field] = value
    raw, receipt = inputs(changed)
    with pytest.raises((ValueError, TypeError)):
        qualify_season_inactive(raw, receipt, "2023-24", dependencies)


def test_duplicate_and_played_keys_rejected(sample):
    root, frame, dependencies, inputs = sample
    for changed in [pd.concat([frame, frame]), frame.assign(player_id=1, first_name="One")]:
        raw, receipt = inputs(changed)
        with pytest.raises(ValueError):
            qualify_season_inactive(raw, receipt, "2023-24", dependencies)


@pytest.mark.parametrize(
    "field,value",
    [
        ("origin_table", "CommonTeamRoster"),
        ("sha256", "0" * 64),
        ("source_url", "https://example.com/roster.csv"),
        ("retrieved_at", "2026-11-15T10:00:00"),
    ],
)
def test_provenance_cannot_be_relabelled(sample, field, value):
    root, frame, dependencies, inputs = sample
    raw, receipt = inputs()
    receipt[field] = value
    with pytest.raises(ValueError):
        qualify_season_inactive(raw, receipt, "2023-24", dependencies)


def test_immutable_stage_and_replay_reject_expansion(sample):
    root, frame, dependencies, inputs = sample
    raw, receipt = inputs()
    stage_season_inactive(root, raw, receipt, "2023-24")
    with pytest.raises(ValueError, match="immutable"):
        stage_season_inactive(root, raw, receipt, "2023-24")
    target = root / "raw/player_game_inactive/2023-24_regular_season.csv"
    rows = pd.read_csv(target)
    target.write_text(pd.concat([rows, rows.assign(game_id=22300002)]).to_csv(index=False))
    with pytest.raises(ValueError, match="differ"):
        validate_season_inactive(root)


def test_original_and_canonical_tampering_rejected(sample):
    root, frame, dependencies, inputs = sample
    raw, receipt = inputs()
    for altered, deps in [
        (raw + b"\n", dependencies),
        (raw, {**dependencies, next(iter(dependencies)): b"changed"}),
    ]:
        with pytest.raises(ValueError, match="mismatch"):
            qualify_season_inactive(altered, receipt, "2023-24", deps)


def test_existing_source_authority_is_preserved_and_conflicts_fail(sample):
    root, frame, dependencies, inputs = sample
    raw, receipt = inputs()
    rows = stage_season_inactive(root, raw, receipt, "2023-24")
    old = rows.copy()
    old["source"] = "nba_stats_structured_archive:" + "b" * 40 + ":0022300001"
    old["source_sha256"] = "c" * 64
    target = root / "raw/player_game_availability/2023-24_regular_season.csv"
    target.parent.mkdir(parents=True)
    target.write_text(old.to_csv(index=False))
    merged = load_observations(["2023-24"], "Regular Season")
    assert len(merged) == 1 and merged.source.iloc[0] == old.source.iloc[0]
    old["participation_state"] = "played"
    old["source_minutes"] = 4
    target.write_text(old.to_csv(index=False))
    clear_frame_cache()
    with pytest.raises(ValueError, match="contradicts"):
        load_observations(["2023-24"], "Regular Season")
    with pytest.raises(ValueError, match="contradicts"):
        validate_season_inactive(root)


def test_published_generation_cannot_be_mutated(sample):
    root, frame, dependencies, inputs = sample
    (root / "metadata").mkdir()
    (root / "metadata/generation_manifest.json").write_text("{}")
    raw, receipt = inputs()
    with pytest.raises(ValueError, match="published"):
        stage_season_inactive(root, raw, receipt, "2023-24")


def test_regular_inactive_batch_cannot_enter_playoff_scope(sample):
    root, frame, dependencies, inputs = sample
    raw, receipt = inputs()
    regular = stage_season_inactive(root, raw, receipt, "2023-24")
    playoff = regular.copy()
    playoff["game_id"] = 42300001
    playoff["game_date"] = "2024-04-20"
    playoff["season_type"] = "Playoffs"
    playoff["source"] = "nba_stats_structured_archive:" + "b" * 40 + ":0042300001"
    target = root / "raw/player_game_availability/2023-24_playoffs.csv"
    target.parent.mkdir(parents=True)
    target.write_text(playoff.to_csv(index=False))
    actual = load_observations(["2023-24"], "Playoffs")
    assert len(actual) == 1
    assert actual.season_type.eq("Playoffs").all()
    assert actual.game_id.tolist() == [42300001]


def _conflicting_sample(sample):
    root, frame, dependencies, inputs = sample
    path = inactive_dependencies("2023-24")[-1]
    # Retain the canonical name in game two, but no appearance in game one.
    players = pd.read_csv(root / path)
    dependencies[path] = players.iloc[1:].to_csv(index=False).encode()
    (root / path).write_bytes(dependencies[path])
    conflict = frame.assign(player_id=1, first_name="Different", last_name="Name")
    mixed = pd.concat([frame, conflict], ignore_index=True)
    raw, receipt = inputs(mixed)
    return root, mixed, dependencies, inputs, raw, receipt


def test_explicit_quarantine_keeps_original_and_omissions_unknown(sample):
    from datetime import date

    root, mixed, dependencies, inputs, raw, receipt = _conflicting_sample(sample)
    with pytest.raises(ValueError, match="name conflicts"):
        qualify_season_inactive(raw, receipt, "2023-24", dependencies)
    receipt["identity_name_policy"] = "quarantine_known_conflicts_v1"
    rows = stage_season_inactive(root, raw, receipt, "2023-24")
    assert rows.player_id.tolist() == [2]
    ledger = rows.attrs["identity_name_rejections"]
    assert ledger == [
        dict(game_id=22300001, team_id=10, player_id=1, reason="identity_name_conflict")
    ]
    assert (
        root / "raw/player_game_inactive_sources" / f"{receipt['sha256']}.csv"
    ).read_bytes() == raw
    validate_season_inactive(root)
    observations = load_observations(["2023-24"], "Regular Season")
    empty = pd.DataFrame(columns=MEMBERSHIP_COLUMNS)
    for tid, other in [(10, 20), (20, 10)]:
        state, membership = game_participation(
            observations, empty, 1, 22300001, tid, date(2023, 11, 3), other_team=other
        )
        assert state == "unknown" and membership.state == "unknown"


@pytest.mark.parametrize("damage", ["side", "duplicate", "appearance"])
def test_quarantine_cannot_hide_other_invalid_rows(sample, damage):
    root, mixed, dependencies, inputs, raw, receipt = _conflicting_sample(sample)
    if damage == "side":
        mixed.loc[1, "team_id"] = 99
    elif damage == "duplicate":
        mixed = pd.concat([mixed, mixed.iloc[[1]]], ignore_index=True)
    else:
        mixed.loc[1, "game_id"] = "0022300002"
    raw, receipt = inputs(mixed)
    receipt["identity_name_policy"] = "quarantine_known_conflicts_v1"
    with pytest.raises(ValueError):
        stage_season_inactive(root, raw, receipt, "2023-24")
    assert not (root / "raw/player_game_inactive").exists()


@pytest.mark.parametrize("damage", ["missing", "removed", "extra", "wrong_type", "unknown_policy"])
def test_quarantine_replay_recomputes_exact_rejection_ledger(sample, damage):
    root, mixed, dependencies, inputs, raw, receipt = _conflicting_sample(sample)
    receipt["identity_name_policy"] = "quarantine_known_conflicts_v1"
    stage_season_inactive(root, raw, receipt, "2023-24")
    path = root / "raw/player_game_inactive/2023-24_regular_season.source.json"
    stored = json.loads(path.read_bytes())
    if damage == "missing":
        del stored["identity_name_rejections"]
    elif damage == "removed":
        stored["identity_name_rejections"] = []
    elif damage == "extra":
        stored["identity_name_rejections"].append(stored["identity_name_rejections"][0])
    elif damage == "wrong_type":
        stored["identity_name_rejections"][0]["player_id"] = True
    else:
        stored["identity_name_policy"] = "ignore_names"
    path.write_text(json.dumps(stored))
    with pytest.raises(ValueError):
        validate_season_inactive(root)


def test_all_rejected_and_unrequested_quarantine_are_invalid(sample):
    root, mixed, dependencies, inputs, raw, receipt = _conflicting_sample(sample)
    raw, receipt = inputs(mixed.iloc[[1]])
    receipt["identity_name_policy"] = "quarantine_known_conflicts_v1"
    with pytest.raises(ValueError, match="No qualified"):
        qualify_season_inactive(raw, receipt, "2023-24", dependencies)
    raw, receipt = inputs()
    receipt["identity_name_rejections"] = []
    with pytest.raises(ValueError, match="explicit policy"):
        qualify_season_inactive(raw, receipt, "2023-24", dependencies)
