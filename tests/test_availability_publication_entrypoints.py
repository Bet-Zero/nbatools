"""Fixture-only compatibility and fail-closed checks for fixed publisher entry points."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from nbatools.commands.pipeline import generation_publication as publication
from nbatools.commands.pipeline import generation_refresh as refresh

ROOT = Path(__file__).resolve().parents[1]
PROGRAM = ROOT / "working/nba-tools-completion-program"
pytestmark = [pytest.mark.fixture_data, pytest.mark.engine]


def load(path):
    spec = importlib.util.spec_from_file_location("availability_publisher_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def package(tmp_path):
    overlay = tmp_path / "overlay"
    (overlay / "raw/player_game_availability").mkdir(parents=True)
    (overlay / "raw/player_game_availability/2025-26_regular_season.csv").write_text("fixture\n")
    (overlay / "validation.json").write_text(
        json.dumps(dict(candidate_sha="request", base_generation="base"))
    )
    inventory = dict(
        request_sha="request",
        reviewed_sha="reviewed",
        base_generation="base",
        files=[
            dict(
                path=p.relative_to(overlay).as_posix(),
                size_bytes=p.stat().st_size,
                sha256=hashlib.sha256(p.read_bytes()).hexdigest(),
            )
            for p in sorted(overlay.rglob("*"))
            if p.is_file()
        ],
        code_files=[
            dict(
                path="src/nbatools/commands/pipeline/generation_publication.py",
                sha256=hashlib.sha256(Path(publication.__file__).read_bytes()).hexdigest(),
            )
        ],
    )
    path = tmp_path / "fixed-inventory.json"
    path.write_text(json.dumps(inventory))
    return overlay, path


def test_existing_opening_default_still_verifies_offline(tmp_path, monkeypatch, capsys):
    overlay, inventory = package(tmp_path)
    script = tmp_path / "publish-opening-availability.py"
    shutil.copy2(PROGRAM / script.name, script)
    shutil.copy2(inventory, script.with_name("opening-availability-inventory.json"))
    monkeypatch.setattr(sys, "argv", [str(script), "--artifact-dir", str(overlay)])
    load(script).main()
    assert json.loads(capsys.readouterr().out)["verified_overlay_files"] == 1


def test_combined_wrapper_cannot_run_without_reviewed_inventory(tmp_path, monkeypatch):
    for filename in ("publish-opening-availability.py", "publish-combined-availability.py"):
        shutil.copy2(PROGRAM / filename, tmp_path / filename)
    monkeypatch.setattr(sys, "argv", ["publisher", "--artifact-dir", str(tmp_path / "missing")])
    with pytest.raises(FileNotFoundError, match="combined-availability-inventory.json"):
        load(tmp_path / "publish-combined-availability.py").main()


@pytest.mark.parametrize("failure", [None, "base", "overwrite", "unexpected_change", "code"])
def test_fixed_inventory_preparation_preserves_existing_safeguards(tmp_path, monkeypatch, failure):
    overlay, inventory_path = package(tmp_path)
    inventory = json.loads(inventory_path.read_text())
    if failure == "code":
        inventory["code_files"][0]["sha256"] = "unreviewed"
        inventory_path.write_text(json.dumps(inventory))
    work = tmp_path / "work"
    calls = []
    changed = ["raw/player_game_availability/2025-26_regular_season.csv"]

    def download(data, **kwargs):
        data.mkdir()
        if failure == "overwrite":
            existing = data / changed[0]
            existing.parent.mkdir(parents=True)
            existing.write_text("different existing dataset\n")
        return SimpleNamespace(
            generation_id="changed" if failure == "base" else "base", manifest={}
        )

    def local(generation_id, **kwargs):
        calls.append(generation_id)
        assert (kwargs["source_dir"] / changed[0]).read_bytes() == (
            overlay / changed[0]
        ).read_bytes()
        return publication.GenerationPublicationResult(
            "local", generation_id, "base", 1, 8, "hash", "local-pointer"
        )

    def forbidden(*args, **kwargs):
        pytest.fail("No remote write is permitted by --prepare")

    monkeypatch.setattr(refresh, "download_active_generation", download)
    monkeypatch.setattr(
        refresh,
        "changed_data_files",
        lambda *args: ["raw/unreviewed.csv"] if failure == "unexpected_change" else changed,
    )
    monkeypatch.setattr(publication, "publish_local_generation", local)
    monkeypatch.setattr(publication, "publish_r2_generation", forbidden)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "publisher",
            "--artifact-dir",
            str(overlay),
            "--code-root",
            str(ROOT),
            "--work-dir",
            str(work),
            "--prepare",
        ],
    )
    publisher = load(PROGRAM / "publish-opening-availability.py")
    if failure:
        with pytest.raises(ValueError):
            publisher.main(inventory_path=inventory_path, default_generation="fixed-combined")
        assert calls == []
    else:
        publisher.main(inventory_path=inventory_path, default_generation="fixed-combined")
        assert calls == ["fixed-combined"]
        assert (
            json.loads((work / "local-validation.json").read_text())["generation_id"]
            == "fixed-combined"
        )
        assert not (work / "publication.json").exists()
