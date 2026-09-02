"""The two validation gates must only claim what they actually proved.

Two false-green paths are guarded here:

1. `make raw-query-answer-qa` used to omit `--fail-on-expectation-failure`, so
   the named Raw QA target exited zero while printing failed cases.
2. `tools/filter_execution_sweep.py` used to call every comparison an honest
   refusal when there was no data at all, and exit zero - "no lies found" from
   a run that compared nothing.

These tests need no NBA data: the Make gate runs against a stub interpreter and
the sweep runs against an injected query engine.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from dataclasses import dataclass, field, is_dataclass
from inspect import isclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pandas as pd
import pytest
import yaml

from nbatools.commands import structured_results as sr
from tools import filter_execution_sweep as sweep
from tools import raw_query_answer_qa as qa

REPO_ROOT = Path(__file__).resolve().parents[1]
CANONICAL_CORPUS = "qa/raw_query_answer_corpus.yaml"
FAIL_FLAG = "--fail-on-expectation-failure"

requires_make = pytest.mark.skipif(shutil.which("make") is None, reason="make is not installed")


# ── Raw QA Make gate ──────────────────────────────────────────────


def _stub_python(tmp_path: Path, *, exit_code: int) -> tuple[Path, Path]:
    """A fake interpreter that records its argv and exits with `exit_code`.

    Keeps the gate test on the Make target itself instead of running the real
    356-case corpus, and never touches the canonical corpus.
    """
    argv_log = tmp_path / "argv.txt"
    stub = tmp_path / "stub_python"
    stub.write_text(
        f'#!/bin/sh\nprintf "%s\\n" "$@" > "{argv_log}"\nexit {exit_code}\n',
        encoding="utf-8",
    )
    stub.chmod(0o755)
    return stub, argv_log


def _run_make_target(tmp_path: Path, *, exit_code: int) -> tuple[int, list[str]]:
    stub, argv_log = _stub_python(tmp_path, exit_code=exit_code)
    completed = subprocess.run(
        ["make", "raw-query-answer-qa", f"PYTHON={stub}"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    argv = argv_log.read_text(encoding="utf-8").split() if argv_log.exists() else []
    return completed.returncode, argv


@requires_make
def test_make_target_passes_the_failing_flag_to_the_harness(tmp_path):
    _, argv = _run_make_target(tmp_path, exit_code=0)

    assert FAIL_FLAG in argv


@requires_make
def test_make_target_defaults_to_the_canonical_corpus(tmp_path):
    _, argv = _run_make_target(tmp_path, exit_code=0)

    assert "--corpus" in argv
    assert argv[argv.index("--corpus") + 1] == CANONICAL_CORPUS
    assert argv[0].endswith("tools/raw_query_answer_qa.py")


@requires_make
def test_failed_expectations_make_the_target_non_zero(tmp_path):
    returncode, _ = _run_make_target(tmp_path, exit_code=1)

    assert returncode != 0


@requires_make
def test_a_passing_harness_keeps_the_target_green(tmp_path):
    returncode, _ = _run_make_target(tmp_path, exit_code=0)

    assert returncode == 0


def test_direct_harness_use_without_the_flag_stays_report_only():
    assert (
        qa.harness_exit_code(
            closure_integrity_state="pass",
            failed_case_ids=["some_failed_case"],
            fail_on_expectation_failure=False,
        )
        == 0
    )


def test_the_flag_turns_failed_expectations_into_a_non_zero_exit():
    assert (
        qa.harness_exit_code(
            closure_integrity_state="pass",
            failed_case_ids=["some_failed_case"],
            fail_on_expectation_failure=True,
        )
        == 1
    )


def test_closure_integrity_failure_fails_with_or_without_the_flag():
    for gating in (False, True):
        assert (
            qa.harness_exit_code(
                closure_integrity_state="fail",
                failed_case_ids=[],
                fail_on_expectation_failure=gating,
            )
            == 1
        )


def test_a_clean_run_exits_zero():
    assert (
        qa.harness_exit_code(
            closure_integrity_state="pass",
            failed_case_ids=[],
            fail_on_expectation_failure=True,
        )
        == 0
    )


def test_report_only_mode_remains_the_harness_default(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["raw_query_answer_qa.py", "--corpus", CANONICAL_CORPUS])

    assert qa.parse_args().fail_on_expectation_failure is False


# ── Filter sweep row classification ───────────────────────────────


def _side(
    *,
    status: str | None = "ok",
    reason: str | None = None,
    fingerprint: str | None = "leaders:(10, 3):abc",
    populated: bool = True,
    badges: list[str] | None = None,
    error: str | None = None,
    error_kind: str | None = None,
) -> dict[str, Any]:
    """One side of a comparison, shaped exactly as `_run` returns it."""
    if error_kind is None:
        error_kind = sweep.RAISED_EXCEPTION if error else sweep._returned_error_kind(status)
    return {
        "status": status,
        "reason": reason,
        "fingerprint": fingerprint,
        "populated": populated,
        "badges": badges or [],
        "route": "season_leaders",
        "error": error,
        "error_kind": error_kind,
    }


def test_changed_data_against_a_valid_control_is_applied():
    verdict = sweep._classify(_side(fingerprint="changed"), _side(), "Last N games")

    assert verdict.verdict == sweep.APPLIED


def test_a_refusal_against_a_valid_control_is_an_honest_refusal():
    verdict = sweep._classify(
        _side(status="no_result", reason="filter_not_supported", fingerprint="NONE"),
        _side(),
        "Last N games",
    )

    assert verdict.verdict == sweep.REFUSED
    assert verdict.no_signal_reason is None


def test_identical_data_behind_a_matching_badge_is_a_lie():
    verdict = sweep._classify(
        _side(badges=["Last N games=10"]),
        _side(),
        "Last N games",
    )

    assert verdict.verdict == sweep.LIED


def test_identical_data_without_a_badge_is_a_silent_drop():
    verdict = sweep._classify(_side(badges=["Season=2023-24"]), _side(), "Last N games")

    assert verdict.verdict == sweep.DROPPED


def test_a_control_that_returned_nothing_is_no_signal_not_a_refusal():
    verdict = sweep._classify(
        _side(status="no_result", reason="no_data", fingerprint="NONE"),
        _side(status="no_result", reason="no_data", fingerprint="NONE", populated=False),
        "Last N games",
    )

    assert verdict.verdict == sweep.NO_SIGNAL
    assert verdict.no_signal_reason == "control_no_result:no_data"


def test_an_empty_but_ok_control_is_no_signal():
    verdict = sweep._classify(
        _side(fingerprint="changed"),
        _side(fingerprint="leaders:(0, 3):empty", populated=False),
        "Last N games",
    )

    assert verdict.verdict == sweep.NO_SIGNAL
    assert verdict.no_signal_reason == "control_empty_result"


def test_a_control_that_raised_is_an_error_never_applied():
    verdict = sweep._classify(
        _side(fingerprint="changed"),
        _side(status=None, fingerprint=None, populated=False, error="ValueError: boom"),
        "Last N games",
    )

    assert verdict.verdict == sweep.ERROR
    assert verdict.error_source == "control"


def test_a_filtered_query_that_raised_is_an_error():
    verdict = sweep._classify(
        _side(status=None, fingerprint=None, populated=False, error="KeyError: boom"),
        _side(),
        "Last N games",
    )

    assert verdict.verdict == sweep.ERROR
    assert verdict.error_source == "filtered"


def test_a_filtered_system_error_envelope_is_an_error_not_a_refusal():
    verdict = sweep._classify(
        _side(status="error", reason="error", fingerprint="NONE", populated=False),
        _side(),
        "Last N games",
    )

    assert verdict.verdict == sweep.ERROR
    assert verdict.verdict != sweep.REFUSED
    assert verdict.error_source == "filtered"
    assert verdict.error_kind == sweep.RETURNED_ERROR_STATUS


def test_a_control_system_error_envelope_is_an_error_not_a_gap():
    verdict = sweep._classify(
        _side(fingerprint="changed"),
        _side(status="error", reason="unrouted", fingerprint="NONE", populated=False),
        "Last N games",
    )

    assert verdict.verdict == sweep.ERROR
    assert verdict.verdict not in (sweep.NO_SIGNAL, sweep.APPLIED)
    assert verdict.error_source == "control"
    assert verdict.error_kind == sweep.RETURNED_ERROR_STATUS


def test_a_status_outside_the_contract_fails_closed():
    verdict = sweep._classify(
        _side(status="partially_ok", reason=None),
        _side(),
        "Last N games",
    )

    assert verdict.verdict == sweep.ERROR
    assert verdict.error_kind == sweep.UNKNOWN_RESULT_STATUS


# Every canonical result status, and the sweep policy deliberately chosen for
# it. A new ResultStatus value fails this guard until someone decides whether
# it is an answer, an expected negative, or a system failure - it must never
# fall through to REFUSED or NO_SIGNAL by default.
EXPECTED_STATUS_POLICY = {
    "ok": None,  # a real answer
    "no_result": None,  # an expected negative outcome
    "error": sweep.RETURNED_ERROR_STATUS,  # a system-level failure
}


def test_every_canonical_status_has_an_explicit_sweep_policy():
    assert set(sweep.CANONICAL_RESULT_STATUSES) == set(EXPECTED_STATUS_POLICY), (
        "the result contract gained or lost a status; decide explicitly whether "
        "the sweep treats it as an answer, an expected negative, or a system "
        "failure before this guard is updated"
    )
    for status, expected_kind in EXPECTED_STATUS_POLICY.items():
        assert sweep._returned_error_kind(status) == expected_kind

    # A status nobody has ruled on fails closed rather than becoming REFUSED.
    assert sweep._returned_error_kind("brand_new_status") == sweep.UNKNOWN_RESULT_STATUS


def test_the_canonical_status_set_comes_from_the_result_contract():
    assert sweep.CANONICAL_RESULT_STATUSES == {"ok", "no_result", "error"}
    # An expected negative outcome is not a system failure.
    assert sweep._returned_error_kind("no_result") is None
    assert sweep._returned_error_kind("ok") is None
    assert sweep._returned_error_kind("error") == sweep.RETURNED_ERROR_STATUS


def test_no_signal_is_not_one_of_the_comparable_verdicts():
    assert sweep.NO_SIGNAL not in sweep.COMPARABLE_VERDICTS
    assert sweep.ERROR not in sweep.COMPARABLE_VERDICTS
    for verdict in (sweep.APPLIED, sweep.REFUSED, sweep.LIED, sweep.DROPPED):
        assert verdict in sweep.COMPARABLE_VERDICTS


# ── Public answer-data evidence ───────────────────────────────────


FRAME = pd.DataFrame({"a": [1, 2], "b": ["x", "y"]})
OTHER_FRAME = pd.DataFrame({"a": [1, 3], "b": ["x", "z"]})


def _print(result) -> str:
    return sweep.fingerprint_sections(sweep.public_sections(result))


def _fully_populated_results() -> dict[str, Any]:
    """One instance per supported result type, every optional section filled."""
    return {
        "NoResult": sr.NoResult(query_class="leaderboard"),
        "SummaryResult": sr.SummaryResult(
            summary=FRAME, by_season=FRAME, game_log=FRAME, top_performers=FRAME
        ),
        "ComparisonResult": sr.ComparisonResult(summary=FRAME, comparison=FRAME),
        "SplitSummaryResult": sr.SplitSummaryResult(summary=FRAME, split_comparison=FRAME),
        "FinderResult": sr.FinderResult(games=FRAME),
        "LeaderboardResult": sr.LeaderboardResult(leaders=FRAME),
        "StreakResult": sr.StreakResult(streaks=FRAME),
        "CountResult": sr.CountResult(count=2, games=FRAME),
    }


def test_a_changed_split_comparison_changes_the_fingerprint():
    # The old hand-maintained list looked for "splits" and never saw
    # split_comparison, so a filter that only moved the split table looked
    # like an unchanged answer.
    unchanged = sr.SplitSummaryResult(summary=FRAME, split_comparison=FRAME)
    changed = sr.SplitSummaryResult(summary=FRAME, split_comparison=OTHER_FRAME)

    assert "split_comparison" in sweep.public_sections(unchanged)
    assert _print(unchanged) != _print(changed)


def test_identical_split_results_still_fingerprint_the_same():
    left = sr.SplitSummaryResult(summary=FRAME, split_comparison=FRAME)
    right = sr.SplitSummaryResult(summary=FRAME, split_comparison=FRAME)

    assert _print(left) == _print(right)


@pytest.mark.parametrize("section", ["by_season", "game_log", "top_performers"])
def test_a_changed_summary_secondary_section_changes_the_fingerprint(section):
    base = {"by_season": FRAME, "game_log": FRAME, "top_performers": FRAME}
    unchanged = sr.SummaryResult(summary=FRAME, **base)
    changed = sr.SummaryResult(summary=FRAME, **{**base, section: OTHER_FRAME})

    assert section in sweep.public_sections(unchanged)
    assert _print(unchanged) != _print(changed)


def test_a_changed_public_count_changes_the_fingerprint():
    assert _print(sr.CountResult(count=2, games=FRAME)) != _print(
        sr.CountResult(count=5, games=FRAME)
    )


def test_changed_count_games_change_the_fingerprint():
    assert _print(sr.CountResult(count=2, games=FRAME)) != _print(
        sr.CountResult(count=2, games=OTHER_FRAME)
    )


def test_identical_counts_and_games_fingerprint_the_same():
    assert _print(sr.CountResult(count=2, games=FRAME)) == _print(
        sr.CountResult(count=2, games=FRAME)
    )


def test_a_zero_count_is_not_a_populated_baseline():
    # A zero count is an expected-negative answer. Treating it as populated
    # would invent a comparable control out of "nothing matched".
    assert sweep.sections_are_populated(sweep.public_sections(sr.CountResult(count=0))) is False
    assert sweep.sections_are_populated(sweep.public_sections(sr.CountResult(count=3))) is True


def test_a_positive_count_without_games_is_still_a_real_answer():
    assert sweep.sections_are_populated(sweep.public_sections(sr.CountResult(count=3))) is True


@pytest.mark.parametrize(
    ("unchanged", "changed"),
    [
        (sr.FinderResult(games=FRAME), sr.FinderResult(games=OTHER_FRAME)),
        (sr.LeaderboardResult(leaders=FRAME), sr.LeaderboardResult(leaders=OTHER_FRAME)),
        (sr.StreakResult(streaks=FRAME), sr.StreakResult(streaks=OTHER_FRAME)),
        (
            sr.ComparisonResult(summary=FRAME, comparison=FRAME),
            sr.ComparisonResult(summary=OTHER_FRAME, comparison=FRAME),
        ),
        (
            sr.ComparisonResult(summary=FRAME, comparison=FRAME),
            sr.ComparisonResult(summary=FRAME, comparison=OTHER_FRAME),
        ),
        (sr.SummaryResult(summary=FRAME), sr.SummaryResult(summary=OTHER_FRAME)),
    ],
)
def test_primary_result_sections_still_detect_ordinary_changes(unchanged, changed):
    assert _print(unchanged) != _print(changed)


def test_metadata_and_presentation_never_reach_the_answer_fingerprint():
    plain = sr.LeaderboardResult(leaders=FRAME)
    decorated = sr.LeaderboardResult(
        leaders=FRAME,
        current_through="2024-04-14",
        metadata={"route": "season_leaders", "applied_filters": [{"label": "Last N games"}]},
        notes=["a note"],
        caveats=["a caveat"],
    )

    assert _print(plain) == _print(decorated)


def test_an_empty_result_is_not_populated():
    assert (
        sweep.sections_are_populated(sweep.public_sections(sr.NoResult(query_class="x"))) is False
    )
    assert sweep.sections_are_populated(sweep.public_sections(sr.LeaderboardResult())) is False


def test_a_result_without_the_public_contract_cannot_be_compared():
    stand_in = SimpleNamespace(leaders=FRAME)

    assert sweep.public_sections(stand_in) is None
    assert _print(stand_in) == sweep.NO_PUBLIC_CONTRACT
    assert sweep.sections_are_populated(sweep.public_sections(stand_in)) is False


def test_fingerprint_and_populated_read_the_same_extraction():
    result = sr.SplitSummaryResult(summary=FRAME, split_comparison=OTHER_FRAME)
    sections = sweep.public_sections(result)

    assert sweep.fingerprint_sections(sections) == _print(result)
    assert sweep.sections_are_populated(sections) is True
    assert sorted(sections) == ["split_comparison", "summary"]


# ── Result-contract inventory guard ───────────────────────────────


def test_every_structured_result_type_has_an_extraction_policy():
    published = {
        name
        for name, obj in vars(sr).items()
        if is_dataclass(obj) and isclass(obj) and obj.__module__ == sr.__name__
    }

    assert published == set(sweep.SUPPORTED_RESULT_SECTIONS), (
        "a structured result type was added or removed; give it an explicit "
        "entry in SUPPORTED_RESULT_SECTIONS and decide how its sections count "
        "as answer data"
    )


@pytest.mark.parametrize("name", sorted(_fully_populated_results()))
def test_every_public_section_has_an_extraction_policy(name):
    result = _fully_populated_results()[name]
    sections = sweep.public_sections(result)

    assert sections is not None
    assert set(sections) == sweep.SUPPORTED_RESULT_SECTIONS[name], (
        f"{name} publishes a public section the sweep has no policy for; add it "
        "to SUPPORTED_RESULT_SECTIONS and decide whether it counts as a "
        "populated answer"
    )


def test_the_registry_matches_what_the_extractor_actually_compares():
    # Evidence is never filtered through the registry - everything a result
    # publishes is compared - so the registry must describe reality.
    for name, result in _fully_populated_results().items():
        sections = sweep.public_sections(result)
        assert set(sections) <= sweep.SUPPORTED_RESULT_SECTIONS[name]
        for section in sections:
            assert section in sweep.SUPPORTED_RESULT_SECTIONS[name]


# ── Filter sweep run status and exit contract ─────────────────────


@dataclass
class FakeExecuted:
    """Stands in for one executed natural query."""

    result_status: str = "ok"
    result_reason: str | None = None
    result: Any = None
    metadata: dict[str, Any] = field(default_factory=dict)


def _leaderboard(rows: int = 3, *, value: int = 1) -> sr.LeaderboardResult:
    frame = pd.DataFrame({"player": [f"p{index}" for index in range(rows)], "pts": [value] * rows})
    return sr.LeaderboardResult(leaders=frame)


def _answer(
    rows: int = 3,
    *,
    value: int = 1,
    badges: list[dict[str, str]] | None = None,
    result: Any = None,
):
    return FakeExecuted(
        result_status="ok",
        result=_leaderboard(rows, value=value) if result is None else result,
        metadata={"route": "season_leaders", "applied_filters": badges or []},
    )


def _refusal(reason: str = "no_data"):
    """An expected negative outcome: no_result with a user/data reason."""
    return FakeExecuted(
        result_status="no_result",
        result_reason=reason,
        result=sr.NoResult(query_class="leaderboard", reason=reason),
        metadata={},
    )


def _system_error(reason: str = "error"):
    """A system-level failure delivered as a result envelope, not an exception."""
    return FakeExecuted(
        result_status="error",
        result_reason=reason,
        result=sr.NoResult(query_class="unknown", reason=reason, result_status="error"),
        metadata={"route": None},
    )


CONTROL = "points leaders in 2023-24"
FILTERED = "points leaders in 2023-24 last 10 games"
OTHER_CONTROL = "rebounds leaders in 2023-24"
OTHER_FILTERED = "rebounds leaders in 2023-24 last 10 games"


def _config(tmp_path: Path, seeds: list[str]) -> Path:
    path = tmp_path / "sweep_config.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "version": 1,
                "seeds": [
                    {"id": f"seed_{index}", "query": query} for index, query in enumerate(seeds)
                ],
                "filters": [{"id": "last_n", "phrase": "last 10 games", "badge": "Last N games"}],
            }
        ),
        encoding="utf-8",
    )
    return path


def _run_sweep(tmp_path, monkeypatch, *, seeds: list[str], answers: dict[str, Any]):
    """Drive the real CLI entrypoint with an injected query engine."""

    def fake_execute(query: str):
        answer = answers[query]
        if isinstance(answer, Exception):
            raise answer
        return answer

    monkeypatch.setattr(sweep, "execute_natural_query", fake_execute)
    json_path = tmp_path / "sweep.json"
    exit_code = sweep.main(["--config", str(_config(tmp_path, seeds)), "--json", str(json_path)])
    return exit_code, json.loads(json_path.read_text(encoding="utf-8"))


def test_a_data_free_run_reports_no_signal_and_exits_non_zero(tmp_path, monkeypatch, capsys):
    exit_code, document = _run_sweep(
        tmp_path,
        monkeypatch,
        seeds=[CONTROL, OTHER_CONTROL],
        answers={
            CONTROL: _refusal(),
            FILTERED: _refusal(),
            OTHER_CONTROL: _refusal(),
            OTHER_FILTERED: _refusal(),
        },
    )
    summary = document["summary"]
    printed = capsys.readouterr().out

    assert exit_code == sweep.EXIT_NO_SIGNAL
    assert exit_code != sweep.EXIT_PASS
    assert exit_code != sweep.EXIT_FAIL
    assert summary["status"] == sweep.STATUS_NO_SIGNAL
    assert summary["exit_code"] == sweep.EXIT_NO_SIGNAL
    assert summary["comparable_comparisons"] == 0
    assert summary["configured_comparisons"] == 2
    assert summary["verdict_counts"][sweep.NO_SIGNAL] == 2
    # The rows are not honest refusals, and nothing was verified about them.
    assert summary["verdict_counts"][sweep.REFUSED] == 0
    assert summary["no_signal_reason_counts"] == {"control_no_result:no_data": 2}
    assert all(row["verdict"] == sweep.NO_SIGNAL for row in document["rows"])
    assert all(row["comparable"] is False for row in document["rows"])

    assert "NO_SIGNAL" in printed
    assert "0 of 2 configured comparisons had a populated control answer." in printed
    assert "not a clean result" in printed
    # The old report headlined "0 LIED"/"0 were silently dropped" here.
    assert "LIED       answered unfiltered" not in printed
    assert "DROPPED    words ignored" not in printed


def test_partial_signal_reports_the_gap_instead_of_full_coverage(tmp_path, monkeypatch, capsys):
    exit_code, document = _run_sweep(
        tmp_path,
        monkeypatch,
        seeds=[CONTROL, OTHER_CONTROL],
        answers={
            CONTROL: _answer(value=1),
            FILTERED: _answer(value=2),
            OTHER_CONTROL: _refusal("no_data"),
            OTHER_FILTERED: _refusal("no_data"),
        },
    )
    summary = document["summary"]
    printed = capsys.readouterr().out
    verdicts = {row["seed"]: row["verdict"] for row in document["rows"]}

    assert exit_code == sweep.EXIT_PASS
    assert summary["status"] == sweep.STATUS_PASS_WITH_GAPS
    assert verdicts["seed_0"] == sweep.APPLIED
    assert verdicts["seed_1"] == sweep.NO_SIGNAL
    assert summary["comparable_comparisons"] == 1
    assert summary["no_signal_comparisons"] == 1
    assert summary["configured_comparisons"] == 2
    assert "covers the 1 comparable rows only" in printed
    assert "full 2-row configured matrix" in printed
    assert "are not evidence that those filters are honest" in printed


def test_a_lie_fails_the_run(tmp_path, monkeypatch):
    exit_code, document = _run_sweep(
        tmp_path,
        monkeypatch,
        seeds=[CONTROL],
        answers={
            CONTROL: _answer(value=1),
            FILTERED: _answer(value=1, badges=[{"label": "Last N games", "value": "10"}]),
        },
    )
    summary = document["summary"]

    assert exit_code == sweep.EXIT_FAIL
    assert summary["status"] == sweep.STATUS_FAIL
    assert summary["verdict_counts"][sweep.LIED] == 1


def test_a_filtered_execution_error_cannot_exit_clean(tmp_path, monkeypatch):
    exit_code, document = _run_sweep(
        tmp_path,
        monkeypatch,
        seeds=[CONTROL],
        answers={CONTROL: _answer(), FILTERED: RuntimeError("filtered blew up")},
    )
    summary = document["summary"]
    row = document["rows"][0]

    assert exit_code == sweep.EXIT_FAIL
    assert summary["status"] == sweep.STATUS_FAIL
    assert summary["verdict_counts"][sweep.ERROR] == 1
    assert row["error_source"] == "filtered"
    assert "RuntimeError: filtered blew up" in row["error"]


def test_a_control_execution_error_cannot_be_counted_applied(tmp_path, monkeypatch):
    exit_code, document = _run_sweep(
        tmp_path,
        monkeypatch,
        seeds=[CONTROL],
        answers={CONTROL: RuntimeError("control blew up"), FILTERED: _answer()},
    )
    summary = document["summary"]
    row = document["rows"][0]

    assert exit_code == sweep.EXIT_FAIL
    assert summary["status"] == sweep.STATUS_FAIL
    assert summary["verdict_counts"][sweep.ERROR] == 1
    assert summary["verdict_counts"][sweep.APPLIED] == 0
    assert row["verdict"] == sweep.ERROR
    assert row["error_source"] == "control"
    assert "RuntimeError: control blew up" in row["error"]


def test_a_filtered_system_error_envelope_cannot_exit_clean(tmp_path, monkeypatch):
    exit_code, document = _run_sweep(
        tmp_path,
        monkeypatch,
        seeds=[CONTROL],
        answers={CONTROL: _answer(), FILTERED: _system_error("error")},
    )
    summary = document["summary"]
    row = document["rows"][0]

    assert exit_code == sweep.EXIT_FAIL
    assert summary["status"] == sweep.STATUS_FAIL
    assert summary["verdict_counts"][sweep.ERROR] == 1
    assert summary["verdict_counts"][sweep.REFUSED] == 0
    assert row["verdict"] == sweep.ERROR
    assert row["verdict"] != sweep.REFUSED
    assert row["error_source"] == "filtered"
    assert row["error_kind"] == sweep.RETURNED_ERROR_STATUS
    # The returned envelope is preserved, not flattened into a crash message.
    assert row["filtered"]["status"] == "error"
    assert row["filtered"]["reason"] == "error"
    assert "result_status=error" in row["error"]


def test_a_control_system_error_envelope_cannot_be_a_gap_or_applied(tmp_path, monkeypatch):
    exit_code, document = _run_sweep(
        tmp_path,
        monkeypatch,
        seeds=[CONTROL],
        answers={CONTROL: _system_error("unrouted"), FILTERED: _answer()},
    )
    summary = document["summary"]
    row = document["rows"][0]

    assert exit_code == sweep.EXIT_FAIL
    assert summary["status"] == sweep.STATUS_FAIL
    assert summary["verdict_counts"][sweep.ERROR] == 1
    assert summary["verdict_counts"][sweep.NO_SIGNAL] == 0
    assert summary["verdict_counts"][sweep.APPLIED] == 0
    assert row["verdict"] == sweep.ERROR
    assert row["verdict"] not in (sweep.NO_SIGNAL, sweep.APPLIED)
    assert row["error_source"] == "control"
    assert row["error_kind"] == sweep.RETURNED_ERROR_STATUS
    assert row["control"]["status"] == "error"
    assert row["control"]["reason"] == "unrouted"
    assert "result_reason=unrouted" in row["error"]


def test_a_system_error_outranks_a_run_that_otherwise_had_no_signal(tmp_path, monkeypatch):
    exit_code, document = _run_sweep(
        tmp_path,
        monkeypatch,
        seeds=[CONTROL, OTHER_CONTROL],
        answers={
            CONTROL: _system_error("unrouted"),
            FILTERED: _answer(),
            OTHER_CONTROL: _refusal("no_data"),
            OTHER_FILTERED: _refusal("no_data"),
        },
    )
    summary = document["summary"]

    assert exit_code == sweep.EXIT_FAIL
    assert exit_code != sweep.EXIT_NO_SIGNAL
    assert summary["status"] == sweep.STATUS_FAIL
    assert summary["comparable_comparisons"] == 0


def test_the_error_report_does_not_claim_every_error_row_raised(tmp_path, monkeypatch, capsys):
    _run_sweep(
        tmp_path,
        monkeypatch,
        seeds=[CONTROL],
        answers={CONTROL: _answer(), FILTERED: _system_error("error")},
    )
    printed = capsys.readouterr().out

    assert "raised or returned a system-error result" in printed
    assert "CRASHED:" not in printed
    assert sweep.RETURNED_ERROR_STATUS in printed


def test_a_filter_that_only_moves_the_split_table_is_applied(tmp_path, monkeypatch):
    # Against the old partial fingerprint this pair looked identical, so a
    # badge would have made it LIED and no badge would have made it DROPPED.
    control = sr.SplitSummaryResult(summary=FRAME, split_comparison=FRAME)
    filtered = sr.SplitSummaryResult(summary=FRAME, split_comparison=OTHER_FRAME)
    exit_code, document = _run_sweep(
        tmp_path,
        monkeypatch,
        seeds=[CONTROL],
        answers={
            CONTROL: _answer(result=control),
            FILTERED: _answer(result=filtered, badges=[{"label": "Last N games", "value": "10"}]),
        },
    )
    row = document["rows"][0]

    assert row["verdict"] == sweep.APPLIED
    assert row["verdict"] not in (sweep.LIED, sweep.DROPPED)
    assert row["fingerprint_match"] is False
    assert row["control"]["sections"] == ["split_comparison", "summary"]
    assert exit_code == sweep.EXIT_PASS
    assert document["summary"]["status"] == sweep.STATUS_PASS


def test_an_unchanged_split_result_behind_a_badge_is_still_a_lie(tmp_path, monkeypatch):
    same = sr.SplitSummaryResult(summary=FRAME, split_comparison=FRAME)
    exit_code, document = _run_sweep(
        tmp_path,
        monkeypatch,
        seeds=[CONTROL],
        answers={
            CONTROL: _answer(result=same),
            FILTERED: _answer(result=same, badges=[{"label": "Last N games", "value": "10"}]),
        },
    )
    row = document["rows"][0]

    assert row["verdict"] == sweep.LIED
    assert row["fingerprint_match"] is True
    assert exit_code == sweep.EXIT_FAIL


def test_a_positive_count_control_is_comparable(tmp_path, monkeypatch):
    exit_code, document = _run_sweep(
        tmp_path,
        monkeypatch,
        seeds=[CONTROL],
        answers={
            CONTROL: _answer(result=sr.CountResult(count=7, games=FRAME)),
            FILTERED: _answer(result=sr.CountResult(count=3, games=OTHER_FRAME)),
        },
    )
    row = document["rows"][0]

    assert row["control"]["populated"] is True
    assert row["verdict"] == sweep.APPLIED
    assert exit_code == sweep.EXIT_PASS


def test_a_zero_count_control_leaves_no_signal(tmp_path, monkeypatch):
    exit_code, document = _run_sweep(
        tmp_path,
        monkeypatch,
        seeds=[CONTROL],
        answers={
            CONTROL: _answer(result=sr.CountResult(count=0)),
            FILTERED: _answer(result=sr.CountResult(count=0)),
        },
    )
    row = document["rows"][0]

    assert row["control"]["populated"] is False
    assert row["verdict"] == sweep.NO_SIGNAL
    assert row["no_signal_reason"] == "control_empty_result"
    assert exit_code == sweep.EXIT_NO_SIGNAL


def test_a_fully_comparable_clean_run_passes(tmp_path, monkeypatch):
    exit_code, document = _run_sweep(
        tmp_path,
        monkeypatch,
        seeds=[CONTROL, OTHER_CONTROL],
        answers={
            CONTROL: _answer(value=1),
            FILTERED: _answer(value=2),
            OTHER_CONTROL: _answer(value=3),
            OTHER_FILTERED: _refusal("filter_not_supported"),
        },
    )
    summary = document["summary"]

    assert exit_code == sweep.EXIT_PASS
    assert summary["status"] == sweep.STATUS_PASS
    assert summary["comparable_comparisons"] == 2
    assert summary["no_signal_comparisons"] == 0
    assert summary["verdict_counts"][sweep.APPLIED] == 1
    assert summary["verdict_counts"][sweep.REFUSED] == 1


def test_dropped_rows_are_reported_without_failing_the_run(tmp_path, monkeypatch):
    exit_code, document = _run_sweep(
        tmp_path,
        monkeypatch,
        seeds=[CONTROL],
        answers={CONTROL: _answer(value=1), FILTERED: _answer(value=1)},
    )
    summary = document["summary"]

    assert summary["verdict_counts"][sweep.DROPPED] == 1
    assert summary["status"] == sweep.STATUS_PASS
    assert exit_code == sweep.EXIT_PASS


def test_json_evidence_carries_the_full_run_and_row_detail(tmp_path, monkeypatch):
    exit_code, document = _run_sweep(
        tmp_path,
        monkeypatch,
        seeds=[CONTROL, OTHER_CONTROL],
        answers={
            CONTROL: _answer(value=1),
            FILTERED: _answer(value=2),
            OTHER_CONTROL: _refusal("no_data"),
            OTHER_FILTERED: _refusal("no_data"),
        },
    )
    summary = document["summary"]

    assert document["schema_version"] == sweep.JSON_SCHEMA_VERSION
    assert summary["exit_code"] == exit_code
    assert set(summary["verdict_counts"]) == set(sweep.VERDICTS)
    assert summary["data_generation"]
    assert summary["config_sha256"]
    assert summary["executed_comparisons"] == len(document["rows"])
    assert (
        summary["comparable_comparisons"]
        + summary["verdict_counts"][sweep.NO_SIGNAL]
        + summary["verdict_counts"][sweep.ERROR]
        == summary["executed_comparisons"]
    )

    applied = next(row for row in document["rows"] if row["verdict"] == sweep.APPLIED)
    assert applied["control"]["status"] == "ok"
    assert applied["control"]["populated"] is True
    assert applied["filtered"]["status"] == "ok"
    assert applied["fingerprint_match"] is False
    assert applied["route"] == "season_leaders"

    gap = next(row for row in document["rows"] if row["verdict"] == sweep.NO_SIGNAL)
    assert gap["no_signal_reason"] == "control_no_result:no_data"
    assert gap["control"]["status"] == "no_result"
    assert gap["control"]["reason"] == "no_data"
    assert gap["comparable"] is False


def test_run_status_never_turns_an_untested_matrix_into_a_pass():
    counts = {verdict: 0 for verdict in sweep.VERDICTS}

    assert sweep.run_status({**counts, sweep.NO_SIGNAL: 5}, comparable=0) == sweep.STATUS_NO_SIGNAL
    assert (
        sweep.run_status({**counts, sweep.NO_SIGNAL: 5}, comparable=1)
        == sweep.STATUS_PASS_WITH_GAPS
    )
    assert sweep.run_status({**counts, sweep.APPLIED: 5}, comparable=5) == sweep.STATUS_PASS
    assert sweep.run_status({**counts, sweep.LIED: 1}, comparable=5) == sweep.STATUS_FAIL
    assert sweep.run_status({**counts, sweep.ERROR: 1}, comparable=5) == sweep.STATUS_FAIL
    # An error outranks an otherwise empty run: it is a verified defect.
    assert sweep.run_status({**counts, sweep.ERROR: 1}, comparable=0) == sweep.STATUS_FAIL
