"""Controlled failure experiments: synthetic tests, no NBA data or R2 access."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "tools/required_data_validation.py"


@pytest.fixture
def sandbox(tmp_path: Path) -> tuple[Path, dict[str, str]]:
    (tmp_path / "tests").mkdir()
    (tmp_path / "pytest.ini").write_text(
        "[pytest]\naddopts = -n 0\nmarkers =\n    needs_data: required data tests\n"
    )
    # Pin a real local revision without invoking any network or publishing data.
    for args in (
        ["init", "-q"],
        ["config", "user.name", "Gate Test"],
        ["config", "user.email", "gate-test@example.invalid"],
        ["add", "pytest.ini"],
        ["commit", "-qm", "Controlled gate fixture"],
    ):
        subprocess.run(["git", *args], cwd=tmp_path, check=True, capture_output=True)
    sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=tmp_path, text=True).strip()
    env = {
        **os.environ,
        "DATA_SOURCE": "local",
        "SCOPE": "targeted",
        "TESTS": "tests/test_controlled.py",
        "VALIDATION_SHA": sha,
        "NBATOOLS_DATA_GENERATION": "controlled-fixture-not-nba-data",
    }
    env.pop("GITHUB_STEP_SUMMARY", None)
    env.pop("PYTEST_ADDOPTS", None)
    return tmp_path, env


def run_gate(sandbox, body: str, *, selection=None, scope=None, parallel=False):
    root, env = sandbox
    env = dict(env)
    (root / "tests/test_controlled.py").write_text(
        "import pytest\npytestmark = pytest.mark.needs_data\n" + body
    )
    if selection is not None:
        env["TESTS"] = selection
    if scope is not None:
        env["SCOPE"] = scope
    if parallel:
        env["PYTEST_ADDOPTS"] = "-n 2"
    result = subprocess.run(
        [sys.executable, str(HARNESS)],
        cwd=root,
        env=env,
        text=True,
        capture_output=True,
        timeout=45,
    )
    # Read only evidence just generated in this test's temporary repository.
    report_path = root / "outputs" / "required_data_validation" / "summary.json"
    report = json.loads(report_path.read_text())
    return result, report


@pytest.mark.parametrize("parallel", [False, True])
def test_positive_selection_executes_and_reports_identity(sandbox, parallel) -> None:
    result, report = run_gate(
        sandbox, "def test_good():\n    assert 2 + 3 == 5\n", parallel=parallel
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert report["conclusion"] == "success"
    assert {key: report[key] for key in ("selected", "executed", "passed", "skipped")} == {
        "selected": 1,
        "executed": 1,
        "passed": 1,
        "skipped": 0,
    }
    assert report["candidate_sha"] == sandbox[1]["VALIDATION_SHA"]
    assert report["generation"] == "controlled-fixture-not-nba-data"


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        ("def test_wrong():\n    assert 2 + 3 == 6\n", {"failed": 1, "executed": 1}),
        ("def test_skipped():\n    pytest.skip('required data unavailable')\n", {"skipped": 1}),
        (
            "@pytest.mark.skip(reason='missing data')\ndef test_skipped():\n    pass\n",
            {"skipped": 1, "executed": 0},
        ),
        (
            "def test_good():\n    pass\ndef test_skip():\n    pytest.skip('missing season')\n",
            {"passed": 1, "skipped": 1},
        ),
        (
            "@pytest.fixture(autouse=True)\ndef broken():\n    raise RuntimeError('missing dataset')\ndef test_error():\n    pass\n",
            {"errors": 1, "executed": 0},
        ),
        (
            "@pytest.fixture(autouse=True)\ndef broken():\n    yield\n    raise RuntimeError('teardown')\ndef test_error():\n    pass\n",
            {"errors": 1, "passed": 0},
        ),
        (
            "@pytest.mark.xfail\ndef test_expected_failure():\n    assert False\n",
            {"xfailed": 1, "passed": 0},
        ),
        (
            "@pytest.mark.xfail(strict=False)\ndef test_unexpected_pass():\n    pass\n",
            {"xfailed": 1, "passed": 0},
        ),
        ("raise RuntimeError('collection error')\n", {"errors": 1, "executed": 0}),
        ("", {"selected": 0, "executed": 0}),
        ("pytestmark = []\ndef test_not_numerical():\n    pass\n", {"selected": 0}),
    ],
)
def test_required_failure_paths_cannot_pass(sandbox, body, expected) -> None:
    result, report = run_gate(sandbox, body)
    assert result.returncode != 0, result.stdout + result.stderr
    assert report["conclusion"] == "failure"
    for key, value in expected.items():
        assert report[key] == value, report


@pytest.mark.parametrize(
    "selection",
    [
        "",
        " ",
        "tests/typo.py",
        "tests/test_controlled.py::typo",
        "-k",
        "tests/../secret.py",
        "tests/x.py;env",
        "qa/run.py",
    ],
)
def test_empty_typo_and_invalid_selections_fail(sandbox, selection) -> None:
    result, report = run_gate(sandbox, "def test_good():\n    pass\n", selection=selection)
    assert result.returncode != 0
    assert report["conclusion"] == "failure"
    assert report["executed"] == 0


def test_each_named_selector_requires_numerical_tests(sandbox) -> None:
    (sandbox[0] / "tests/test_unmarked.py").write_text("def test_unmarked():\n    pass\n")
    result, report = run_gate(
        sandbox,
        "def test_good():\n    pass\n",
        selection="tests/test_controlled.py tests/test_unmarked.py",
    )
    assert result.returncode != 0
    assert report["passed"] == 1
    assert any("test_unmarked.py" in problem for problem in report["problems"])


def test_missing_data_uses_actual_repository_skip_and_cannot_pass(sandbox) -> None:
    # Load the real skip fixture without the repository's unrelated autouse fixtures.
    (sandbox[0] / "tests/conftest.py").write_text(
        "import importlib.util\n"
        f"spec = importlib.util.spec_from_file_location('real_conftest', {str(ROOT / 'tests/conftest.py')!r})\n"
        "module = importlib.util.module_from_spec(spec)\nspec.loader.exec_module(module)\n"
        "_skip_needs_data = module._skip_needs_data\n"
    )
    result, report = run_gate(sandbox, "def test_requires_data():\n    assert False\n")
    assert result.returncode != 0
    assert report["selected"] == 1
    assert report["skipped"] == 1
    assert report["executed"] == 0
    assert report["pytest_exit"] == 0  # Ordinary pytest used to make this green.


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("VALIDATION_SHA", "0" * 40),
        ("NBATOOLS_DATA_GENERATION", ""),
        ("NBATOOLS_DATA_GENERATION", "legacy"),
    ],
)
def test_missing_or_mismatched_identity_fails_before_execution(sandbox, key, value) -> None:
    sandbox[1][key] = value
    result, report = run_gate(sandbox, "def test_good():\n    pass\n")
    assert result.returncode != 0
    assert report["executed"] == 0


def test_full_scope_preserves_required_suite(sandbox) -> None:
    result, report = run_gate(sandbox, "def test_good():\n    pass\n", selection="", scope="full")
    assert result.returncode == 0, result.stdout + result.stderr
    assert report["selected"] == report["passed"] == 1


def test_parameterized_node_selection_runs_only_the_required_case(sandbox) -> None:
    result, report = run_gate(
        sandbox,
        '@pytest.mark.parametrize("value", [1, 2], ids=["first", "second"])\n'
        "def test_value(value):\n    assert value == 2\n",
        selection="tests/test_controlled.py::test_value[second]",
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert report["selected"] == report["passed"] == 1


def test_automatic_collection_budget_stops_before_execution_even_with_xdist_env(sandbox) -> None:
    sandbox[1]["VALIDATION_MAX_TESTS"] = "2"
    body = (
        '@pytest.mark.parametrize("number", range(3))\n'
        "def test_expansion(number):\n"
        "    from pathlib import Path\n"
        '    Path("must-not-execute").touch()\n'
    )
    result, report = run_gate(sandbox, body, parallel=True)
    assert result.returncode != 0
    assert report["selected"] == 3
    assert report["executed"] == 0
    assert report["required_test_limit"] == 2
    assert not (sandbox[0] / "must-not-execute").exists()


def test_automatic_selection_within_budget_executes_normally(sandbox) -> None:
    sandbox[1]["VALIDATION_MAX_TESTS"] = "2"
    result, report = run_gate(sandbox, "def test_good():\n    assert 7 * 6 == 42\n", parallel=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert report["selected"] == report["executed"] == report["passed"] == 1
    assert report["required_test_limit"] == 2


def test_ranked_zero_data_fixtures_obey_guard_but_required_skips_still_fail(sandbox) -> None:
    root, env = sandbox
    filename = "test_ranked_zero_conditions_real_data.py"
    (root / "tests" / filename).write_text((ROOT / "tests" / filename).read_text())
    (root / "tests/conftest.py").write_text(
        "import importlib.util\n"
        f"spec = importlib.util.spec_from_file_location('real_conftest', {str(ROOT / 'tests/conftest.py')!r})\n"
        "module = importlib.util.module_from_spec(spec)\nspec.loader.exec_module(module)\n"
        "_skip_needs_data = module._skip_needs_data\n"
    )
    ordinary = subprocess.run(
        [sys.executable, "-m", "pytest", "-n", "0", "-q", f"tests/{filename}"],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert ordinary.returncode == 0, ordinary.stdout + ordinary.stderr
    assert "10 skipped" in ordinary.stdout
    result, report = run_gate(sandbox, "", selection=f"tests/{filename}")
    assert result.returncode != 0
    assert report["selected"] == report["skipped"] == 10
    assert report["executed"] == report["passed"] == report["errors"] == 0
    assert report["pytest_exit"] == 0
    assert report["conclusion"] == "failure"
