import hashlib
import json

import pytest

from tools.prepare_team_appearance_package import _append_appearance_scope, prepare

pytestmark = pytest.mark.engine


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
