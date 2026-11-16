"""Fail-closed transport checks against the retained qualified bundle."""

import hashlib
import importlib.util
import json
import shutil
import sys
from pathlib import Path

import pytest

pytestmark = [pytest.mark.fixture_data, pytest.mark.engine]
ROOT = Path(__file__).resolve().parents[1]
PROGRAM = ROOT / "working/nba-tools-completion-program"


def wrapper():
    spec = importlib.util.spec_from_file_location(
        "season_publisher_test", PROGRAM / "publish-season-inactive.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_exact_bundle_transport_preserves_every_file(tmp_path):
    module = wrapper()
    inventory = json.loads((PROGRAM / "season-inactive-inventory.json").read_bytes())
    root = tmp_path / "input"
    root.mkdir()
    shutil.copyfile(
        PROGRAM / "source-evidence/season-inactive-pilot-20261115" / module.BUNDLE,
        root / module.BUNDLE,
    )
    output = tmp_path / "output"
    module.unpack(root, output, inventory)
    assert len([p for p in output.rglob("*") if p.is_file()]) == 30
    for item in inventory["overlay_files"]:
        raw = (output / item["path"]).read_bytes()
        assert len(raw) == item["size_bytes"]
        assert hashlib.sha256(raw).hexdigest() == item["sha256"]


@pytest.mark.parametrize("failure", ["bytes", "extra", "member", "missing"])
def test_bundle_substitution_or_scope_change_is_rejected(tmp_path, failure):
    module = wrapper()
    inventory = json.loads((PROGRAM / "season-inactive-inventory.json").read_bytes())
    root = tmp_path / "input"
    root.mkdir()
    path = root / module.BUNDLE
    shutil.copyfile(
        PROGRAM / "source-evidence/season-inactive-pilot-20261115" / module.BUNDLE, path
    )
    if failure == "bytes":
        path.write_bytes(path.read_bytes() + b"modified")
    elif failure == "extra":
        (root / "unreviewed.csv").write_text("extra")
    elif failure == "member":
        inventory["overlay_files"][0]["sha256"] = "0" * 64
    else:
        inventory["overlay_files"].pop()
    with pytest.raises(ValueError):
        module.unpack(root, tmp_path / "output", inventory)


def test_preparation_rejects_wrong_generation_before_network(tmp_path, monkeypatch):
    module = wrapper()
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "publisher",
            "--artifact-dir",
            str(tmp_path),
            "--code-root",
            str(ROOT),
            "--work-dir",
            str(tmp_path / "output"),
            "--generation-id",
            "unreviewed",
            "--prepare",
        ],
    )
    with pytest.raises(ValueError, match="Fixed generation"):
        module.main()
    assert not (tmp_path / "output").exists()
