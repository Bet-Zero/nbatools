"""Independent focused composition/OT-gate/starter consumer checks on pinned v3."""

import asyncio
import json
import os
import tempfile
from pathlib import Path
from zipfile import ZipFile

import httpx
import pandas as pd

import nbatools.development_data as development
from nbatools.api_handlers import natural_query_payload, structured_query_payload
from nbatools.commands.pipeline.reported_absence_reasons import validate_publication
from nbatools.commands.validation_control import build_slice_manifest
from nbatools.development_data import MANIFEST, DevelopmentSnapshot, development_snapshot, sha256
from nbatools.query_output_snapshot import build_query_ui_snapshot
from tests.test_validation_control_plane import _build, _fixture, _record
from tools.development_query import create_app

ROOT = Path("/workspace/nbatools")
SOURCE = ROOT / "work/current123-integration"
E = SOURCE / "working/nba-tools-completion-program/source-evidence/id18-current-required-20261107"
OUT = ROOT / "working/nba-tools-completion-program/source-evidence" / E.name / "independent"
SUFFIX = "2026-27_regular_season.csv"
CANDIDATE = "3bc3dbc806df8a55819ae862191f987a28efac7e"


def main():
    assert Path(development.__file__).is_relative_to(SOURCE / "src")
    os.environ["DATA_SOURCE"] = "local"
    b = json.loads((E / "required-v3-binding.json").read_bytes())
    assert sha256((E / b["archive"]).read_bytes()) == b["archive_sha256"]
    receipt = dict(
        reviewer="/root/id18_checker",
        candidate_sha=CANDIDATE,
        backend_model="unavailable",
        snapshot=b,
        executed_code_path=str(development.__file__),
        natural=[],
        structured=[],
        http=[],
        guards={},
        production_writes=0,
        source_requests=0,
    )
    with tempfile.TemporaryDirectory(prefix="id18-v3-check-", dir=ROOT / "work") as tmp:
        root = Path(tmp) / "snapshot"
        with ZipFile(E / b["archive"]) as z:
            assert all(n.startswith("data/") and ".." not in Path(n).parts for n in z.namelist())
            z.extractall(root)
        DevelopmentSnapshot(root, b["manifest_sha256"])
        validate_publication(root / "data")
        with ZipFile(E / "current123-id18-v2.zip") as old:
            names = [n for n in old.namelist() if "availability" in n or "absence_reason" in n]
            for n in names:
                assert old.read(n) == (root / n).read_bytes()
            for family in [
                "player_game_stats",
                "team_game_stats",
                "player_game_period_stats",
                "team_game_period_stats",
            ]:
                name = f"data/raw/{family}/{SUFFIX}"
                assert old.read(name) == (root / name).read_bytes()
        receipt["preserved_id18_files"] = names
        report = build_slice_manifest(
            "2026-27",
            "Regular Season",
            data_root=root / "data",
            generation_id="independent-v3-replay",
        )
        team = next(r for r in report["datasets"] if r["name"] == "team_game_period_stats")
        failures = {
            r["name"]: r["validation"]["errors"]
            for r in report["datasets"]
            if r["validation"]["errors"]
        }
        assert failures == {
            "player_game_period_stats": ["coverage missing 2208 requested keys"],
            "team_game_period_stats": ["coverage missing 196 requested keys"],
        }
        assert (
            team["coverage"]["expected_keys"] == 1490
            and "overtime:ot" in team["coverage"]["missing_windows"]
        )
        receipt["fresh_structural_replay"] = dict(
            failures=failures, team_expected_keys=1490, source_windows=745
        )
        catalog = pd.read_csv(root / f"data/raw/games/{SUFFIX}")
        assert set(catalog.loc[catalog.overtime_periods.gt(0), "game_id"]) == {
            22600110,
            22600120,
            22600128,
            22600141,
            22600165,
            22600179,
            22600186,
        }
        assert pd.isna(catalog.loc[catalog.game_id.eq(22600111), "overtime_periods"].item())
        custody = json.loads((root / "data/metadata/required-current-custody.json").read_bytes())
        assert len(custody["accepted_old_ot_metadata_changes"]) == 5
        assert all(
            r["before"] is None and r["after"] == 1
            for r in custody["accepted_old_ot_metadata_changes"]
        )
        players = pd.read_csv(root / f"data/raw/player_game_stats/{SUFFIX}")
        roles = pd.read_csv(root / f"data/raw/player_game_starter_roles/{SUFFIX}")
        keycols = ["game_id", "team_id", "player_id"]
        selected = (
            players.loc[players.player_id.eq(1630559)]
            .drop(columns="starter_flag", errors="ignore")
            .merge(roles[keycols + ["starter_flag"]], on=keycols, validate="one_to_one")
        )
        selected = selected.loc[selected.starter_flag.eq(1)]
        expected = set(selected.game_id)
        assert len(selected) == 9 and selected.pts.sum() == 210 and 22600185 in expected
        receipt["starter_oracle"] = dict(
            game_ids=sorted(map(int, expected)), games=9, pts_sum=210, pts_average="70/3"
        )
        queries = [
            "Austin Reaves stats this season as a starter",
            "Austin Reaves average points as a starter in 2026-27",
            "Austin Reaves stats as a bench player this season",
            "Lakers record when Luka Doncic rests",
        ]

        def check(body, index):
            meta = body["result"]["metadata"]
            quality = meta["data_quality"]
            assert (
                quality["manifest_sha256"] == b["manifest_sha256"]
                and quality["state"] == "provisional"
            )
            assert quality["numerical_acceptance"] is quality["production_accepted"] is False
            assert "PROVISIONAL" in " ".join(body["notes"])
            if index < 2:
                assert body["result_status"] == "ok", body
                sections = body["result"]["sections"]
                ids = {int(r["game_id"]) for r in sections["game_log"]}
                assert ids == expected
                s = sections["summary"][0]
                assert s["games"] == 9 and s["pts_sum"] == 210
                assert abs(s["pts_avg"] - 210 / 9) < 0.001
                assert meta["role"] == "starter"
            else:
                assert (
                    body["result_status"] == "no_result" and body["result_reason"] == "no_match"
                ), body
                assert body["result"]["sections"] == {}
                if index == 3:
                    assert "0 Rest, 1 reported other, 0 unknown" in " ".join(
                        body["notes"]
                    ) and "in 9 selected games" in " ".join(body["notes"])
            return build_query_ui_snapshot(body)

        with development_snapshot(root, b["manifest_sha256"]):
            for index, q in enumerate(queries):
                body = natural_query_payload(q)
                view = check(body, index)
                receipt["natural"].append(dict(query=q, payload=body, output=view))
            body = structured_query_payload(
                "player_game_summary",
                dict(player="Austin Reaves", season="2026-27", role="starter"),
            )
            view = check(body, 0)
            receipt["structured"].append(
                dict(route="player_game_summary", payload=body, output=view)
            )

        async def http():
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=create_app(root, b["manifest_sha256"])),
                base_url="http://127.0.0.1",
            ) as client:
                for index in [0, 3]:
                    response = await client.post("/query", json={"query": queries[index]})
                    assert response.status_code == 200
                    body = response.json()
                    view = check(body, index)
                    receipt["http"].append(dict(query=queries[index], payload=body, output=view))

        asyncio.run(http())
        for field in ["starter_flag", "role_source_trusted", "starter_count_for_team_game"]:
            corrupt = Path(tmp) / field
            import shutil

            shutil.copytree(root, corrupt)
            path = corrupt / f"data/raw/player_game_starter_roles/{SUFFIX}"
            frame = pd.read_csv(path)
            frame.loc[frame.player_id.eq(1630559), field] = None
            frame.to_csv(path, index=False)
            doc = json.loads((corrupt / MANIFEST).read_bytes())
            doc["files"][path.relative_to(corrupt).as_posix()] = sha256(path.read_bytes())
            (corrupt / MANIFEST).write_text(json.dumps(doc))
            with development_snapshot(corrupt, sha256((corrupt / MANIFEST).read_bytes())):
                assert natural_query_payload(queries[0])["result_reason"] == "no_data"
            receipt["guards"][field] = "missing_numeric_rejected"
        for value in [True, False, "true", "false", -1, 1.5, "unqualified"]:
            with tempfile.TemporaryDirectory(dir=ROOT / "work") as d:
                path = Path(d)
                _fixture(path)
                f = path / "raw/games/2099-00_regular_season.csv"
                g = pd.read_csv(f)
                g["overtime_periods"] = [value, value]
                g.to_csv(f, index=False)
                result = _build(path)
                assert (
                    "invalid source overtime-period count"
                    in _record(result, "games")["validation"]["errors"]
                ), value
        receipt["guards"]["boolean_and_other_invalid_provided_ot_counts"] = "rejected"
        for variable in ["VERCEL_ENV", "ENVIRONMENT"]:
            os.environ[variable] = "production"
            try:
                try:
                    DevelopmentSnapshot(root, b["manifest_sha256"])
                except ValueError:
                    pass
                else:
                    raise AssertionError("production selection accepted")
            finally:
                os.environ.pop(variable)
        receipt["guards"]["production_selection"] = "rejected"
        receipt["conclusion"] = (
            "approved bounded source composition, known-team-OT coverage gate and starter "
            "metadata repair; complete snapshot/current release acceptance remains false"
        )
        (OUT / "integrated-v3-independent-execution.json").write_text(
            json.dumps(receipt, indent=2, allow_nan=False) + "\n"
        )
        print(
            dict(
                natural=4,
                structured=1,
                http=2,
                role_guards=3,
                invalid_ot_count_guards=7,
                team_expected_keys=1490,
                conclusion="passed",
            )
        )


if __name__ == "__main__":
    main()
