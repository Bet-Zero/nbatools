import copy
import hashlib
import json
import shutil
from pathlib import Path
from zipfile import ZipFile

import pandas as pd
import pytest

from nbatools.commands.pipeline import generation_publication as publication
from nbatools.commands.pipeline.structured_participation import stage_structured_game
from nbatools.commands.pipeline.team_appearance_coverage import qualify_retained_appearances
from nbatools.participation_source_packs import INDEX, SOURCE_DIR
from tests.test_structured_participation import REV, source  # noqa: F401
from tools import compose_participation_overlays as composition
from tools.prepare_team_appearance_package import _append_appearance_scope, prepare

pytestmark = pytest.mark.engine
CODE_ROOT = Path(__file__).resolve().parents[1]
SUFFIX = "2025-26_regular_season"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.mark.parametrize("fault", ["truncated", "wrong_side", "wrong_date", "future_game"])
def test_package_rejects_incomplete_or_misbound_team_season(tmp_path, fault):
    base = tmp_path / "base"
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    (base / "metadata").mkdir(parents=True)
    rows = (
        "game_id,game_date,season,season_type,status,team_a_id,team_b_id,home_team_id,away_team_id\n"
        "1,2026-01-01,2025-26,Regular Season,Final,12,34,12,34\n"
        "2,2026-01-02,2025-26,Regular Season,Final,34,12,34,12\n"
    )
    files = []
    for family in ("games", "schedule"):
        relative = f"raw/{family}/2025-26_regular_season.csv"
        path = base / relative
        path.parent.mkdir(parents=True)
        path.write_text(
            rows.replace(
                "2026-01-02,2025-26,Regular Season,Final",
                "2026-01-02,2025-26,Regular Season,Scheduled",
            )
            if family == "schedule" and fault == "future_game"
            else rows
        )
        files.append(dict(path=relative, sha256=digest(path)))
    manifest = base / "metadata/generation_manifest.json"
    manifest.write_text(json.dumps(dict(generation_id="base", files=files)))
    overlay = artifacts / "qualified-overlay.zip"
    overlay.write_bytes(b"scope validation precedes opening an overlay")
    proof = artifacts / "2025-26_regular_season.json"
    games = [1] if fault == "truncated" else [1, 2]
    proof.write_text(
        json.dumps(
            dict(
                season="2025-26",
                season_type="Regular Season",
                scope="complete_team_appearance_lists",
                sides=[
                    dict(
                        game_id=game,
                        game_date=f"2026-01-0{3 if fault == 'wrong_date' else game}",
                        team_id=34 if fault == "wrong_side" else 12,
                    )
                    for game in games
                ],
            )
        )
    )
    (artifacts / "package.json").write_text(
        json.dumps(
            dict(
                schema_version=1,
                base_generation="base",
                base_manifest_sha256=digest(manifest),
                generation_id="candidate",
                season="2025-26",
                season_type="Regular Season",
                team_id=12,
                game_ids=games,
                overlay_sha256=digest(overlay),
                appearance_proof_sha256=digest(proof),
            )
        )
    )
    with pytest.raises(
        ValueError, match="team-season population|finalized team-season|denominator"
    ):
        prepare(artifacts, tmp_path, tmp_path / "output", "candidate", base)


def test_additional_team_sides_preserve_existing_authority():
    schema = dict(
        schema_version=1,
        season="2025-26",
        season_type="Regular Season",
        scope="complete_team_appearance_lists",
        dependencies={"games": "frozen"},
        unqualified=[],
        source_requests=0,
    )
    retained = dict(game_id=20, team_id=12, played_ids=[1, 2])
    addition = dict(game_id=20, team_id=34, played_ids=[3, 4])
    previous = dict(schema, sides=[retained])
    assert _append_appearance_scope(previous, dict(schema, sides=[addition]))["sides"] == [
        retained,
        addition,
    ]
    with pytest.raises(ValueError, match="replace an accepted side"):
        _append_appearance_scope(previous, dict(schema, sides=[dict(retained, played_ids=[3])]))


@pytest.fixture
def grouped_inputs(source, tmp_path):  # noqa: F811 - reuse the existing source fixture
    base, traditional, summary, trad, summ = source
    days = {22500002: "2025-10-21", 22500003: "2025-10-22"}
    for family in ("games", "team_game_stats", "player_game_stats"):
        path = base / f"raw/{family}/{SUFFIX}.csv"
        first = pd.read_csv(path)
        rows = pd.concat([first.assign(game_id=game, game_date=day) for game, day in days.items()])
        if family == "games":
            rows = rows.assign(team_a_id=1, team_b_id=2, status="Final")
            schedule = base / f"raw/schedule/{SUFFIX}.csv"
            schedule.parent.mkdir()
            rows.to_csv(schedule, index=False)
        rows.to_csv(path, index=False)
    manifest_receipt = base / "metadata/dataset_manifests/games-fixture.json"
    manifest_receipt.parent.mkdir(parents=True)
    games = f"raw/games/{SUFFIX}.csv"
    manifest_receipt.write_text(
        json.dumps(
            dict(
                generation_id="base-fixture",
                validation_state="passed",
                datasets=[
                    dict(
                        name="games",
                        generation_id="base-fixture",
                        validation={"state": "passed"},
                        path=games,
                        file_sha256=digest(base / games),
                    )
                ],
            )
        )
    )
    publication._write_player_names(base)
    base_digest = digest(publication._write_generation_manifest(base, "base-fixture"))
    artifacts = tmp_path / "grouped-artifacts"
    artifacts.mkdir()
    candidates = tmp_path / "native-proofs"
    shutil.copytree(base, candidates)
    overlays = {}
    for game, day in days.items():
        identifier = f"{game:010d}"
        left, right = copy.deepcopy(trad), copy.deepcopy(summ)
        left["boxScoreTraditional"]["gameId"] = identifier
        for table in right["resultSets"]:
            for row in table["rowSet"]:
                for key, value in (("GAME_ID", identifier), ("GAME_DATE_EST", day)):
                    if key in table["headers"]:
                        row[table["headers"].index(key)] = value
        traditional.write_text(json.dumps(left))
        summary.write_text(json.dumps(right))
        one_game = tmp_path / identifier
        shutil.copytree(base, one_game)
        for root in (one_game, candidates):
            stage_structured_game(
                root,
                season="2025-26",
                season_type="Regular Season",
                game_id=game,
                traditional=traditional,
                summary=summary,
                summary_version=2,
                revision=REV,
                retrieved_at="2026-10-31T12:00:00Z",
            )
        raw = one_game / "raw"
        files = [
            path
            for family in ("player_game_availability", "player_game_availability_sources")
            for path in sorted((raw / family).iterdir())
        ]
        entries = [
            dict(
                path=path.relative_to(one_game).as_posix(),
                sha256=digest(path),
                size_bytes=path.stat().st_size,
            )
            for path in files
        ]
        csv_path = f"raw/player_game_availability/{SUFFIX}.csv"
        ledger_path = csv_path.replace(".csv", ".imports.json")
        validation = dict(
            base_generation="base-fixture",
            base_manifest_sha256=base_digest,
            publication_state="staged_only_no_writes",
            production_writes=0,
            overlay_files=entries,
            manifest_absent_creations={
                relative: dict(
                    base_presence="manifest_absent",
                    added_game_ids=[identifier],
                    added_records=count,
                )
                for relative, count in ((csv_path, 4), (ledger_path, 1))
            },
        )
        overlay = artifacts / f"overlay-{game}.zip"
        with ZipFile(overlay, "w") as archive:
            archive.writestr("validation.json", json.dumps(validation))
            for path, entry in zip(files, entries, strict=True):
                archive.write(path, entry["path"])
        overlays[overlay.name] = digest(overlay)
    full = qualify_retained_appearances(candidates, "2025-26", "Regular Season")
    scopes = []
    for team in (2, 1):
        proof = artifacts / f"{SUFFIX}-{team}.json"
        sides = [side for side in full["sides"] if side["team_id"] == team]
        proof.write_text(json.dumps(dict(full, sides=sides)))
        scopes.append(
            dict(
                season="2025-26",
                season_type="Regular Season",
                team_id=team,
                game_ids=list(days),
                appearance_proof_sha256=digest(proof),
            )
        )
    packet = dict(
        schema_version=2,
        base_generation="base-fixture",
        base_manifest_sha256=base_digest,
        generation_id="candidate",
        team_scopes=scopes,
        overlays=overlays,
    )
    (artifacts / "package.json").write_text(json.dumps(packet))
    return base, artifacts, packet, full


@pytest.mark.parametrize("packed", [False, True])
def test_grouped_scopes_compose_and_run_the_real_validator_once(
    grouped_inputs, tmp_path, monkeypatch, packed
):
    base, artifacts, packet, independently_replayed = grouped_inputs
    if packed:
        (artifacts / "package.json").write_text(json.dumps(dict(packet, pack_sources=True)))
    base_bytes = {p: p.read_bytes() for p in base.rglob("*") if p.is_file()}
    composed, validated = [], []
    native_compose, native_validate = (
        composition.compose_overlays,
        publication.validate_staged_generation,
    )

    def compose(packages, *args, **kwargs):
        composed.append(len(packages))
        return native_compose(packages, *args, **kwargs)

    def validate(stage, generation):
        validated.append(generation)
        return native_validate(stage, generation)

    monkeypatch.setattr(composition, "compose_overlays", compose)
    monkeypatch.setattr(publication, "validate_staged_generation", validate)
    work = tmp_path / "prepare-group"
    result = prepare(artifacts, CODE_ROOT, work, "candidate", base)
    stage = work / "validation/generations/candidate"
    day_sides = json.loads((stage / f"raw/team_game_appearances/{SUFFIX}.json").read_bytes())
    assert day_sides["sides"] == sorted(
        independently_replayed["sides"], key=lambda side: (side["team_id"], side["game_id"])
    )
    assert composed == [2] and validated == [result.generation_id]
    if packed:
        index = json.loads((stage / INDEX).read_bytes())["files"]
        assert not (stage / SOURCE_DIR).exists()
        assert len({item["pack"] for item in index.values()}) == 1
        assert all(
            index[name]["sha256"] == sha
            for side in day_sides["sides"]
            for name, sha in side["source_files"].items()
        )
    metrics = json.loads((work / "preparation-metrics.json").read_bytes())
    assert metrics["qualified_side_count"] == 4 and metrics["production_writes"] == 0
    assert {p: p.read_bytes() for p in base_bytes} == base_bytes


def test_group_rejects_native_changes_outside_declared_games(grouped_inputs, tmp_path, monkeypatch):
    base, artifacts, _, _ = grouped_inputs
    native_compose = composition.compose_overlays

    def with_outside_game(*args, **kwargs):
        staged = native_compose(*args, **kwargs)
        csv_path = f"raw/player_game_availability/{SUFFIX}.csv"
        staged["manifest_absent_creations"][csv_path]["added_game_ids"].append("0022500004")
        return staged

    monkeypatch.setattr(composition, "compose_overlays", with_outside_game)
    work = tmp_path / "outside-group"
    with pytest.raises(ValueError, match="outside the declared games"):
        prepare(artifacts, CODE_ROOT, work, "candidate", base)
    assert not (work / "validation").exists()


@pytest.mark.parametrize(
    "fault", ["omitted_game", "wrong_side", "forged_players", "duplicate_scope"]
)
def test_group_rejects_any_incomplete_or_unreplayed_scope(grouped_inputs, tmp_path, fault):
    base, artifacts, packet, _ = grouped_inputs
    spec = packet["team_scopes"][0]
    path = artifacts / f"{SUFFIX}-{spec['team_id']}.json"
    proof = json.loads(path.read_bytes())
    if fault == "omitted_game":
        spec["game_ids"].pop()
        proof["sides"].pop()
    elif fault == "wrong_side":
        proof["sides"][0]["team_id"] = 1
    elif fault == "forged_players":
        proof["sides"][0]["played_ids"] = [9999]
    else:
        packet["team_scopes"].append(spec)
    path.write_text(json.dumps(proof))
    spec["appearance_proof_sha256"] = digest(path)
    (artifacts / "package.json").write_text(json.dumps(packet))
    error, message = (
        (publication.GenerationValidationError, "Complete appearance claim does not match replay")
        if fault == "forged_players"
        else (ValueError, "team-season")
    )
    work = tmp_path / "invalid-group"
    with pytest.raises(error, match=message):
        prepare(artifacts, CODE_ROOT, work, "candidate", base)
    assert not (work / "validation/metadata/active_generation.json").exists()
