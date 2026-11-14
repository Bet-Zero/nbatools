"""Run the one-command Core-1 acceptance view against the served generation."""

import json
import os
from pathlib import Path

import pytest

from tools.core1_acceptance_view import FAIL, build_view, render

pytestmark = [pytest.mark.needs_data, pytest.mark.query]


def test_core1_acceptance_view_has_no_software_failures():
    output = Path(os.environ["NBATOOLS_ACQUISITION_OUTPUT"]) / "core1-acceptance-view"
    output.mkdir(parents=True, exist_ok=False)
    view = build_view()
    view["candidate_sha"] = os.environ.get("VALIDATION_SHA")
    (output / "view.json").write_text(json.dumps(view, indent=2, default=str) + "\n")
    (output / "view.txt").write_text(render(view) + "\n")
    print(render(view))
    failed = [k for k, row in view["groups"].items() if row["verdict"] == FAIL]
    assert not failed, failed
